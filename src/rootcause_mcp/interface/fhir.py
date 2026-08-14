"""FHIR presenters for RootCause MCP artifacts."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from rootcause_mcp.domain.value_objects.clinical_concept import (
    ClinicalConcept,
    CodingSystem,
)
from rootcause_mcp.domain.value_objects.contract_report import ContractReport

_SYSTEM_URLS = {
    CodingSystem.SNOMED_CT: "http://snomed.info/sct",
    CodingSystem.ICD_10: "http://hl7.org/fhir/sid/icd-10",
    CodingSystem.ICD_10_CM: "http://hl7.org/fhir/sid/icd-10-cm",
    CodingSystem.RXNORM: "http://www.nlm.nih.gov/research/umls/rxnorm",
    CodingSystem.LOINC: "http://loinc.org",
    CodingSystem.CPT: "http://www.ama-assn.org/go/cpt",
    CodingSystem.CUSTOM: "urn:rootcause-mcp:custom-clinical-concept",
}


def clinical_concept_to_fhir_coding(concept: ClinicalConcept) -> dict[str, str]:
    """Map a validated clinical concept to a FHIR Coding object."""
    coding = {
        "system": _SYSTEM_URLS[concept.system],
        "code": concept.code,
        "display": concept.display,
    }
    if concept.version:
        coding["version"] = concept.version
    return coding


def render_contract_report_fhir(report: ContractReport) -> dict[str, Any]:
    """Render a resilient FHIR-compatible DiagnosticReport resource."""
    ranked_hypotheses = sorted(
        report.hypotheses,
        key=_hypothesis_probability,
        reverse=True,
    )
    conclusion_codes: list[dict[str, list[dict[str, str]]]] = []
    for hypothesis in ranked_hypotheses[:3]:
        diagnosis = hypothesis.get("diagnosis")
        if not isinstance(diagnosis, dict):
            continue
        try:
            concept = ClinicalConcept.model_validate(diagnosis)
        except ValidationError:
            continue
        conclusion_codes.append(
            {"coding": [clinical_concept_to_fhir_coding(concept)]}
        )

    return {
        "resourceType": "DiagnosticReport",
        "id": report.report_id,
        "status": "final" if report.is_finalized else "preliminary",
        "code": {
            "coding": [
                {
                    "system": "urn:rootcause-mcp:report-type",
                    "code": "clinical-reasoning-report",
                    "display": "Clinical reasoning report",
                }
            ],
            "text": "Clinical Reasoning Report",
        },
        "effectiveDateTime": report.generated_at.isoformat(),
        "issued": report.finalized_at.isoformat() if report.finalized_at else None,
        "performer": [{"display": report.generated_by}],
        "conclusion": (
            f"Differential diagnosis with {len(report.hypotheses)} hypotheses"
        ),
        "conclusionCode": conclusion_codes,
    }


def _hypothesis_probability(hypothesis: dict[str, Any]) -> float:
    """Return a sortable probability without trusting persisted free-form data."""
    try:
        return float(hypothesis.get("current_probability", 0.0))
    except (TypeError, ValueError):
        return 0.0
