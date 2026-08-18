"""Regression tests for the synthetic case preview runner."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest


def _load_case_trial_module() -> ModuleType:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_case_trial.py"
    spec = importlib.util.spec_from_file_location("case_trial_test_module", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load case trial module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


run_case_trial = _load_case_trial_module()


def _guidance(*, ready: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        is_ready_for_report=ready,
        completeness_score=0.75,
        missing_prerequisites=[] if ready else ["must-not-miss hypothesis required"],
    )


def test_preview_response_is_validated_before_content_access() -> None:
    results: dict[str, Any] = {"errors": []}

    content = run_case_trial._record_preview_result(
        {"status": "error", "message": "preview unavailable"},
        results,
        _guidance(),
    )

    assert content is None
    assert results["errors"] == [
        "Preliminary report generation failed (error): preview unavailable"
    ]
    assert results["report"] == {
        "status": "error",
        "mode": "PRELIMINARY",
        "finalized": None,
    }
    assert results["readiness"]["is_ready_for_report"] is False


def test_preview_response_rejects_unexpected_finalization() -> None:
    results: dict[str, Any] = {"errors": []}

    content = run_case_trial._record_preview_result(
        {"status": "success", "content": "report", "finalized": True},
        results,
        _guidance(ready=True),
    )

    assert content is None
    assert results["errors"] == [
        "Preview request unexpectedly returned a finalized report"
    ]


def test_provenance_warning_marks_preview_case_failed() -> None:
    results: dict[str, Any] = {"errors": [], "warnings": ["snippet did not match"]}

    completed = run_case_trial._complete_preview_case(
        results,
        0.0,
        _guidance(),
        "TEST",
        SimpleNamespace(diagnosis="Synthetic diagnosis", current_probability=0.5),
    )

    assert completed["success"] is False


@pytest.mark.asyncio
async def test_main_returns_nonzero_when_a_case_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def failed_case() -> dict[str, Any]:
        return {
            "case": "synthetic_failure",
            "success": False,
            "elapsed_seconds": 0.01,
            "warnings": [],
            "errors": ["report failed"],
            "report": {"status": "error", "mode": "PRELIMINARY"},
            "readiness": {"is_ready_for_report": False},
        }

    monkeypatch.setattr(run_case_trial, "run_sam_case", failed_case)
    monkeypatch.setattr(sys, "argv", ["run_case_trial.py", "--case", "sam"])

    assert await run_case_trial.main() == 1
