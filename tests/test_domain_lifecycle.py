"""Lifecycle and boundary tests for core RCA domain objects."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from rootcause_mcp.domain.entities.cause import Cause
from rootcause_mcp.domain.entities.fishbone import Fishbone, FishboneCause
from rootcause_mcp.domain.entities.session import RCASession, StageRecord
from rootcause_mcp.domain.entities.thinking_step import (
    AlternativeConsidered,
    ThinkingChain,
    ThinkingStep,
    ThinkingType,
)
from rootcause_mcp.domain.value_objects.enums import (
    CaseType,
    FishboneCategoryType,
    SessionStatus,
    Stage,
    StageStatus,
)
from rootcause_mcp.domain.value_objects.identifiers import (
    ActionId,
    CauseId,
    EvidenceId,
    FishboneId,
    HypothesisId,
    ReasoningStepId,
    SessionId,
)
from rootcause_mcp.domain.value_objects.scores import ConfidenceScore, QualityScore


def test_cause_lifecycle_and_hfacs_mapping() -> None:
    cause = Cause.create(
        session_id=SessionId.generate(),
        description="No independent double check",
        category=FishboneCategoryType.PROCESS,
    )
    original_updated_at = cause.updated_at

    cause.add_evidence("Medication policy")
    cause.add_evidence("Medication policy")
    cause.set_hfacs("OF-OP", confidence=0.9)
    cause.verify(0.85)

    assert cause.has_evidence
    assert cause.evidence == ["Medication policy"]
    assert cause.get_hfacs() is not None
    assert cause.confidence_level == "high"
    assert cause.verified
    assert cause.is_root_cause
    assert cause.updated_at >= original_updated_at

    cause.remove_evidence("Medication policy")
    cause.unverify()
    assert not cause.has_evidence
    assert cause.confidence_level == "unknown"


@pytest.mark.parametrize("depth", [0, 6])
def test_cause_rejects_invalid_depth(depth: int) -> None:
    with pytest.raises(ValueError, match="depth"):
        Cause.create(
            session_id=SessionId.generate(),
            description="Invalid depth",
            category=FishboneCategoryType.PROCESS,
            depth=depth,
        )


def test_fishbone_lifecycle_and_queries() -> None:
    fishbone = Fishbone.create(
        session_id=SessionId.generate(),
        problem_statement="Medication dose error",
    )
    cause = FishboneCause(
        cause_id=CauseId.generate(),
        category=FishboneCategoryType.PROCESS,
        description="No double check",
        hfacs_code="OF-OP",
        verified=True,
    )

    fishbone.add_cause_to_category(FishboneCategoryType.PROCESS, cause)
    assert fishbone.total_cause_count == 1
    assert fishbone.coverage_ratio == pytest.approx(1 / 6)
    assert fishbone.populated_categories == [FishboneCategoryType.PROCESS]
    assert len(fishbone.empty_categories) == 5
    assert fishbone.get_verified_causes() == [cause]
    assert fishbone.get_causes_by_hfacs_level("OF") == [cause]
    assert fishbone.get_all_causes() == [cause]
    assert (
        fishbone.get_category(FishboneCategoryType.PROCESS).get_cause(cause.cause_id)
        is cause
    )
    assert fishbone.to_dict()["problem_statement"] == "Medication dose error"

    assert fishbone.remove_cause(FishboneCategoryType.PROCESS, cause.cause_id)
    assert not fishbone.remove_cause(FishboneCategoryType.PROCESS, cause.cause_id)


def test_session_stage_and_status_lifecycle() -> None:
    session = RCASession.create(
        case_type=CaseType.NEAR_MISS,
        case_title="Dose near miss",
        initial_description="Intercepted before administration",
        created_by="reviewer",
    )
    assert session.is_active
    assert session.stage_records[Stage.GATHER].status is StageStatus.IN_PROGRESS
    assert session.can_advance_to(Stage.CONTEXTUALIZE)

    session.set_problem("Ten-fold dose error")
    session.set_stage_data(Stage.GATHER, {"documents": 3})
    session.update_stage_data(Stage.GATHER, {"interviews": 2})
    assert session.get_stage_data(Stage.GATHER) == {
        "documents": 3,
        "interviews": 2,
    }
    assert session.advance_stage() is Stage.CONTEXTUALIZE
    assert Stage.GATHER in session.get_completed_stages()
    assert session.rollback_to(Stage.GATHER, "Need more evidence")
    assert session.current_stage is Stage.GATHER

    session.complete()
    assert session.is_completed
    assert not session.can_advance_to(Stage.CONTEXTUALIZE)
    session.abandon()
    assert session.status is SessionStatus.ABANDONED
    session.archive()
    assert session.status is SessionStatus.ARCHIVED
    assert set(session.get_progress()) == {stage.value for stage in Stage}


def test_stage_record_failure_and_completion() -> None:
    record = StageRecord(stage=Stage.ANALYZE)
    record.start()
    record.fail(["Missing timeline"])
    assert record.status is StageStatus.FAILED
    assert record.validation_errors == ["Missing timeline"]
    record.complete()
    assert record.is_completed


def test_thinking_chain_reports_decisions_biases_and_uncertainty() -> None:
    chain = ThinkingChain(session_id="case-001")
    chain.add_step(
        ThinkingStep(
            thinking_type=ThinkingType.DECISION_POINT,
            content="Acute MI remains most likely",
            internal_reasoning="Troponin and ECG findings align with acute MI.",
            alternatives=[
                AlternativeConsidered(
                    alternative="Pulmonary embolism",
                    reason_rejected="No right-heart strain",
                    confidence_if_chosen=0.2,
                )
            ],
            confidence=0.8,
            uncertainty_factors=["Serial ECG pending"],
            related_hypothesis_ids=["HYP-001"],
            assumptions_made=["Troponin reflects acute injury"],
            potential_biases=["Anchoring"],
        )
    )
    chain.add_step(
        ThinkingStep(
            thinking_type=ThinkingType.HYPOTHESIS_REJECTED,
            content="Pulmonary embolism rejected",
            internal_reasoning="Imaging and physiology do not support PE.",
            confidence=0.7,
        )
    )

    assert len(chain.get_decision_points()) == 1
    assert chain.get_rejected_hypotheses() == ["Pulmonary embolism rejected"]
    assert chain.get_uncertainty_map() == {"HYP-001": ["Serial ECG pending"]}
    assert chain.get_bias_report() == ["Anchoring"]
    assert chain.get_assumption_report() == ["Troponin reflects acute injury"]
    report = chain.export_for_review()
    assert "KEY DECISION POINTS" in report
    assert "Potential Biases" in chain.steps[0].to_human_readable()


@pytest.mark.parametrize(
    ("score", "level"),
    [(0.8, "high"), (0.5, "medium"), (0.3, "low")],
)
def test_confidence_score_levels(score: float, level: str) -> None:
    value = ConfidenceScore(score)
    assert value.to_level() == level
    assert float(value) == score
    assert str(value) == f"{score:.2f}"
    assert ConfidenceScore.from_string(level).to_level() == level


def test_score_boundaries_and_quality_grades() -> None:
    assert ConfidenceScore.high().value == 0.8
    assert ConfidenceScore.medium().value == 0.5
    assert ConfidenceScore.low().value == 0.3
    with pytest.raises(ValueError):
        ConfidenceScore(1.1)
    with pytest.raises(ValueError):
        ConfidenceScore.from_string("unknown")

    assert [QualityScore(value).to_grade() for value in (95, 85, 75, 65, 55)] == [
        "A",
        "B",
        "C",
        "D",
        "F",
    ]
    quality = QualityScore.from_percentage(0.82)
    assert int(quality) == 82
    assert str(quality) == "82/100"
    with pytest.raises(ValueError):
        QualityScore(101)


@pytest.mark.parametrize(
    ("factory", "prefix"),
    [
        (SessionId.generate, "rc_sess_"),
        (CauseId.generate, "c_"),
        (FishboneId.generate, "fb_"),
        (ActionId.generate, "act_"),
        (EvidenceId.generate, "EVD-"),
        (HypothesisId.generate, "HYP-"),
        (ReasoningStepId.generate, "RS-"),
    ],
)
def test_identifier_factories(factory: Callable[[], Any], prefix: str) -> None:
    identifier = factory()
    assert str(identifier).startswith(prefix)
    assert type(identifier).from_string(str(identifier)) == identifier
