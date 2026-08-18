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


def test_normalized_match_ignores_blank_lines(tmp_path: Path) -> None:
    sample_file = tmp_path / "notes.md"
    sample_file.write_text(
        "Document heading\n\nActual clinical content\n",
        encoding="utf-8",
    )
    verifier = ProvenanceVerifier(search_roots=[tmp_path])

    match = verifier.verify_provenance(
        document_id="notes.md",
        raw_snippet="THIS STRING DOES NOT EXIST",
    )

    assert match.is_verified is False
    assert match.match_type == "SNIPPET_NOT_FOUND"


def test_file_or_location_existence_does_not_verify_finding(tmp_path: Path) -> None:
    sample_file = tmp_path / "chart.txt"
    sample_file.write_text("Line 1: actual chart content\n", encoding="utf-8")
    verifier = ProvenanceVerifier(search_roots=[tmp_path])

    file_only = verifier.verify_provenance(document_id="chart.txt")
    location_only = verifier.verify_provenance(
        document_id="chart.txt",
        location="Line 1",
    )

    assert file_only.is_verified is False
    assert file_only.match_type == "FILE_EXISTS_UNVERIFIED"
    assert location_only.is_verified is False
    assert location_only.match_type == "LOCATION_EXISTS_UNVERIFIED"


def test_provenance_verifier_rejects_path_outside_approved_roots(
    tmp_path: Path,
) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("secret outside approved roots", encoding="utf-8")
    verifier = ProvenanceVerifier(search_roots=[allowed])

    match = verifier.verify_provenance(
        document_id=str(outside),
        raw_snippet="secret outside approved roots",
    )

    assert match.is_verified is False
    assert match.match_type == "FILE_NOT_FOUND"


def test_failed_match_is_not_silently_marked_verified(tmp_path: Path) -> None:
    sample_file = tmp_path / "lab.txt"
    sample_file.write_text("Potassium: 4.1 mmol/L\n", encoding="utf-8")
    orchestrator = ClinicalReasoningOrchestrator("failed-verification")
    orchestrator._provenance_verifier = ProvenanceVerifier(search_roots=[tmp_path])
    evidence = orchestrator.add_evidence(
        content="Potassium: 9.1 mmol/L",
        source_document="lab.txt",
        raw_snippet="Potassium: 9.1 mmol/L",
        auto_verify=False,
    )

    checked, match = orchestrator.verify_evidence(
        evidence.id.value,
        verified_by="agent",
    )

    assert match is not None and match.match_type == "SNIPPET_NOT_FOUND"
    assert checked.verified is False
    assert checked.verification_method is None


