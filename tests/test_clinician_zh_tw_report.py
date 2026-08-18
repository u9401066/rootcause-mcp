"""Clinician-facing zh-TW report and MCP transport regressions."""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from rootcause_mcp.application.clinical_reasoning_orchestrator import (
    ClinicalReasoningOrchestrator,
)
from rootcause_mcp.application.server_state import ServerState
from rootcause_mcp.domain.value_objects.contract_report import ContractReport
from rootcause_mcp.interface.contract_markdown import render_contract_report_markdown
from rootcause_mcp.interface.handlers.contract_handlers import ContractHandlers
from rootcause_mcp.interface.mermaid import build_evidence_graph, build_timeline


@pytest.mark.asyncio
async def test_zh_tw_clinician_report_explains_each_ddx_without_placeholder_probability(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The clinician view should expose reasoning, unknowns, and neutral LR semantics."""
    monkeypatch.setenv("ROOTCAUSE_DATA_DIR", str(tmp_path))
    state = ServerState()
    session_id = "rc_sess_full_collision_safe_identity"
    orchestrator = await state.get_or_create_orchestrator(session_id)
    evidence = orchestrator.add_evidence(
        content="ECG showed VF immediately before defibrillation and ROSC.",
        evidence_type="DEVICE_LOG",
        source_document="SRC-ECG-DERIVATIVE",
        source_location="line 4",
        raw_snippet="ECG showed VF immediately before defibrillation and ROSC.",
        extraction_method="verbatim_quote",
        clinical_strength="MODERATE",
        source_reliability="GRADE_C",
        event_timestamp=datetime(2026, 8, 18, 3, 0, tzinfo=UTC),
        auto_verify=False,
    )
    orchestrator.evidence_store[evidence.id.value] = evidence.mark_verified(
        verifier="SYSTEM_PROVENANCE_VERIFIER",
        verification_method="EXACT_SNIPPET_MATCH",
        matched_lines=[4],
    )

    diagnoses = [
        (
            "Hyperkalemia-associated ventricular tachyarrhythmia",
            "METABOLIC_ENDOCRINE",
            True,
        ),
        ("Acute myocardial ischemia with VF", "VASCULAR", True),
        ("Long-QT-associated polymorphic VT", "OTHER", False),
    ]
    hypotheses = []
    for diagnosis, mechanism, must_not_miss in diagnoses:
        hypothesis = orchestrator.propose_hypothesis(
            diagnosis=diagnosis,
            prior_probability=0.1,
            rationale=(
                f"{diagnosis} remains plausible because the recorded rhythm and "
                "perioperative context are compatible but not diagnostic."
            ),
            inclusion_criteria=["Original waveform shows a compatible mechanism"],
            exclusion_criteria=["Original waveform and serial tests refute it"],
            must_not_miss=must_not_miss,
            mechanism_category=mechanism,
            certainty="POSSIBLE",
            reasoning_basis="MECHANISM_INFERENCE",
            uncertainty_factors=["Original monitor waveform is unavailable"],
            confidence_rationale="Schema-compatible uncalibrated placeholder",
            planned_tests=[
                {
                    "name": f"Adjudicate {diagnosis}",
                    "purpose": "DISCRIMINATE",
                    "expected_supporting_result": "Compatible original waveform",
                    "expected_refuting_result": "Incompatible original waveform",
                    "status": "PLANNED",
                }
            ],
        )
        hypotheses.append(hypothesis)

    orchestrator.select_leading_hypothesis(
        hypotheses[0].id.value,
        reason="This working lead is explicitly selected for transparent challenge.",
        changed_by="test-agent",
    )

    orchestrator.record_differential_breadth_audit(
        {
            "audit_id": "DBA-clinician-renderer",
            "framework": "CUSTOM",
            "framework_name": "Perioperative arrest mechanism matrix",
            "framework_rationale": (
                "The arrest phenotype requires explicit review of metabolic, "
                "oxygenation, and toxicologic mechanisms."
            ),
            "role": "PRIMARY",
            "cells": [
                {
                    "cell_id": "METABOLIC",
                    "status": "CANDIDATES_PRESENT",
                    "hypothesis_ids": [hypotheses[0].id.value],
                    "mechanism_categories": ["METABOLIC_ENDOCRINE"],
                    "rationale": (
                        "A metabolic candidate is retained in the active ledger."
                    ),
                    "unknowns": [],
                    "planned_discriminators": [],
                },
                {
                    "cell_id": "OXYGENATION",
                    "status": "REVIEWED_INSUFFICIENT_DATA",
                    "hypothesis_ids": [],
                    "mechanism_categories": [],
                    "rationale": (
                        "The supplied extract does not contain continuous respiratory "
                        "waveforms."
                    ),
                    "unknowns": ["Continuous ETCO2 waveform is unavailable"],
                    "planned_discriminators": [
                        {
                            "name": "Retrieve continuous ETCO2 waveform",
                            "kind": "DATA_RETRIEVAL",
                            "expected_supporting_result": (
                                "Abrupt loss or progressive decline before arrest"
                            ),
                            "expected_refuting_result": (
                                "Stable ventilation through the arrest transition"
                            ),
                            "status": "PLANNED",
                        }
                    ],
                },
                {
                    "cell_id": "TOXIC_IATROGENIC",
                    "status": "NOT_ASSESSED",
                    "hypothesis_ids": [],
                    "mechanism_categories": [],
                    "rationale": (
                        "Medication administration records have not yet been reviewed."
                    ),
                    "unknowns": [
                        "Complete medication administration record is pending"
                    ],
                    "planned_discriminators": [],
                },
            ],
            "stop_rationale": (
                "The framework remains open until oxygenation and medication data are "
                "reviewed."
            ),
            "recorded_by": "test-agent",
        }
    )

    orchestrator.link_evidence_to_hypothesis(
        evidence_id=evidence.id.value,
        hypothesis_id=hypotheses[0].id.value,
        likelihood_ratio=1.0,
        supports=None,
        rationale="Compatible but nonspecific; no calibrated LR is available.",
        calibration_status="QUANTITATIVELY_UNKNOWN",
    )

    result = await ContractHandlers(state).handle_generate_contract_report(
        {
            "session_id": session_id,
            "format": "markdown",
            "locale": "zh-TW",
            "audience": "clinician",
            "detail_level": "full",
        },
        persist_export=False,
    )

    assert result["status"] == "success"
    assert result["locale"] == "zh-TW"
    assert result["audience"] == "clinician"
    assert result["report_id"] == f"RPT-{session_id}"
    markdown = result["content"]
    assert "Clinical Reasoning 與 Root Cause 分析報告" in markdown
    assert "DDx 的目的，是在未知仍多時保留最大範圍的合理推論" in markdown
    assert "Hyperkalemia-associated ventricular tachyarrhythmia" in markdown
    assert "Evidence for（僅 LR > 1" in markdown
    assert "Direction-neutral / qualitative evidence" in markdown
    assert "applied LR 1" in markdown
    assert "尚無已記錄的 LR > 1 evidence" in markdown
    assert "Original monitor waveform is unavailable" in markdown
    assert "Planned discriminating tests" in markdown
    assert "## DDx breadth audit" in markdown
    assert "Perioperative arrest mechanism matrix" in markdown
    assert "Coverage status：INCOMPLETE" in markdown
    assert "`OXYGENATION` — `REVIEWED_INSUFFICIENT_DATA`" in markdown
    assert "Continuous ETCO2 waveform is unavailable" in markdown
    assert "Retrieve continuous ETCO2 waveform" in markdown
    assert "`TOXIC_IATROGENIC` — `NOT_ASSESSED`" in markdown
    assert "The framework remains open until oxygenation" in markdown
    assert "未校準／資料不足" in markdown
    assert "clinical probability ranking" in markdown
    assert "| Prior |" not in markdown
    assert "| Posterior |" not in markdown
    assert "registered source exact text match" in markdown
    assert "independently verified" not in markdown
    assert f"{evidence.id.value}: true (EXACT_SNIPPET_MATCH)" in markdown
    assert "Verified: False (UNVERIFIED)" not in markdown


@pytest.mark.asyncio
async def test_stdio_client_accepts_contract_report_string_content_schema(
    tmp_path: Path,
) -> None:
    """A standard MCP client must validate report structuredContent successfully."""
    project_root = Path(__file__).resolve().parents[1]
    environment = {
        **os.environ,
        "ROOTCAUSE_DATA_DIR": str(tmp_path / "runtime"),
        "ROOTCAUSE_CONFIG_DIR": str(project_root / "config"),
        "ROOTCAUSE_TOOL_PROFILE": "all",
        "ROOTCAUSE_RESPONSE_MODE": "compact",
    }
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "rootcause_mcp.server_v2"],
        cwd=project_root,
        env=environment,
    )

    async with (
        stdio_client(parameters) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        await session.initialize()
        added = await session.call_tool(
            "rc_add_evidence",
            {
                "session_id": "stdio-report-schema-case",
                "content": "VF documented; source waveform not supplied.",
                "auto_verify": False,
            },
        )
        assert added.is_error is False
        report = await session.call_tool(
            "rc_generate_contract_report",
            {
                "session_id": "stdio-report-schema-case",
                "format": "markdown",
                "locale": "zh-TW",
                "audience": "clinician",
                "finalize": False,
            },
        )

    assert report.is_error is False
    structured = report.structured_content
    assert isinstance(structured, dict)
    assert isinstance(structured["content"], str)
    assert structured["locale"] == "zh-TW"
    assert structured["audience"] == "clinician"
    assert "Clinical Reasoning 與 Root Cause 分析報告" in structured["content"]


def test_english_and_custom_reports_do_not_render_placeholder_probability(
    tmp_path: Path,
) -> None:
    """Legacy numeric state must not be presented as patient probability."""
    hypothesis_id = "HYP-placeholder-regression"
    report = ContractReport(
        report_id="RPT-placeholder-regression",
        session_id="placeholder-regression",
        generated_by="test-agent",
        hypotheses=[
            {
                "id": hypothesis_id,
                "diagnosis": {
                    "display": "Hyperkalemia-associated ventricular tachyarrhythmia"
                },
                "prior_probability": 0.1,
                "current_probability": 0.1,
                "mechanism_category": "METABOLIC_ENDOCRINE",
                "diagnostic_role": "ETIOLOGIC",
                "certainty": "POSSIBLE",
                "reasoning_basis": "MECHANISM_INFERENCE",
                "clinical_rationale": (
                    "The mechanism remains plausible but is not established."
                ),
                "status": "ACTIVE",
                "likelihood_ratios": [],
                "supporting_evidence_ids": [],
                "contradicting_evidence_ids": [],
                "uncertainty_factors": ["Original waveform is unavailable"],
                "planned_tests": [],
            }
        ],
        differential_breadth_audits=[
            {
                "audit_id": "DBA-placeholder-regression",
                "framework": "CUSTOM",
                "framework_name": "Arrest mechanism matrix",
                "framework_rationale": (
                    "The arrest phenotype warrants a structured mechanism review."
                ),
                "role": "PRIMARY",
                "cells": [
                    {
                        "cell_id": "METABOLIC",
                        "status": "CANDIDATES_PRESENT",
                        "hypothesis_ids": [hypothesis_id],
                        "mechanism_categories": ["METABOLIC_ENDOCRINE"],
                        "rationale": "This cell contains the retained metabolic candidate.",
                        "unknowns": [],
                        "planned_discriminators": [],
                    },
                    {
                        "cell_id": "OXYGENATION",
                        "status": "REVIEWED_NO_PLAUSIBLE_CANDIDATE",
                        "hypothesis_ids": [],
                        "mechanism_categories": [],
                        "rationale": "No plausible oxygenation candidate was recorded.",
                        "unknowns": [],
                        "planned_discriminators": [],
                    },
                    {
                        "cell_id": "TOXIC_IATROGENIC",
                        "status": "NOT_ASSESSED",
                        "hypothesis_ids": [],
                        "mechanism_categories": [],
                        "rationale": "The medication record has not yet been reviewed.",
                        "unknowns": ["Medication administration record is unavailable"],
                        "planned_discriminators": [],
                    },
                ],
                "stop_rationale": (
                    "The review remains open pending the medication source record."
                ),
                "recorded_by": "test-agent",
                "recorded_at": "2026-08-18T00:00:00Z",
            }
        ],
    )

    english = render_contract_report_markdown(report)
    assert "Qualitative certainty" in english
    assert "POSSIBLE" in english
    assert "| Prior |" not in english
    assert "| Posterior |" not in english
    assert "10%" not in english
    assert "0.1" not in english

    shipped_custom = render_contract_report_markdown(
        report,
        template_path="clinical_reasoning_report_template.md",
    )
    assert "{{top_certainty}}" not in shipped_custom
    assert "{{differential_breadth_audit_section}}" not in shipped_custom
    assert "Leading Working Diagnosis:** None (Qualitative certainty: UNKNOWN)" in (
        shipped_custom
    )
    assert "POSSIBLE" in shipped_custom
    assert "## Differential Diagnosis Breadth Audit" in shipped_custom
    assert "10%" not in shipped_custom
    assert "0.1" not in shipped_custom

    zh_custom = render_contract_report_markdown(
        report,
        template_path="clinician_ddx_discussion_zh_tw.md",
        locale="zh-TW",
        audience="clinician",
    )
    assert "{{" not in zh_custom
    assert "Clinical Reasoning 與 Root Cause 分析報告" in zh_custom
    assert "## DDx breadth audit" in zh_custom
    assert "### DDx 1：Hyperkalemia-associated ventricular tachyarrhythmia" in zh_custom
    assert (
        "- 為何納入：The mechanism remains plausible but is not established."
        in zh_custom
    )
    assert "- Unknowns：" in zh_custom
    assert "Original waveform is unavailable" in zh_custom
    assert "- Planned discriminating tests：" in zh_custom
    assert "Certainty：recorded `POSSIBLE`" in zh_custom
    assert "10%" not in zh_custom
    assert "0.1" not in zh_custom

    custom_root = tmp_path / "templates"
    custom_root.mkdir()
    custom_template = custom_root / "legacy-placeholder.md"
    custom_template.write_text(
        "# Custom\n\n{{hypothesis_table}}\n\nLegacy: {{top_probability}}\n",
        encoding="utf-8",
    )
    custom = render_contract_report_markdown(
        report,
        template_path=custom_template.name,
        template_root=custom_root,
    )
    assert (
        "Legacy: Not presented; use qualitative certainty and evidence disposition"
        in custom
    )
    assert "## Differential Diagnosis Breadth Audit" in custom
    assert "10%" not in custom
    assert "0.1" not in custom


def test_report_tool_schemas_advertise_locale_audience_and_string_content() -> None:
    """Both report surfaces should advertise the new opt-in presentation contract."""
    from rootcause_mcp.interface.tools import get_all_tools

    report_tools: dict[str, Any] = {}
    for profile in ("all", "condensed"):
        for tool in get_all_tools(profile):
            if tool.name in {"rc_generate_contract_report", "rc_report"}:
                report_tools[tool.name] = tool

    assert set(report_tools) == {"rc_generate_contract_report", "rc_report"}
    for tool in report_tools.values():
        properties = tool.input_schema["properties"]
        assert properties["locale"]["default"] == "en"
        assert properties["locale"]["enum"] == ["en", "zh-TW"]
        assert properties["audience"]["default"] == "general"
        assert properties["audience"]["enum"] == ["general", "clinician"]
        content_schema = tool.output_schema["properties"]["content"]
        assert {entry["type"] for entry in content_schema["oneOf"]} == {
            "string",
            "array",
        }


def test_neutral_lr_graph_and_perioperative_arrest_timeline_are_not_mislabelled() -> (
    None
):
    """LR=1 is neutral, while arrest/resuscitation events must not be baseline."""
    orchestrator = ClinicalReasoningOrchestrator("report-presenter-regression")
    evidence = orchestrator.add_evidence(
        content="02:48 VT alarm preceded pulseless arrest and CPR.",
        event_timestamp=datetime(2026, 8, 18, 2, 48, tzinfo=UTC),
        auto_verify=False,
    )
    hypothesis = orchestrator.propose_hypothesis(
        diagnosis="Hyperkalemia-associated ventricular tachyarrhythmia",
        rationale="The rhythm is compatible, but mechanism remains unproven.",
    )
    orchestrator.link_evidence_to_hypothesis(
        evidence_id=evidence.id.value,
        hypothesis_id=hypothesis.id.value,
        likelihood_ratio=1.0,
        supports=None,
        rationale="Qualitative compatibility only.",
        calibration_status="QUANTITATIVELY_UNKNOWN",
    )

    graph = build_evidence_graph(
        orchestrator.evidence_store.values(),
        orchestrator.hypothesis_store.values(),
    )
    assert graph["edges"] == [
        {
            "source": evidence.id.value,
            "target": hypothesis.id.value,
            "relationship": "neutral",
        }
    ]
    assert "neutral LR=1" in graph["mermaid"]
    assert '|"supports"|' not in graph["mermaid"]

    timeline = build_timeline(
        custom_events=[
            {
                "time": "2026-08-17T23:25:00+08:00",
                "content": "Induction with propofol and rocuronium.",
            },
            {
                "time": "2026-08-18T02:49:00+08:00",
                "content": "Pulseless cardiac arrest; CPR initiated.",
            },
            {
                "time": "2026-08-18T03:02:00+08:00",
                "content": "ROSC after defibrillation.",
            },
        ]
    )
    phases = {event["content"]: event["phase"] for event in timeline["events"]}
    assert timeline["pattern"] == "perioperative_sequence"
    assert phases["Pulseless cardiac arrest; CPR initiated."] == (
        "5. Critical Collapse & Resuscitation"
    )
    assert phases["ROSC after defibrillation."] == (
        "5. Critical Collapse & Resuscitation"
    )
