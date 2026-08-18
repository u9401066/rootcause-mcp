"""
End-to-End test for complete clinical reasoning workflow.

Tests the full pipeline:
1. Add evidence
2. Propose hypotheses
3. Link evidence to hypotheses (Bayesian update)
4. Record thinking process
5. Generate CONTRACT report
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from rootcause_mcp.interface.contract_markdown import render_contract_report_markdown
from rootcause_mcp.interface.fhir import render_contract_report_fhir
from rootcause_mcp.interface.handlers import (
    ContractHandlers,
    DDHandlers,
    EvidenceHandlers,
    ThinkingHandlers,
)


async def _assert_markdown_report_levels(
    contract_handler: ContractHandlers,
    session_id: str,
) -> None:
    markdown_report = await contract_handler.handle(
        "rc_generate_contract_report",
        {
            "session_id": session_id,
            "format": "markdown",
            "detail_level": "standard",
            "finalize": False,
        },
    )
    markdown_path = Path(markdown_report["output_path"])
    markdown = markdown_path.read_text(encoding="utf-8")
    assert markdown_path.suffix == ".md"
    assert markdown_report["generation_mode"] == "deterministic"
    assert markdown_report["llm_tokens_used"] == 0
    assert markdown_report["artifact_bytes"] == len(markdown.encode())
    assert "## Executive Summary" in markdown
    assert "## Ranked Differential Diagnosis" in markdown
    assert "## Evidence Matrix" in markdown
    assert "## Uncertainty and Cognitive Safety" in markdown
    assert "## Automated Completeness Checks" in markdown
    assert "## Deterministic Conformance Checks" in markdown
    assert "this snapshot cannot be treated as final" not in markdown
    assert "1 evidence record(s) have not been independently verified" in markdown
    assert "## Evidence Graph" in markdown
    assert "Cardiogenic shock" in markdown
    assert "**1 evidence record**" in markdown
    assert "**1 hypothesis**" in markdown
    assert "nursing_flowsheet.csv @ Line 42" in markdown
    assert "## Recorded Agent Rationale" not in markdown

    brief_report = await contract_handler.handle(
        "rc_generate_contract_report",
        {
            "session_id": session_id,
            "format": "markdown",
            "detail_level": "brief",
        },
    )
    brief = Path(brief_report["output_path"]).read_text(encoding="utf-8")
    assert "## Evidence Graph" not in brief
    assert "## Reasoning Audit" not in brief

    full_report = await contract_handler.handle(
        "rc_generate_contract_report",
        {
            "session_id": session_id,
            "format": "markdown",
            "detail_level": "full",
        },
    )
    full = Path(full_report["output_path"]).read_text(encoding="utf-8")
    assert "## Recorded Agent Rationale" in full
    assert "Post-CABG patient with hypotension and tachycardia" in full


async def _assert_contract_inclusion_filters(
    contract_handler: ContractHandlers,
    session_id: str,
) -> None:
    minimal_report = await contract_handler.handle(
        "rc_generate_contract_report",
        {
            "session_id": session_id,
            "format": "json",
            "include_reasoning_chain": False,
            "include_thinking_chain": False,
            "include_evidence_graph": False,
            "include_quality_metrics": False,
        },
    )
    minimal_payload = json.loads(
        Path(minimal_report["output_path"]).read_text(encoding="utf-8")
    )
    assert minimal_payload["reasoning_chain"] == []
    assert minimal_payload["thinking_chain"] == []
    assert "evidence_graph" not in minimal_payload
    assert "evidence_metrics" not in minimal_payload
    assert "reasoning_metrics" not in minimal_payload
    assert "evidence_metrics" not in minimal_report
    assert "reasoning_metrics" not in minimal_report

    thinking_only_report = await contract_handler.handle(
        "rc_generate_contract_report",
        {
            "session_id": session_id,
            "format": "json",
            "include_reasoning_chain": False,
            "include_thinking_chain": True,
        },
    )
    thinking_only_payload = json.loads(
        Path(thinking_only_report["output_path"]).read_text(encoding="utf-8")
    )
    assert thinking_only_payload["reasoning_chain"] == []
    assert thinking_only_payload["thinking_chain"]


@pytest.mark.asyncio
async def test_complete_clinical_reasoning_workflow(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Test complete end-to-end clinical reasoning workflow."""
    monkeypatch.setenv("ROOTCAUSE_DATA_DIR", str(tmp_path))

    # Initialize shared state
    from rootcause_mcp.application.server_state import ServerState

    server_state = ServerState()

    # Initialize handlers with shared state
    thinking_handler = ThinkingHandlers(server_state)
    evidence_handler = EvidenceHandlers(server_state)
    dd_handler = DDHandlers(server_state)
    contract_handler = ContractHandlers(server_state)

    session_id = "e2e_test_session"

    # Step 1: Add evidence
    evd1 = await evidence_handler.handle(
        "rc_add_evidence",
        {
            "session_id": session_id,
            "content": "08:30 BP 75/40 mmHg, HR 120 bpm",
            "evidence_type": "DOCUMENT",
            "source_document": "nursing_flowsheet.csv",
            "source_location": "Line 42",
            "clinical_strength": "STRONG",
            "source_reliability": "GRADE_A",
        },
    )
    assert evd1["status"] == "success"
    assert "evidence_id" in evd1

    # Step 2: Record thinking process
    think1 = await thinking_handler.handle(
        "rc_think_aloud",
        {
            "session_id": session_id,
            "thinking_type": "HYPOTHESIS_CONSIDERED",
            "content": "Considering cardiogenic shock",
            "internal_reasoning": "Post-CABG patient with hypotension and tachycardia",
            "confidence": 0.7,
            "alternatives": [
                {
                    "alternative": "Septic shock",
                    "reason_rejected": "No fever, WBC normal",
                    "confidence_if_chosen": 0.3,
                }
            ],
        },
    )
    assert think1["status"] == "success"

    # Step 3: Propose hypothesis
    hyp1 = await dd_handler.handle(
        "rc_propose_hypothesis",
        {
            "session_id": session_id,
            "diagnosis": "Cardiogenic shock",
            "icd10_code": "R57.0",
            "prior_probability": 0.3,
            "clinical_reasoning": "Recent CABG, hypotension, on vasopressors",
            "differential_diagnoses_considered": [
                {
                    "diagnosis": "Septic shock",
                    "reason_rejected": "No fever, WBC normal",
                    "likelihood_if_not_rejected": "low",
                }
            ],
            "evidence_supporting": [evd1["evidence_id"]],
            "uncertainty_factors": ["Troponin pending", "Echo not done yet"],
            "confidence_rationale": "Moderate confidence due to typical presentation but pending labs",
        },
    )
    assert hyp1["status"] == "success"
    assert "hypothesis_id" in hyp1

    # Step 4: Link evidence to hypothesis (Bayesian update)
    link1 = await dd_handler.handle(
        "rc_link_evidence_to_hypothesis",
        {
            "session_id": session_id,
            "evidence_id": evd1["evidence_id"],
            "hypothesis_id": hyp1["hypothesis_id"],
            "likelihood_ratio": 5.0,
            "supports": True,
            "rationale": "Hypotension strongly supports cardiogenic shock in post-CABG patient",
        },
    )
    assert link1["status"] == "success"
    assert link1["posterior_probability"] > 0.3  # Prior was 0.3

    # Step 5: Get differential diagnosis
    ddx = await dd_handler.handle(
        "rc_get_differential_diagnosis",
        {
            "session_id": session_id,
            "status_filter": "ACTIVE",
            "min_probability": 0.01,
        },
    )
    assert ddx["status"] == "success"
    assert len(ddx["hypotheses"]) > 0

    excluded = await dd_handler.handle(
        "rc_exclude_hypothesis",
        {
            "session_id": session_id,
            "hypothesis_id": hyp1["hypothesis_id"],
            "exclusion_reason": "Subsequent imaging ruled out cardiogenic shock.",
            "excluded_by": "test-reviewer",
        },
    )
    assert excluded["status"] == "success"
    assert excluded["hypothesis_status"] == "EXCLUDED"

    # Step 6: Generate CONTRACT report
    report = await contract_handler.handle(
        "rc_generate_contract_report",
        {
            "session_id": session_id,
            "format": "json",
            "finalize": False,
            "include_reasoning_chain": True,
            "include_evidence_graph": True,
            "include_quality_metrics": True,
        },
    )
    assert report["status"] == "success"
    assert report["finalized"] is False
    assert "output_path" in report
    assert report["evidence_graph_nodes"] == 2
    assert report["evidence_graph_edges"] == 1

    report_payload = json.loads(Path(report["output_path"]).read_text(encoding="utf-8"))
    graph = report_payload["evidence_graph"]
    assert {node["type"] for node in graph["nodes"]} == {
        "evidence",
        "hypothesis",
    }
    assert graph["edges"] == [
        {
            "source": evd1["evidence_id"],
            "target": hyp1["hypothesis_id"],
            "relationship": "supports",
        }
    ]
    assert graph["mermaid"].startswith("```mermaid\nflowchart LR")

    await _assert_contract_inclusion_filters(contract_handler, session_id)

    fhir_report = await contract_handler.handle(
        "rc_generate_contract_report",
        {"session_id": session_id, "format": "fhir"},
    )
    fhir_path = Path(fhir_report["output_path"])
    assert fhir_path.suffix == ".json"
    assert json.loads(fhir_path.read_text(encoding="utf-8"))["resourceType"] == (
        "DiagnosticReport"
    )

    await _assert_markdown_report_levels(contract_handler, session_id)


