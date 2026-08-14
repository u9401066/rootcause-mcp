"""
Evidence Management Handlers.

Handles all evidence-related MCP tool calls.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from rootcause_mcp.application.server_state import ServerState


class EvidenceHandlers:
    """Handlers for evidence management tools (thin wrapper around Orchestrator)."""

    def __init__(self, server_state: ServerState) -> None:
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
        orch = await self._state.get_or_create_orchestrator(session_id)

        # Delegate to orchestrator
        evidence = orch.add_evidence(
            content=args["content"],
            evidence_type=args.get("evidence_type", "DOCUMENT"),
            source_document=args.get("source_document"),
            source_location=args.get("source_location"),
            raw_snippet=args.get("raw_snippet"),
            content_hash=args.get("content_hash"),
            extraction_method=args.get("extraction_method"),
            collected_by=args.get("collected_by", "agent"),
            clinical_strength=args.get("clinical_strength", "MODERATE"),
            source_reliability=args.get("source_reliability", "GRADE_B"),
            clinical_context=args.get("clinical_context"),
            auto_verify=args.get("auto_verify", True),
        )
        await self._state.persist_orchestrator(session_id)

        guidance = orch.get_guidance()

        return {
            "status": "success",
            "evidence_id": evidence.id.value,
            "session_id": session_id,
            "quality_score": evidence.quality.overall_score,
            "verified": evidence.verified,
            "verification_method": evidence.verification_method,
            "matched_lines": evidence.matched_lines,
            "content_hash": evidence.source.content_hash,
            "total_evidence_in_session": len(orch.evidence_store),
            "guidance": guidance.model_dump(mode="json"),
        }

    async def handle_get_evidence(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle rc_get_evidence tool call (delegates to Orchestrator)."""
        session_id = args["session_id"]
        evidence_id = args["evidence_id"]

        orch = await self._state.get_orchestrator(session_id)
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
        raw_snippet = args.get("raw_snippet")
        document_id = args.get("document_id")

        orch = await self._state.get_orchestrator(session_id)
        if not orch:
            return {
                "status": "not_found",
                "message": f"No orchestrator found for session {session_id}",
            }

        try:
            verified_evidence, match = orch.verify_evidence(
                evidence_id=evidence_id,
                verified_by=verified_by,
                raw_snippet=raw_snippet,
                document_id=document_id,
            )
        except KeyError as e:
            return {
                "status": "not_found",
                "message": str(e),
            }

        await self._state.persist_orchestrator(session_id)
        guidance = orch.get_guidance()

        return {
            "status": "success",
            "evidence_id": evidence_id,
            "verified": verified_evidence.verified,
            "verified_by": verified_by,
            "verification_method": verified_evidence.verification_method,
            "matched_lines": verified_evidence.matched_lines,
            "content_hash": verified_evidence.source.content_hash,
            "provenance_match": match.to_dict() if match else None,
            "verification_timestamp": verified_evidence.verification_timestamp.isoformat()
            if verified_evidence.verification_timestamp
            else None,
            "guidance": guidance.model_dump(mode="json"),
        }
