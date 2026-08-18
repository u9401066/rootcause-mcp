"""Integration tests for the MCP SDK 2.0 server entry point."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from rootcause_mcp import server_v2
from rootcause_mcp.application.server_state import ServerState
from rootcause_mcp.interface.handlers.dd_handlers import DDHandlers
from rootcause_mcp.interface.tools import get_all_tools
from rootcause_mcp.server_v2 import lifespan, on_list_tools, server

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.asyncio
async def test_sdk2_lifespan_exposes_complete_tool_catalog(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """The production entry point starts and exposes every registered tool."""
    monkeypatch.setenv("ROOTCAUSE_DATA_DIR", str(tmp_path))

    async with lifespan(server):
        context: Any = None
        result = await on_list_tools(context, None)
        dispatch = server_v2._build_tool_dispatch()

    tool_names = {tool.name for tool in result.tools}
    assert len(tool_names) == 46
    assert set(dispatch) == tool_names
    assert {
        "rc_add_evidence",
        "rc_propose_hypothesis",
        "rc_audit_differential_breadth",
        "rc_select_leading_hypothesis",
        "rc_think_aloud",
        "rc_audit_reasoning_state",
        "rc_detect_conflicts",
        "rc_create_checkpoint",
        "rc_restore_checkpoint",
        "rc_list_checkpoints",
        "rc_generate_contract_report",
        "rc_verify_causation",
        "rc_validate_diagram",
        "rc_render_timeline",
    } <= tool_names
    assert (tmp_path / "rca_sessions.db").exists()


@pytest.mark.asyncio
async def test_sdk2_clinical_profile_matches_dispatch_surface(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A profile must reduce both advertised and executable tools."""
    monkeypatch.setenv("ROOTCAUSE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ROOTCAUSE_TOOL_PROFILE", "clinical")

    async with lifespan(server):
        context: Any = None
        result = await on_list_tools(context, None)
        monkeypatch.setenv("ROOTCAUSE_TOOL_PROFILE", "all")
        dispatch = server_v2._build_tool_dispatch()
        frozen_result = await on_list_tools(context, None)

    tool_names = {tool.name for tool in result.tools}
    assert len(tool_names) == 25
    assert set(dispatch) == tool_names
    assert {tool.name for tool in frozen_result.tools} == tool_names
    assert "rc_add_evidence" in tool_names
    assert "rc_audit_differential_breadth" in tool_names
    assert "rc_select_leading_hypothesis" in tool_names
    assert "rc_export_fishbone" not in tool_names


def test_sdk2_server_metadata() -> None:
    """The package advertises the SDK 2.0 server and alpha release version."""
    assert server.name == "rootcause-mcp"
    assert server.version == "2.0.0a2"


def test_propose_schema_deprecates_context_only_evidence_arrays() -> None:
    """Legacy proposal arrays must not imply or require an evidence association."""
    tool = next(
        item for item in get_all_tools("all") if item.name == "rc_propose_hypothesis"
    )
    required = set(tool.input_schema["required"])

    for field_name in ("evidence_supporting", "evidence_contradicting"):
        assert field_name not in required
        description = tool.input_schema["properties"][field_name]["description"]
        assert "deprecated context-only" in description.lower()
        assert "does not create evidence links" in description
        assert "rc_link_evidence_to_hypothesis" in description


@pytest.mark.asyncio
async def test_only_link_tool_associates_evidence_with_hypothesis() -> None:
    """Supplying deprecated proposal arrays cannot bypass the explicit link tool."""
    state = ServerState()
    session_id = "proposal-context-only-session"
    orchestrator = await state.get_or_create_orchestrator(session_id)
    supporting = orchestrator.add_evidence(
        content="Serial ECG demonstrates new inferior ST elevation.",
        source_document="ecg.txt",
        auto_verify=False,
    )
    contradicting = orchestrator.add_evidence(
        content="CT angiography shows no pulmonary embolus.",
        source_document="cta.txt",
        auto_verify=False,
    )
    calibration = orchestrator.add_evidence(
        content="Published validation table reports LR 3.0 for this ECG pattern.",
        evidence_type="LITERATURE",
        source_document="literature.txt",
        source_location="Table 2",
        raw_snippet="Inferior ST elevation LR 3.0",
        extraction_method="verbatim_quote",
        auto_verify=False,
    ).mark_verified(
        verifier="SYSTEM_PROVENANCE_VERIFIER",
        verification_method="EXACT_SNIPPET_MATCH",
        content_hash="sha256:" + "a" * 64,
    )
    orchestrator.evidence_store[calibration.id.value] = calibration
    orchestrator.evidence_store[supporting.id.value] = supporting.mark_verified(
        verifier="SYSTEM_PROVENANCE_VERIFIER",
        verification_method="EXACT_SNIPPET_MATCH",
    )
    handler = DDHandlers(state)

    proposed = await handler.handle(
        "rc_propose_hypothesis",
        {
            "session_id": session_id,
            "diagnosis": "Acute myocardial infarction",
            "clinical_reasoning": "The symptom and ECG pattern require explicit review.",
            "differential_diagnoses_considered": [],
            "evidence_supporting": [supporting.id.value],
            "evidence_contradicting": [contradicting.id.value],
            "uncertainty_factors": ["Troponin trend pending"],
            "confidence_rationale": "Moderate pre-test probability",
        },
    )
    hypothesis_id = proposed["hypothesis_id"]
    hypothesis = orchestrator.hypothesis_store[hypothesis_id]
    assert hypothesis.supporting_evidence_ids == []
    assert hypothesis.contradicting_evidence_ids == []
    assert (
        orchestrator.evidence_store[supporting.id.value].supports_hypothesis_ids == []
    )

    await handler.handle(
        "rc_link_evidence_to_hypothesis",
        {
            "session_id": session_id,
            "evidence_id": supporting.id.value,
            "hypothesis_id": hypothesis_id,
            "likelihood_ratio": 3.0,
            "supports": True,
            "rationale": "The observed ECG finding supports this hypothesis.",
            "calibration_status": "SOURCE_CALIBRATED",
            "calibration_source_ref": calibration.id.value,
        },
    )
    assert orchestrator.hypothesis_store[hypothesis_id].supporting_evidence_ids == [
        supporting.id.value
    ]
    assert orchestrator.evidence_store[supporting.id.value].supports_hypothesis_ids == [
        hypothesis_id
    ]
