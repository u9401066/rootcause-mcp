"""Public-handler coverage for manifest-bound physical provenance."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import pytest

from rootcause_mcp.application.server_state import ServerState
from rootcause_mcp.domain.entities.session import RCASession
from rootcause_mcp.domain.services.provenance_verifier import (
    ProvenanceMatch,
    ProvenanceVerifier,
)
from rootcause_mcp.domain.value_objects.case_manifest import (
    CaseInputManifest,
    SourceDocument,
    SourceIndependenceStatus,
    SourceReviewStatus,
)
from rootcause_mcp.domain.value_objects.enums import CaseType
from rootcause_mcp.infrastructure.persistence.database import Database
from rootcause_mcp.infrastructure.persistence.session_repository import (
    SQLiteSessionRepository,
)
from rootcause_mcp.interface.handlers.evidence_handlers import EvidenceHandlers


@dataclass(slots=True)
class _Harness:
    handler: EvidenceHandlers
    state: ServerState
    session_id: str
    database: Database


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_document(
    document_id: str,
    *,
    independence_status: SourceIndependenceStatus,
    parent_document_id: str | None = None,
    derivation_method: str | None = None,
    source_group_id: str | None = None,
) -> SourceDocument:
    return SourceDocument(
        document_id=document_id,
        source_uri=f"host://case/{document_id}",
        sha256="a" * 64,
        media_type="text/plain",
        source_kind="clinical_note",
        status=SourceReviewStatus.REVIEWED,
        de_identified=True,
        independence_status=independence_status,
        parent_document_id=parent_document_id,
        derivation_method=derivation_method,
        source_group_id=source_group_id,
    )


def test_manifest_accepts_explicit_independent_and_derived_lineage() -> None:
    manifest = CaseInputManifest(
        documents=(
            _source_document(
                "SRC-ROOT",
                independence_status=SourceIndependenceStatus.INDEPENDENT,
                source_group_id="GROUP-ROOT",
            ),
            _source_document(
                "SRC-EXTRACT",
                independence_status=SourceIndependenceStatus.DERIVED,
                parent_document_id="SRC-ROOT",
                derivation_method="local OOXML text extraction",
                source_group_id="GROUP-ROOT",
            ),
        )
    )

    assert manifest.documents[1].parent_document_id == "SRC-ROOT"
    assert manifest.documents[1].independence_status == "derived"


def test_manifest_rejects_missing_or_cyclic_derivation_lineage() -> None:
    with pytest.raises(ValueError, match="not in the manifest"):
        CaseInputManifest(
            documents=(
                _source_document(
                    "SRC-DERIVED",
                    independence_status=SourceIndependenceStatus.DERIVED,
                    parent_document_id="SRC-MISSING",
                    derivation_method="manual transcription",
                ),
            )
        )

    with pytest.raises(ValueError, match="cycles"):
        CaseInputManifest(
            documents=(
                _source_document(
                    "SRC-A",
                    independence_status=SourceIndependenceStatus.DERIVED,
                    parent_document_id="SRC-B",
                    derivation_method="first transform",
                ),
                _source_document(
                    "SRC-B",
                    independence_status=SourceIndependenceStatus.DERIVED,
                    parent_document_id="SRC-A",
                    derivation_method="second transform",
                ),
            )
        )


def _build_harness(
    tmp_path: Path,
    *,
    allowed_root: Path,
    source_uri: str,
    source_sha256: str,
) -> _Harness:
    database = Database(tmp_path / "manifest-provenance.db")
    database.create_tables()
    session_repository = SQLiteSessionRepository(database)
    session = RCASession.create(
        case_type=CaseType.NEAR_MISS,
        case_title="Stable manifest identity provenance",
    )
    session.set_source_manifest(
        CaseInputManifest(
            documents=(
                SourceDocument(
                    document_id="SRC-001",
                    source_uri=source_uri,
                    sha256=source_sha256,
                    media_type="text/plain",
                    source_kind="clinical_note",
                    status=SourceReviewStatus.REVIEWED,
                    de_identified=True,
                ),
            )
        )
    )
    session_repository.save(session)
    state = ServerState()
    return _Harness(
        handler=EvidenceHandlers(
            state,
            session_repository=session_repository,
            provenance_verifier=ProvenanceVerifier(search_roots=[allowed_root]),
        ),
        state=state,
        session_id=str(session.id),
        database=database,
    )


@pytest.mark.parametrize("uri_kind", ["file_uri", "local_path"])
@pytest.mark.asyncio
async def test_manifest_id_maps_to_physical_source_and_hash_drift_fails_closed(
    tmp_path: Path,
    uri_kind: str,
) -> None:
    allowed_root = tmp_path / "allowed"
    allowed_root.mkdir()
    source = allowed_root / "actual-chart-file.txt"
    snippet = "10:00 BP 82/48 after medication administration."
    source.write_text(f"{snippet}\n", encoding="utf-8")
    source_uri = source.as_uri() if uri_kind == "file_uri" else str(source)
    harness = _build_harness(
        tmp_path,
        allowed_root=allowed_root,
        source_uri=source_uri,
        source_sha256=_digest(source),
    )

    try:
        added = await harness.handler.handle(
            "rc_add_evidence",
            {
                "session_id": harness.session_id,
                "content": "Medication-associated hypotension was observed.",
                "source_document": "SRC-001",
                "source_location": "Line 1",
                "raw_snippet": snippet,
                "auto_verify": True,
            },
        )

        assert added["verified"] is True
        assert added["match_type"] == "EXACT_SNIPPET_MATCH"
        evidence_id = added["evidence_id"]
        stored = await harness.handler.handle(
            "rc_get_evidence",
            {"session_id": harness.session_id, "evidence_id": evidence_id},
        )
        assert stored["evidence"]["source"]["document_id"] == "SRC-001"

        mismatched_source = await harness.handler.handle(
            "rc_verify_evidence",
            {
                "session_id": harness.session_id,
                "evidence_id": evidence_id,
                "document_id": "SRC-999",
            },
        )
        assert mismatched_source["verified"] is False
        assert mismatched_source["match_type"] == "SOURCE_DOCUMENT_ID_MISMATCH"

        restored = await harness.handler.handle(
            "rc_verify_evidence",
            {"session_id": harness.session_id, "evidence_id": evidence_id},
        )
        assert restored["verified"] is True
        assert restored["match_type"] == "EXACT_SNIPPET_MATCH"

        source.write_text(f"{snippet}\nlate unauthorized amendment\n", encoding="utf-8")
        rechecked = await harness.handler.handle(
            "rc_verify_evidence",
            {
                "session_id": harness.session_id,
                "evidence_id": evidence_id,
                "verified_by": "reviewer",
            },
        )

        assert rechecked["verified"] is False
        assert rechecked["match_type"] == "SOURCE_HASH_MISMATCH"
        assert rechecked["verification_method"] == "SOURCE_HASH_MISMATCH"
        assert rechecked["provenance_match"]["is_verified"] is False
        stored_after_drift = await harness.handler.handle(
            "rc_get_evidence",
            {"session_id": harness.session_id, "evidence_id": evidence_id},
        )
        assert stored_after_drift["evidence"]["verified"] is False
        assert stored_after_drift["evidence"]["source"]["document_id"] == "SRC-001"
    finally:
        harness.database.close()


@pytest.mark.parametrize(
    ("source_kind", "expected_match_type"),
    [
        ("remote", "UNSUPPORTED_SOURCE_URI_SCHEME"),
        ("outside_root", "SOURCE_PATH_NOT_ALLOWED"),
    ],
)
@pytest.mark.asyncio
async def test_manifest_verification_rejects_nonlocal_or_disallowed_sources(
    tmp_path: Path,
    source_kind: str,
    expected_match_type: str,
) -> None:
    allowed_root = tmp_path / "allowed"
    allowed_root.mkdir()
    outside_source = tmp_path / "outside.txt"
    outside_source.write_text("Exact clinical snippet\n", encoding="utf-8")
    source_uri = (
        "https://example.invalid/record.txt"
        if source_kind == "remote"
        else outside_source.as_uri()
    )
    harness = _build_harness(
        tmp_path,
        allowed_root=allowed_root,
        source_uri=source_uri,
        source_sha256=_digest(outside_source),
    )

    try:
        result = await harness.handler.handle(
            "rc_add_evidence",
            {
                "session_id": harness.session_id,
                "content": "An exact clinical observation.",
                "source_document": "SRC-001",
                "raw_snippet": "Exact clinical snippet",
                "auto_verify": True,
            },
        )
    finally:
        harness.database.close()

    assert result["verified"] is False
    assert result["match_type"] == expected_match_type
    assert result["verification_method"] == expected_match_type


def test_configured_source_roots_do_not_implicitly_trust_output_or_example_dirs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    allowed_root = tmp_path / "allowed"
    output_root = tmp_path / "output"
    allowed_root.mkdir()
    output_root.mkdir()
    output_source = output_root / "record.txt"
    output_source.write_text("not an approved raw source\n", encoding="utf-8")
    monkeypatch.setenv("ROOTCAUSE_SOURCE_ROOTS", str(allowed_root))
    monkeypatch.setenv("ROOTCAUSE_DATA_DIR", str(output_root))

    result = ProvenanceVerifier().resolve_source_uri(output_source.as_uri())

    assert isinstance(result, ProvenanceMatch)
    assert result.match_type == "SOURCE_PATH_NOT_ALLOWED"
