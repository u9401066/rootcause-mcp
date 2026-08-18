"""Deterministic conformance probes for the typed report contract."""

from __future__ import annotations

from collections.abc import Mapping
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
AUTHORIZED_REVIEWERS = frozenset({"reviewer", "Dr Reviewer"})


def _diagnosis(
    hypothesis_id: str,
    display: str,
    probability: float,
    *,
    must_not_miss: bool = False,
) -> dict[str, Any]:
    mechanism_by_id = {
        "HYP-1": "VASCULAR",
        "HYP-2": "FUNCTIONAL_PHYSIOLOGIC",
        "HYP-3": "METABOLIC_ENDOCRINE",
    }
    return {
        "id": hypothesis_id,
        "diagnosis": {"code": display, "display": display, "system": "CUSTOM"},
        "prior_probability": probability,
        "current_probability": probability,
        "probability_semantics": "UNCALIBRATED_COMPATIBILITY_ONLY",
        "clinical_probability_established": False,
        "must_not_miss": must_not_miss,
        "mechanism_category": mechanism_by_id[hypothesis_id],
        "diagnostic_role": "ETIOLOGIC",
        "certainty": "POSSIBLE",
        "reasoning_basis": "MECHANISM_INFERENCE",
        "uncertainty_factors": ["Definitive adjudication remains pending"],
        "supporting_evidence_ids": ["EVD-1"],
        "contradicting_evidence_ids": ["EVD-2"],
        "likelihood_ratios": [
            {
                "evidence_id": "EVD-1",
                "applied_likelihood_ratio": 2.0,
                "supports": True,
                "rationale": "Direct supporting relationship.",
                "calibration_status": "SOURCE_CALIBRATED",
                "calibration_source_ref": "EVD-CAL-1",
            },
            {
                "evidence_id": "EVD-2",
                "applied_likelihood_ratio": 0.5,
                "supports": False,
                "rationale": "Direct refuting relationship.",
                "calibration_status": "SOURCE_CALIBRATED",
                "calibration_source_ref": "EVD-CAL-1",
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
        "temporal": {
            "kind": "instant",
            "raw_value": GENERATED_AT.isoformat(),
            "precision": "second",
            "normalized_start": GENERATED_AT.isoformat(),
            "normalized_end": GENERATED_AT.isoformat(),
            "timezone_provenance": "source_explicit_offset",
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


def _breadth_audit() -> dict[str, Any]:
    hypothesis_by_cell = {
        "HYP-1": "VASCULAR",
        "HYP-2": "FUNCTIONAL_PHYSIOLOGIC",
        "HYP-3": "METABOLIC_ENDOCRINE",
    }
    hypothesis_by_cell = {
        category: hypothesis_id
        for hypothesis_id, category in hypothesis_by_cell.items()
    }
    return {
        "audit_id": "DBA-contract",
        "framework": "VINDICATE",
        "framework_rationale": (
            "VINDICATE systematically reviews etiologic mechanisms for this fixture."
        ),
        "role": "PRIMARY",
        "cells": [
            {
                "cell_id": cell_id,
                "status": (
                    "CANDIDATES_PRESENT"
                    if cell_id in hypothesis_by_cell
                    else "REVIEWED_NO_PLAUSIBLE_CANDIDATE"
                ),
                "hypothesis_ids": (
                    [hypothesis_by_cell[cell_id]]
                    if cell_id in hypothesis_by_cell
                    else []
                ),
                "mechanism_categories": (
                    [cell_id] if cell_id in hypothesis_by_cell else []
                ),
                "rationale": (
                    "The linked diagnosis represents this etiologic mechanism."
                    if cell_id in hypothesis_by_cell
                    else "This etiologic mechanism was reviewed without a plausible candidate."
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
            "All declared cells were reviewed before stopping differential expansion."
        ),
        "recorded_by": "test-agent",
        "recorded_at": GENERATED_AT.isoformat(),
    }


def _calibration_evidence() -> dict[str, Any]:
    return {
        "id": "EVD-CAL-1",
        "content": "Published diagnostic performance table reports LR values.",
        "evidence_type": "LITERATURE",
        "quality": {"strength": "STRONG", "reliability": "GRADE_A"},
        "source": {
            "document_id": "SRC-1",
            "location": "Reference appendix, Table 1",
            "raw_snippet": "Positive LR 2.0; negative LR 0.5",
            "content_hash": "c" * 64,
            "extraction_method": "verbatim_quote",
            "collected_by": "test-extractor",
            "collection_timestamp": GENERATED_AT.isoformat(),
        },
        "temporal": {
            "kind": "unknown",
            "raw_value": None,
            "precision": "unknown",
            "normalized_start": None,
            "normalized_end": None,
            "timezone_provenance": "unknown",
        },
        "event_timestamp": None,
        "supports_hypothesis_ids": [],
        "contradicts_hypothesis_ids": [],
        "verified": True,
        "verifier": "reviewer",
        "verification_method": "EXACT_SNIPPET_MATCH",
    }


def _preliminary_report(*, mermaid: str = "flowchart LR") -> ContractReport:
    root_description = "Escalation trigger was absent from the handoff"
    evidence = [
        _evidence("EVD-1", "SRC-1", "Observed supporting finding."),
        _evidence("EVD-2", "SRC-2", "Observed disconfirming finding."),
        _calibration_evidence(),
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
        leading_hypothesis_id="HYP-1",
        differential_breadth_audits=[_breadth_audit()],
        evidence=evidence,
        source_inventory=[
            {
                "document": "SRC-1",
                "source_uri": "file:///case/source-1.txt",
                "sha256": "1" * 64,
                "media_type": "text/plain",
                "source_kind": "progress_note",
                "de_identified": True,
                "evidence_count": 2,
                "verified_count": 2,
                "coverage_status": "reviewed",
                "independence_status": "independent",
                "source_group_id": "GROUP-1",
                "parent_document_id": None,
                "derivation_method": None,
                "source_review_adjudication_id": "SRV-source-1",
                "source_reviewed_by": "Dr Reviewer",
                "source_reviewed_at": GENERATED_AT.isoformat(),
                "source_review_reason": "Source extraction and lineage reviewed.",
            },
            {
                "document": "SRC-2",
                "source_uri": "file:///case/source-2.txt",
                "sha256": "2" * 64,
                "media_type": "text/plain",
                "source_kind": "imaging",
                "de_identified": True,
                "evidence_count": 1,
                "verified_count": 1,
                "coverage_status": "reviewed",
                "independence_status": "independent",
                "source_group_id": "GROUP-2",
                "parent_document_id": None,
                "derivation_method": None,
                "source_review_adjudication_id": "SRV-source-2",
                "source_reviewed_by": "Dr Reviewer",
                "source_reviewed_at": GENERATED_AT.isoformat(),
                "source_review_reason": "Source extraction and lineage reviewed.",
            },
        ],
        source_review_ledger=[
            {
                "adjudication_id": "SRV-source-1",
                "manifest_digest": f"sha256:{'d' * 64}",
                "document_id": "SRC-1",
                "status": "reviewed",
                "de_identified": True,
                "independence_status": "independent",
                "source_group_id": "GROUP-1",
                "parent_document_id": None,
                "derivation_method": None,
                "reviewed_by": "Dr Reviewer",
                "reason": "Source extraction and lineage reviewed.",
                "reviewed_at": GENERATED_AT.isoformat(),
            },
            {
                "adjudication_id": "SRV-source-2",
                "manifest_digest": f"sha256:{'d' * 64}",
                "document_id": "SRC-2",
                "status": "reviewed",
                "de_identified": True,
                "independence_status": "independent",
                "source_group_id": "GROUP-2",
                "parent_document_id": None,
                "derivation_method": None,
                "reviewed_by": "Dr Reviewer",
                "reason": "Source extraction and lineage reviewed.",
                "reviewed_at": GENERATED_AT.isoformat(),
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
                    "temporal": evidence[0]["temporal"],
                    "chronology_status": "ORDERED_INSTANT",
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
            },
            {
                "id": "THINK-LEAD-1",
                "timestamp": GENERATED_AT.isoformat(),
                "thinking_type": "DECISION_POINT",
                "content": "Explicitly selected the current leading diagnosis.",
                "internal_reasoning": (
                    "The selected diagnosis best fits the current linked evidence."
                ),
                "structured_data": {
                    "record_type": "LEADING_HYPOTHESIS_SELECTION",
                    "selection": {
                        "selection_id": "LHS-typed-1",
                        "hypothesis_id": "HYP-1",
                        "previous_hypothesis_id": None,
                        "reason": (
                            "The selected diagnosis best fits the current linked evidence."
                        ),
                        "changed_by": "reviewer",
                        "changed_at": GENERATED_AT.isoformat(),
                    },
                },
            },
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
            "source_manifest_digest": f"sha256:{'d' * 64}",
            "source_document_count": 2,
            "source_review_event_count": 2,
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
                            "hfacs_code": "UA-DE",
                            "hfacs_review_status": "CONFIRMED",
                            "hfacs_reviewed_by": "reviewer",
                            "hfacs_reviewed_at": GENERATED_AT.isoformat(),
                            "hfacs_review_reason": (
                                "Decision-error classification independently reviewed."
                            ),
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
                "hfacs_code": "UA-DE",
                "review_status": "CONFIRMED",
                "reviewed_by": "reviewer",
                "reviewed_at": GENERATED_AT.isoformat(),
                "review_reason": (
                    "Decision-error classification independently reviewed."
                ),
                "confidence": 0.8,
                "evidence": ["EVD-1"],
                "verified": True,
                "source": "fishbone_cause",
            }
        ],
        causation_verifications=[
            {
                "verification_id": "VER-1",
                "verification_level": "standard",
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
                "tests": {
                    "temporality": {
                        "passed": False,
                        "conclusion": (
                            "The supplied evidence does not establish causal chronology."
                        ),
                    },
                    "necessity": {
                        "passed": False,
                        "counterfactual_question": (
                            "Would delayed recognition occur without the missing trigger?"
                        ),
                        "counterfactual_answer": "uncertain",
                        "reasoning": (
                            "The available records cannot resolve necessity."
                        ),
                    },
                },
                "interpretation": (
                    "Data are insufficient; retain only as a proposed relationship."
                ),
                "next_steps": ["Obtain timestamped escalation-policy records."],
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
            "checklist": {
                "evidence_count": 2,
                "verified_evidence_count": 2,
                "evidence_with_sources": 2,
                "hypotheses_count": 3,
                "unique_hypotheses_count": 3,
                "duplicate_normalized_diagnoses": [],
                "active_hypotheses_count": 3,
                "min_hypotheses_met": True,
                "mechanism_categories": [
                    "FUNCTIONAL_PHYSIOLOGIC",
                    "METABOLIC_ENDOCRINE",
                    "VASCULAR",
                ],
                "mechanism_categories_count": 3,
                "mechanism_breadth_met": True,
                "differential_breadth_audit_complete": True,
                "must_not_miss_hypotheses_count": 1,
                "must_not_miss_reviewed": True,
                "unlinked_evidence_count": 0,
                "disconfirming_evidence_tested": True,
                "active_differential_disposition_complete": True,
                "diagnostic_certainty_supported": True,
                "leading_hypothesis_id": "HYP-1",
                "explicit_leading_hypothesis_selected": True,
                "leading_selection_eligible": True,
                "leading_diagnosis_challenged": True,
                "must_not_miss_disposition_complete": True,
                "uncertainty_acknowledged": True,
                "bias_reviewed": True,
                "reasoning_steps_recorded": 1,
            },
            "missing_prerequisites": [],
            "next_recommended_actions": ["Generate the auditable final snapshot."],
            "push_questions": ["Is every claim source-linked and challenged?"],
            "is_ready_for_report": True,
        },
        evidence_metrics={
            "total_evidence": 3,
            "verified_evidence": 3,
            "strong_evidence": 1,
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
    report.finalize(
        "reviewer",
        authorized_reviewers=AUTHORIZED_REVIEWERS,
        finalized_at=FINALIZED_AT,
    )
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


@pytest.mark.parametrize(
    "mutate_final_payload",
    [
        lambda payload: payload["evidence"][0].pop("evidence_type"),
        lambda payload: payload["evidence"][0].pop("quality"),
        lambda payload: payload["evidence"][0]["quality"].pop("strength"),
        lambda payload: payload["evidence"][0].pop("verified"),
        lambda payload: payload["evidence"][0].pop("verification_method"),
        lambda payload: payload["evidence"][0].pop("event_timestamp"),
        lambda payload: payload["evidence"][0]["source"].pop("content_hash"),
        lambda payload: payload["source_inventory"][0].pop("sha256"),
        lambda payload: payload["evidence"][0].__setitem__("verified", False),
        lambda payload: payload["evidence"][0].__setitem__("verifier", None),
        lambda payload: payload["hypotheses"][0]["diagnosis"].__setitem__("code", ""),
        lambda payload: payload["hypotheses"][0].pop("probability_semantics"),
        lambda payload: payload["hypotheses"][0].__setitem__(
            "clinical_probability_established", True
        ),
        lambda payload: payload["hypotheses"][0]["likelihood_ratios"][0].pop(
            "calibration_status"
        ),
        lambda payload: payload["hypotheses"][0]["likelihood_ratios"][0].pop(
            "calibration_source_ref"
        ),
        lambda payload: payload.pop("leading_hypothesis_id"),
        lambda payload: payload["source_inventory"][0].__setitem__(
            "evidence_count", -1
        ),
        lambda payload: payload["source_inventory"][0].__setitem__(
            "de_identified", False
        ),
        lambda payload: payload["source_inventory"][0].pop(
            "source_review_adjudication_id"
        ),
        lambda payload: payload["source_inventory"][0].pop("source_reviewed_by"),
        lambda payload: payload["source_inventory"][0].pop("source_reviewed_at"),
        lambda payload: payload["source_inventory"][0].pop("source_review_reason"),
        lambda payload: payload["source_review_ledger"][0].pop("manifest_digest"),
        lambda payload: payload["source_review_ledger"][0].pop("parent_document_id"),
        lambda payload: payload["source_review_ledger"][0].__setitem__(
            "status", "registered"
        ),
        lambda payload: payload["rca_session"].pop("source_manifest_digest"),
        lambda payload: payload["rca_session"].pop("source_review_event_count"),
        lambda payload: payload["timeline"]["events"][0].__setitem__("time", ""),
        lambda payload: payload["causation_verifications"][0].pop("verification_level"),
        lambda payload: payload["causation_verifications"][0].pop("tests"),
        lambda payload: payload["causation_verifications"][0].pop("interpretation"),
        lambda payload: payload["causation_verifications"][0].pop("next_steps"),
    ],
    ids=[
        "evidence-type",
        "evidence-quality",
        "quality-strength",
        "evidence-verification-state",
        "evidence-verification-method",
        "evidence-time-state",
        "evidence-source-hash",
        "manifest-source-hash",
        "evidence-not-verified",
        "missing-evidence-verifier",
        "blank-diagnosis-code",
        "missing-probability-semantics",
        "false-clinical-probability-claim",
        "missing-lr-calibration-status",
        "missing-lr-calibration-source-ref",
        "missing-explicit-leading-id",
        "negative-source-evidence-count",
        "source-not-de-identified",
        "missing-source-review-event-id",
        "missing-source-reviewer",
        "missing-source-review-time",
        "missing-source-review-reason",
        "missing-ledger-manifest-binding",
        "incomplete-ledger-nullable-lineage",
        "ledger-registered-transition",
        "missing-session-manifest-digest",
        "missing-session-review-event-count",
        "blank-timeline-time",
        "missing-causation-verification-level",
        "missing-causation-tests",
        "missing-causation-interpretation",
        "missing-causation-next-steps",
    ],
)
def test_final_schema_and_runtime_reject_unsafe_nested_mutation(
    mutate_final_payload: Any,
) -> None:
    """A final envelope cannot hide an incomplete nested clinical record."""
    final_payload = _final_report().model_dump(mode="json")
    mutate_final_payload(final_payload)
    with pytest.raises(JsonSchemaValidationError):
        validate(final_payload, ContractReport.model_json_schema())

    preliminary = _preliminary_report()
    mutate_final_payload(preliminary.__dict__)
    with pytest.raises(ValueError, match="Cannot finalize"):
        preliminary.finalize(
            "reviewer",
            authorized_reviewers=AUTHORIZED_REVIEWERS,
            finalized_at=FINALIZED_AT,
        )


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
    assert isinstance(
        report.to_final_snapshot(authorized_reviewers=AUTHORIZED_REVIEWERS),
        FinalContractReport,
    )


def test_finalization_and_final_load_require_operator_authorization_context() -> None:
    with pytest.raises(ValueError, match="must identify a reviewer"):
        _preliminary_report().finalize(  # type: ignore[arg-type]
            None,
            authorized_reviewers=AUTHORIZED_REVIEWERS,
            finalized_at=FINALIZED_AT,
        )
    with pytest.raises(ValueError, match="cannot be None"):
        _preliminary_report().finalize(
            "reviewer",
            authorized_reviewers=None,
            finalized_at=FINALIZED_AT,
        )
    with pytest.raises(ValueError, match="cannot be empty"):
        _preliminary_report().finalize(
            "reviewer",
            authorized_reviewers=set(),
            finalized_at=FINALIZED_AT,
        )
    with pytest.raises(
        ValidationError, match="authorized_reviewers validation context"
    ):
        ContractReport.model_validate(_final_report().model_dump(mode="json"))
    with pytest.raises(ValidationError, match="hard conformance checks"):
        ContractReport.model_validate(
            _final_report().model_dump(mode="json"),
            context={"authorized_reviewers": {"different-reviewer"}},
        )


def test_finalization_time_cannot_precede_report_generation() -> None:
    with pytest.raises(ValueError, match="cannot precede generated_at"):
        _preliminary_report().finalize(
            "reviewer",
            authorized_reviewers=AUTHORIZED_REVIEWERS,
            finalized_at=GENERATED_AT - timedelta(seconds=1),
        )


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
        ContractReport.model_validate(
            payload,
            context={
                "authorized_reviewers": {
                    *AUTHORIZED_REVIEWERS,
                    replacement,
                }
            },
        )


def test_final_load_rejects_status_downgrade_with_final_metadata() -> None:
    payload = _final_report().model_dump(mode="json")
    payload["is_finalized"] = False

    with pytest.raises(ValidationError, match="Preliminary reports cannot carry"):
        ContractReport.model_validate(
            payload,
            context={"authorized_reviewers": AUTHORIZED_REVIEWERS},
        )


def test_final_snapshot_rejects_top_level_and_nested_mutation() -> None:
    report = _final_report()

    with pytest.raises(TypeError, match="immutable"):
        report.report_id = "RPT-other"
    with pytest.raises(TypeError, match="immutable"):
        report.hypotheses.append({})
    with pytest.raises(TypeError, match="immutable"):
        report.hypotheses[0]["status"] = "EXCLUDED"
    diagnosis = report.hypotheses[0]["diagnosis"]
    assert isinstance(diagnosis, Mapping)
    with pytest.raises(TypeError, match="immutable"):
        diagnosis["display"] = "Altered"
    with pytest.raises(TypeError, match="immutable"):
        report.conformance_checks[0].refs.append("#/tampered")
    with pytest.raises(TypeError, match="immutable"):
        report.conformance_checks[0].details["tampered"] = True
    with pytest.raises(TypeError, match="immutable"):
        report.model_copy(update={"report_id": "RPT-other"})


def test_final_snapshot_rejects_unbound_builtin_container_mutation() -> None:
    """Built-in base methods cannot bypass the immutable wrapper types."""
    report = _final_report()

    with pytest.raises(TypeError):
        list.append(report.hypotheses, {})
    with pytest.raises(TypeError):
        dict.__setitem__(report.hypotheses[0], "status", "EXCLUDED")
    assert report.verify_content_hash()


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
        report.finalize(
            "reviewer",
            authorized_reviewers=AUTHORIZED_REVIEWERS,
            finalized_at=FINALIZED_AT,
        )


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
        report.finalize(
            "reviewer",
            authorized_reviewers=AUTHORIZED_REVIEWERS,
            finalized_at=FINALIZED_AT,
        )


def test_hash_covers_persisted_rendering_used_in_clinician_output() -> None:
    first = _preliminary_report(mermaid="style version one")
    second = _preliminary_report(mermaid="style version two")
    first.finalize(
        "reviewer",
        authorized_reviewers=AUTHORIZED_REVIEWERS,
        finalized_at=FINALIZED_AT,
    )
    second.finalize(
        "reviewer",
        authorized_reviewers=AUTHORIZED_REVIEWERS,
        finalized_at=FINALIZED_AT,
    )

    assert first.content_hash != second.content_hash


def test_hash_does_not_globally_ignore_same_named_semantic_extension() -> None:
    first = _preliminary_report()
    second = _preliminary_report()
    first.root_causes[0]["table"] = "semantic extension one"
    second.root_causes[0]["table"] = "semantic extension two"
    first.finalize(
        "reviewer",
        authorized_reviewers=AUTHORIZED_REVIEWERS,
        finalized_at=FINALIZED_AT,
    )
    second.finalize(
        "reviewer",
        authorized_reviewers=AUTHORIZED_REVIEWERS,
        finalized_at=FINALIZED_AT,
    )

    assert first.content_hash != second.content_hash


def test_direct_final_model_validation_requires_metadata_and_matching_hash() -> None:
    payload = deepcopy(_preliminary_report().model_dump(mode="json"))
    payload["is_finalized"] = True
    with pytest.raises(ValidationError, match="approved_by"):
        ContractReport.model_validate(
            payload,
            context={"authorized_reviewers": AUTHORIZED_REVIEWERS},
        )


def test_rehashed_final_snapshot_cannot_remove_lifecycle_conformance_check() -> None:
    """A caller cannot delete a core PASS and legitimize it with a new hash."""
    payload = _final_report().model_dump(mode="json")
    payload["conformance_checks"] = [
        check
        for check in payload["conformance_checks"]
        if check["code"] != "TYPED_REPORT_SCHEMA"
    ]
    payload["content_hash"] = "0" * 64
    unvalidated = ContractReport.model_construct(**payload)
    payload["content_hash"] = unvalidated.compute_content_hash()

    with pytest.raises(ValidationError, match="lifecycle conformance checks"):
        ContractReport.model_validate(
            payload,
            context={"authorized_reviewers": AUTHORIZED_REVIEWERS},
        )
