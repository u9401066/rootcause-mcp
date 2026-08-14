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
    )
    certain = _hypothesis(1.0).bayesian_update(
        evidence_id="EVD-one",
        likelihood_ratio=0.2,
        updated_by="test-agent",
    )

    assert impossible.current_probability == 0.0
    assert certain.current_probability == 1.0


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
