"""Focused regression tests for medical reasoning domain behavior."""

from rootcause_mcp.domain.entities.hypothesis import Hypothesis, HypothesisStatus
from rootcause_mcp.domain.value_objects.clinical_concept import (
    ClinicalConcept,
    CodingSystem,
)


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

    assert concept.to_fhir_coding() == {
        "system": "http://hl7.org/fhir/sid/icd-10",
        "code": "I21.9",
        "display": "Acute myocardial infarction",
    }


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
