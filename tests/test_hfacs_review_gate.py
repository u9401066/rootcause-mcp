"""P0 persistence and authorization tests for HFACS Fishbone review."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from rootcause_mcp.domain.entities.fishbone import Fishbone, FishboneCause
from rootcause_mcp.domain.value_objects.enums import (
    FishboneCategoryType,
    HFACSReviewStatus,
)
from rootcause_mcp.domain.value_objects.identifiers import CauseId, SessionId
from rootcause_mcp.infrastructure.persistence.database import Database
from rootcause_mcp.infrastructure.persistence.fishbone_repository import (
    SQLiteFishboneRepository,
)
from rootcause_mcp.interface.handlers.fishbone_handlers import FishboneHandlers
from rootcause_mcp.interface.handlers.hfacs_handlers import HFACSHandlers
from rootcause_mcp.interface.tools.hfacs_tools import get_hfacs_tools


def _repository(tmp_path: Path) -> tuple[Database, SQLiteFishboneRepository]:
    database = Database(tmp_path / "hfacs-review.db")
    database.create_tables()
    return database, SQLiteFishboneRepository(database)


def _fishbone(*, code: str | None = None) -> tuple[Fishbone, CauseId]:
    session_id = SessionId.from_string("rc_sess_hfacs")
    cause_id = CauseId.from_string("c_hfacs")
    fishbone = Fishbone.create(session_id, "Delayed escalation")
    fishbone.add_cause_to_category(
        FishboneCategoryType.PROCESS,
        FishboneCause(
            cause_id=cause_id,
            category=FishboneCategoryType.PROCESS,
            description="Escalation threshold was absent",
            hfacs_code=code,
            evidence=["EVD-1"],
        ),
    )
    return fishbone, cause_id


def test_confirmed_and_not_applicable_reviews_survive_sqlite_round_trip(
    tmp_path: Path,
) -> None:
    database, repository = _repository(tmp_path)
    try:
        fishbone, cause_id = _fishbone(code="caller-invented-code")
        initial = fishbone.get_all_causes()[0]
        assert initial.hfacs_review_status is HFACSReviewStatus.UNREVIEWED

        fishbone.review_cause_hfacs(
            cause_id,
            status=HFACSReviewStatus.CONFIRMED,
            hfacs_code="OF-OP",
            reviewed_by="Dr Reviewer",
            reason="Organizational process classification reviewed.",
            reviewed_at=datetime(2026, 8, 18, 10, 0, tzinfo=UTC),
        )
        repository.save(fishbone)

        restored = repository.get_by_session(fishbone.session_id)
        assert restored is not None
        confirmed = restored.get_all_causes()[0]
        assert confirmed.hfacs_code == "OF-OP"
        assert confirmed.hfacs_review_status is HFACSReviewStatus.CONFIRMED
        assert confirmed.hfacs_reviewed_by == "Dr Reviewer"
        assert confirmed.hfacs_reviewed_at == datetime(2026, 8, 18, 10, 0, tzinfo=UTC)

        restored.review_cause_hfacs(
            cause_id,
            status=HFACSReviewStatus.NOT_APPLICABLE,
            hfacs_code=None,
            reviewed_by="Dr Reviewer",
            reason="HFACS does not apply to this equipment failure.",
            reviewed_at=datetime(2026, 8, 18, 10, 5, tzinfo=UTC),
        )
        repository.save(restored)
        not_applicable = repository.get_by_session(fishbone.session_id)
        assert not_applicable is not None
        disposition = not_applicable.get_all_causes()[0]
        assert disposition.hfacs_review_status is HFACSReviewStatus.NOT_APPLICABLE
        assert disposition.hfacs_code is None
    finally:
        database.close()


@pytest.mark.asyncio
async def test_handler_rejects_unauthorized_reviewer_then_persists_exact_cause_review(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database, repository = _repository(tmp_path)
    try:
        fishbone, cause_id = _fishbone()
        repository.save(fishbone)
        handler = HFACSHandlers(fishbone_repository=repository)
        arguments = {
            "session_id": str(fishbone.session_id),
            "cause_id": str(cause_id),
            "description": "Escalation threshold was absent",
            "hfacs_code": "OF-OP",
            "review_status": "CONFIRMED",
            "reason": "Organizational process classification reviewed.",
        }

        monkeypatch.setenv("ROOTCAUSE_AUTHORIZED_REVIEWERS", "Dr Allowed")
        rejected = await handler.handle_confirm_classification(
            {**arguments, "reviewed_by": "agent"}
        )
        assert "Error:" in rejected[0].text
        unchanged = repository.get_by_session(fishbone.session_id)
        assert unchanged is not None
        assert (
            unchanged.get_all_causes()[0].hfacs_review_status
            is HFACSReviewStatus.UNREVIEWED
        )

        wrong_cause = await handler.handle_confirm_classification(
            {
                **arguments,
                "cause_id": "c_other_session",
                "reviewed_by": "Dr Allowed",
            }
        )
        assert "must identify exactly one Fishbone cause" in wrong_cause[0].text

        accepted = await handler.handle_confirm_classification(
            {**arguments, "reviewed_by": "Dr Allowed"}
        )
        assert "HFACS Review Persisted" in accepted[0].text
        restored = repository.get_by_session(fishbone.session_id)
        assert restored is not None
        reviewed = restored.get_all_causes()[0]
        assert reviewed.hfacs_review_status is HFACSReviewStatus.CONFIRMED
        assert reviewed.hfacs_code == "OF-OP"
        assert reviewed.hfacs_reviewed_by == "Dr Allowed"
        assert reviewed.hfacs_reviewed_at is not None
    finally:
        database.close()


@pytest.mark.asyncio
async def test_rc_add_cause_hfacs_code_remains_unreviewed(
    tmp_path: Path,
) -> None:
    database, repository = _repository(tmp_path)
    try:
        fishbone, _ = _fishbone()
        repository.save(fishbone)
        handler = FishboneHandlers(fishbone_repository=repository)

        result = await handler.handle_add_cause(
            {
                "session_id": str(fishbone.session_id),
                "category": "Personnel",
                "description": "Caller supplied a plausible-sounding label",
                "hfacs_code": "ARBITRARY-CODE",
                "evidence": [],
            }
        )

        assert "HFACS review status:** UNREVIEWED" in result[0].text
        restored = repository.get_by_session(fishbone.session_id)
        assert restored is not None
        added = next(
            cause
            for cause in restored.get_all_causes()
            if cause.description == "Caller supplied a plausible-sounding label"
        )
        assert added.hfacs_code == "ARBITRARY-CODE"
        assert added.hfacs_review_status is HFACSReviewStatus.UNREVIEWED
        assert added.hfacs_reviewed_by is None
    finally:
        database.close()


@pytest.mark.parametrize(
    ("status", "code"),
    [
        (HFACSReviewStatus.CONFIRMED, None),
        (HFACSReviewStatus.CONFIRMED, "ARBITRARY-CODE"),
        (HFACSReviewStatus.NOT_APPLICABLE, "OF-OP"),
    ],
)
def test_impossible_review_states_are_rejected(
    status: HFACSReviewStatus,
    code: str | None,
) -> None:
    with pytest.raises(ValueError):
        FishboneCause(
            cause_id=CauseId.from_string("c_invalid"),
            category=FishboneCategoryType.PROCESS,
            description="Invalid review state",
            hfacs_code=code,
            hfacs_review_status=status,
            hfacs_reviewed_by="Dr Reviewer",
            hfacs_reviewed_at=datetime(2026, 8, 18, 10, 0, tzinfo=UTC),
            hfacs_review_reason="Review attempted.",
        )


def test_confirmation_tool_requires_session_cause_reviewer_and_typed_disposition() -> (
    None
):
    tool = next(
        item for item in get_hfacs_tools() if item.name == "rc_confirm_classification"
    )
    schema = tool.input_schema

    assert set(schema["required"]) == {
        "session_id",
        "cause_id",
        "review_status",
        "reviewed_by",
        "reason",
    }
    assert schema["properties"]["review_status"]["enum"] == [
        "CONFIRMED",
        "NOT_APPLICABLE",
    ]
    assert schema["allOf"][0]["then"]["required"] == ["hfacs_code"]
