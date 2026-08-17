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
    relationships = [
        {
            "evidence_id": "EVD-1",
            "applied_likelihood_ratio": 2.0,
            "supports": True,
            "rationale": "Direct supporting relationship",
        }
    ]
    if contradicting:
        relationships.append(
            {
                "evidence_id": "EVD-2",
                "applied_likelihood_ratio": 0.2,
                "supports": False,
                "rationale": "Direct refuting relationship",
            }
        )
    return {
        "id": hypothesis_id,
        "diagnosis": {"code": hypothesis_id, "display": diagnosis, "system": "CUSTOM"},
        "prior_probability": probability,
        "current_probability": probability,
        "must_not_miss": must_not_miss,
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
        "hypotheses": hypotheses,
        "evidence": [
            {
                "id": "EVD-1",
                "content": "Observed hypotension",
                "source": {"document_id": "SRC-1"},
                "supports_hypothesis_ids": ["HYP-1", "HYP-2", "HYP-3"],
                "contradicts_hypothesis_ids": [],
            },
            {
                "id": "EVD-2",
                "content": "Adequate negative study",
                "source": {"document_id": "SRC-2"},
                "supports_hypothesis_ids": [],
                "contradicts_hypothesis_ids": ["HYP-3"],
            },
        ],
        "source_inventory": [
            {"document": "SRC-1", "coverage_status": "reviewed"},
            {"document": "SRC-2", "coverage_status": "reviewed"},
        ],
        "timeline": {"events": [{"id": "EVD-1", "content": "Observed hypotension"}]},
        "reasoning_chain": [{"id": "RS-1", "content": "Compared diagnoses"}],
        "thinking_chain": [{"id": "THINK-1", "content": "Bias review"}],
        "evidence_graph": {"nodes": [], "edges": []},
        "rca_session": {"source_document_count": 2},
        "fishbone": {
            "categories": [
                {
                    "category": "Process",
                    "causes": [{"cause_id": "c_1", "description": "Missing trigger"}],
                }
            ]
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
            }
        ],
        "hfacs_classifications": [],
        "gap_analysis": {
            "critical_count": 0,
            "high_count": 0,
            "safety_invariants_met": True,
        },
        "report_readiness": {"is_ready_for_report": True},
        "evidence_metrics": {
            "total_evidence": 2,
            "verified_evidence": 0,
            "strong_evidence": 0,
            "moderate_evidence": 0,
            "weak_evidence": 2,
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
        report["gap_analysis"]["critical_count"] = 1
    elif mutation == "single_source":
        report["rca_session"]["source_document_count"] = 1
        report["source_inventory"] = report["source_inventory"][:1]
    elif mutation == "source_unreviewed":
        report["source_inventory"][0]["coverage_status"] = "extracted"
    elif mutation == "evidence_undeclared":
        report["evidence"][0]["source"]["document_id"] = "SRC-X"
    elif mutation == "section_omitted":
        report["evidence_graph"] = None
    elif mutation == "fishbone_empty":
        report["fishbone"]["categories"] = []
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
    elif mutation == "rejected_in_root_bucket":
        report["causation_verifications"][0]["overall_result"] = "REJECTED"
        report["root_causes"][0]["causation_result"] = "REJECTED"
    elif mutation == "insufficient_promoted":
        report["root_causes"][0]["disposition"] = "AUDIT_OBLIGATIONS_PASSED"
    elif mutation == "duplicate_diagnosis":
        report["hypotheses"][1]["diagnosis"]["display"] = "  PULMONARY-embolism  "
    elif mutation == "active_without_evidence":
        report["hypotheses"][1]["likelihood_ratios"] = []
        report["hypotheses"][1]["supporting_evidence_ids"] = []
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
        ("single_source", "MULTI_SOURCE_MANIFEST"),
        ("source_unreviewed", "MANIFEST_DOCUMENTS_REVIEWED"),
        ("evidence_undeclared", "EVIDENCE_SOURCES_DECLARED"),
        ("section_omitted", "FINAL_REPORT_SECTIONS_INCLUDED"),
        ("fishbone_empty", "FISHBONE_PRESENT"),
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
        ("rejected_in_root_bucket", "ROOT_CAUSE_DISPOSITION_SAFE"),
        ("insufficient_promoted", "ROOT_CAUSE_DISPOSITION_SAFE"),
        ("duplicate_diagnosis", "DIFFERENTIAL_MINIMUM_UNIQUE"),
        ("active_without_evidence", "ACTIVE_DIFFERENTIAL_DISPOSITION"),
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
        typed_report.finalize("reviewer")


def test_complete_report_passes_every_required_hard_check() -> None:
    checks = evaluate_final_report_conformance(
        _valid_report(),
        approved_by="reviewer",
        authorized_reviewers={"reviewer"},
    )

    assert {check["code"] for check in checks} == HARD_CONFORMANCE_CODES
    assert hard_failures(checks) == []


def test_resolved_differential_with_no_active_entries_can_finalize() -> None:
    report = _valid_report()
    report["hypotheses"][0]["status"] = "CONFIRMED"
    report["hypotheses"][1]["status"] = "EXCLUDED"
    report["hypotheses"][2]["status"] = "EXCLUDED"

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
    typed_report.finalize("reviewer")
    assert typed_report.is_finalized is True


def test_rejected_historical_why_root_is_omitted_while_proposed_root_remains() -> None:
    report = _valid_report()
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
            "overall_result": "REJECTED",
            "cause_event": {
                "id": "c_rejected",
                "description": "Chronologically impossible claim",
                "evidence": ["EVD-1"],
            },
            "effect_event": {
                "description": "Delayed escalation",
                "evidence": ["EVD-2"],
            },
        }
    )

    checks = evaluate_final_report_conformance(
        report,
        approved_by="reviewer",
        authorized_reviewers={"reviewer"},
    )

    assert [item["id"] for item in report["root_causes"]] == ["c_1"]
    assert hard_failures(checks) == []


def test_operator_allowlist_does_not_accept_an_unlisted_identity() -> None:
    checks = evaluate_final_report_conformance(
        _valid_report(),
        approved_by="unlisted-reviewer",
        authorized_reviewers={"listed-reviewer"},
    )

    assert {failure["code"] for failure in hard_failures(checks)} == {
        "REVIEWER_AUTHORIZED"
    }
