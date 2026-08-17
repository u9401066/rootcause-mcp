"""Deterministic conformance probes for the typed report contract."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from jsonschema import ValidationError as JsonSchemaValidationError
from jsonschema import validate
from pydantic import ValidationError

from rootcause_mcp.domain.services.final_report_conformance import (
    HARD_CONFORMANCE_CODES,
)
from rootcause_mcp.domain.value_objects.contract_report import (
    ConformanceCheck,
    ConformanceSeverity,
    ConformanceStatus,
    ContractReport,
    FinalContractReport,
)

GENERATED_AT = datetime(2026, 8, 17, 8, 0, tzinfo=UTC)
FINALIZED_AT = datetime(2026, 8, 17, 9, 0, tzinfo=UTC)


def _diagnosis(
    hypothesis_id: str,
    display: str,
    probability: float,
    *,
    must_not_miss: bool = False,
) -> dict[str, Any]:
    return {
        "id": hypothesis_id,
        "diagnosis": {"code": display, "display": display, "system": "CUSTOM"},
        "prior_probability": probability,
        "current_probability": probability,
        "must_not_miss": must_not_miss,
        "supporting_evidence_ids": ["EVD-1"],
        "contradicting_evidence_ids": ["EVD-2"],
        "likelihood_ratios": [
            {
                "evidence_id": "EVD-1",
                "applied_likelihood_ratio": 2.0,
                "supports": True,
                "rationale": "Direct supporting relationship.",
            },
            {
                "evidence_id": "EVD-2",
                "applied_likelihood_ratio": 0.5,
                "supports": False,
                "rationale": "Direct refuting relationship.",
            },
        ],
        "planned_tests": [
            {
                "test_id": f"TEST-{hypothesis_id}",
                "name": f"Disconfirm {display}",
                "purpose": "RULE_OUT" if must_not_miss else "DISCONFIRM",
                "target_hypothesis_id": hypothesis_id,
                "expected_supporting_result": "Specified supporting result",
                "expected_refuting_result": "Specified refuting result",
                "status": "PLANNED",
                "result_evidence_id": None,
                "result_summary": None,
            }
        ],
        "status": "ACTIVE",
        "clinical_rationale": f"Evidence-grounded rationale for {display}.",
        "created_by": "test-agent",
        "created_at": GENERATED_AT.isoformat(),
    }


def _evidence(evidence_id: str, document: str, content: str) -> dict[str, Any]:
    return {
        "id": evidence_id,
        "content": content,
        "evidence_type": "DOCUMENT",
        "quality": {"strength": "MODERATE", "reliability": "GRADE_A"},
        "source": {
            "document_id": document,
            "location": "line 1",
            "raw_snippet": content,
            "content_hash": "a" * 64,
            "extraction_method": "verbatim_quote",
            "collected_by": "test-extractor",
            "collection_timestamp": GENERATED_AT.isoformat(),
        },
        "event_timestamp": GENERATED_AT.isoformat(),
        "supports_hypothesis_ids": (
            ["HYP-1", "HYP-2", "HYP-3"] if evidence_id == "EVD-1" else []
        ),
        "contradicts_hypothesis_ids": (
            ["HYP-1", "HYP-2", "HYP-3"] if evidence_id == "EVD-2" else []
        ),
        "verified": True,
        "verifier": "reviewer",
        "verification_method": "EXACT_SNIPPET_MATCH",
    }


def _preliminary_report(*, mermaid: str = "flowchart LR") -> ContractReport:
    root_description = "Escalation trigger was absent from the handoff"
    evidence = [
        _evidence("EVD-1", "SRC-1", "Observed supporting finding."),
        _evidence("EVD-2", "SRC-2", "Observed disconfirming finding."),
    ]
    return ContractReport(
        report_id="RPT-1",
        session_id="CASE-1",
        generated_at=GENERATED_AT,
        generated_by="test-agent",
        hypotheses=[
            _diagnosis("HYP-1", "Leading diagnosis", 0.6),
            _diagnosis("HYP-2", "Competing diagnosis", 0.25),
            _diagnosis(
                "HYP-3",
                "Must-not-miss diagnosis",
                0.15,
                must_not_miss=True,
            ),
        ],
        evidence=evidence,
        source_inventory=[
            {
                "document": "SRC-1",
                "sha256": "1" * 64,
                "media_type": "text/plain",
                "source_kind": "progress_note",
                "evidence_count": 1,
                "verified_count": 1,
                "coverage_status": "reviewed",
            },
            {
                "document": "SRC-2",
                "sha256": "2" * 64,
                "media_type": "text/plain",
                "source_kind": "imaging",
                "evidence_count": 1,
                "verified_count": 1,
                "coverage_status": "reviewed",
            },
        ],
        timeline={
            "pattern": "acute_crisis",
            "title": "Canonical timeline",
            "events": [
                {
                    "id": "EVD-1",
                    "time": GENERATED_AT.isoformat(),
                    "phase": "Observation",
                    "content": "Observed supporting finding.",
                    "source_document": "SRC-1",
                    "verified": True,
                    "evidence_type": "DOCUMENT",
                }
            ],
            "mermaid": "timeline",
            "table": "| time | event |",
        },
        reasoning_chain=[
            {
                "id": "RS-1",
                "sequence_number": 1,
                "timestamp": GENERATED_AT.isoformat(),
                "step_type": "EVIDENCE_LINKING",
                "content": "Linked exact observations to competing diagnoses.",
                "rationale": "Keep source and hypothesis lineage explicit.",
                "evidence_ids": ["EVD-1", "EVD-2"],
                "hypothesis_ids": ["HYP-1", "HYP-2", "HYP-3"],
                "agent_id": "test-agent",
            }
        ],
        thinking_chain=[
            {
                "id": "THINK-1",
                "timestamp": GENERATED_AT.isoformat(),
                "thinking_type": "UNCERTAINTY_ACKNOWLEDGED",
                "content": "Uncertainty remains.",
                "internal_reasoning": "A planned disconfirming test remains necessary.",
                "confidence": 0.5,
                "uncertainty_factors": ["Pending tests"],
                "potential_biases": ["Anchoring"],
            }
        ],
        evidence_graph={
            "nodes": [{"id": "EVD-1", "type": "evidence", "label": "Finding"}],
            "edges": [],
            "warnings": [],
            "mermaid": mermaid,
        },
        rca_session={
            "session_id": "CASE-1",
            "status": "ACTIVE",
            "current_stage": "VERIFY",
            "problem_statement": "Delayed recognition",
            "source_document_count": 2,
        },
        fishbone={
            "fishbone_id": "FB-1",
            "problem_statement": "Delayed recognition",
            "categories": [
                {
                    "category": "Process",
                    "causes": [
                        {
                            "cause_id": "CAUSE-1",
                            "description": root_description,
                            "evidence": ["EVD-1"],
                            "verified": True,
                        }
                    ],
                }
            ],
        },
        why_tree={
            "initial_problem": "Delayed recognition",
            "depth": 1,
            "is_complete": True,
            "nodes": [
                {
                    "id": "CAUSE-1",
                    "level": 1,
                    "question": "Why was recognition delayed?",
                    "answer": root_description,
                    "is_root_cause": True,
                    "evidence": ["EVD-1"],
                }
            ],
            "root_causes": ["CAUSE-1"],
        },
        root_causes=[
            {
                "id": "CAUSE-1",
                "answer": root_description,
                "question": "Why was recognition delayed?",
                "level": 1,
                "evidence": ["EVD-1"],
                "causation_verification_id": "VER-1",
                "causation_result": "INSUFFICIENT_DATA",
                "disposition": "PROPOSED",
            }
        ],
        hfacs_classifications=[
            {
                "cause_id": "CAUSE-1",
                "cause": root_description,
                "category": "Process",
                "hfacs_code": "UA.DM",
                "confidence": 0.8,
                "evidence": ["EVD-1"],
                "verified": True,
                "source": "fishbone_cause",
            }
        ],
        causation_verifications=[
            {
                "verification_id": "VER-1",
                "verification_level": "comprehensive",
                "cause": root_description,
                "effect": "Delayed recognition",
                "cause_event": {
                    "id": "CAUSE-1",
                    "description": root_description,
                    "evidence": ["EVD-1"],
                },
                "effect_event": {
                    "id": None,
                    "description": "Delayed recognition",
                    "evidence": ["EVD-1"],
                },
                "overall_result": "INSUFFICIENT_DATA",
                "confidence": {"value": 0.4},
                "audit_scope": "CONSERVATIVE_CAUSATION_AUDIT",
                "clinical_causality_established": False,
            }
        ],
        gap_analysis={
            "session_id": "CASE-1",
            "total_conflicts": 0,
            "critical_count": 0,
            "high_count": 0,
            "conflicts": [],
            "guideline_alerts": [],
            "safety_invariants_met": True,
        },
        report_readiness={
            "session_id": "CASE-1",
            "current_stage": "READY_FOR_SYNTHESIS",
            "stage_display": "Ready",
            "completeness_score": 1.0,
            "checklist": {},
            "missing_prerequisites": [],
            "next_recommended_actions": [],
            "push_questions": [],
            "is_ready_for_report": True,
        },
        evidence_metrics={
            "total_evidence": 2,
            "verified_evidence": 2,
            "strong_evidence": 0,
            "moderate_evidence": 2,
            "weak_evidence": 0,
        },
        reasoning_metrics={
            "total_steps": 1,
            "avg_confidence": 0.5,
            "hypothesis_coverage": 1.0,
            "evidence_coverage": 1.0,
            "decision_points": 0,
            "alternatives_considered": 2,
            "biases_identified": 1,
            "uncertainties_acknowledged": 1,
        },
    )


def _final_report() -> ContractReport:
    report = _preliminary_report()
    report.finalize("reviewer", finalized_at=FINALIZED_AT)
    return report


def test_external_schema_rejects_minimal_envelope_and_nested_type_errors() -> None:
    schema = ContractReport.model_json_schema()

    with pytest.raises(JsonSchemaValidationError):
        validate(
            {"report_id": "R", "session_id": "S", "generated_by": "agent"},
            schema,
        )

    payload = _preliminary_report().model_dump(mode="json")
    payload["hypotheses"][0]["current_probability"] = "likely"
    with pytest.raises(JsonSchemaValidationError):
        validate(payload, schema)


def test_external_schema_conditionally_requires_complete_final_sections() -> None:
    schema = ContractReport.model_json_schema()
    payload = _preliminary_report().model_dump(mode="json")
    payload["is_finalized"] = True

    with pytest.raises(JsonSchemaValidationError):
        validate(payload, schema)

    final_payload = _final_report().model_dump(mode="json")
    validate(final_payload, schema)


def test_runtime_rejects_unknown_top_level_and_malformed_nested_values() -> None:
    with pytest.raises(ValidationError, match="extra_forbidden"):
        ContractReport(
            report_id="R",
            session_id="S",
            generated_by="agent",
            unexpected=True,
        )

    with pytest.raises(ValidationError, match=r"hypotheses\.0\.current_probability"):
        ContractReport(
            report_id="R",
            session_id="S",
            generated_by="agent",
            hypotheses=[{"current_probability": "likely"}],
        )


def test_finalization_adds_typed_checks_and_recomputable_full_snapshot_hash() -> None:
    report = _final_report()

    assert report.verify_content_hash()
    assert {check.code for check in report.conformance_checks} >= {
        "TYPED_REPORT_SCHEMA",
        "FINALIZATION_METADATA_COMPLETE",
        "CONTENT_HASH_RECOMPUTABLE",
    }
    assert all(
        isinstance(check, ConformanceCheck) for check in report.conformance_checks
    )
    assert report.approved_by == "reviewer"
    assert report.reviewed_by == ["reviewer"]
    assert report.finalized_at == FINALIZED_AT
    assert isinstance(report.to_final_snapshot(), FinalContractReport)


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("report_id", "RPT-tampered"),
        ("generated_at", (GENERATED_AT + timedelta(minutes=1)).isoformat()),
        ("finalized_at", (FINALIZED_AT + timedelta(minutes=1)).isoformat()),
        ("approved_by", "different-reviewer"),
    ],
)
def test_final_load_rejects_integrity_metadata_or_identity_tampering(
    field: str,
    replacement: str,
) -> None:
    payload = _final_report().model_dump(mode="json")
    payload[field] = replacement
    if field == "approved_by":
        payload["reviewed_by"] = [replacement]

    with pytest.raises(ValidationError, match="content_hash"):
        ContractReport.model_validate(payload)


def test_final_load_rejects_status_downgrade_with_final_metadata() -> None:
    payload = _final_report().model_dump(mode="json")
    payload["is_finalized"] = False

    with pytest.raises(ValidationError, match="Preliminary reports cannot carry"):
        ContractReport.model_validate(payload)


def test_final_snapshot_rejects_top_level_and_nested_mutation() -> None:
    report = _final_report()

    with pytest.raises(TypeError, match="immutable"):
        report.report_id = "RPT-other"
    with pytest.raises(TypeError, match="immutable"):
        report.hypotheses.append({})
    with pytest.raises(TypeError, match="immutable"):
        report.hypotheses[0]["status"] = "EXCLUDED"
    diagnosis = report.hypotheses[0]["diagnosis"]
    assert isinstance(diagnosis, dict)
    with pytest.raises(TypeError, match="immutable"):
        diagnosis["display"] = "Altered"
    with pytest.raises(TypeError, match="immutable"):
        report.conformance_checks[0].refs.append("#/tampered")
    with pytest.raises(TypeError, match="immutable"):
        report.conformance_checks[0].details["tampered"] = True
    with pytest.raises(TypeError, match="immutable"):
        report.model_copy(update={"report_id": "RPT-other"})


def test_failed_hard_check_blocks_finalization() -> None:
    report = _preliminary_report()
    report.conformance_checks = [
        ConformanceCheck(
            code="ROOT_LINEAGE_VALID",
            status=ConformanceStatus.FAIL,
            severity=ConformanceSeverity.HARD,
            message="Root evidence description mismatch.",
            refs=["#/root_causes/0"],
        )
    ]

    with pytest.raises(ValueError, match="ROOT_LINEAGE_VALID"):
        report.finalize("reviewer", finalized_at=FINALIZED_AT)


def test_fabricated_hard_passes_cannot_bypass_recomputed_invariants() -> None:
    report = _preliminary_report()
    report.root_causes[0]["answer"] = "Caller-substituted root description"
    report.conformance_checks = [
        ConformanceCheck(
            code=code,
            status=ConformanceStatus.PASS,
            severity=ConformanceSeverity.HARD,
            message="Caller claims this passed.",
            refs=[],
        )
        for code in HARD_CONFORMANCE_CODES
    ]

    with pytest.raises(ValueError, match="ROOT_EVIDENCE_LINEAGE"):
        report.finalize("reviewer", finalized_at=FINALIZED_AT)


def test_hash_ignores_only_derived_rendering_for_same_snapshot() -> None:
    first = _preliminary_report(mermaid="style version one")
    second = _preliminary_report(mermaid="style version two")
    first.finalize("reviewer", finalized_at=FINALIZED_AT)
    second.finalize("reviewer", finalized_at=FINALIZED_AT)

    assert first.content_hash == second.content_hash


def test_hash_does_not_globally_ignore_same_named_semantic_extension() -> None:
    first = _preliminary_report()
    second = _preliminary_report()
    first.root_causes[0]["table"] = "semantic extension one"
    second.root_causes[0]["table"] = "semantic extension two"
    first.finalize("reviewer", finalized_at=FINALIZED_AT)
    second.finalize("reviewer", finalized_at=FINALIZED_AT)

    assert first.content_hash != second.content_hash


def test_direct_final_model_validation_requires_metadata_and_matching_hash() -> None:
    payload = deepcopy(_preliminary_report().model_dump(mode="json"))
    payload["is_finalized"] = True
    with pytest.raises(ValidationError, match="approved_by"):
        ContractReport.model_validate(payload)
