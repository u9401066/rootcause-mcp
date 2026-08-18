"""
Evidence Management Handlers.

Handles all evidence-related MCP tool calls.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from rootcause_mcp.domain.services.provenance_verifier import (
    ProvenanceMatch,
    ProvenanceVerifier,
)
from rootcause_mcp.domain.value_objects.clinical_temporal import (
    resolve_clinical_temporal,
)

if TYPE_CHECKING:
    from rootcause_mcp.application.server_state import ServerState
    from rootcause_mcp.domain.repositories.session_repository import SessionRepository
    from rootcause_mcp.domain.value_objects.case_manifest import CaseInputManifest


@dataclass(frozen=True, slots=True)
class _VerificationSource:
    """Physical target resolved without changing the stable ledger identity."""

    reference: str | None
    expected_sha256: str | None = None
    manifest_bound: bool = False
    failure: ProvenanceMatch | None = None


class EvidenceHandlers:
    """Handlers for evidence management tools (thin wrapper around Orchestrator)."""

    def __init__(
        self,
        server_state: ServerState,
        *,
        session_repository: SessionRepository | None = None,
        provenance_verifier: ProvenanceVerifier | None = None,
    ) -> None:
        """
        Initialize evidence handlers with shared server state.

        Args:
            server_state: ServerState instance for accessing Orchestrators
            session_repository: Optional RCA session repository used to resolve
                stable manifest document IDs
            provenance_verifier: Optional verifier override for focused tests
        """
        self._state = server_state
        self._session_repo = session_repository
        self._provenance_verifier = provenance_verifier or ProvenanceVerifier()

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

        try:
            temporal = resolve_clinical_temporal(
                args.get("temporal"),
                args.get("event_timestamp"),
            )
        except (ValidationError, ValueError) as exc:
            return {
                "status": "error",
                "message": str(exc),
            }

        # Get or create orchestrator
        orch = await self._state.get_or_create_orchestrator(session_id)

        auto_verify = bool(args.get("auto_verify", True))

        # Keep the stable document ID in the evidence ledger. Physical
        # verification is performed separately against the manifest source URI.
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
            temporal=temporal,
            event_timestamp=temporal.source_aware_instant,
            auto_verify=False,
        )
        provenance_match: ProvenanceMatch | None = None
        if auto_verify and evidence.source.document_id:
            verification_source = self._resolve_verification_source(
                session_id,
                evidence.source.document_id,
            )
            if verification_source.failure is not None:
                provenance_match = verification_source.failure
                evidence = orch.record_failed_provenance_verification(
                    evidence.id.value,
                    provenance_match,
                )
            elif verification_source.reference is not None:
                evidence, provenance_match = orch.verify_evidence(
                    evidence_id=evidence.id.value,
                    verified_by="SYSTEM_PROVENANCE_VERIFIER",
                    raw_snippet=args.get("raw_snippet"),
                    document_id=verification_source.reference,
                    expected_source_sha256=verification_source.expected_sha256,
                    fail_closed=verification_source.manifest_bound,
                    provenance_verifier=self._provenance_verifier,
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
            "match_type": (
                provenance_match.match_type if provenance_match is not None else None
            ),
            "provenance_match": (
                provenance_match.to_dict() if provenance_match is not None else None
            ),
            "matched_lines": evidence.matched_lines,
            "content_hash": evidence.source.content_hash,
            "temporal": evidence.temporal.model_dump(mode="json"),
            "event_timestamp": (
                evidence.event_timestamp.isoformat()
                if evidence.event_timestamp is not None
                else None
            ),
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
        verified_by = args.get("verified_by", "agent")
        raw_snippet = args.get("raw_snippet")
        document_id = args.get("document_id")
        manual_confirmation = args.get("manual_confirmation", False)

        orch = await self._state.get_orchestrator(session_id)
        if not orch:
            return {
                "status": "not_found",
                "message": f"No orchestrator found for session {session_id}",
            }

        evidence = orch.get_evidence(evidence_id)
        if evidence is None:
            return {
                "status": "not_found",
                "message": f"Evidence {evidence_id} not found in session {session_id}",
            }

        manifest = self._get_source_manifest(session_id)
        source_document_id = evidence.source.document_id
        if (
            manifest is not None
            and document_id is not None
            and document_id != source_document_id
        ):
            verification_source = _VerificationSource(
                reference=None,
                manifest_bound=True,
                failure=ProvenanceMatch(
                    is_verified=False,
                    match_type="SOURCE_DOCUMENT_ID_MISMATCH",
                    diagnostics=(
                        "Manifest-bound evidence must be re-verified against its "
                        "original stable source document ID."
                    ),
                ),
            )
        else:
            stable_document_id = document_id or source_document_id
            verification_source = self._resolve_verification_source(
                session_id,
                stable_document_id,
                manifest=manifest,
            )
        match: ProvenanceMatch | None
        if verification_source.failure is not None:
            match = verification_source.failure
            verified_evidence = orch.record_failed_provenance_verification(
                evidence_id,
                match,
            )
        else:
            verified_evidence, match = orch.verify_evidence(
                evidence_id=evidence_id,
                verified_by=verified_by,
                raw_snippet=raw_snippet,
                document_id=verification_source.reference,
                manual_confirmation=manual_confirmation,
                expected_source_sha256=verification_source.expected_sha256,
                fail_closed=verification_source.manifest_bound,
                provenance_verifier=self._provenance_verifier,
            )

        await self._state.persist_orchestrator(session_id)
        guidance = orch.get_guidance()

        return {
            "status": "success",
            "evidence_id": evidence_id,
            "verified": verified_evidence.verified,
            "verified_by": verified_evidence.verifier,
            "verification_method": verified_evidence.verification_method,
            "match_type": match.match_type if match is not None else None,
            "matched_lines": verified_evidence.matched_lines,
            "content_hash": verified_evidence.source.content_hash,
            "provenance_match": match.to_dict() if match else None,
            "verification_timestamp": verified_evidence.verification_timestamp.isoformat()
            if verified_evidence.verification_timestamp
            else None,
            "guidance": guidance.model_dump(mode="json"),
        }

    def _resolve_verification_source(
        self,
        session_id: str,
        stable_document_id: str | None,
        *,
        manifest: CaseInputManifest | None = None,
    ) -> _VerificationSource:
        """Map a manifest ID to an approved local source without changing it."""
        if not stable_document_id:
            return _VerificationSource(reference=None)
        if self._session_repo is None:
            return _VerificationSource(reference=stable_document_id)

        manifest = manifest or self._get_source_manifest(session_id)
        if manifest is None:
            return _VerificationSource(reference=stable_document_id)

        source_document = next(
            (
                document
                for document in manifest.documents
                if document.document_id == stable_document_id
            ),
            None,
        )
        if source_document is None:
            return _VerificationSource(
                reference=None,
                manifest_bound=True,
                failure=ProvenanceMatch(
                    is_verified=False,
                    match_type="SOURCE_DOCUMENT_NOT_IN_MANIFEST",
                    diagnostics=(
                        f"Stable document ID '{stable_document_id}' is not registered "
                        "in the session source manifest."
                    ),
                ),
            )

        resolved = self._provenance_verifier.resolve_source_uri(
            source_document.source_uri
        )
        if isinstance(resolved, ProvenanceMatch):
            return _VerificationSource(
                reference=None,
                expected_sha256=source_document.sha256,
                manifest_bound=True,
                failure=resolved,
            )
        return _VerificationSource(
            reference=str(resolved),
            expected_sha256=source_document.sha256,
            manifest_bound=True,
        )

    def _get_source_manifest(self, session_id: str) -> CaseInputManifest | None:
        """Load the pinned manifest when an RCA session repository is available."""
        if self._session_repo is None:
            return None
        session = self._session_repo.get_by_id(session_id)
        return session.get_source_manifest() if session is not None else None
