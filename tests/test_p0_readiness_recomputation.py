"""Adversarial checks for deterministic final-report readiness projection."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from rootcause_mcp.domain.services.final_report_conformance import (
    evaluate_final_report_conformance,
)
from test_p0_final_report_conformance import _valid_report


def _guidance_status(report: dict[str, Any]) -> str:
    checks = evaluate_final_report_conformance(
        report,
        approved_by="reviewer",
        authorized_reviewers={"reviewer", "Dr Reviewer"},
    )
    return next(
        str(check["status"]) for check in checks if check["code"] == "GUIDANCE_READY"
    )


@pytest.mark.parametrize(
    "mutate",
    [
        lambda report: report["report_readiness"].__setitem__(
            "current_stage", "COGNITIVE_AUDIT"
        ),
        lambda report: report["report_readiness"].__setitem__(
            "completeness_score", 0.5
        ),
        lambda report: report["report_readiness"].__setitem__(
            "missing_prerequisites", ["still missing"]
        ),
        lambda report: report["report_readiness"]["checklist"].__setitem__(
            "evidence_count", 999
        ),
        lambda report: report["report_readiness"]["checklist"].__setitem__(
            "leading_hypothesis_id", "HYP-not-selected"
        ),
        lambda report: report["thinking_chain"][0].__setitem__("potential_biases", []),
        lambda report: report["thinking_chain"][0].__setitem__(
            "uncertainty_factors", []
        ),
        lambda report: report["report_readiness"].__setitem__(
            "session_id", "different-session"
        ),
        lambda report: report["report_readiness"].__setitem__(
            "next_recommended_actions", []
        ),
        lambda report: report["report_readiness"].__setitem__("push_questions", []),
    ],
    ids=[
        "stage-forged",
        "score-forged",
        "missing-list-forged",
        "evidence-count-forged",
        "leading-id-forged",
        "bias-missing",
        "uncertainty-missing",
        "session-mismatch",
        "actions-empty",
        "questions-empty",
    ],
)
def test_caller_ready_true_cannot_hide_snapshot_inconsistency(
    mutate: Callable[[dict[str, Any]], Any],
) -> None:
    report = _valid_report()
    mutate(report)

    assert report["report_readiness"]["is_ready_for_report"] is True
    assert _guidance_status(report) == "FAIL"


def test_valid_snapshot_readiness_is_recomputable() -> None:
    assert _guidance_status(_valid_report()) == "PASS"
