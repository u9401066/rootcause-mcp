"""
Differential Diagnosis Handlers.

Handles all DD-related MCP tool calls.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

from rootcause_mcp.domain.entities.hypothesis import HypothesisStatus

if TYPE_CHECKING:
    from rootcause_mcp.application.server_state import ServerState


def _parse_direct_likelihood_input(
    args: dict[str, Any],
) -> tuple[float, bool | None]:
    """Parse only a direct LR; legacy weights have no valid conversion."""
    if "weight" in args:
        raise ValueError(
            "weight is no longer accepted because no clinically valid "
            "weight-to-LR conversion exists; migrate to a direct "
            "likelihood_ratio (>1 supports, <1 refutes, 1.0 neutral) "
            "with an explicit rationale"
        )
    try:
        likelihood_ratio = float(args.get("likelihood_ratio", 1.0))
    except (TypeError, ValueError) as exc:
        raise ValueError("likelihood_ratio must be a direct numeric LR") from exc
    if (
        not math.isfinite(likelihood_ratio)
        or likelihood_ratio <= 0
        or likelihood_ratio > 100
    ):
        raise ValueError("likelihood_ratio must be finite and in (0, 100]")
    if "supports" in args:
        supports = args["supports"]
        if supports is not None and not isinstance(supports, bool):
            raise ValueError("supports must be true, false, or null")
        return likelihood_ratio, supports
    if "direction" in args:
        return likelihood_ratio, _parse_likelihood_direction(args["direction"])
    if likelihood_ratio > 1.0:
        return likelihood_ratio, True
    if likelihood_ratio < 1.0:
        return likelihood_ratio, False
    return likelihood_ratio, None


def _parse_likelihood_direction(value: Any) -> bool | None:
    """Normalize one explicit direction without coercing arbitrary values."""
    direction = str(value).upper()
    if direction in {"SUPPORTS", "SUPPORT", "CONFIRMS"}:
        return True
    if direction in {"REFUTES", "CONTRADICTS", "RULE_OUT", "EXCLUDE"}:
        return False
    if direction == "NEUTRAL":
        return None
    raise ValueError("direction must be SUPPORTS, REFUTES, or NEUTRAL")


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
        elif tool_name == "rc_audit_differential_breadth":
            return await self.handle_audit_differential_breadth(arguments)
        elif tool_name == "rc_link_evidence_to_hypothesis":
            return await self.handle_link_evidence(arguments)
        elif tool_name == "rc_select_leading_hypothesis":
            return await self.handle_select_leading_hypothesis(arguments)
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

        rationale = (
            args.get("clinical_reasoning")
            or args.get("rationale")
            or args.get("reasoning")
            or ""
        )

        # Delegate to orchestrator
        try:
            hypothesis = orch.propose_hypothesis(
                diagnosis=args["diagnosis"],
                icd10_code=args.get("icd10_code"),
                snomed_code=args.get("snomed_code"),
                prior_probability=args.get("prior_probability", 0.5),
                rationale=rationale,
                inclusion_criteria=args.get("inclusion_criteria"),
                exclusion_criteria=args.get("exclusion_criteria"),
                must_not_miss=args.get("must_not_miss", False),
                mechanism_category=args.get("mechanism_category", "UNKNOWN"),
                diagnostic_role=args.get("diagnostic_role", "UNKNOWN"),
                certainty=args.get("certainty", "UNKNOWN"),
                reasoning_basis=args.get("reasoning_basis", "UNKNOWN"),
                alternatives_considered=args.get(
                    "differential_diagnoses_considered", []
                ),
                uncertainty_factors=args.get("uncertainty_factors", []),
                confidence_rationale=args.get("confidence_rationale", ""),
                planned_tests=args.get("planned_tests", []),
            )
        except (TypeError, ValueError) as exc:
            return {"status": "error", "message": str(exc), "session_id": session_id}
        await self._state.persist_orchestrator(session_id)
        guidance = orch.get_guidance()

        return {
            "status": "success",
            "hypothesis_id": hypothesis.id.value,
            "session_id": session_id,
            "diagnosis": hypothesis.diagnosis.display,
            "prior_probability": hypothesis.prior_probability,
            "probability_semantics": "UNCALIBRATED_COMPATIBILITY_ONLY",
            "clinical_probability_established": False,
            "must_not_miss": hypothesis.must_not_miss,
            "mechanism_category": hypothesis.mechanism_category.value,
            "diagnostic_role": hypothesis.diagnostic_role.value,
            "certainty": hypothesis.certainty.value,
            "reasoning_basis": hypothesis.reasoning_basis.value,
            "differential_diagnoses_considered": hypothesis.alternatives_considered,
            "uncertainty_factors": hypothesis.uncertainty_factors,
            "confidence_rationale": hypothesis.confidence_rationale,
            "planned_tests": [
                item.model_dump(mode="json") for item in hypothesis.planned_tests
            ],
            "guidance": guidance.model_dump(mode="json"),
        }

    async def handle_select_leading_hypothesis(
        self,
        args: dict[str, Any],
    ) -> dict[str, Any]:
        """Persist an explicit leading diagnosis selection and its audit history."""
        session_id = args["session_id"]
        orch = await self._state.get_orchestrator(session_id)
        if orch is None:
            return {
                "status": "not_found",
                "message": f"No orchestrator found for session {session_id}",
            }
        try:
            selection = orch.select_leading_hypothesis(
                str(args["hypothesis_id"]),
                reason=str(args["reason"]),
                changed_by=str(args["changed_by"]),
            )
            await self._state.persist_orchestrator(session_id)
        except KeyError as exc:
            return {"status": "not_found", "message": str(exc)}
        except (TypeError, ValueError) as exc:
            return {"status": "error", "message": str(exc)}
        return {
            "status": "success",
            "session_id": session_id,
            "leading_hypothesis_id": selection.hypothesis_id,
            "selection": selection.model_dump(mode="json"),
            "selection_history": [
                item.model_dump(mode="json")
                for item in orch.get_leading_hypothesis_selection_history()
            ],
        }

    async def handle_audit_differential_breadth(
        self, args: dict[str, Any]
    ) -> dict[str, Any]:
        """Persist a typed, syndrome-appropriate systematic breadth audit."""
        session_id = args["session_id"]
        orch = await self._state.get_orchestrator(session_id)
        if orch is None:
            return {
                "status": "not_found",
                "message": f"No orchestrator found for session {session_id}",
            }
        audit_payload = args.get("audit") or args.get("breadth_audit")
        if not isinstance(audit_payload, dict):
            return {
                "status": "error",
                "message": "audit/breadth_audit must be a typed object",
                "session_id": session_id,
            }
        try:
            audit = orch.record_differential_breadth_audit(audit_payload)
            await self._state.persist_orchestrator(session_id)
        except (TypeError, ValueError) as exc:
            return {"status": "error", "message": str(exc), "session_id": session_id}
        guidance = orch.get_guidance()
        return {
            "status": "success",
            "session_id": session_id,
            "differential_breadth_audit": audit.model_dump(mode="json"),
            "guidance": guidance.model_dump(mode="json"),
        }

    async def handle_link_evidence(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle rc_link_evidence_to_hypothesis tool call (delegates to Orchestrator)."""
        session_id = args["session_id"]
        evidence_id = args["evidence_id"]
        hypothesis_id = args["hypothesis_id"]

        try:
            likelihood_ratio, supports = _parse_direct_likelihood_input(args)
        except ValueError as exc:
            return {
                "status": "error",
                "session_id": session_id,
                "message": str(exc),
            }

        rationale = (
            args.get("rationale")
            or args.get("reasoning")
            or args.get("clinical_reasoning")
            or ""
        )
        if likelihood_ratio != 1.0 and not rationale.strip():
            return {
                "status": "error",
                "message": (
                    "A non-neutral likelihood_ratio requires an explicit clinical "
                    "rationale and calibration/source limitation"
                ),
            }

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
                rationale=rationale,
                calibration_status=args.get("calibration_status"),
                calibration_source_ref=args.get("calibration_source_ref"),
            )
            await self._state.persist_orchestrator(session_id)
        except KeyError as e:
            return {
                "status": "not_found",
                "message": str(e),
            }
        except ValueError as e:
            return {
                "status": "error",
                "message": str(e),
            }

        guidance = orch.get_guidance()

        return {
            "status": "success",
            "hypothesis_id": hypothesis_id,
            "diagnosis": updated_hypothesis.diagnosis.display,
            "posterior_probability": updated_hypothesis.current_probability,
            "probability_semantics": "UNCALIBRATED_COMPATIBILITY_ONLY",
            "clinical_probability_established": False,
            "likelihood_ratio": likelihood_ratio,
            "applied_likelihood_ratio": likelihood_ratio,
            "supports": supports,
            "calibration_status": args.get("calibration_status"),
            "calibration_source_ref": args.get("calibration_source_ref"),
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
                "leading_hypothesis_id": None,
                "ordering_semantics": "WORKING_LEDGER_ORDER",
                "probability_semantics": "UNCALIBRATED_COMPATIBILITY_ONLY",
                "clinical_probability_established": False,
            }

        # Delegate to orchestrator
        status_enum = HypothesisStatus(status_filter) if status_filter else None
        hypotheses = orch.get_differential_diagnosis(
            status_filter=status_enum,
            min_probability=min_probability,
        )
        guidance = orch.get_guidance()
        leading_hypothesis_id = orch.get_leading_hypothesis_id()

        return {
            "status": "success",
            "session_id": session_id,
            "hypotheses": [
                {
                    **h.model_dump(mode="json"),
                    "is_explicit_leading": h.id.value == leading_hypothesis_id,
                    "probability_semantics": "UNCALIBRATED_COMPATIBILITY_ONLY",
                    "clinical_probability_established": False,
                }
                for h in hypotheses
            ],
            "total": len(hypotheses),
            "leading_hypothesis_id": leading_hypothesis_id,
            "ordering_semantics": "WORKING_LEDGER_ORDER",
            "probability_semantics": "UNCALIBRATED_COMPATIBILITY_ONLY",
            "clinical_probability_established": False,
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
