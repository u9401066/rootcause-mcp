"""
Evidence Management Handlers.

Handles all evidence-related MCP tool calls.
"""

from __future__ import annotations

from typing import Any

from rootcause_mcp.domain.entities.evidence import Evidence, EvidenceSource, EvidenceType
from rootcause_mcp.domain.value_objects.evidence_quality import (
    EvidenceQuality,
    EvidenceReliability,
    EvidenceStrength,
)


class EvidenceHandlers:
    """Handlers for evidence management tools (thin wrapper around Orchestrator)."""

    def __init__(self, server_state: Any) -> None:
        """
        Initialize evidence handlers with shared server state.

        Args:
            server_state: ServerState instance for accessing Orchestrators
        """
        self._state = server_state

    async def handle(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Route evidence tool calls to appropriate methods."""
        if tool_name == "rc_add_evidence":
            return await self.handle_add_evidence(arguments)
        elif tool_name == "rc_get_evidence":
            return await self.handle_get_evidence(arguments)
        elif tool_name == "rc_verify_evidence":
            return await self.handle_verify_evidence(arguments)
        else:
            raise ValueError(f"Unknown evidence tool: {tool_name}")

    async def handle_add_evidence(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle rc_add_evidence tool call (delegates to Orchestrator)."""
        session_id = args["session_id"]

        # Get or create orchestrator
        orch = self._state.get_or_create_orchestrator(session_id)

        # Delegate to orchestrator
        evidence = orch.add_evidence(
            content=args["content"],
            evidence_type=args.get("evidence_type", "DOCUMENT"),
            source_document=args.get("source_document"),
            source_location=args.get("source_location"),
            collected_by=args.get("collected_by", "agent"),
            clinical_strength=args.get("clinical_strength", "MODERATE"),
            source_reliability=args.get("source_reliability", "GRADE_B"),
            clinical_context=args.get("clinical_context"),
        )

        return {
            "status": "success",
            "evidence_id": evidence.id.value,
            "session_id": session_id,
            "quality_score": evidence.quality.overall_score,
            "total_evidence_in_session": len(orch.evidence_store),
        }

    async def handle_get_evidence(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle rc_get_evidence tool call (delegates to Orchestrator)."""
        session_id = args["session_id"]
        evidence_id = args["evidence_id"]

        orch = self._state.get_orchestrator(session_id)
        if not orch:
            return {
                "status": "not_found",
                "message": f"No orchestrator found for session {session_id}",
            }

        evidence = orch.get_evidence(evidence_id)
        if not evidence:
            return {
                "status": "not_found",
                "message": f"Evidence {evidence_id} not found in session {session_id}",
            }

        return {
            "status": "success",
            "evidence": evidence.model_dump(mode="json"),
        }

    async def handle_verify_evidence(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle rc_verify_evidence tool call (delegates to Orchestrator)."""
        session_id = args["session_id"]
        evidence_id = args["evidence_id"]
        verified_by = args["verified_by"]

        orch = self._state.get_orchestrator(session_id)
        if not orch:
            return {
                "status": "not_found",
                "message": f"No orchestrator found for session {session_id}",
            }

        evidence = orch.get_evidence(evidence_id)
        if not evidence:
            return {
                "status": "not_found",
                "message": f"Evidence {evidence_id} not found in session {session_id}",
            }

        # Mark as verified (via orchestrator)
        verified_evidence = evidence.mark_verified(verified_by)
        orch.evidence_store[evidence_id] = verified_evidence

        return {
            "status": "success",
            "evidence_id": evidence_id,
            "verified": True,
            "verified_by": verified_by,
            "verification_timestamp": verified_evidence.verification_timestamp.isoformat() if verified_evidence.verification_timestamp else None,
        }
