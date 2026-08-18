"""Table-driven P0 probes for deterministic final-report invariants."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from rootcause_mcp.domain.services.final_report_conformance import (
    HARD_CONFORMANCE_CODES,
    evaluate_final_report_conformance,
    hard_failures,
)
from rootcause_mcp.domain.value_objects.contract_report import ContractReport


def _temporal_instant(raw_value: str) -> dict[str, Any]:
    return {
        "kind": "instant",
        "raw_value": raw_value,
        "precision": "second",
        "normalized_start": raw_value,
        "normalized_end": raw_value,
        "timezone_provenance": "source_explicit_offset",
    }


def _temporal_unknown() -> dict[str, Any]:
    return {
        "kind": "unknown",
        "raw_value": None,
        "precision": "unknown",
        "normalized_start": None,
        "normalized_end": None,
        "timezone_provenance": "unknown",
    }


def _retime_evidence(
    report: dict[str, Any],
    evidence_id: str,
    timestamp: str,
) -> None:
    """Keep Evidence and its timeline projection on one canonical instant."""
    for evidence in report["evidence"]:
        if evidence["id"] == evidence_id:
            evidence["temporal"] = _temporal_instant(timestamp)
            evidence["event_timestamp"] = timestamp
    for event in report["timeline"]["events"]:
        if event["id"] == evidence_id:
            event["time"] = timestamp
            event["temporal"] = _temporal_instant(timestamp)
            event["chronology_status"] = "ORDERED_INSTANT"


def _planned_test(hypothesis_id: str) -> dict[str, Any]:
    return {
        "test_id": f"TST-{hypothesis_id[-4:]}",
        "name": "Definitive local diagnostic study",
        "purpose": "RULE_OUT",
        "target_hypothesis_id": hypothesis_id,
        "expected_supporting_result": "Predefined positive pattern",
        "expected_refuting_result": "Predefined adequate negative pattern",
        "status": "PLANNED",
        "result_evidence_id": None,
        "result_summary": None,
    }


def _hypothesis(
    hypothesis_id: str,
    diagnosis: str,
    probability: float,
    *,
    must_not_miss: bool = False,
    contradicting: bool = False,
) -> dict[str, Any]:
    mechanism_by_id = {
        "HYP-1": "VASCULAR",
        "HYP-2": "FUNCTIONAL_PHYSIOLOGIC",
        "HYP-3": "METABOLIC_ENDOCRINE",
    }
    relationships = [
        {
            "evidence_id": "EVD-1",
            "applied_likelihood_ratio": 2.0,
            "supports": True,
            "rationale": "Direct supporting relationship",
            "calibration_status": "SOURCE_CALIBRATED",
            "calibration_source_ref": "EVD-CAL-1",
        }
    ]
    if contradicting:
        relationships.append(
            {
                "evidence_id": "EVD-2",
                "applied_likelihood_ratio": 0.2,
                "supports": False,
                "rationale": "Direct refuting relationship",
                "calibration_status": "SOURCE_CALIBRATED",
                "calibration_source_ref": "EVD-CAL-1",
            }
        )
    return {
        "id": hypothesis_id,
        "diagnosis": {"code": hypothesis_id, "display": diagnosis, "system": "CUSTOM"},
        "prior_probability": probability,
        "current_probability": probability,
        "probability_semantics": "UNCALIBRATED_COMPATIBILITY_ONLY",
        "clinical_probability_established": False,
        "must_not_miss": must_not_miss,
        "mechanism_category": mechanism_by_id[hypothesis_id],
        "diagnostic_role": "ETIOLOGIC",
        "certainty": "POSSIBLE",
        "reasoning_basis": "MECHANISM_INFERENCE",
        "uncertainty_factors": ["Definitive diagnostic adjudication remains pending"],
        "likelihood_ratios": relationships,
        "supporting_evidence_ids": ["EVD-1"],
        "contradicting_evidence_ids": ["EVD-2"] if contradicting else [],
        "planned_tests": [_planned_test(hypothesis_id)],
        "status": "ACTIVE",
        "clinical_rationale": f"Auditable rationale for {diagnosis}",
    }


def _valid_report() -> dict[str, Any]:
    hypotheses = [
        _hypothesis("HYP-1", "Pulmonary embolism", 0.50),
        _hypothesis("HYP-2", "Cardiogenic shock", 0.30),
        _hypothesis(
            "HYP-3",
            "Acute myocardial infarction",
            0.20,
            must_not_miss=True,
            contradicting=True,
        ),
    ]
    return {
        "report_id": "RPT-test",
        "session_id": "rc_sess_test",
        "generated_by": "agent",
        "leading_hypothesis_id": "HYP-1",
        "hypotheses": hypotheses,
        "differential_breadth_audits": [
            {
                "audit_id": "DBA-valid",
                "framework": "ANATOMIC_SYSTEM",
                "framework_rationale": (
                    "The presenting shock syndrome warrants systematic review "
                    "across canonical anatomic systems."
                ),
                "role": "PRIMARY",
                "cells": [
                    {
                        "cell_id": cell_id,
                        "status": (
                            "CANDIDATES_PRESENT"
                            if cell_id in {"CARDIOVASCULAR", "RESPIRATORY"}
                            else "REVIEWED_NO_PLAUSIBLE_CANDIDATE"
                        ),
                        "hypothesis_ids": (
                            ["HYP-2", "HYP-3"]
                            if cell_id == "CARDIOVASCULAR"
                            else ["HYP-1"]
                            if cell_id == "RESPIRATORY"
                            else []
                        ),
                        "mechanism_categories": (
                            ["FUNCTIONAL_PHYSIOLOGIC", "METABOLIC_ENDOCRINE"]
                            if cell_id == "CARDIOVASCULAR"
                            else ["VASCULAR"]
                            if cell_id == "RESPIRATORY"
                            else []
                        ),
                        "rationale": (
                            "Linked candidates remain plausible in this system."
                            if cell_id in {"CARDIOVASCULAR", "RESPIRATORY"}
                            else "This canonical system was reviewed without a plausible candidate."
                        ),
                        "unknowns": [],
                        "planned_discriminators": [],
                    }
                    for cell_id in (
                        "CARDIOVASCULAR",
                        "RESPIRATORY",
                        "NEUROLOGIC",
                        "GASTROINTESTINAL_HEPATOBILIARY",
                        "RENAL_GENITOURINARY",
                        "ENDOCRINE_METABOLIC",
                        "HEMATOLOGIC",
                        "INFECTIOUS_IMMUNE",
                        "MUSCULOSKELETAL",
                        "DERMATOLOGIC",
                        "PSYCHIATRIC_FUNCTIONAL",
                    )
                ],
                "stop_rationale": (
                    "All framework cells were reviewed and no additional plausible "
                    "candidate was supported by the supplied presentation."
                ),
                "recorded_by": "test-agent",
                "recorded_at": "2026-08-18T10:00:00+00:00",
            }
        ],
        "evidence": [
            {
                "id": "EVD-1",
                "content": "Observed hypotension",
                "evidence_type": "OBSERVATION",
                "quality": {"strength": "STRONG", "reliability": "GRADE_A"},
                "source": {
                    "document_id": "SRC-1",
                    "location": "Line 1",
                    "raw_snippet": "Observed hypotension",
                    "content_hash": "1" * 64,
                    "extraction_method": "verbatim_quote",
                    "collected_by": "test-agent",
                    "collection_timestamp": "2026-08-18T09:00:00+00:00",
                },
                "temporal": _temporal_instant("2026-08-18T09:00:00+00:00"),
                "event_timestamp": "2026-08-18T09:00:00+00:00",
                "supports_hypothesis_ids": ["HYP-1", "HYP-2", "HYP-3"],
                "contradicts_hypothesis_ids": [],
                "verified": True,
                "verifier": "SYSTEM_PROVENANCE_VERIFIER",
                "verification_method": "EXACT_SNIPPET_MATCH",
            },
            {
                "id": "EVD-2",
                "content": "Adequate negative study",
                "evidence_type": "TEST_RESULT",
                "quality": {"strength": "STRONG", "reliability": "GRADE_A"},
                "source": {
                    "document_id": "SRC-2",
                    "location": "Line 1",
                    "raw_snippet": "Adequate negative study",
                    "content_hash": "2" * 64,
                    "extraction_method": "verbatim_quote",
                    "collected_by": "test-agent",
                    "collection_timestamp": "2026-08-18T09:10:00+00:00",
                },
                "temporal": _temporal_instant("2026-08-18T09:10:00+00:00"),
                "event_timestamp": "2026-08-18T09:10:00+00:00",
                "supports_hypothesis_ids": [],
                "contradicts_hypothesis_ids": ["HYP-3"],
                "verified": True,
                "verifier": "SYSTEM_PROVENANCE_VERIFIER",
                "verification_method": "EXACT_SNIPPET_MATCH",
            },
            {
                "id": "EVD-CAL-1",
                "content": "Published diagnostic performance table reports LR 2.0.",
                "evidence_type": "LITERATURE",
                "quality": {"strength": "STRONG", "reliability": "GRADE_A"},
                "source": {
                    "document_id": "SRC-1",
                    "location": "Reference appendix, Table 1",
                    "raw_snippet": "Positive finding likelihood ratio 2.0",
                    "content_hash": "3" * 64,
                    "extraction_method": "verbatim_quote",
                    "collected_by": "test-agent",
                    "collection_timestamp": "2026-08-18T09:05:00+00:00",
                },
                "temporal": _temporal_unknown(),
                "event_timestamp": None,
                "supports_hypothesis_ids": [],
                "contradicts_hypothesis_ids": [],
                "verified": True,
                "verifier": "SYSTEM_PROVENANCE_VERIFIER",
                "verification_method": "EXACT_SNIPPET_MATCH",
            },
        ],
        "source_inventory": [
            {
                "document": "SRC-1",
                "source_uri": "file:///deidentified/source-1.txt",
                "sha256": "a" * 64,
                "media_type": "text/plain",
                "source_kind": "clinical_note",
                "de_identified": True,
                "evidence_count": 2,
                "verified_count": 2,
                "coverage_status": "reviewed",
                "source_review_adjudication_id": "SRV-review-1",
                "source_reviewed_by": "reviewer",
                "source_reviewed_at": "2026-08-18T09:30:00+00:00",
                "source_review_reason": "Source extraction and provenance reviewed.",
                "independence_status": "independent",
                "source_group_id": "GROUP-1",
                "parent_document_id": None,
                "derivation_method": None,
            },
            {
                "document": "SRC-2",
                "source_uri": "file:///deidentified/source-2.txt",
                "sha256": "b" * 64,
                "media_type": "text/plain",
                "source_kind": "diagnostic_report",
                "de_identified": True,
                "evidence_count": 1,
                "verified_count": 1,
                "coverage_status": "reviewed",
                "source_review_adjudication_id": "SRV-review-2",
                "source_reviewed_by": "reviewer",
                "source_reviewed_at": "2026-08-18T09:35:00+00:00",
                "source_review_reason": "Diagnostic report provenance reviewed.",
                "independence_status": "independent",
                "source_group_id": "GROUP-2",
                "parent_document_id": None,
                "derivation_method": None,
            },
        ],
        "source_review_ledger": [
            {
                "adjudication_id": "SRV-review-1",
                "manifest_digest": f"sha256:{'d' * 64}",
                "document_id": "SRC-1",
                "status": "reviewed",
                "de_identified": True,
                "independence_status": "independent",
                "source_group_id": "GROUP-1",
                "parent_document_id": None,
                "derivation_method": None,
                "reviewed_by": "reviewer",
                "reason": "Source extraction and provenance reviewed.",
                "reviewed_at": "2026-08-18T09:30:00+00:00",
            },
            {
                "adjudication_id": "SRV-review-2",
                "manifest_digest": f"sha256:{'d' * 64}",
                "document_id": "SRC-2",
                "status": "reviewed",
                "de_identified": True,
                "independence_status": "independent",
                "source_group_id": "GROUP-2",
                "parent_document_id": None,
                "derivation_method": None,
                "reviewed_by": "reviewer",
                "reason": "Diagnostic report provenance reviewed.",
                "reviewed_at": "2026-08-18T09:35:00+00:00",
            },
        ],
        "timeline": {
            "events": [
                {
                    "id": "EVD-1",
                    "time": "2026-08-18T09:00:00+00:00",
                    "phase": "DETERIORATION",
                    "content": "Observed hypotension",
                    "source_document": "SRC-1",
                    "verified": True,
                    "evidence_type": "OBSERVATION",
                    "temporal": _temporal_instant("2026-08-18T09:00:00+00:00"),
                    "chronology_status": "ORDERED_INSTANT",
                }
            ]
        },
        "reasoning_chain": [{"id": "RS-1", "content": "Compared diagnoses"}],
        "thinking_chain": [
            {
                "id": "THINK-1",
                "thinking_type": "UNCERTAINTY_ACKNOWLEDGED",
                "content": "Bias and uncertainty review",
                "uncertainty_factors": ["Definitive adjudication remains pending"],
                "potential_biases": ["Anchoring", "Premature closure"],
            },
            {
                "id": "THINK-LEAD-1",
                "timestamp": "2026-08-18T10:05:00+00:00",
                "thinking_type": "DECISION_POINT",
                "content": "Explicitly selected the current leading diagnosis.",
                "internal_reasoning": (
                    "Pulmonary embolism currently best fits the linked evidence."
                ),
                "structured_data": {
                    "record_type": "LEADING_HYPOTHESIS_SELECTION",
                    "selection": {
                        "selection_id": "LHS-valid-1",
                        "hypothesis_id": "HYP-1",
                        "previous_hypothesis_id": None,
                        "reason": (
                            "Pulmonary embolism currently best fits the linked evidence."
                        ),
                        "changed_by": "reviewer",
                        "changed_at": "2026-08-18T10:05:00+00:00",
                    },
                },
            },
        ],
        "evidence_graph": {"nodes": [], "edges": []},
        "rca_session": {
            "source_manifest_digest": f"sha256:{'d' * 64}",
            "source_document_count": 2,
            "source_review_event_count": 2,
        },
        "fishbone": {
            "fishbone_id": "fb_1",
            "problem_statement": "Delayed escalation",
            "categories": [
                {
                    "category": "Process",
                    "causes": [
                        {
                            "cause_id": "c_1",
                            "description": "Missing trigger",
                            "hfacs_code": "OF-OP",
                            "hfacs_review_status": "CONFIRMED",
                            "hfacs_reviewed_by": "reviewer",
                            "hfacs_reviewed_at": "2026-08-18T09:40:00+00:00",
                            "hfacs_review_reason": "Process classification reviewed.",
                            "evidence": ["EVD-1"],
                        }
                    ],
                }
            ],
        },
        "why_tree": {
            "nodes": [
                {
                    "id": "c_1",
                    "answer": "Missing escalation trigger",
                    "evidence": ["EVD-1"],
                    "is_root_cause": True,
                }
            ],
            "root_causes": ["c_1"],
        },
        "root_causes": [
            {
                "id": "c_1",
                "answer": "Missing escalation trigger",
                "evidence": ["EVD-1"],
                "causation_verification_id": "ver_1",
                "causation_result": "INSUFFICIENT_DATA",
                "disposition": "PROPOSED",
            }
        ],
        "causation_verifications": [
            {
                "verification_id": "ver_1",
                "audit_scope": "CONSERVATIVE_CAUSATION_AUDIT",
                "clinical_causality_established": False,
                "verification_level": "standard",
                "overall_result": "INSUFFICIENT_DATA",
                "cause_event": {
                    "id": "c_1",
                    "description": "Missing escalation trigger",
                    "evidence": ["EVD-1"],
                },
                "effect_event": {
                    "description": "Delayed escalation",
                    "evidence": ["EVD-2"],
                },
                "tests": {
                    "temporality": {
                        "passed": False,
                        "conclusion": "Cannot verify chronology without event timestamps.",
                    },
                    "necessity": {
                        "passed": False,
                        "counterfactual_question": (
                            "Would delayed escalation occur without the missing trigger?"
                        ),
                        "counterfactual_answer": "uncertain",
                        "reasoning": "The available records cannot resolve necessity.",
                    },
                    "mechanism": None,
                    "sufficiency": None,
                },
                "interpretation": (
                    "Data are insufficient; retain only as a proposed relationship."
                ),
                "next_steps": ["Obtain timestamped escalation policy records."],
            }
        ],
        "hfacs_classifications": [
            {
                "cause_id": "c_1",
                "cause": "Missing trigger",
                "category": "Process",
                "hfacs_code": "OF-OP",
                "review_status": "CONFIRMED",
                "reviewed_by": "reviewer",
                "reviewed_at": "2026-08-18T09:40:00+00:00",
                "review_reason": "Process classification reviewed.",
                "evidence": ["EVD-1"],
                "source": "fishbone_cause",
            }
        ],
        "gap_analysis": {
            "total_conflicts": 0,
            "critical_count": 0,
            "high_count": 0,
            "conflicts": [],
            "safety_invariants_met": True,
        },
        "report_readiness": {
            "session_id": "rc_sess_test",
            "current_stage": "READY_FOR_SYNTHESIS",
            "stage_display": "5. Ready for Auditable Report Synthesis",
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
            "next_recommended_actions": ["Generate a preliminary report."],
            "push_questions": ["Is every claim source-linked and challenged?"],
            "is_ready_for_report": True,
        },
        "evidence_metrics": {
            "total_evidence": 3,
            "verified_evidence": 3,
            "strong_evidence": 3,
            "moderate_evidence": 0,
            "weak_evidence": 0,
        },
        "reasoning_metrics": {
            "total_steps": 1,
            "avg_confidence": None,
            "hypothesis_coverage": 1.0,
            "evidence_coverage": 1.0,
            "decision_points": 1,
            "alternatives_considered": 1,
            "biases_identified": 1,
            "uncertainties_acknowledged": 1,
        },
    }


def _mutate(report: dict[str, Any], mutation: str) -> None:  # noqa: PLR0912
    if mutation == "guidance_false":
        report["report_readiness"]["is_ready_for_report"] = False
    elif mutation == "safety_conflict":
        report["gap_analysis"]["total_conflicts"] = 1
        report["gap_analysis"]["critical_count"] = 1
        report["gap_analysis"]["conflicts"] = [
            {"conflict_id": "CONF-1", "severity": "CRITICAL"}
        ]
        report["gap_analysis"]["safety_invariants_met"] = False
    elif mutation == "gap_summary_forged":
        report["gap_analysis"]["conflicts"] = [
            {"conflict_id": "CONF-1", "severity": "HIGH"}
        ]
    elif mutation == "single_source":
        report["rca_session"]["source_document_count"] = 1
        report["source_inventory"] = report["source_inventory"][:1]
    elif mutation == "derived_sources_same_root":
        report["source_inventory"][1].update(
            {
                "independence_status": "derived",
                "source_group_id": "GROUP-1",
                "parent_document_id": "SRC-1",
                "derivation_method": "host text extraction",
            }
        )
    elif mutation == "source_independence_unknown":
        report["source_inventory"][1]["independence_status"] = "unknown"
    elif mutation == "source_unreviewed":
        report["source_inventory"][0]["coverage_status"] = "extracted"
    elif mutation == "source_review_missing":
        report["source_inventory"][0].pop("source_review_adjudication_id")
    elif mutation == "source_reviewer_unauthorized":
        report["source_inventory"][0]["source_reviewed_by"] = "untrusted-agent"
    elif mutation == "source_review_duplicate_id":
        report["source_inventory"][1]["source_review_adjudication_id"] = report[
            "source_inventory"
        ][0]["source_review_adjudication_id"]
    elif mutation == "source_review_ledger_missing":
        report["source_review_ledger"] = []
    elif mutation == "source_review_ledger_duplicate_id":
        report["source_review_ledger"][1]["adjudication_id"] = report[
            "source_review_ledger"
        ][0]["adjudication_id"]
    elif mutation == "source_review_ledger_unauthorized_reviewer":
        report["source_review_ledger"][0]["reviewed_by"] = "untrusted-agent"
    elif mutation == "source_review_ledger_wrong_manifest":
        report["source_review_ledger"][0]["manifest_digest"] = f"sha256:{'e' * 64}"
    elif mutation == "source_review_ledger_count_forged":
        report["rca_session"]["source_review_event_count"] = 99
    elif mutation == "source_review_ledger_reordered":
        report["source_review_ledger"].reverse()
    elif mutation == "source_review_ledger_manifest_document_missing":
        report["source_review_ledger"].pop()
        report["rca_session"]["source_review_event_count"] = 1
    elif mutation == "source_review_ledger_regression":
        report["source_review_ledger"].append(
            {
                "adjudication_id": "SRV-review-regression",
                "manifest_digest": f"sha256:{'d' * 64}",
                "document_id": "SRC-1",
                "status": "extracted",
                "de_identified": None,
                "independence_status": "unknown",
                "source_group_id": None,
                "parent_document_id": None,
                "derivation_method": None,
                "reviewed_by": "reviewer",
                "reason": "Attempted regression after the completed source review.",
                "reviewed_at": "2026-08-18T09:40:00+00:00",
            }
        )
        report["rca_session"]["source_review_event_count"] = 3
    elif mutation == "source_review_ledger_incomplete":
        report["source_review_ledger"][0].pop("reason")
    elif mutation == "evidence_undeclared":
        report["evidence"][0]["source"]["document_id"] = "SRC-X"
    elif mutation == "evidence_unverified":
        report["evidence"][0]["verified"] = False
    elif mutation == "evidence_verifier_missing":
        report["evidence"][0].pop("verifier")
    elif mutation == "evidence_method_invalid":
        report["evidence"][0]["verification_method"] = "SOURCE_HASH_MISMATCH"
    elif mutation == "inventory_count_forged":
        report["source_inventory"][0]["evidence_count"] = 99
    elif mutation == "inventory_count_negative":
        report["source_inventory"][0]["verified_count"] = -1
    elif mutation == "timeline_evidence_unknown":
        report["timeline"]["events"][0]["id"] = "EVD-X"
    elif mutation == "timeline_source_wrong":
        report["timeline"]["events"][0]["source_document"] = "SRC-2"
    elif mutation == "timeline_time_wrong":
        report["timeline"]["events"][0]["time"] = "2026-08-18T12:00:00+00:00"
    elif mutation == "timeline_time_blank":
        report["timeline"]["events"][0]["time"] = ""
    elif mutation == "diagnosis_code_blank":
        report["hypotheses"][0]["diagnosis"]["code"] = " "
    elif mutation == "diagnosis_system_blank":
        report["hypotheses"][0]["diagnosis"]["system"] = ""
    elif mutation == "section_omitted":
        report["evidence_graph"] = None
    elif mutation == "fishbone_empty":
        report["fishbone"]["categories"] = []
    elif mutation == "hfacs_arbitrary_unreviewed":
        cause = report["fishbone"]["categories"][0]["causes"][0]
        classification = report["hfacs_classifications"][0]
        cause["hfacs_code"] = "ARBITRARY-CODE"
        cause["hfacs_review_status"] = "UNREVIEWED"
        classification["hfacs_code"] = "ARBITRARY-CODE"
        classification["review_status"] = "UNREVIEWED"
    elif mutation == "hfacs_reviewer_unauthorized":
        report["fishbone"]["categories"][0]["causes"][0]["hfacs_reviewed_by"] = (
            "untrusted-agent"
        )
        report["hfacs_classifications"][0]["reviewed_by"] = "untrusted-agent"
    elif mutation == "hfacs_description_mismatch":
        report["hfacs_classifications"][0]["cause"] = "Different cause"
    elif mutation == "hfacs_evidence_mismatch":
        report["hfacs_classifications"][0]["evidence"] = ["EVD-2"]
    elif mutation == "hfacs_not_applicable_with_code":
        report["fishbone"]["categories"][0]["causes"][0]["hfacs_review_status"] = (
            "NOT_APPLICABLE"
        )
        report["hfacs_classifications"][0]["review_status"] = "NOT_APPLICABLE"
    elif mutation == "hfacs_orphan_review":
        report["hfacs_classifications"][0]["cause_id"] = "c_orphan"
    elif mutation == "why_root_missing":
        report["why_tree"]["nodes"] = []
    elif mutation == "root_description_wrong":
        report["root_causes"][0]["answer"] = "Different root"
    elif mutation == "root_evidence_wrong":
        report["root_causes"][0]["evidence"] = ["EVD-X"]
    elif mutation == "audit_id_wrong":
        report["causation_verifications"][0]["cause_event"]["id"] = "c_wrong"
    elif mutation == "audit_description_wrong":
        report["causation_verifications"][0]["cause_event"]["description"] = (
            "Different cause"
        )
    elif mutation == "audit_evidence_wrong":
        report["causation_verifications"][0]["cause_event"]["evidence"] = ["EVD-2"]
    elif mutation == "effect_evidence_unknown":
        report["causation_verifications"][0]["effect_event"]["evidence"] = ["EVD-X"]
    elif mutation == "audit_scope_missing":
        report["causation_verifications"][0].pop("audit_scope")
    elif mutation == "audit_reference_wrong":
        report["root_causes"][0]["causation_verification_id"] = "ver_wrong"
    elif mutation == "duplicate_audit_id":
        duplicate = deepcopy(report["causation_verifications"][0])
        report["causation_verifications"].append(duplicate)
    elif mutation == "causation_verified_fabricated":
        report["causation_verifications"][0]["overall_result"] = "VERIFIED"
        report["causation_verifications"][0].pop("tests")
        report["root_causes"][0]["causation_result"] = "VERIFIED"
        report["root_causes"][0]["disposition"] = "AUDIT_OBLIGATIONS_PASSED"
    elif mutation == "causation_required_test_missing":
        report["causation_verifications"][0]["tests"].pop("necessity")
    elif mutation == "rejected_in_root_bucket":
        report["causation_verifications"][0]["overall_result"] = "REJECTED"
        report["root_causes"][0]["causation_result"] = "REJECTED"
    elif mutation == "insufficient_promoted":
        report["root_causes"][0]["disposition"] = "AUDIT_OBLIGATIONS_PASSED"
    elif mutation == "duplicate_diagnosis":
        report["hypotheses"][1]["diagnosis"]["display"] = "  PULMONARY-embolism  "
    elif mutation == "active_without_evidence_or_test":
        report["hypotheses"][1]["likelihood_ratios"] = []
        report["hypotheses"][1]["supporting_evidence_ids"] = []
        report["hypotheses"][1]["planned_tests"] = []
    elif mutation == "lr_calibration_missing":
        report["hypotheses"][0]["likelihood_ratios"][0].pop("calibration_status")
        report["hypotheses"][0]["likelihood_ratios"][0].pop("calibration_source_ref")
    elif mutation == "unknown_calibration_with_non_neutral_lr":
        relationship = report["hypotheses"][0]["likelihood_ratios"][0]
        relationship["applied_likelihood_ratio"] = 99.0
        relationship["calibration_status"] = "QUANTITATIVELY_UNKNOWN"
        relationship["calibration_source_ref"] = None
    elif mutation == "calibration_ref_is_not_literature":
        report["hypotheses"][0]["likelihood_ratios"][0]["calibration_source_ref"] = (
            "EVD-1"
        )
    elif mutation == "calibration_target_is_literature":
        report["hypotheses"][0]["likelihood_ratios"][0]["evidence_id"] = "EVD-CAL-1"
    elif mutation == "calibrated_lr_direction_mismatch":
        report["hypotheses"][0]["likelihood_ratios"][0]["supports"] = False
    elif mutation == "calibrated_lr_not_finite":
        report["hypotheses"][0]["likelihood_ratios"][0]["applied_likelihood_ratio"] = (
            float("inf")
        )
    elif mutation == "active_without_uncertainty":
        report["hypotheses"][1]["uncertainty_factors"] = []
    elif mutation == "typed_classification_missing":
        report["hypotheses"][0].pop("diagnostic_role")
    elif mutation == "mechanism_breadth_collapsed":
        for hypothesis in report["hypotheses"]:
            hypothesis["mechanism_category"] = "VASCULAR"
        for cell in report["differential_breadth_audits"][0]["cells"]:
            cell["mechanism_categories"] = ["VASCULAR"]
    elif mutation == "breadth_audit_not_assessed":
        cell = report["differential_breadth_audits"][0]["cells"][1]
        cell["status"] = "NOT_ASSESSED"
        cell["hypothesis_ids"] = []
        cell["mechanism_categories"] = []
    elif mutation == "breadth_audit_linkage_wrong":
        report["differential_breadth_audits"][0]["cells"][1]["mechanism_categories"] = [
            "INFECTIOUS"
        ]
    elif mutation == "custom_primary_catchall":
        report["differential_breadth_audits"] = [
            {
                "audit_id": "DBA-catchall",
                "framework": "CUSTOM",
                "framework_name": "Everything else",
                "framework_rationale": (
                    "A caller-defined catch-all must not satisfy the canonical final gate."
                ),
                "role": "PRIMARY",
                "cells": [
                    {
                        "cell_id": "EVERYTHING",
                        "status": "CANDIDATES_PRESENT",
                        "hypothesis_ids": ["HYP-1", "HYP-2", "HYP-3"],
                        "mechanism_categories": [
                            "VASCULAR",
                            "FUNCTIONAL_PHYSIOLOGIC",
                            "METABOLIC_ENDOCRINE",
                        ],
                        "rationale": "All candidates are placed in one catch-all cell.",
                        "unknowns": [],
                        "planned_discriminators": [],
                    },
                    {
                        "cell_id": "EMPTY_ONE",
                        "status": "REVIEWED_NO_PLAUSIBLE_CANDIDATE",
                        "hypothesis_ids": [],
                        "mechanism_categories": [],
                        "rationale": "This empty cell exists only to meet a numeric floor.",
                        "unknowns": [],
                        "planned_discriminators": [],
                    },
                    {
                        "cell_id": "EMPTY_TWO",
                        "status": "REVIEWED_NO_PLAUSIBLE_CANDIDATE",
                        "hypothesis_ids": [],
                        "mechanism_categories": [],
                        "rationale": "This second empty cell also lacks canonical meaning.",
                        "unknowns": [],
                        "planned_discriminators": [],
                    },
                ],
                "stop_rationale": "The caller stops after a meaningless catch-all review.",
                "recorded_by": "test-agent",
                "recorded_at": "2026-08-18T10:00:00+00:00",
            }
        ]
    elif mutation == "unsupported_high_certainty":
        report["hypotheses"][1]["certainty"] = "PROBABLE"
        report["hypotheses"][1]["likelihood_ratios"] = []
        report["hypotheses"][1]["supporting_evidence_ids"] = []
    elif mutation == "confirmed_certainty_mismatch":
        report["hypotheses"][1]["certainty"] = "CONFIRMED"
    elif mutation == "leading_selection_missing":
        report["thinking_chain"] = [
            step
            for step in report["thinking_chain"]
            if step.get("structured_data", {}).get("record_type")
            != "LEADING_HYPOTHESIS_SELECTION"
        ]
    elif mutation == "leading_selection_mismatch":
        report["thinking_chain"][1]["structured_data"]["selection"]["hypothesis_id"] = (
            "HYP-2"
        )
    elif mutation == "leading_selection_reason_short":
        report["thinking_chain"][1]["structured_data"]["selection"]["reason"] = "short"
    elif mutation == "leading_selection_actor_blank":
        report["thinking_chain"][1]["structured_data"]["selection"]["changed_by"] = " "
    elif mutation == "leading_selection_time_naive":
        report["thinking_chain"][1]["structured_data"]["selection"]["changed_at"] = (
            "2026-08-18T10:05:00"
        )
    elif mutation == "leading_neutral_support":
        report["hypotheses"][0]["likelihood_ratios"][0]["applied_likelihood_ratio"] = (
            1.0
        )
    elif mutation == "must_not_miss_unchallenged":
        report["hypotheses"][2]["likelihood_ratios"] = report["hypotheses"][2][
            "likelihood_ratios"
        ][:1]
        report["hypotheses"][2]["contradicting_evidence_ids"] = []
        report["hypotheses"][2]["planned_tests"] = []
    else:  # pragma: no cover - protects the table itself
        raise AssertionError(f"Unknown mutation: {mutation}")


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        ("guidance_false", "GUIDANCE_READY"),
        ("safety_conflict", "NO_UNRESOLVED_SAFETY_CONFLICTS"),
        ("gap_summary_forged", "GAP_ANALYSIS_RECOMPUTABLE"),
        ("single_source", "MULTI_SOURCE_MANIFEST"),
        ("derived_sources_same_root", "MULTI_SOURCE_MANIFEST"),
        ("source_independence_unknown", "SOURCE_INDEPENDENCE_LINEAGE"),
        ("source_unreviewed", "MANIFEST_DOCUMENTS_REVIEWED"),
        ("source_review_missing", "SOURCE_REVIEW_ADJUDICATION_AUTHORIZED"),
        ("source_reviewer_unauthorized", "SOURCE_REVIEW_ADJUDICATION_AUTHORIZED"),
        ("source_review_duplicate_id", "SOURCE_REVIEW_ADJUDICATION_AUTHORIZED"),
        ("source_review_ledger_missing", "SOURCE_REVIEW_ADJUDICATION_AUTHORIZED"),
        (
            "source_review_ledger_duplicate_id",
            "SOURCE_REVIEW_ADJUDICATION_AUTHORIZED",
        ),
        (
            "source_review_ledger_unauthorized_reviewer",
            "SOURCE_REVIEW_ADJUDICATION_AUTHORIZED",
        ),
        (
            "source_review_ledger_wrong_manifest",
            "SOURCE_REVIEW_ADJUDICATION_AUTHORIZED",
        ),
        (
            "source_review_ledger_count_forged",
            "SOURCE_REVIEW_ADJUDICATION_AUTHORIZED",
        ),
        (
            "source_review_ledger_reordered",
            "SOURCE_REVIEW_ADJUDICATION_AUTHORIZED",
        ),
        (
            "source_review_ledger_manifest_document_missing",
            "SOURCE_REVIEW_ADJUDICATION_AUTHORIZED",
        ),
        (
            "source_review_ledger_regression",
            "SOURCE_REVIEW_ADJUDICATION_AUTHORIZED",
        ),
        (
            "source_review_ledger_incomplete",
            "SOURCE_REVIEW_ADJUDICATION_AUTHORIZED",
        ),
        ("evidence_undeclared", "EVIDENCE_SOURCES_DECLARED"),
        ("evidence_unverified", "EVIDENCE_VERIFICATION_COMPLETE"),
        ("evidence_verifier_missing", "EVIDENCE_VERIFICATION_COMPLETE"),
        ("evidence_method_invalid", "EVIDENCE_VERIFICATION_COMPLETE"),
        ("inventory_count_forged", "SOURCE_INVENTORY_COUNTS_RECOMPUTABLE"),
        ("inventory_count_negative", "SOURCE_INVENTORY_COUNTS_RECOMPUTABLE"),
        ("timeline_evidence_unknown", "TIMELINE_EVIDENCE_LINEAGE"),
        ("timeline_source_wrong", "TIMELINE_EVIDENCE_LINEAGE"),
        ("timeline_time_wrong", "TIMELINE_EVIDENCE_LINEAGE"),
        ("timeline_time_blank", "TIMELINE_EVIDENCE_LINEAGE"),
        ("diagnosis_code_blank", "DIAGNOSIS_CONCEPT_IDENTIFIED"),
        ("diagnosis_system_blank", "DIAGNOSIS_CONCEPT_IDENTIFIED"),
        ("section_omitted", "FINAL_REPORT_SECTIONS_INCLUDED"),
        ("fishbone_empty", "FISHBONE_PRESENT"),
        ("hfacs_arbitrary_unreviewed", "HFACS_REVIEW_LINEAGE"),
        ("hfacs_reviewer_unauthorized", "HFACS_REVIEW_LINEAGE"),
        ("hfacs_description_mismatch", "HFACS_REVIEW_LINEAGE"),
        ("hfacs_evidence_mismatch", "HFACS_REVIEW_LINEAGE"),
        ("hfacs_not_applicable_with_code", "HFACS_REVIEW_LINEAGE"),
        ("hfacs_orphan_review", "HFACS_REVIEW_LINEAGE"),
        ("why_root_missing", "WHY_ROOT_PRESENT"),
        ("root_description_wrong", "ROOT_EVIDENCE_LINEAGE"),
        ("root_evidence_wrong", "ROOT_EVIDENCE_LINEAGE"),
        ("audit_id_wrong", "ROOT_CAUSATION_AUDIT_LINEAGE"),
        ("audit_description_wrong", "ROOT_CAUSATION_AUDIT_LINEAGE"),
        ("audit_evidence_wrong", "ROOT_CAUSATION_AUDIT_LINEAGE"),
        ("effect_evidence_unknown", "ROOT_CAUSATION_AUDIT_LINEAGE"),
        ("audit_scope_missing", "ROOT_CAUSATION_AUDIT_LINEAGE"),
        ("audit_reference_wrong", "ROOT_CAUSATION_AUDIT_LINEAGE"),
        ("duplicate_audit_id", "ROOT_CAUSATION_AUDIT_LINEAGE"),
        ("causation_verified_fabricated", "ROOT_CAUSATION_AUDIT_LINEAGE"),
        ("causation_required_test_missing", "ROOT_CAUSATION_AUDIT_LINEAGE"),
        ("rejected_in_root_bucket", "ROOT_CAUSE_DISPOSITION_SAFE"),
        ("insufficient_promoted", "ROOT_CAUSE_DISPOSITION_SAFE"),
        ("duplicate_diagnosis", "DIFFERENTIAL_MINIMUM_UNIQUE"),
        ("active_without_evidence_or_test", "ACTIVE_DIFFERENTIAL_DISPOSITION"),
        ("lr_calibration_missing", "LIKELIHOOD_RATIO_CALIBRATION_VALID"),
        (
            "unknown_calibration_with_non_neutral_lr",
            "LIKELIHOOD_RATIO_CALIBRATION_VALID",
        ),
        ("calibration_ref_is_not_literature", "LIKELIHOOD_RATIO_CALIBRATION_VALID"),
        ("calibration_target_is_literature", "LIKELIHOOD_RATIO_CALIBRATION_VALID"),
        ("calibrated_lr_direction_mismatch", "LIKELIHOOD_RATIO_CALIBRATION_VALID"),
        ("calibrated_lr_not_finite", "LIKELIHOOD_RATIO_CALIBRATION_VALID"),
        ("active_without_uncertainty", "ACTIVE_DIFFERENTIAL_DISPOSITION"),
        ("typed_classification_missing", "DIFFERENTIAL_TYPED_CLASSIFICATION"),
        ("mechanism_breadth_collapsed", "DIFFERENTIAL_MECHANISM_BREADTH"),
        ("breadth_audit_not_assessed", "DIFFERENTIAL_BREADTH_AUDIT_COMPLETE"),
        ("breadth_audit_linkage_wrong", "DIFFERENTIAL_BREADTH_AUDIT_COMPLETE"),
        ("custom_primary_catchall", "DIFFERENTIAL_BREADTH_AUDIT_COMPLETE"),
        ("unsupported_high_certainty", "DIAGNOSTIC_CERTAINTY_SUPPORTED"),
        ("confirmed_certainty_mismatch", "DIAGNOSTIC_CERTAINTY_SUPPORTED"),
        ("leading_selection_missing", "LEADING_SELECTION_LINEAGE"),
        ("leading_selection_mismatch", "LEADING_SELECTION_LINEAGE"),
        ("leading_selection_reason_short", "LEADING_SELECTION_LINEAGE"),
        ("leading_selection_actor_blank", "LEADING_SELECTION_LINEAGE"),
        ("leading_selection_time_naive", "LEADING_SELECTION_LINEAGE"),
        ("leading_neutral_support", "LEADING_DIAGNOSIS_CHALLENGED"),
        ("must_not_miss_unchallenged", "MUST_NOT_MISS_CHALLENGED"),
    ],
)
def test_every_negative_mutation_produces_a_hard_failure(
    mutation: str,
    expected_code: str,
) -> None:
    report = _valid_report()
    _mutate(report, mutation)

    checks = evaluate_final_report_conformance(
        report,
        approved_by="reviewer",
        authorized_reviewers={"reviewer"},
    )
    failures = hard_failures(checks)

    assert expected_code in {failure["code"] for failure in failures}
    assert all(failure["status"] == "FAIL" for failure in failures)
    assert all(failure["severity"] == "HARD" for failure in failures)

    # The domain lifecycle recomputes these checks; caller-supplied PASS records
    # therefore cannot turn any unsafe mutation into a final snapshot.
    typed_report = ContractReport.model_validate(report)
    with pytest.raises(ValueError, match="deterministic conformance failed"):
        typed_report.finalize(
            "reviewer",
            authorized_reviewers={"reviewer"},
        )


def test_complete_report_passes_every_required_hard_check() -> None:
    checks = evaluate_final_report_conformance(
        _valid_report(),
        approved_by="reviewer",
        authorized_reviewers={"reviewer"},
    )

    assert {check["code"] for check in checks} == HARD_CONFORMANCE_CODES
    assert hard_failures(checks) == []


def test_not_applicable_hfacs_review_is_typed_and_can_finalize_without_a_code() -> None:
    report = _valid_report()
    cause = report["fishbone"]["categories"][0]["causes"][0]
    classification = report["hfacs_classifications"][0]
    cause["hfacs_review_status"] = "NOT_APPLICABLE"
    cause["hfacs_code"] = None
    cause["hfacs_review_reason"] = "HFACS was reviewed and is not applicable."
    classification["review_status"] = "NOT_APPLICABLE"
    classification["hfacs_code"] = None
    classification["review_reason"] = "HFACS was reviewed and is not applicable."

    checks = evaluate_final_report_conformance(
        report,
        approved_by="reviewer",
        authorized_reviewers={"reviewer"},
    )

    assert hard_failures(checks) == []
    finalized = ContractReport.model_validate(report)
    finalized.finalize("reviewer", authorized_reviewers={"reviewer"})
    assert finalized.is_finalized is True


def test_active_candidate_can_use_typed_discriminating_plan_without_fake_lr() -> None:
    report = _valid_report()
    candidate = report["hypotheses"][1]
    candidate["likelihood_ratios"] = []
    candidate["supporting_evidence_ids"] = []
    candidate["planned_tests"][0]["purpose"] = "DISCRIMINATE"

    checks = evaluate_final_report_conformance(
        report,
        approved_by="reviewer",
        authorized_reviewers={"reviewer"},
    )

    active_check = next(
        item for item in checks if item["code"] == "ACTIVE_DIFFERENTIAL_DISPOSITION"
    )
    assert active_check["status"] == "PASS"
    assert hard_failures(checks) == []


def test_resolved_differential_with_no_active_entries_can_finalize() -> None:
    report = _valid_report()
    report["hypotheses"][0]["status"] = "CONFIRMED"
    report["hypotheses"][0]["certainty"] = "CONFIRMED"
    report["hypotheses"][1]["status"] = "EXCLUDED"
    report["hypotheses"][1]["certainty"] = "EXCLUDED"
    report["hypotheses"][2]["status"] = "EXCLUDED"
    report["hypotheses"][2]["certainty"] = "EXCLUDED"
    report["report_readiness"]["checklist"]["active_hypotheses_count"] = 1

    checks = evaluate_final_report_conformance(
        report,
        approved_by="reviewer",
        authorized_reviewers={"reviewer"},
    )

    assert (
        next(
            check
            for check in checks
            if check["code"] == "ACTIVE_DIFFERENTIAL_DISPOSITION"
        )["status"]
        == "PASS"
    )
    assert hard_failures(checks) == []
    typed_report = ContractReport.model_validate(report)
    typed_report.finalize("reviewer", authorized_reviewers={"reviewer"})
    assert typed_report.is_finalized is True


def test_confirmed_diagnosis_cannot_rely_on_refuting_evidence_only() -> None:
    report = _valid_report()
    confirmed = report["hypotheses"][2]
    confirmed["status"] = "CONFIRMED"
    confirmed["certainty"] = "CONFIRMED"
    confirmed["supporting_evidence_ids"] = []
    confirmed["likelihood_ratios"] = [
        relationship
        for relationship in confirmed["likelihood_ratios"]
        if relationship["supports"] is False
    ]

    checks = evaluate_final_report_conformance(
        report,
        approved_by="reviewer",
        authorized_reviewers={"reviewer"},
    )

    certainty_check = next(
        check for check in checks if check["code"] == "DIAGNOSTIC_CERTAINTY_SUPPORTED"
    )
    assert certainty_check["status"] == "FAIL"
    assert "HYP-3" in certainty_check["refs"]


@pytest.mark.parametrize("certainty", ["PROBABLE", "HIGH_CONFIDENCE"])
def test_positive_certainty_cannot_rely_on_refuting_evidence_only(
    certainty: str,
) -> None:
    report = _valid_report()
    candidate = report["hypotheses"][2]
    candidate["certainty"] = certainty
    candidate["supporting_evidence_ids"] = []
    candidate["likelihood_ratios"] = [
        relationship
        for relationship in candidate["likelihood_ratios"]
        if relationship["supports"] is False
    ]

    checks = evaluate_final_report_conformance(
        report,
        approved_by="reviewer",
        authorized_reviewers={"reviewer"},
    )

    certainty_check = next(
        check for check in checks if check["code"] == "DIAGNOSTIC_CERTAINTY_SUPPORTED"
    )
    assert certainty_check["status"] == "FAIL"
    assert "HYP-3" in certainty_check["refs"]


@pytest.mark.parametrize(
    "result_disposition",
    [None, "REFUTES_HYPOTHESIS", "INDETERMINATE", "NEUTRAL"],
)
def test_completed_test_needs_typed_supporting_disposition_for_positive_certainty(
    result_disposition: str | None,
) -> None:
    report = _valid_report()
    candidate = report["hypotheses"][1]
    candidate["certainty"] = "PROBABLE"
    candidate["supporting_evidence_ids"] = []
    candidate["likelihood_ratios"] = []
    completed = candidate["planned_tests"][0]
    completed.update(
        {
            "status": "COMPLETED",
            "result_evidence_id": "EVD-1",
            "result_summary": "The completed study has a typed disposition.",
        }
    )
    if result_disposition is not None:
        completed["result_disposition"] = result_disposition

    checks = evaluate_final_report_conformance(
        report,
        approved_by="reviewer",
        authorized_reviewers={"reviewer"},
    )

    certainty_check = next(
        check for check in checks if check["code"] == "DIAGNOSTIC_CERTAINTY_SUPPORTED"
    )
    assert certainty_check["status"] == "FAIL"


def test_completed_test_with_typed_supporting_disposition_can_support_certainty() -> (
    None
):
    report = _valid_report()
    candidate = report["hypotheses"][1]
    candidate["certainty"] = "PROBABLE"
    candidate["supporting_evidence_ids"] = []
    candidate["likelihood_ratios"] = []
    candidate["planned_tests"][0].update(
        {
            "status": "COMPLETED",
            "result_evidence_id": "EVD-1",
            "result_summary": "The completed study supports this hypothesis.",
            "result_disposition": "SUPPORTS_HYPOTHESIS",
        }
    )

    checks = evaluate_final_report_conformance(
        report,
        approved_by="reviewer",
        authorized_reviewers={"reviewer"},
    )

    certainty_check = next(
        check for check in checks if check["code"] == "DIAGNOSTIC_CERTAINTY_SUPPORTED"
    )
    assert certainty_check["status"] == "PASS"


def test_unverified_completed_test_result_cannot_support_positive_certainty() -> None:
    report = _valid_report()
    candidate = report["hypotheses"][1]
    candidate["certainty"] = "PROBABLE"
    candidate["supporting_evidence_ids"] = []
    candidate["likelihood_ratios"] = []
    candidate["planned_tests"][0].update(
        {
            "status": "COMPLETED",
            "result_evidence_id": "EVD-1",
            "result_summary": "Caller labels the result as supporting.",
            "result_disposition": "SUPPORTS_HYPOTHESIS",
        }
    )
    report["evidence"][0]["verified"] = False

    checks = evaluate_final_report_conformance(
        report,
        approved_by="reviewer",
        authorized_reviewers={"reviewer"},
    )

    certainty_check = next(
        check for check in checks if check["code"] == "DIAGNOSTIC_CERTAINTY_SUPPORTED"
    )
    assert certainty_check["status"] == "FAIL"


def test_literature_record_cannot_masquerade_as_completed_case_test_result() -> None:
    report = _valid_report()
    candidate = report["hypotheses"][1]
    candidate["certainty"] = "PROBABLE"
    candidate["supporting_evidence_ids"] = []
    candidate["likelihood_ratios"] = []
    candidate["planned_tests"][0].update(
        {
            "status": "COMPLETED",
            "result_evidence_id": "EVD-CAL-1",
            "result_summary": "A literature quote is not a patient test result.",
            "result_disposition": "SUPPORTS_HYPOTHESIS",
        }
    )

    checks = evaluate_final_report_conformance(
        report,
        approved_by="reviewer",
        authorized_reviewers={"reviewer"},
    )

    certainty_check = next(
        check for check in checks if check["code"] == "DIAGNOSTIC_CERTAINTY_SUPPORTED"
    )
    assert certainty_check["status"] == "FAIL"


def test_verified_completed_test_dispositions_supply_support_and_refutation() -> None:
    report = _valid_report()
    leading = report["hypotheses"][0]
    leading["likelihood_ratios"] = []
    leading["supporting_evidence_ids"] = []
    leading["contradicting_evidence_ids"] = []
    supporting_test = _planned_test("HYP-1")
    supporting_test.update(
        {
            "test_id": "TST-support",
            "status": "COMPLETED",
            "result_evidence_id": "EVD-1",
            "result_summary": "The verified result supports this hypothesis.",
            "result_disposition": "SUPPORTS_HYPOTHESIS",
        }
    )
    refuting_test = _planned_test("HYP-1")
    refuting_test.update(
        {
            "test_id": "TST-refute",
            "status": "COMPLETED",
            "result_evidence_id": "EVD-2",
            "result_summary": "The verified result refutes this hypothesis.",
            "result_disposition": "REFUTES_HYPOTHESIS",
        }
    )
    leading["planned_tests"] = [supporting_test, refuting_test]

    checks = evaluate_final_report_conformance(
        report,
        approved_by="reviewer",
        authorized_reviewers={"reviewer"},
    )

    leading_check = next(
        check for check in checks if check["code"] == "LEADING_DIAGNOSIS_CHALLENGED"
    )
    assert leading_check["status"] == "PASS"
    assert hard_failures(checks) == []


def test_same_content_hash_cannot_masquerade_as_two_independent_sources() -> None:
    report = _valid_report()
    for source in report["source_inventory"]:
        source["sha256"] = "a" * 64

    checks = evaluate_final_report_conformance(
        report,
        approved_by="reviewer",
        authorized_reviewers={"reviewer"},
    )
    by_code = {check["code"]: check for check in checks}

    assert by_code["MULTI_SOURCE_MANIFEST"]["status"] == "FAIL"
    assert by_code["SOURCE_INDEPENDENCE_LINEAGE"]["status"] == "FAIL"
    assert "host-declared" in by_code["MULTI_SOURCE_MANIFEST"]["message"].lower()


def test_literature_reference_does_not_increase_clinical_multi_source_floor() -> None:
    report = _valid_report()
    report["source_inventory"][1]["source_kind"] = "LiTeRaTuRe"

    checks = evaluate_final_report_conformance(
        report,
        approved_by="reviewer",
        authorized_reviewers={"reviewer"},
    )
    multi_source = next(
        check for check in checks if check["code"] == "MULTI_SOURCE_MANIFEST"
    )

    assert multi_source["status"] == "FAIL"
    assert multi_source["details"]["excluded_reference_documents"] == ["SRC-2"]


def test_all_rejected_why_roots_allow_an_empty_root_cause_bucket() -> None:
    report = _valid_report()
    _retime_evidence(report, "EVD-1", "2026-08-18T10:00:00+00:00")
    audit = report["causation_verifications"][0]
    audit["overall_result"] = "REJECTED"
    audit["cause_event"]["timestamp"] = "2026-08-18T10:00:00+00:00"
    audit["effect_event"]["timestamp"] = "2026-08-18T09:10:00+00:00"
    audit["tests"] = {
        "temporality": {
            "passed": False,
            "cause_time": "2026-08-18T10:00:00+00:00",
            "effect_time": "2026-08-18T09:10:00+00:00",
            "time_diff_minutes": None,
            "conclusion": "The submitted effect predates the proposed cause.",
        }
    }
    report["root_causes"] = []

    checks = evaluate_final_report_conformance(
        report,
        approved_by="reviewer",
        authorized_reviewers={"reviewer"},
    )

    assert hard_failures(checks) == []
    finalized = ContractReport.model_validate(report)
    finalized.finalize("reviewer", authorized_reviewers={"reviewer"})
    assert finalized.is_finalized is True


def test_rejected_historical_why_root_is_omitted_while_proposed_root_remains() -> None:
    report = _valid_report()
    _retime_evidence(report, "EVD-1", "2026-08-18T10:00:00+00:00")
    report["why_tree"]["nodes"].append(
        {
            "id": "c_rejected",
            "answer": "Chronologically impossible claim",
            "evidence": ["EVD-1"],
            "is_root_cause": True,
        }
    )
    report["why_tree"]["root_causes"].append("c_rejected")
    report["causation_verifications"].append(
        {
            "verification_id": "ver_rejected",
            "audit_scope": "CONSERVATIVE_CAUSATION_AUDIT",
            "clinical_causality_established": False,
            "verification_level": "standard",
            "overall_result": "REJECTED",
            "cause_event": {
                "id": "c_rejected",
                "description": "Chronologically impossible claim",
                "evidence": ["EVD-1"],
                "timestamp": "2026-08-18T10:00:00+00:00",
            },
            "effect_event": {
                "description": "Delayed escalation",
                "evidence": ["EVD-2"],
                "timestamp": "2026-08-18T09:10:00+00:00",
            },
            "tests": {
                "temporality": {
                    "passed": False,
                    "cause_time": "2026-08-18T10:00:00+00:00",
                    "effect_time": "2026-08-18T09:10:00+00:00",
                    "time_diff_minutes": None,
                    "conclusion": "The effect predates the proposed cause.",
                }
            },
            "interpretation": "Reverse chronology rejects this submitted claim.",
            "next_steps": ["Correct the event ordering before another audit."],
        }
    )

    checks = evaluate_final_report_conformance(
        report,
        approved_by="reviewer",
        authorized_reviewers={"reviewer"},
    )

    assert [item["id"] for item in report["root_causes"]] == ["c_1"]
    assert hard_failures(checks) == []


def test_prior_leading_diagnosis_may_be_excluded_after_coherent_reselection() -> None:
    report = _valid_report()
    report["hypotheses"][0]["status"] = "EXCLUDED"
    report["hypotheses"][0]["certainty"] = "EXCLUDED"
    report["leading_hypothesis_id"] = "HYP-2"
    report["thinking_chain"].append(
        {
            "id": "THINK-LEAD-2",
            "timestamp": "2026-08-18T10:10:00+00:00",
            "thinking_type": "DECISION_POINT",
            "content": "Reselected the leading diagnosis after new evidence.",
            "internal_reasoning": (
                "The prior lead was excluded, so the next supported candidate was selected."
            ),
            "structured_data": {
                "record_type": "LEADING_HYPOTHESIS_SELECTION",
                "selection": {
                    "selection_id": "LHS-valid-2",
                    "hypothesis_id": "HYP-2",
                    "previous_hypothesis_id": "HYP-1",
                    "reason": (
                        "The prior lead was excluded, so the next supported candidate was selected."
                    ),
                    "changed_by": "reviewer",
                    "changed_at": "2026-08-18T10:10:00+00:00",
                },
            },
        }
    )
    checklist = report["report_readiness"]["checklist"]
    checklist["active_hypotheses_count"] = 2
    checklist["leading_hypothesis_id"] = "HYP-2"

    checks = evaluate_final_report_conformance(
        report,
        approved_by="reviewer",
        authorized_reviewers={"reviewer"},
    )

    assert hard_failures(checks) == []


def test_operator_allowlist_does_not_accept_an_unlisted_identity() -> None:
    checks = evaluate_final_report_conformance(
        _valid_report(),
        approved_by="unlisted-reviewer",
        authorized_reviewers={"listed-reviewer", "reviewer"},
    )

    assert {failure["code"] for failure in hard_failures(checks)} == {
        "REVIEWER_AUTHORIZED"
    }


def test_missing_operator_allowlist_fails_reviewer_authorization_closed() -> None:
    checks = evaluate_final_report_conformance(
        _valid_report(),
        approved_by="reviewer",
        authorized_reviewers=None,
    )

    assert "REVIEWER_AUTHORIZED" in {
        failure["code"] for failure in hard_failures(checks)
    }
