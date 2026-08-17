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
    ranked_hypotheses = report.ranked_conclusion_hypotheses()
    conclusion_codes: list[dict[str, list[dict[str, str]]]] = []
    for hypothesis in ranked_hypotheses[:3]:
        diagnosis = hypothesis.get("diagnosis")
        if not isinstance(diagnosis, dict):
            continue
        try:
            concept = ClinicalConcept.model_validate(diagnosis)
        except ValidationError:
            continue
        conclusion_codes.append({"coding": [clinical_concept_to_fhir_coding(concept)]})

    if ranked_hypotheses:
        leading_diagnosis = ranked_hypotheses[0].get("diagnosis")
        leading_display = (
            leading_diagnosis.get("display", "Unknown diagnosis")
            if isinstance(leading_diagnosis, dict)
            else "Unknown diagnosis"
        )
        conclusion = (
            f"Leading eligible diagnosis: {leading_display}; "
            f"{len(ranked_hypotheses)} eligible of {len(report.hypotheses)} "
            "recorded hypotheses"
        )
    else:
        conclusion = (
            "No active diagnosis hypothesis is eligible for conclusion; "
            f"{len(report.hypotheses)} hypotheses remain in the audit record"
        )
    if report.root_causes:
        conclusion += f"; {len(report.root_causes)} proposed structured root cause(s)"
    if report.gap_analysis:
        conclusion += (
            f"; {int(report.gap_analysis.get('total_conflicts', 0))} "
            "gap/conflict finding(s)"
        )

    resource: dict[str, Any] = {
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
        "performer": [{"display": report.generated_by}],
        "conclusion": conclusion,
        "conclusionCode": conclusion_codes,
    }
    if report.finalized_at is not None:
        resource["issued"] = report.finalized_at.isoformat()
    extensions = _contract_report_extensions(report)
    if extensions:
        resource["extension"] = extensions
    return resource


def _contract_report_extensions(report: ContractReport) -> list[dict[str, Any]]:
    """Map non-core RCA snapshots into namespaced FHIR extensions."""
    namespace = "urn:rootcause-mcp:StructureDefinition"
    extensions: list[dict[str, Any]] = []

    for source in report.source_inventory:
        extensions.append(
            {
                "url": f"{namespace}/source-inventory",
                "extension": _nested_extensions(
                    document=source.get("document") or "not-recorded",
                    evidenceCount=int(source.get("evidence_count", 0)),
                    verifiedCount=int(source.get("verified_count", 0)),
                    coverageStatus=source.get("coverage_status", "unknown"),
                    sourceSha256=source.get("sha256"),
                    mediaType=source.get("media_type"),
                    sourceKind=source.get("source_kind"),
                ),
            }
        )

    extensions.extend(_timeline_extensions(report, namespace))

    categories = (
        report.fishbone.get("categories", [])
        if isinstance(report.fishbone, dict)
        else []
    )
    for category in categories:
        if not isinstance(category, dict):
            continue
        for cause in category.get("causes", []):
            if not isinstance(cause, dict):
                continue
            extensions.append(
                {
                    "url": f"{namespace}/fishbone-cause",
                    "extension": _nested_extensions(
                        causeId=cause.get("cause_id"),
                        category=category.get("category"),
                        description=cause.get("description"),
                        verified=bool(cause.get("verified")),
                        hfacsCode=cause.get("hfacs_code"),
                    ),
                }
            )

    why_nodes = (
        report.why_tree.get("nodes", []) if isinstance(report.why_tree, dict) else []
    )
    for node in why_nodes:
        if not isinstance(node, dict):
            continue
        extensions.append(
            {
                "url": f"{namespace}/why-node",
                "extension": _nested_extensions(
                    nodeId=node.get("id"),
                    level=int(node.get("level", 0)),
                    question=node.get("question"),
                    answer=node.get("answer"),
                    rootCause=bool(node.get("is_root_cause")),
                    parentId=node.get("parent_id"),
                ),
            }
        )

    for root_cause in report.root_causes:
        extensions.append(
            {
                "url": f"{namespace}/root-cause",
                "extension": _nested_extensions(
                    causeId=root_cause.get("id"),
                    description=root_cause.get("answer"),
                    confidence=root_cause.get("confidence"),
                    evidenceCount=len(root_cause.get("evidence", [])),
                    causationResult=root_cause.get("causation_result"),
                    disposition=root_cause.get("disposition"),
                    verificationId=root_cause.get("causation_verification_id"),
                ),
            }
        )

    for verification in report.causation_verifications:
        cause_event = verification.get("cause_event", {})
        effect_event = verification.get("effect_event", {})
        confidence: object = verification.get("confidence", {})
        confidence_value = (
            confidence.get("value") if isinstance(confidence, dict) else confidence
        )
        extensions.append(
            {
                "url": f"{namespace}/causation-verification",
                "extension": _nested_extensions(
                    verificationId=verification.get("verification_id"),
                    causeId=cause_event.get("id"),
                    cause=cause_event.get("description"),
                    effect=effect_event.get("description"),
                    result=verification.get("overall_result"),
                    confidence=confidence_value,
                    auditScope=verification.get("audit_scope"),
                    clinicalCausalityEstablished=verification.get(
                        "clinical_causality_established"
                    ),
                ),
            }
        )

    extensions.extend(_conformance_extensions(report, namespace))

    for classification in report.hfacs_classifications:
        extensions.append(
            {
                "url": f"{namespace}/hfacs-classification",
                "extension": _nested_extensions(
                    causeId=classification.get("cause_id"),
                    code=classification.get("hfacs_code"),
                    confidence=classification.get("confidence"),
                    source=classification.get("source"),
                ),
            }
        )

    conflicts = (
        report.gap_analysis.get("conflicts", [])
        if isinstance(report.gap_analysis, dict)
        else []
    )
    for conflict in conflicts:
        if not isinstance(conflict, dict):
            continue
        extensions.append(
            {
                "url": f"{namespace}/clinical-gap-conflict",
                "extension": _nested_extensions(
                    conflictId=conflict.get("conflict_id"),
                    severity=conflict.get("severity"),
                    category=conflict.get("category"),
                    title=conflict.get("title"),
                    remedy=conflict.get("actionable_remedy"),
                ),
            }
        )
    return extensions


