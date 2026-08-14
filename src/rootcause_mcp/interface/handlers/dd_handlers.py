"""
Differential Diagnosis Handlers.

Handles all DD-related MCP tool calls.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rootcause_mcp.domain.entities.hypothesis import HypothesisStatus

if TYPE_CHECKING:
    from rootcause_mcp.application.server_state import ServerState


class DDHandlers:
    """Handlers for differential diagnosis tools (thin wrapper around Orchestrator)."""

    def __init__(self, server_state: ServerState) -> None:
        """
        Initialize DD handlers with shared server state.

        Args:
            server_state: ServerState instance for accessing Orchestrators
        """
        self._state = server_state

    async def handle(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Route DD tool calls to appropriate methods."""
        if tool_name == "rc_propose_hypothesis":
            return await self.handle_propose_hypothesis(arguments)
        elif tool_name == "rc_link_evidence_to_hypothesis":
            return await self.handle_link_evidence(arguments)
        elif tool_name == "rc_get_differential_diagnosis":
            return await self.handle_get_differential_diagnosis(arguments)
        elif tool_name == "rc_exclude_hypothesis":
            return await self.handle_exclude_hypothesis(arguments)
        else:
            raise ValueError(f"Unknown DD tool: {tool_name}")

    async def handle_propose_hypothesis(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle rc_propose_hypothesis tool call (delegates to Orchestrator)."""
        session_id = args["session_id"]

        # Get or create orchestrator
        orch = await self._state.get_or_create_orchestrator(session_id)

        # Delegate to orchestrator
        hypothesis = orch.propose_hypothesis(
            diagnosis=args["diagnosis"],
            icd10_code=args.get("icd10_code"),
            snomed_code=args.get("snomed_code"),
            prior_probability=args.get("prior_probability", 0.1),
            rationale=args["clinical_reasoning"],
            inclusion_criteria=args.get("inclusion_criteria"),
            exclusion_criteria=args.get("exclusion_criteria"),
        )
        await self._state.persist_orchestrator(session_id)
        guidance = orch.get_guidance()

        return {
            "status": "success",
            "hypothesis_id": hypothesis.id.value,
            "session_id": session_id,
            "diagnosis": hypothesis.diagnosis.display,
            "prior_probability": hypothesis.prior_probability,
            "differential_diagnoses_considered": args.get(
                "differential_diagnoses_considered", []
            ),
            "uncertainty_factors": args.get("uncertainty_factors", []),
            "guidance": guidance.model_dump(mode="json"),
        }

    async def handle_link_evidence(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle rc_link_evidence_to_hypothesis tool call (delegates to Orchestrator)."""
        session_id = args["session_id"]
        evidence_id = args["evidence_id"]
        hypothesis_id = args["hypothesis_id"]
        likelihood_ratio = args.get("likelihood_ratio", 1.0)
        supports = args.get("supports", True)

        orch = await self._state.get_orchestrator(session_id)
        if not orch:
            return {
                "status": "not_found",
                "message": f"No orchestrator found for session {session_id}",
            }

        # Delegate to orchestrator (performs Bayesian update)
        try:
            updated_hypothesis = orch.link_evidence_to_hypothesis(
                evidence_id=evidence_id,
                hypothesis_id=hypothesis_id,
                likelihood_ratio=likelihood_ratio,
                supports=supports,
                rationale=args.get("rationale", ""),
            )
            await self._state.persist_orchestrator(session_id)
        except KeyError as e:
            return {
                "status": "not_found",
                "message": str(e),
            }

        guidance = orch.get_guidance()

        return {
            "status": "success",
            "hypothesis_id": hypothesis_id,
            "diagnosis": updated_hypothesis.diagnosis.display,
            "posterior_probability": updated_hypothesis.current_probability,
            "likelihood_ratio": likelihood_ratio,
            "supports": supports,
            "guidance": guidance.model_dump(mode="json"),
        }

    async def handle_get_differential_diagnosis(
        self, args: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle rc_get_differential_diagnosis tool call (delegates to Orchestrator)."""
        session_id = args["session_id"]
        status_filter = args.get("status_filter", "ACTIVE")
        min_probability = args.get("min_probability", 0.01)

        orch = await self._state.get_orchestrator(session_id)
        if not orch:
            return {
                "status": "success",
                "session_id": session_id,
                "hypotheses": [],
                "total": 0,
            }

        # Delegate to orchestrator
        status_enum = HypothesisStatus(status_filter) if status_filter else None
        hypotheses = orch.get_differential_diagnosis(
            status_filter=status_enum,
            min_probability=min_probability,
        )
        guidance = orch.get_guidance()

        return {
            "status": "success",
            "session_id": session_id,
            "hypotheses": [h.model_dump(mode="json") for h in hypotheses],
            "total": len(hypotheses),
            "guidance": guidance.model_dump(mode="json"),
        }

    async def handle_exclude_hypothesis(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle rc_exclude_hypothesis tool call (delegates to Orchestrator)."""
        session_id = args["session_id"]
        hypothesis_id = args["hypothesis_id"]

        orch = await self._state.get_orchestrator(session_id)
        if not orch:
            return {
                "status": "not_found",
                "message": f"No orchestrator found for session {session_id}",
            }

        try:
            excluded_hypothesis = orch.exclude_hypothesis(
                hypothesis_id,
                excluded_by=args["excluded_by"],
                reason=args["exclusion_reason"],
            )
        except KeyError:
            return {
                "status": "not_found",
                "message": f"Hypothesis {hypothesis_id} not found in session {session_id}",
            }
        await self._state.persist_orchestrator(session_id)
        guidance = orch.get_guidance()

        return {
            "status": "success",
            "hypothesis_id": hypothesis_id,
            "diagnosis": excluded_hypothesis.diagnosis.display,
            "hypothesis_status": excluded_hypothesis.status.value,
            "exclusion_reason": args["exclusion_reason"],
            "guidance": guidance.model_dump(mode="json"),
        }
