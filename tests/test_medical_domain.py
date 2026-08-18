"""Focused regression tests for medical reasoning domain behavior."""

import pytest

from rootcause_mcp.application.clinical_reasoning_orchestrator import (
    ClinicalReasoningOrchestrator,
)
from rootcause_mcp.domain.entities.hypothesis import Hypothesis, HypothesisStatus
from rootcause_mcp.domain.value_objects.clinical_concept import (
    ClinicalConcept,
    CodingSystem,
)
from rootcause_mcp.interface.fhir import clinical_concept_to_fhir_coding


def _hypothesis(probability: float) -> Hypothesis:
    return Hypothesis(
        diagnosis=ClinicalConcept(
            code="I21.9",
            display="Acute myocardial infarction",
            system=CodingSystem.ICD_10,
            version=None,
        ),
        prior_probability=probability,
        current_probability=probability,
        created_by="test-agent",
        clinical_rationale="Chest pain and troponin elevation support acute MI.",
    )


def test_clinical_concept_exports_fhir_coding() -> None:
    concept = _hypothesis(0.3).diagnosis

    assert clinical_concept_to_fhir_coding(concept) == {
        "system": "http://hl7.org/fhir/sid/icd-10",
        "code": "I21.9",
        "display": "Acute myocardial infarction",
    }


@pytest.mark.parametrize(
    ("system", "code"),
    [
        (CodingSystem.ICD_10, "not-an-icd-code"),
        (CodingSystem.SNOMED_CT, "I21.9"),
    ],
)
def test_clinical_concept_rejects_malformed_standard_codes(
    system: CodingSystem,
    code: str,
) -> None:
    with pytest.raises(ValueError):
        ClinicalConcept(
            code=code,
            display="Invalid concept",
            system=system,
            version=None,
        )


def test_custom_diagnosis_code_is_stable_and_fhir_safe() -> None:
    orchestrator = ClinicalReasoningOrchestrator("stable-code")
    hypothesis = orchestrator.propose_hypothesis(
        diagnosis="Acute myocardial infarction",
        rationale="Clinical syndrome requires a stable custom concept identifier.",
    )

    assert hypothesis.diagnosis.code == "CUSTOM-DD339F0D6655"
    assert clinical_concept_to_fhir_coding(hypothesis.diagnosis)["system"] == (
        "urn:rootcause-mcp:custom-clinical-concept"
    )


def test_bayesian_update_handles_probability_boundaries() -> None:
    impossible = _hypothesis(0.0).bayesian_update(
        evidence_id="EVD-zero",
        likelihood_ratio=5.0,
        updated_by="test-agent",
        supports=True,
    )
    certain = _hypothesis(1.0).bayesian_update(
        evidence_id="EVD-one",
        likelihood_ratio=0.2,
        updated_by="test-agent",
        supports=False,
    )

    assert impossible.current_probability == 0.0
    assert certain.current_probability == 1.0


def test_contradicting_likelihood_ratio_reduces_probability() -> None:
    contradicted = _hypothesis(0.3).bayesian_update(
        evidence_id="EVD-refutes",
        likelihood_ratio=0.145,
        updated_by="test-agent",
        supports=False,
    )

    assert contradicted.current_probability < 0.3
    assert contradicted.bayesian_history[-1].likelihood_ratio == pytest.approx(0.145)
    assert contradicted.contradicting_evidence_ids == ["EVD-refutes"]


@pytest.mark.parametrize(
    ("supports", "likelihood_ratio"),
    [(True, 0.5), (False, 2.0)],
)
def test_bayesian_update_rejects_directionally_inconsistent_lr(
    supports: bool,
    likelihood_ratio: float,
) -> None:
    with pytest.raises(ValueError, match="likelihood ratio"):
        _hypothesis(0.3).bayesian_update(
            evidence_id="EVD-inconsistent",
            likelihood_ratio=likelihood_ratio,
            updated_by="test-agent",
            supports=supports,
        )


def _verified_case_evidence(orchestrator: ClinicalReasoningOrchestrator, content: str):
    evidence = orchestrator.add_evidence(content, auto_verify=False).mark_verified(
        verifier="SYSTEM_PROVENANCE_VERIFIER",
        verification_method="EXACT_SNIPPET_MATCH",
    )
    orchestrator.evidence_store[evidence.id.value] = evidence
    return evidence


