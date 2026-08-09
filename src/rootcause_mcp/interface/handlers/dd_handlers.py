"""
Differential Diagnosis Handlers.

Handles all DD-related MCP tool calls.
"""

from __future__ import annotations

from typing import Any

from rootcause_mcp.domain.entities.hypothesis import Hypothesis, HypothesisStatus
from rootcause_mcp.domain.value_objects.clinical_concept import ClinicalConcept, CodingSystem


class DDHandlers:
    """Handlers for differential diagnosis tools."""

    def __init__(self) -> None:
        """Initialize DD handlers with in-memory storage."""
        # session_id → {hypothesis_id → Hypothesis}
        self._hypothesis_store: dict[str, dict[str, Hypothesis]] = {}

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
        """Handle rc_propose_hypothesis tool call."""
        session_id = args["session_id"]

        # Get or create session hypothesis store
        if session_id not in self._hypothesis_store:
            self._hypothesis_store[session_id] = {}

        # Create clinical concept
        if "icd10_code" in args and args["icd10_code"]:
            concept = ClinicalConcept(
                code=args["icd10_code"],
                display=args["diagnosis"],
                system=CodingSystem.ICD_10,
                version=None,
            )
        elif "snomed_code" in args and args["snomed_code"]:
            concept = ClinicalConcept(
                code=args["snomed_code"],
                display=args["diagnosis"],
                system=CodingSystem.SNOMED_CT,
                version=None,
            )
        else:
            concept = ClinicalConcept(
                code=f"CUSTOM-{hash(args['diagnosis']) % 100000:05d}",
                display=args["diagnosis"],
                system=CodingSystem.CUSTOM,
                version=None,
            )

        # Create hypothesis
        hypothesis = Hypothesis(
            diagnosis=concept,
            prior_probability=args.get("prior_probability", 0.1),
            current_probability=args.get("prior_probability", 0.1),
            inclusion_criteria=args.get("inclusion_criteria", []),
            exclusion_criteria=args.get("exclusion_criteria", []),
            created_by="agent",
            clinical_rationale=args["clinical_reasoning"],
        )

        # Store hypothesis
        self._hypothesis_store[session_id][hypothesis.id.value] = hypothesis

        return {
            "status": "success",
            "hypothesis_id": hypothesis.id.value,
            "session_id": session_id,
            "diagnosis": hypothesis.diagnosis.display,
            "prior_probability": hypothesis.prior_probability,
            "differential_diagnoses_considered": args.get("differential_diagnoses_considered", []),
            "uncertainty_factors": args.get("uncertainty_factors", []),
        }

    async def handle_link_evidence(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle rc_link_evidence_to_hypothesis tool call."""
        session_id = args["session_id"]
        evidence_id = args["evidence_id"]
        hypothesis_id = args["hypothesis_id"]
        likelihood_ratio = args.get("likelihood_ratio", 1.0)
        supports = args.get("supports", True)

        if session_id not in self._hypothesis_store:
            return {
                "status": "not_found",
                "message": f"No hypotheses found for session {session_id}",
            }

        hypothesis = self._hypothesis_store[session_id].get(hypothesis_id)

        if not hypothesis:
            return {
                "status": "not_found",
                "message": f"Hypothesis {hypothesis_id} not found in session {session_id}",
            }

        # Perform Bayesian update
        updated_hypothesis = hypothesis.bayesian_update(
            evidence_id=evidence_id,
            likelihood_ratio=likelihood_ratio,
            updated_by="agent",
            supports=supports,
        )

        # Update store
        self._hypothesis_store[session_id][hypothesis_id] = updated_hypothesis

        return {
            "status": "success",
            "hypothesis_id": hypothesis_id,
            "diagnosis": updated_hypothesis.diagnosis.display,
            "prior_probability": hypothesis.current_probability,
            "posterior_probability": updated_hypothesis.current_probability,
            "likelihood_ratio": likelihood_ratio,
            "supports": supports,
        }

    async def handle_get_differential_diagnosis(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle rc_get_differential_diagnosis tool call."""
        session_id = args["session_id"]
        status_filter = args.get("status_filter", "ACTIVE")
        min_probability = args.get("min_probability", 0.01)

        if session_id not in self._hypothesis_store:
            return {
                "status": "success",
                "session_id": session_id,
                "hypotheses": [],
                "total": 0,
            }

        hypotheses = list(self._hypothesis_store[session_id].values())

        # Filter by status
        if status_filter:
            status_enum = HypothesisStatus(status_filter)
            hypotheses = [h for h in hypotheses if h.status == status_enum]

        # Filter by minimum probability
        hypotheses = [h for h in hypotheses if h.current_probability >= min_probability]

        # Sort by probability (descending)
        hypotheses.sort(key=lambda h: h.current_probability, reverse=True)

        return {
            "status": "success",
            "session_id": session_id,
            "hypotheses": [h.model_dump(mode="json") for h in hypotheses],
            "total": len(hypotheses),
        }

    async def handle_exclude_hypothesis(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle rc_exclude_hypothesis tool call."""
        session_id = args["session_id"]
        hypothesis_id = args["hypothesis_id"]

        if session_id not in self._hypothesis_store:
            return {
                "status": "not_found",
                "message": f"No hypotheses found for session {session_id}",
            }

        hypothesis = self._hypothesis_store[session_id].get(hypothesis_id)

        if not hypothesis:
            return {
                "status": "not_found",
                "message": f"Hypothesis {hypothesis_id} not found in session {session_id}",
            }

        # Mark as excluded
        excluded_hypothesis = hypothesis.mark_excluded(
            excluded_by=args["excluded_by"],
            reason=args["exclusion_reason"],
        )

        # Update store
        self._hypothesis_store[session_id][hypothesis_id] = excluded_hypothesis

        return {
            "status": "success",
            "hypothesis_id": hypothesis_id,
            "diagnosis": excluded_hypothesis.diagnosis.display,
            "status": excluded_hypothesis.status.value,
            "exclusion_reason": args["exclusion_reason"],
        }