def _conformance_extensions(
    report: ContractReport,
    namespace: str,
) -> list[dict[str, Any]]:
    """Expose portable deterministic checks and final integrity metadata."""
    extensions = [
        {
            "url": f"{namespace}/conformance-check",
            "extension": _nested_extensions(
                code=check.code,
                status=check.status.value,
                severity=check.severity.value,
                message=check.message,
                references=",".join(str(ref) for ref in check.refs),
            ),
        }
        for check in report.conformance_checks
    ]
    if report.approved_by or report.content_hash:
        extensions.append(
            {
                "url": f"{namespace}/final-snapshot-integrity",
                "extension": _nested_extensions(
                    approvedBy=report.approved_by,
                    finalizedAt=(
                        report.finalized_at.isoformat()
                        if report.finalized_at is not None
                        else None
                    ),
                    contentSha256=report.content_hash,
                    hashVerified=report.verify_content_hash(),
                ),
            }
        )
    return extensions


def _timeline_extensions(
    report: ContractReport,
    namespace: str,
) -> list[dict[str, Any]]:
    """Map canonical timeline events without duplicating clinical narrative text."""
    timeline_events = (
        report.timeline.get("events", []) if isinstance(report.timeline, dict) else []
    )
    return [
        {
            "url": f"{namespace}/timeline-event",
            "extension": _nested_extensions(
                evidenceId=event.get("id"),
                eventTime=event.get("time"),
                phase=event.get("phase"),
                sourceDocument=event.get("source_document"),
                verified=bool(event.get("verified")),
            ),
        }
        for event in timeline_events
        if isinstance(event, dict)
    ]


def _nested_extensions(**values: Any) -> list[dict[str, Any]]:
    """Build primitive nested extensions while preserving scalar FHIR types."""
    nested: list[dict[str, Any]] = []
    for name, value in values.items():
        if value is None:
            continue
        rendered_value = value
        if isinstance(value, bool):
            value_key = "valueBoolean"
        elif isinstance(value, int):
            value_key = "valueInteger"
        elif isinstance(value, float):
            value_key = "valueDecimal"
        else:
            value_key = "valueString"
            rendered_value = str(value)
        nested.append({"url": name, value_key: rendered_value})
    return nested