def _calibration_evidence(orchestrator: ClinicalReasoningOrchestrator) -> str:
    evidence = orchestrator.add_evidence(
        "Published validation table reports direct LR values.",
        evidence_type="LITERATURE",
        source_document="calibration.txt",
        source_location="Table 1",
        raw_snippet="Validated direct LR values 5.0, 3.0, and 0.2",
        extraction_method="verbatim_quote",
        auto_verify=False,
    ).mark_verified(
        verifier="SYSTEM_PROVENANCE_VERIFIER",
        verification_method="EXACT_SNIPPET_MATCH",
        content_hash="sha256:" + "a" * 64,
    )
    orchestrator.evidence_store[evidence.id.value] = evidence
    return evidence.id.value


def test_orchestrator_rejects_duplicate_evidence_update() -> None:
    orchestrator = ClinicalReasoningOrchestrator("no-double-counting")
    evidence = _verified_case_evidence(orchestrator, "A source-grounded finding")
    calibration_id = _calibration_evidence(orchestrator)
    hypothesis = orchestrator.propose_hypothesis(
        diagnosis="Test diagnosis",
        prior_probability=0.2,
        rationale="A sufficiently detailed clinical rationale.",
    )
    orchestrator.link_evidence_to_hypothesis(
        evidence.id.value,
        hypothesis.id.value,
        likelihood_ratio=3.0,
        supports=True,
        calibration_status="SOURCE_CALIBRATED",
        calibration_source_ref=calibration_id,
    )

    with pytest.raises(ValueError, match="duplicate Bayesian updates"):
        orchestrator.link_evidence_to_hypothesis(
            evidence.id.value,
            hypothesis.id.value,
            likelihood_ratio=3.0,
            supports=True,
            calibration_status="SOURCE_CALIBRATED",
            calibration_source_ref=calibration_id,
        )


def test_likelihood_metadata_does_not_invent_reciprocal_test_values() -> None:
    orchestrator = ClinicalReasoningOrchestrator("lr-metadata")
    supporting = _verified_case_evidence(orchestrator, "Supporting finding")
    contradicting = _verified_case_evidence(orchestrator, "Refuting finding")
    calibration_id = _calibration_evidence(orchestrator)
    hypothesis = orchestrator.propose_hypothesis(
        diagnosis="Test diagnosis",
        prior_probability=0.4,
        rationale="A sufficiently detailed clinical rationale.",
    )

    after_support = orchestrator.link_evidence_to_hypothesis(
        supporting.id.value,
        hypothesis.id.value,
        likelihood_ratio=5.0,
        supports=True,
        calibration_status="SOURCE_CALIBRATED",
        calibration_source_ref=calibration_id,
    )
    after_refute = orchestrator.link_evidence_to_hypothesis(
        contradicting.id.value,
        hypothesis.id.value,
        likelihood_ratio=0.2,
        supports=False,
        calibration_status="SOURCE_CALIBRATED",
        calibration_source_ref=calibration_id,
    )

    support_assessment, refute_assessment = after_refute.likelihood_ratios
    assert after_support.likelihood_ratios[0].lr_negative is None
    assert support_assessment.applied_likelihood_ratio == 5.0
    assert support_assessment.supports is True
    assert refute_assessment.lr_positive is None
    assert refute_assessment.applied_likelihood_ratio == 0.2
    assert refute_assessment.supports is False


def test_hypothesis_status_transition_is_auditable() -> None:
    excluded = _hypothesis(0.3).mark_excluded(
        excluded_by="reviewer-1",
        reason="CT angiography ruled out the diagnosis.",
    )

    assert excluded.status is HypothesisStatus.EXCLUDED
    assert len(excluded.status_history) == 1
    change = excluded.status_history[0]
    assert change.previous_status is HypothesisStatus.ACTIVE
    assert change.new_status is HypothesisStatus.EXCLUDED
    assert change.changed_by == "reviewer-1"
    assert change.reason == "CT angiography ruled out the diagnosis."