def test_export_path_rejects_traversal(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """User-provided paths cannot write outside the configured export root."""
    from rootcause_mcp.infrastructure.export_paths import build_export_path

    monkeypatch.setenv("ROOTCAUSE_DATA_DIR", str(tmp_path / "data"))
    with pytest.raises(ValueError, match="must remain under"):
        build_export_path(
            session_id="case-001",
            artifact="reasoning_chain",
            extension="json",
            requested_path=str(tmp_path / "outside.json"),
        )


@pytest.mark.asyncio
async def test_contract_report_vo() -> None:
    """Test ContractReport value object."""
    from rootcause_mcp.domain.value_objects.contract_report import (
        ContractReport,
        EvidenceCoverageMetrics,
        ReasoningQualityMetrics,
    )

    # Create metrics
    evidence_metrics = EvidenceCoverageMetrics(
        total_evidence=10,
        verified_evidence=7,
        strong_evidence=5,
        moderate_evidence=3,
        weak_evidence=2,
    )

    reasoning_metrics = ReasoningQualityMetrics(
        total_steps=15,
        avg_confidence=0.75,
        hypothesis_coverage=0.8,
        evidence_coverage=0.9,
        decision_points=3,
        alternatives_considered=5,
        biases_identified=2,
        uncertainties_acknowledged=4,
    )

    # Create report
    report = ContractReport(
        report_id="RPT-001",
        session_id="test_session",
        generated_by="test_agent",
        hypotheses=[
            {
                "diagnosis": {
                    "code": "not-a-snomed-code",
                    "display": "Malformed persisted diagnosis",
                    "system": "SNOMED_CT",
                },
                "current_probability": 0.99,
            },
            {
                "diagnosis": {
                    "code": "233604007",
                    "display": "Pneumonia",
                    "system": "SNOMED_CT",
                    "version": None,
                },
                "current_probability": 0.2,
            },
            {
                "diagnosis": {
                    "code": "I21.9",
                    "display": "Acute myocardial infarction",
                    "system": "ICD_10",
                    "version": None,
                },
                "current_probability": 0.8,
            },
        ],
        evidence_metrics=evidence_metrics,
        reasoning_metrics=reasoning_metrics,
    )

    assert report.report_id == "RPT-001"
    assert not report.is_finalized

    # A typed preliminary envelope is renderable, but an incomplete clinical/RCA
    # aggregate must never be promoted to a final snapshot.
    with pytest.raises(ValueError, match="deterministic conformance failed"):
        report.finalize("test_reviewer")
    assert report.is_finalized is False
    assert report.content_hash is None

    # Test FHIR export
    fhir = render_contract_report_fhir(report)
    assert fhir["resourceType"] == "DiagnosticReport"
    assert fhir["status"] == "preliminary"
    assert "issued" not in fhir
    assert fhir["code"]["coding"][0] == {
        "system": "urn:rootcause-mcp:report-type",
        "code": "clinical-reasoning-report",
        "display": "Clinical reasoning report",
    }
    conclusion_codings = [entry["coding"][0] for entry in fhir["conclusionCode"]]
    assert [coding["code"] for coding in conclusion_codings] == [
        "I21.9",
        "233604007",
    ]
    assert [coding["system"] for coding in conclusion_codings] == [
        "http://hl7.org/fhir/sid/icd-10",
        "http://snomed.info/sct",
    ]
    markdown = render_contract_report_markdown(report)
    assert "INVALID CODE: SNOMED_CT:not-a-snomed-code" in markdown


def test_markdown_omits_timeline_only_for_invalid_persisted_evidence(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Malformed legacy evidence degrades explicitly without hiding other errors."""
    from rootcause_mcp.domain.value_objects.contract_report import ContractReport

    report = ContractReport(
        report_id="RPT-invalid-evidence",
        session_id="case-invalid-evidence",
        generated_by="test-agent",
        evidence=[{"id": "legacy-malformed", "content": "Incomplete persisted row"}],
    )

    with caplog.at_level("WARNING", logger="rootcause_mcp.interface.contract_markdown"):
        markdown = render_contract_report_markdown(report)

    assert "## Chronological Timeline" not in markdown
    assert "persisted evidence failed Evidence schema validation" in caplog.text


def test_contract_hash_ignores_derived_mermaid_presentation() -> None:
    from rootcause_mcp.domain.value_objects.contract_report import ContractReport

    graph = {
        "nodes": [{"id": "EVD-1", "type": "evidence", "label": "Finding"}],
        "edges": [],
        "warnings": [],
    }
    generated_at = datetime(2026, 8, 17, 8, 0, tzinfo=UTC)
    first = ContractReport(
        report_id="RPT-1",
        session_id="case-1",
        generated_at=generated_at,
        generated_by="test-agent",
        evidence_graph={**graph, "mermaid": "style version one"},
    )
    second = ContractReport(
        report_id="RPT-1",
        session_id="case-1",
        generated_at=generated_at,
        generated_by="test-agent",
        evidence_graph={**graph, "mermaid": "style version two"},
    )

    assert first.compute_content_hash() == second.compute_content_hash()

    changed_identity = second.model_copy(update={"report_id": "RPT-2"})
    assert first.compute_content_hash() != changed_identity.compute_content_hash()
