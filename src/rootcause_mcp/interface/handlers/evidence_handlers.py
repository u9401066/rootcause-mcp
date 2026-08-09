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
    """Handlers for evidence management tools."""

    def __init__(self) -> None:
        """Initialize evidence handlers with in-memory storage."""
        # session_id → {evidence_id → Evidence}
        self._evidence_store: dict[str, dict[str, Evidence]] = {}

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
        """Handle rc_add_evidence tool call."""
        session_id = args["session_id"]

        # Get or create session evidence store
        if session_id not in self._evidence_store:
            self._evidence_store[session_id] = {}

        # Create quality grading
        quality = EvidenceQuality(
            strength=EvidenceStrength(args.get("clinical_strength", "MODERATE")),
            reliability=EvidenceReliability(args.get("source_reliability", "GRADE_B")),
        )

        # Create source provenance
        source = EvidenceSource(
            document_id=args.get("source_document"),
            location=args.get("source_location"),
            collected_by=args.get("collected_by", "agent"),
            source_system=None,
        )

        # Create evidence
        evidence = Evidence(
            content=args["content"],
            evidence_type=EvidenceType(args.get("evidence_type", "DOCUMENT")),
            clinical_context=args.get("clinical_context"),
            quality=quality,
            source=source,
            event_timestamp=None,
            verified=False,
            verifier=None,
            verification_timestamp=None,
        )

        # Store evidence
        self._evidence_store[session_id][evidence.id.value] = evidence

        return {
            "status": "success",
            "evidence_id": evidence.id.value,
            "session_id": session_id,
            "quality_score": quality.overall_score,
            "total_evidence_in_session": len(self._evidence_store[session_id]),
        }

    async def handle_get_evidence(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle rc_get_evidence tool call."""
        session_id = args["session_id"]
        evidence_id = args["evidence_id"]

        if session_id not in self._evidence_store:
            return {
                "status": "not_found",
                "message": f"No evidence found for session {session_id}",
            }

        evidence = self._evidence_store[session_id].get(evidence_id)

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
        """Handle rc_verify_evidence tool call."""
        session_id = args["session_id"]
        evidence_id = args["evidence_id"]
        verified_by = args["verified_by"]

        if session_id not in self._evidence_store:
            return {
                "status": "not_found",
                "message": f"No evidence found for session {session_id}",
            }

        evidence = self._evidence_store[session_id].get(evidence_id)

        if not evidence:
            return {
                "status": "not_found",
                "message": f"Evidence {evidence_id} not found in session {session_id}",
            }

        # Mark as verified
        verified_evidence = evidence.mark_verified(verified_by)
        self._evidence_store[session_id][evidence_id] = verified_evidence

        return {
            "status": "success",
            "evidence_id": evidence_id,
            "verified": True,
            "verified_by": verified_by,
            "verification_timestamp": verified_evidence.verification_timestamp.isoformat() if verified_evidence.verification_timestamp else None,
        }
