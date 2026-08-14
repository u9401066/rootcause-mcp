"""
Tests for deterministic Provenance Verification and Multi-Loop Clinical Guidance.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from rootcause_mcp.application.clinical_reasoning_orchestrator import (
    ClinicalReasoningOrchestrator,
)
from rootcause_mcp.application.server_state import ServerState
from rootcause_mcp.domain.services.provenance_verifier import (
    ProvenanceVerifier,
)
from rootcause_mcp.domain.value_objects.reasoning_guidance import ReasoningStage
from rootcause_mcp.interface.handlers.contract_handlers import ContractHandlers
from rootcause_mcp.interface.handlers.dd_handlers import DDHandlers
from rootcause_mcp.interface.handlers.evidence_handlers import EvidenceHandlers
from rootcause_mcp.interface.handlers.reasoning_handlers import ReasoningHandlers
from rootcause_mcp.interface.handlers.thinking_handlers import ThinkingHandlers


def test_provenance_verifier_exact_snippet(tmp_path: Path) -> None:
    """ProvenanceVerifier should find verbatim snippets and calculate sha256 checksums."""
    sample_file = tmp_path / "nursing_notes.txt"
    sample_file.write_text(
        "Line 1: Patient admitted to ICU.\n"
        "Line 2: 08:30 BP 75/40 mmHg, HR 120 bpm recorded.\n"
        "Line 3: Norepinephrine infusion started.\n",
        encoding="utf-8",
    )

    verifier = ProvenanceVerifier(search_roots=[tmp_path])
    match = verifier.verify_provenance(
        document_id="nursing_notes.txt",
        raw_snippet="08:30 BP 75/40 mmHg, HR 120 bpm",
    )

    assert match.is_verified is True
    assert match.match_type == "EXACT_SNIPPET_MATCH"
    assert match.line_numbers == (2,)
    assert match.snippet_hash is not None
    assert match.snippet_hash.startswith("sha256:")
    assert "Line 2" in (match.file_path or "") or "nursing_notes.txt" in (
        match.file_path or ""
    )


def test_provenance_verifier_missing_file(tmp_path: Path) -> None:
    """ProvenanceVerifier should flag missing documents without crashing."""
    verifier = ProvenanceVerifier(search_roots=[tmp_path])
    match = verifier.verify_provenance(
        document_id="non_existent_record.txt",
        raw_snippet="Some hallucinated clinical claim",
    )

    assert match.is_verified is False
    assert match.match_type == "FILE_NOT_FOUND"
    assert "could not be located" in match.diagnostics


def test_provenance_verifier_snippet_mismatch(tmp_path: Path) -> None:
    """ProvenanceVerifier should catch hallucinated quotes in real files."""
    sample_file = tmp_path / "lab_results.txt"
    sample_file.write_text(
        "Troponin I: 0.02 ng/mL (Normal)\nPotassium: 4.1 mmol/L\n",
        encoding="utf-8",
    )

    verifier = ProvenanceVerifier(search_roots=[tmp_path])
    match = verifier.verify_provenance(
        document_id="lab_results.txt",
        raw_snippet="Troponin I: 15.5 ng/mL (Critical High)",
    )

    assert match.is_verified is False
    assert match.match_type == "SNIPPET_NOT_FOUND"


@pytest.mark.asyncio
async def test_multi_loop_clinical_guidance_progression() -> None:
    """Guidance engine should guide low-tier agents through multi-step completion."""
    orchestrator = ClinicalReasoningOrchestrator("guidance-session")

    # Step 1: Initial state -> Stage 1 EVIDENCE_COLLECTION
    g1 = orchestrator.get_guidance()
    assert g1.current_stage == ReasoningStage.EVIDENCE_COLLECTION
    assert g1.completeness_score < 0.3
    assert g1.is_ready_for_report is False
    assert any("rc_add_evidence" in act for act in g1.next_recommended_actions)

    # Ingest 2 evidence items
    ev1 = orchestrator.add_evidence(
        content="Postop hypotension 75/40 mmHg",
        source_document="chart.txt",
        raw_snippet="Postop hypotension 75/40 mmHg",
        auto_verify=False,
    )
    ev2 = orchestrator.add_evidence(
        content="ECG showing ST elevation",
        source_document="ecg.txt",
        raw_snippet="ECG showing ST elevation",
        auto_verify=False,
    )

    # Propose 1 hypothesis -> Stage 2 DIFFERENTIAL_EXPANSION
    hyp1 = orchestrator.propose_hypothesis(
        diagnosis="Acute myocardial infarction",
        prior_probability=0.3,
        rationale="Hypotension and ST elevation support acute MI.",
    )

    g2 = orchestrator.get_guidance()
    assert g2.current_stage == ReasoningStage.DIFFERENTIAL_EXPANSION
    assert g2.checklist["hypotheses_count"] == 1
    assert any("competing differential" in act for act in g2.next_recommended_actions)

    # Propose 2 more competing hypotheses (PE and Sepsis)
    hyp2 = orchestrator.propose_hypothesis(
        diagnosis="Pulmonary embolism",
        prior_probability=0.2,
        rationale="Recent surgery increases DVT/PE risk.",
    )
    assert hyp2.diagnosis.display == "Pulmonary embolism"
    hyp3 = orchestrator.propose_hypothesis(
        diagnosis="Septic shock",
        prior_probability=0.1,
        rationale="Postoperative fever and hypotension.",
    )

    # Step 3: Link evidence -> Stage 3 / 4
    orchestrator.link_evidence_to_hypothesis(
        evidence_id=ev1.id.value,
        hypothesis_id=hyp1.id.value,
        likelihood_ratio=5.0,
        supports=True,
        rationale="Hypotension supports MI shock.",
    )
    orchestrator.link_evidence_to_hypothesis(
        evidence_id=ev2.id.value,
        hypothesis_id=hyp1.id.value,
        likelihood_ratio=10.0,
        supports=True,
        rationale="ST elevation highly specific for STEMI.",
    )
    # Disconfirming check on hyp3 (Sepsis ruled out)
    orchestrator.exclude_hypothesis(
        hyp3.id.value,
        excluded_by="reviewer",
        reason="Normal WBC and no fever rules out active sepsis.",
    )

    # Add cognitive transparency reflection
    from rootcause_mcp.domain.entities.thinking_step import ThinkingStep, ThinkingType

    orchestrator.thinking_chain.add_step(
        ThinkingStep(
            thinking_type=ThinkingType.UNCERTAINTY_ACKNOWLEDGED,
            content="Awaiting serial troponin trend and bedside echocardiogram",
            internal_reasoning="Single troponin and ECG pattern must be confirmed with echo.",
            confidence=0.85,
            uncertainty_factors=["Bedside echo pending"],
            potential_biases=["Anchoring on initial ECG"],
        )
    )

    g_final = orchestrator.get_guidance()
    assert g_final.current_stage == ReasoningStage.READY_FOR_SYNTHESIS
    assert g_final.completeness_score >= 0.85
    assert g_final.is_ready_for_report is True
    assert any(
        "rc_generate_contract_report" in act for act in g_final.next_recommended_actions
    )


@pytest.mark.asyncio
async def test_handlers_include_guidance_and_audit_tool() -> None:
    """Evidence, DD, Thinking, and Reasoning handlers should expose guidance."""
    state = ServerState()
    ev_handler = EvidenceHandlers(state)
    dd_handler = DDHandlers(state)
    think_handler = ThinkingHandlers(state)
    reason_handler = ReasoningHandlers(state)

    session_id = "handler-guidance-test"

    # Add evidence
    res_ev = await ev_handler.handle(
        "rc_add_evidence",
        {
            "session_id": session_id,
            "content": "08:30 BP 75/40 mmHg",
            "source_document": "flowsheet.csv",
        },
    )
    assert res_ev["status"] == "success"
    assert "guidance" in res_ev
    assert res_ev["guidance"]["current_stage"] == "EVIDENCE_COLLECTION"

    # Propose hypothesis
    res_dd = await dd_handler.handle(
        "rc_propose_hypothesis",
        {
            "session_id": session_id,
            "diagnosis": "Cardiogenic shock",
            "clinical_reasoning": "Severe hypotension after cardiac procedure.",
            "differential_diagnoses_considered": [],
            "evidence_supporting": [res_ev["evidence_id"]],
            "uncertainty_factors": ["Echo pending"],
            "confidence_rationale": "High clinical suspicion",
        },
    )
    assert res_dd["status"] == "success"
    assert "guidance" in res_dd

    # Think aloud
    res_th = await think_handler.handle(
        "rc_think_aloud",
        {
            "session_id": session_id,
            "thinking_type": "DECISION_POINT",
            "content": "Cardiogenic shock is leading diagnosis",
            "internal_reasoning": "Classic shock physiology present.",
            "confidence": 0.75,
        },
    )
    assert res_th["status"] == "success"
    assert "guidance" in res_th

    # Explicit audit tool
    res_audit = await reason_handler.handle(
        "rc_audit_reasoning_state",
        {"session_id": session_id},
    )
    assert res_audit["status"] == "success"
    assert "stage" in res_audit
    assert "next_recommended_actions" in res_audit
    assert "checklist" in res_audit


@pytest.mark.asyncio
async def test_custom_markdown_report_template_rendering() -> None:
    """Verify that contract report rendering supports customizable Markdown templates."""
    state = ServerState()
    ev_handler = EvidenceHandlers(state)
    dd_handler = DDHandlers(state)
    contract_handler = ContractHandlers(state)

    session_id = "template-render-test"
    ev = await ev_handler.handle(
        "rc_add_evidence",
        {
            "session_id": session_id,
            "content": "Blood pressure 60/30 mmHg post-induction",
            "source_document": "examples/dynamic_lvot_obstruction_sam/DATA_SOURCE_02_ANESTHESIA_RECORD_INDUCTION.csv",
            "raw_snippet": '"08:15","Worsening","60/30","130","98%","25","Ephedrine 10mg IV","**NO RESPONSE**. BP dropping further."',
        },
    )
    h1 = await dd_handler.handle(
        "rc_propose_hypothesis",
        {
            "session_id": session_id,
            "diagnosis": "Dynamic LVOT Obstruction (SAM)",
            "clinical_reasoning": "Paradoxical worsening with ephedrine",
            "prior_probability": 0.4,
        },
    )
    await dd_handler.handle(
        "rc_link_evidence_to_hypothesis",
        {
            "session_id": session_id,
            "hypothesis_id": h1["hypothesis_id"],
            "evidence_id": ev["evidence_id"],
            "likelihood_ratio": 10.0,
            "supports": True,
        },
    )

    template_path = Path("config/templates/clinical_reasoning_report_template.md")
    assert template_path.exists(), (
        "Default template file should exist in config/templates"
    )

    report_res = await contract_handler.handle(
        "rc_generate_contract_report",
        {
            "session_id": session_id,
            "format": "markdown",
            "detail_level": "standard",
            "template_file": str(template_path),
        },
    )
    assert report_res["status"] == "success"
    rendered_md = report_res["content"]

    assert "# 🏥 Clinical Reasoning & Root Cause Report" in rendered_md
    assert "Dynamic LVOT Obstruction (SAM)" in rendered_md
    assert "Recommended Clinical Action Plan & Patient Safety Measures" in rendered_md
    assert "Audit Trail & Cryptographic Provenance" in rendered_md
