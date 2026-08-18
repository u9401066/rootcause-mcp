"""Append-only source review and independence adjudication regression tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from rootcause_mcp.domain.entities.session import RCASession
from rootcause_mcp.domain.value_objects.case_manifest import (
    CaseInputManifest,
    SourceDocument,
    SourceIndependenceStatus,
    SourceReviewAdjudication,
    SourceReviewStatus,
)
from rootcause_mcp.domain.value_objects.enums import CaseType
from rootcause_mcp.infrastructure.persistence.database import Database
from rootcause_mcp.infrastructure.persistence.session_repository import (
    SQLiteSessionRepository,
)
from rootcause_mcp.interface.handlers.contract_handlers import ContractHandlers
from rootcause_mcp.interface.handlers.session_handlers import SessionHandlers


def _manifest() -> CaseInputManifest:
    return CaseInputManifest(
        patient_key="case-pseudonym",
        documents=(
            SourceDocument(
                document_id="SRC-001",
                source_uri="host://case/source-001.txt",
                sha256="a" * 64,
                media_type="text/plain",
                source_kind="progress_note",
            ),
            SourceDocument(
                document_id="SRC-002",
                source_uri="host://case/source-002.txt",
                sha256="b" * 64,
                media_type="text/plain",
                source_kind="device_log",
            ),
        ),
    )


def _review(
    manifest: CaseInputManifest,
    *,
    event_id: str,
    status: SourceReviewStatus,
    reviewed_at: datetime,
) -> SourceReviewAdjudication:
    reviewed = status is SourceReviewStatus.REVIEWED
    return SourceReviewAdjudication(
        adjudication_id=event_id,
        manifest_digest=manifest.digest,
        document_id="SRC-001",
        status=status,
        de_identified=True if reviewed else None,
        independence_status=(
            SourceIndependenceStatus.INDEPENDENT
            if reviewed
            else SourceIndependenceStatus.UNKNOWN
        ),
        source_group_id="GROUP-001" if reviewed else None,
        reviewed_by="Dr Reviewer",
        reason="Exact extraction and source lineage were reviewed.",
        reviewed_at=reviewed_at,
    )


def test_source_review_ledger_preserves_manifest_digest_and_round_trips(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "source-review.db"
    database = Database(database_path)
    database.create_tables()
    repository = SQLiteSessionRepository(database)
    session = RCASession.create(
        case_type=CaseType.COMPLICATION,
        case_title="Source review lifecycle",
    )
    manifest = _manifest()
    session.set_source_manifest(manifest)
    manifest_digest = manifest.digest
    extracted_at = datetime(2026, 8, 18, 12, 0, tzinfo=UTC)
    session.record_source_review(
        _review(
            manifest,
            event_id="SRV-extracted",
            status=SourceReviewStatus.EXTRACTED,
            reviewed_at=extracted_at,
        )
    )
    session.record_source_review(
        _review(
            manifest,
            event_id="SRV-reviewed",
            status=SourceReviewStatus.REVIEWED,
            reviewed_at=extracted_at + timedelta(minutes=5),
        )
    )
    repository.save(session)
    session_id = str(session.id)
    database.close()

    reopened = Database(database_path)
    restored = SQLiteSessionRepository(reopened).get_by_id(session_id)
    assert restored is not None
    assert restored.get_source_manifest() == manifest
    assert restored.get_source_manifest().digest == manifest_digest
    assert [event.status for event in restored.get_source_review_ledger()] == [
        SourceReviewStatus.EXTRACTED,
        SourceReviewStatus.REVIEWED,
    ]
    latest = restored.get_latest_source_reviews()["SRC-001"]
    assert latest.adjudication_id == "SRV-reviewed"
    assert latest.independence_status is SourceIndependenceStatus.INDEPENDENT
    reopened.close()


def test_reviewed_source_cannot_regress_or_cross_manifest_boundary() -> None:
    manifest = _manifest()
    session = RCASession.create(
        case_type=CaseType.NEAR_MISS,
        case_title="Append-only source state",
    )
    session.set_source_manifest(manifest)
    reviewed_at = datetime(2026, 8, 18, 12, 0, tzinfo=UTC)
    session.record_source_review(
        _review(
            manifest,
            event_id="SRV-reviewed",
            status=SourceReviewStatus.REVIEWED,
            reviewed_at=reviewed_at,
        )
    )

    with pytest.raises(ValueError, match="cannot regress"):
        session.record_source_review(
            _review(
                manifest,
                event_id="SRV-regression",
                status=SourceReviewStatus.EXTRACTED,
                reviewed_at=reviewed_at + timedelta(minutes=1),
            )
        )

    wrong_manifest = _review(
        manifest,
        event_id="SRV-wrong-manifest",
        status=SourceReviewStatus.REVIEWED,
        reviewed_at=reviewed_at + timedelta(minutes=2),
    ).model_copy(update={"manifest_digest": f"sha256:{'f' * 64}"})
    with pytest.raises(ValueError, match="manifest_digest"):
        session.record_source_review(wrong_manifest)


@pytest.mark.asyncio
async def test_source_adjudication_requires_allowlisted_reviewer_and_updates_inventory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = Database(tmp_path / "source-review-handler.db")
    database.create_tables()
    repository = SQLiteSessionRepository(database)
    session = RCASession.create(
        case_type=CaseType.SAFETY,
        case_title="Authorized source adjudication",
    )
    manifest = _manifest()
    session.set_source_manifest(manifest)
    repository.save(session)
    session_id = str(session.id)
    handlers = SessionHandlers(session_repository=repository)

    monkeypatch.setenv("ROOTCAUSE_AUTHORIZED_REVIEWERS", "Dr Allowed")
    arguments = {
        "session_id": session_id,
        "document_id": "SRC-001",
        "source_status": "reviewed",
        "de_identified": True,
        "independence_status": "independent",
        "source_group_id": "GROUP-001",
        "reviewed_by": "Dr Not Allowed",
        "reason": "Reviewed exact extraction and source independence.",
    }
    denied = await handlers.handle_adjudicate_source(arguments)
    assert denied["status"] == "error"
    unchanged = repository.get_by_id(session_id)
    assert unchanged is not None
    assert unchanged.get_source_review_ledger() == ()

    accepted = await handlers.handle_adjudicate_source(
        {**arguments, "reviewed_by": "Dr Allowed"}
    )
    assert accepted["status"] == "success"
    assert accepted["manifest_digest"] == manifest.digest
    restored = repository.get_by_id(session_id)
    assert restored is not None
    latest_reviews = restored.get_latest_source_reviews()
    inventory = ContractHandlers._build_source_inventory(
        [],
        restored.get_source_manifest(),
        latest_reviews,
    )
    source = next(item for item in inventory if item["document"] == "SRC-001")
    assert source["coverage_status"] == "reviewed"
    assert source["de_identified"] is True
    assert source["independence_status"] == "independent"
    assert source["source_group_id"] == "GROUP-001"
    assert source["source_reviewed_by"] == "Dr Allowed"
    assert source["source_review_adjudication_id"].startswith("SRV-")
    assert restored.get_source_manifest().digest == manifest.digest
    database.close()
