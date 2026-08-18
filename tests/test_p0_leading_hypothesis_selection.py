"""P0 probes for explicit, persistent leading-diagnosis selection."""

from __future__ import annotations

import pytest

from rootcause_mcp.application.server_state import ServerState
from rootcause_mcp.interface.handlers.dd_handlers import DDHandlers
from rootcause_mcp.interface.handlers.facade_handlers import FacadeHandlers
from rootcause_mcp.interface.tools.condensed_tools import get_condensed_tools
from rootcause_mcp.interface.tools.dd_tools import get_dd_tools


def _propose(orchestrator: object, diagnosis: str) -> str:
    hypothesis = orchestrator.propose_hypothesis(  # type: ignore[attr-defined]
        diagnosis=diagnosis,
        rationale=f"The presentation requires explicit review of {diagnosis}.",
        mechanism_category="VASCULAR",
        diagnostic_role="ETIOLOGIC",
        certainty="POSSIBLE",
        reasoning_basis="MECHANISM_INFERENCE",
        uncertainty_factors=["Definitive adjudication remains pending"],
        confidence_rationale="No calibrated clinical probability is asserted.",
    )
    return hypothesis.id.value


@pytest.mark.asyncio
async def test_leading_selection_is_explicit_and_retains_change_history() -> None:
    state = ServerState()
    orchestrator = await state.get_or_create_orchestrator("leading-history")
    first_id = _propose(orchestrator, "Pulmonary embolism")
    second_id = _propose(orchestrator, "Acute myocardial infarction")
    handler = DDHandlers(state)

    first = await handler.handle_select_leading_hypothesis(
        {
            "session_id": "leading-history",
            "hypothesis_id": first_id,
            "reason": "Acute hypoxemia makes this the current working lead.",
            "changed_by": "test-agent",
        }
    )
    second = await handler.handle_select_leading_hypothesis(
        {
            "session_id": "leading-history",
            "hypothesis_id": second_id,
            "reason": "New verified ECG evidence changes the working lead.",
            "changed_by": "test-agent",
        }
    )

    assert first["status"] == "success"
    assert second["status"] == "success"
    assert orchestrator.get_leading_hypothesis_id() == second_id
    history = orchestrator.get_leading_hypothesis_selection_history()
    assert [item.hypothesis_id for item in history] == [first_id, second_id]
    assert history[0].previous_hypothesis_id is None
    assert history[1].previous_hypothesis_id == first_id
    assert all(item.selection_id.startswith("LHS-") for item in history)


@pytest.mark.asyncio
async def test_excluded_candidate_cannot_be_selected_as_leading() -> None:
    state = ServerState()
    orchestrator = await state.get_or_create_orchestrator("leading-excluded")
    hypothesis_id = _propose(orchestrator, "Aortic dissection")
    orchestrator.exclude_hypothesis(
        hypothesis_id,
        excluded_by="test-reviewer",
        reason="Definitive adequate imaging excludes the diagnosis.",
    )

    result = await DDHandlers(state).handle_select_leading_hypothesis(
        {
            "session_id": "leading-excluded",
            "hypothesis_id": hypothesis_id,
            "reason": "Attempted unsafe selection should be rejected.",
            "changed_by": "test-agent",
        }
    )

    assert result["status"] == "error"
    assert "ACTIVE or CONFIRMED" in result["message"]
    assert orchestrator.get_leading_hypothesis_id() is None


def test_leading_selection_is_available_on_discrete_and_condensed_surfaces() -> None:
    discrete = next(
        tool for tool in get_dd_tools() if tool.name == "rc_select_leading_hypothesis"
    )
    assert set(discrete.input_schema["required"]) == {
        "session_id",
        "hypothesis_id",
        "reason",
        "changed_by",
    }

    condensed = next(
        tool for tool in get_condensed_tools() if tool.name == "rc_hypothesis"
    )
    assert "select_leading" in condensed.input_schema["properties"]["action"]["enum"]
    selection_rule = next(
        item["then"]
        for item in condensed.input_schema["allOf"]
        if item.get("if", {}).get("properties", {}).get("action", {}).get("const")
        == "select_leading"
    )
    assert set(selection_rule["required"]) == {
        "hypothesis_id",
        "reason",
        "changed_by",
    }


def test_condensed_facade_routes_explicit_selection() -> None:
    source = FacadeHandlers.handle_hypothesis.__code__.co_consts
    assert "select_leading" in source
    assert "rc_select_leading_hypothesis" in source