def test_manual_verification_requires_authorized_reviewer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sample_file = tmp_path / "scan.txt"
    sample_file.write_text("Unreadable transcription placeholder\n", encoding="utf-8")
    orchestrator = ClinicalReasoningOrchestrator("manual-verification")
    orchestrator._provenance_verifier = ProvenanceVerifier(search_roots=[tmp_path])
    evidence = orchestrator.add_evidence(
        content="Finding reviewed on original scan",
        source_document="scan.txt",
        raw_snippet="not machine-readable",
        auto_verify=False,
    )

    generic, _ = orchestrator.verify_evidence(
        evidence.id.value,
        verified_by="agent",
        manual_confirmation=True,
    )
    untrusted, _ = orchestrator.verify_evidence(
        evidence.id.value,
        verified_by="Dr Fake",
        manual_confirmation=True,
    )
    monkeypatch.setenv(
        "ROOTCAUSE_AUTHORIZED_REVIEWERS",
        "clinician-reviewer-17,quality-officer-2",
    )
    reviewed, _ = orchestrator.verify_evidence(
        evidence.id.value,
        verified_by="clinician-reviewer-17",
        manual_confirmation=True,
    )

    assert generic.verified is False
    assert untrusted.verified is False
    assert reviewed.verified is True
    assert reviewed.verification_method == "MANUAL_REVIEWER_CONFIRMATION"


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
    orchestrator.evidence_store[ev1.id.value] = ev1.mark_verified(
        verifier="SYSTEM_PROVENANCE_VERIFIER",
        verification_method="EXACT_SNIPPET_MATCH",
    )
    orchestrator.evidence_store[ev2.id.value] = ev2.mark_verified(
        verifier="SYSTEM_PROVENANCE_VERIFIER",
        verification_method="EXACT_SNIPPET_MATCH",
    )
    calibration = orchestrator.add_evidence(
        content="Published validation table reports the direct diagnostic LRs.",
        evidence_type="LITERATURE",
        source_document="chart.txt",
        source_location="Reference appendix, Table 1",
        raw_snippet="Validated findings LR 5.0, 10.0, and 1.5",
        extraction_method="verbatim_quote",
        auto_verify=False,
    ).mark_verified(
        verifier="SYSTEM_PROVENANCE_VERIFIER",
        verification_method="EXACT_SNIPPET_MATCH",
        content_hash="sha256:" + "a" * 64,
    )
    orchestrator.evidence_store[calibration.id.value] = calibration

    # Propose 1 hypothesis -> Stage 2 DIFFERENTIAL_EXPANSION
    hyp1 = orchestrator.propose_hypothesis(
        diagnosis="Acute myocardial infarction",
        prior_probability=0.3,
        rationale="Hypotension and ST elevation support acute MI.",
        mechanism_category="VASCULAR",
        diagnostic_role="ETIOLOGIC",
        certainty="POSSIBLE",
        reasoning_basis="MECHANISM_INFERENCE",
        uncertainty_factors=["Serial ECG and troponin remain pending"],
        planned_tests=[
            {
                "name": "Serial ECG and troponin",
                "purpose": "RULE_OUT",
                "expected_supporting_result": "Dynamic ischemic change",
                "expected_refuting_result": "Adequate serial studies remain negative",
                "status": "PLANNED",
            }
        ],
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
        must_not_miss=True,
        mechanism_category="TRAUMATIC_MECHANICAL",
        diagnostic_role="ETIOLOGIC",
        certainty="POSSIBLE",
        reasoning_basis="MECHANISM_INFERENCE",
        uncertainty_factors=["Definitive pulmonary vascular imaging is pending"],
        planned_tests=[
            {
                "name": "CT pulmonary angiography",
                "purpose": "RULE_OUT",
                "expected_supporting_result": "Pulmonary arterial filling defect",
                "expected_refuting_result": "Adequate study without filling defect",
                "status": "PLANNED",
            }
        ],
    )
    assert hyp2.diagnosis.display == "Pulmonary embolism"
    hyp3 = orchestrator.propose_hypothesis(
        diagnosis="Septic shock",
        prior_probability=0.1,
        rationale="Postoperative fever and hypotension.",
        mechanism_category="INFECTIOUS",
        diagnostic_role="ETIOLOGIC",
        certainty="POSSIBLE",
        reasoning_basis="MECHANISM_INFERENCE",
        uncertainty_factors=["Microbiologic confirmation is unavailable"],
    )
    orchestrator.select_leading_hypothesis(
        hyp1.id.value,
        reason="Acute myocardial infarction is explicitly selected for challenge.",
        changed_by="test-agent",
    )
    orchestrator.record_differential_breadth_audit(
        {
            "audit_id": "DBA-guidance-progression",
            "framework": "VINDICATE",
            "framework_rationale": (
                "Postoperative shock warrants systematic vascular and infectious review."
            ),
            "role": "PRIMARY",
            "cells": [
                {
                    "cell_id": cell_id,
                    "status": (
                        "CANDIDATES_PRESENT"
                        if any(
                            hypothesis.mechanism_category.value == cell_id
                            for hypothesis in (hyp1, hyp2, hyp3)
                        )
                        else "REVIEWED_NO_PLAUSIBLE_CANDIDATE"
                    ),
                    "hypothesis_ids": [
                        hypothesis.id.value
                        for hypothesis in (hyp1, hyp2, hyp3)
                        if hypothesis.mechanism_category.value == cell_id
                    ],
                    "mechanism_categories": (
                        [cell_id]
                        if any(
                            hypothesis.mechanism_category.value == cell_id
                            for hypothesis in (hyp1, hyp2, hyp3)
                        )
                        else []
                    ),
                    "rationale": (
                        "Retained candidates represent this canonical mechanism."
                        if any(
                            hypothesis.mechanism_category.value == cell_id
                            for hypothesis in (hyp1, hyp2, hyp3)
                        )
                        else "This canonical mechanism was reviewed without a plausible candidate."
                    ),
                    "unknowns": [],
                    "planned_discriminators": [],
                }
                for cell_id in (
                    "VASCULAR",
                    "INFECTIOUS",
                    "INFLAMMATORY_IMMUNE",
                    "NEOPLASTIC",
                    "DRUG_TOXIN_IATROGENIC",
                    "METABOLIC_ENDOCRINE",
                    "TRAUMATIC_MECHANICAL",
                    "CONGENITAL_GENETIC",
                    "DEGENERATIVE",
                    "FUNCTIONAL_PHYSIOLOGIC",
                )
            ],
            "stop_rationale": (
                "Every canonical VINDICATE cell was reviewed before stopping expansion."
            ),
            "recorded_by": "test-agent",
        }
    )

    # Step 3: Link evidence -> Stage 3 / 4
    orchestrator.link_evidence_to_hypothesis(
        evidence_id=ev1.id.value,
        hypothesis_id=hyp1.id.value,
        likelihood_ratio=5.0,
        supports=True,
        rationale="Hypotension supports MI shock.",
        calibration_status="SOURCE_CALIBRATED",
        calibration_source_ref=calibration.id.value,
    )
    orchestrator.link_evidence_to_hypothesis(
        evidence_id=ev2.id.value,
        hypothesis_id=hyp1.id.value,
        likelihood_ratio=10.0,
        supports=True,
        rationale="ST elevation highly specific for STEMI.",
        calibration_status="SOURCE_CALIBRATED",
        calibration_source_ref=calibration.id.value,
    )
    orchestrator.link_evidence_to_hypothesis(
        evidence_id=ev1.id.value,
        hypothesis_id=hyp2.id.value,
        likelihood_ratio=1.5,
        supports=True,
        rationale="Acute postoperative hypotension keeps PE in the differential.",
        calibration_status="SOURCE_CALIBRATED",
        calibration_source_ref=calibration.id.value,
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
    assert g_final.missing_prerequisites == []


def test_guidance_never_marks_incomplete_case_ready() -> None:
    orchestrator = ClinicalReasoningOrchestrator("not-ready")
    for index in range(2):
        evidence = orchestrator.add_evidence(
            content=f"Unverified finding {index}",
            source_document=f"missing-{index}.txt",
            auto_verify=False,
        )
        hypothesis = orchestrator.propose_hypothesis(
            diagnosis=f"Hypothesis {index}",
            rationale="A sufficiently detailed clinical rationale.",
        )
        orchestrator.link_evidence_to_hypothesis(
            evidence.id.value,
            hypothesis.id.value,
            likelihood_ratio=1.0,
            supports=None,
            calibration_status="QUANTITATIVELY_UNKNOWN",
        )

    guidance = orchestrator.get_guidance()

    assert guidance.is_ready_for_report is False
    assert guidance.current_stage is not ReasoningStage.READY_FOR_SYNTHESIS
    assert guidance.missing_prerequisites
    assert guidance.checklist["unlinked_evidence_count"] == 0
    assert guidance.checklist["disconfirming_evidence_tested"] is False


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
async def test_legacy_weight_is_rejected_instead_of_inventing_an_lr() -> None:
    state = ServerState()
    evidence_handler = EvidenceHandlers(state)
    dd_handler = DDHandlers(state)
    session_id = "refuting-direction"
    evidence = await evidence_handler.handle_add_evidence(
        {
            "session_id": session_id,
            "content": "Normal right ventricle without strain",
            "auto_verify": False,
        }
    )
    hypothesis = await dd_handler.handle_propose_hypothesis(
        {
            "session_id": session_id,
            "diagnosis": "Massive pulmonary embolism",
            "prior_probability": 0.3,
            "clinical_reasoning": "Acute shock requires explicit PE exclusion.",
        }
    )

    result = await dd_handler.handle_link_evidence(
        {
            "session_id": session_id,
            "evidence_id": evidence["evidence_id"],
            "hypothesis_id": hypothesis["hypothesis_id"],
            "calibration_status": "QUANTITATIVELY_UNKNOWN",
            "direction": "REFUTES",
            "weight": 0.9,
            "rationale": "Normal RV anatomy argues against massive PE.",
        }
    )

    assert result["status"] == "error"
    assert "weight is no longer accepted" in result["message"]
    assert "direct likelihood_ratio" in result["message"]

    orchestrator = await state.get_orchestrator(session_id)
    assert orchestrator is not None
    unchanged = orchestrator.hypothesis_store[hypothesis["hypothesis_id"]]
    assert unchanged.current_probability == pytest.approx(0.3)
    assert unchanged.bayesian_history == []


@pytest.mark.asyncio
async def test_omitted_likelihood_ratio_is_neutral() -> None:
    state = ServerState()
    evidence_handler = EvidenceHandlers(state)
    dd_handler = DDHandlers(state)
    session_id = "neutral-default-lr"
    evidence = await evidence_handler.handle_add_evidence(
        {
            "session_id": session_id,
            "content": "Nonspecific observation",
            "auto_verify": False,
        }
    )
    hypothesis = await dd_handler.handle_propose_hypothesis(
        {
            "session_id": session_id,
            "diagnosis": "Undifferentiated shock",
            "prior_probability": 0.3,
        }
    )

    result = await dd_handler.handle_link_evidence(
        {
            "session_id": session_id,
            "evidence_id": evidence["evidence_id"],
            "hypothesis_id": hypothesis["hypothesis_id"],
            "calibration_status": "QUANTITATIVELY_UNKNOWN",
        }
    )

    assert result["status"] == "success"
    assert result["applied_likelihood_ratio"] == 1.0
    assert result["posterior_probability"] == pytest.approx(0.3)
    orchestrator = await state.get_orchestrator(session_id)
    assert orchestrator is not None
    relationship = orchestrator.hypothesis_store[
        hypothesis["hypothesis_id"]
    ].likelihood_ratios[-1]
    assert relationship.lr_positive is None
    assert relationship.lr_negative is None


@pytest.mark.asyncio
async def test_add_evidence_accepts_canonical_event_timestamp() -> None:
    state = ServerState()
    handler = EvidenceHandlers(state)

    result = await handler.handle_add_evidence(
        {
            "session_id": "canonical-event-time",
            "content": "Hypotension began after induction",
            "event_timestamp": "2026-08-17T08:15:00+08:00",
            "auto_verify": False,
        }
    )

    assert result["status"] == "success"
    assert result["event_timestamp"] == "2026-08-17T08:15:00+08:00"


def test_short_source_line_cannot_verify_longer_invented_snippet(
    tmp_path: Path,
) -> None:
    source = tmp_path / "short-line.txt"
    source.write_text("BP\n", encoding="utf-8")
    verifier = ProvenanceVerifier(search_roots=[tmp_path])

    result = verifier.verify_provenance(
        document_id=str(source),
        raw_snippet="BP 35/15 after induction with no response to vasopressor",
    )

    assert result.is_verified is False
    assert result.match_type == "SNIPPET_NOT_FOUND"


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
    link = await dd_handler.handle(
        "rc_link_evidence_to_hypothesis",
        {
            "session_id": session_id,
            "hypothesis_id": h1["hypothesis_id"],
            "evidence_id": ev["evidence_id"],
            "likelihood_ratio": 1.0,
            "supports": None,
            "rationale": (
                "Quantitative LR is unavailable in this renderer-only fixture."
            ),
            "calibration_status": "QUANTITATIVELY_UNKNOWN",
        },
    )
    assert link["status"] == "success"

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
    assert "Discriminating Data Requests & Safety Handoff" in rendered_md
    assert "not patient-specific treatment orders" in rendered_md
    assert "Posterior Probability" not in rendered_md
    assert "Audit Trail & Cryptographic Provenance" in rendered_md
