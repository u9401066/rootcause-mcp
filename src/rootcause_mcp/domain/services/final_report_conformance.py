"""Pure deterministic conformance checks for final clinical/RCA reports.

The evaluator consumes only a report-shaped mapping.  It is intentionally
independent from ``ContractReport`` so both the interface handler and the
domain finalization boundary can recompute the same hard checks instead of
trusting caller-supplied PASS records.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections.abc import Collection, Mapping, Sequence
from datetime import datetime
from typing import Any

from rootcause_mcp.domain.entities.hypothesis import (
    DiagnosticCertainty,
    DiagnosticReasoningBasis,
    DiagnosticRole,
    LikelihoodRatioCalibrationStatus,
    MechanismCategory,
    is_calibration_evidence_ref,
)
from rootcause_mcp.domain.value_objects.case_manifest import (
    SourceReviewAdjudication,
    SourceReviewStatus,
)
from rootcause_mcp.domain.value_objects.clinical_temporal import (
    ClinicalTemporal,
    ClinicalTemporalKind,
)
from rootcause_mcp.domain.value_objects.differential_breadth import (
    BreadthCellStatus,
    DifferentialBreadthAudit,
    DifferentialBreadthAuditRole,
    DifferentialBreadthFramework,
)
from rootcause_mcp.domain.value_objects.enums import FishboneCategoryType
from rootcause_mcp.domain.value_objects.hfacs import is_valid_hfacs_code
from rootcause_mcp.domain.value_objects.leading_hypothesis import (
    LeadingHypothesisSelection,
)

HARD_CONFORMANCE_CODES = frozenset(
    {
        "GUIDANCE_READY",
        "GAP_ANALYSIS_RECOMPUTABLE",
        "NO_UNRESOLVED_SAFETY_CONFLICTS",
        "MULTI_SOURCE_MANIFEST",
        "SOURCE_INDEPENDENCE_LINEAGE",
        "MANIFEST_DOCUMENTS_REVIEWED",
        "SOURCE_REVIEW_ADJUDICATION_AUTHORIZED",
        "EVIDENCE_SOURCES_DECLARED",
        "EVIDENCE_VERIFICATION_COMPLETE",
        "SOURCE_INVENTORY_COUNTS_RECOMPUTABLE",
        "TIMELINE_EVIDENCE_LINEAGE",
        "CAUSATION_TEMPORAL_LINEAGE",
        "FINAL_REPORT_SECTIONS_INCLUDED",
        "FISHBONE_PRESENT",
        "HFACS_REVIEW_LINEAGE",
        "WHY_ROOT_PRESENT",
        "ROOT_EVIDENCE_LINEAGE",
        "ROOT_CAUSATION_AUDIT_LINEAGE",
        "ROOT_CAUSE_DISPOSITION_SAFE",
        "DIFFERENTIAL_MINIMUM_UNIQUE",
        "DIAGNOSIS_CONCEPT_IDENTIFIED",
        "DIFFERENTIAL_TYPED_CLASSIFICATION",
        "DIFFERENTIAL_MECHANISM_BREADTH",
        "DIFFERENTIAL_BREADTH_AUDIT_COMPLETE",
        "LIKELIHOOD_RATIO_CALIBRATION_VALID",
        "ACTIVE_DIFFERENTIAL_DISPOSITION",
        "DIAGNOSTIC_CERTAINTY_SUPPORTED",
        "LEADING_SELECTION_LINEAGE",
        "LEADING_DIAGNOSIS_CHALLENGED",
        "MUST_NOT_MISS_CHALLENGED",
        "REVIEWER_AUTHORIZED",
    }
)

_AUDIT_RESULTS = {
    "VERIFIED",
    "VERIFIED_WITH_CAVEATS",
    "REJECTED",
    "INSUFFICIENT_DATA",
}
_PENDING_TEST_STATUSES = {"PLANNED", "ORDERED"}
_DISCONFIRMING_TEST_PURPOSES = {"DISCONFIRM", "RULE_OUT"}
_DISCRIMINATING_TEST_PURPOSES = {
    "DISCONFIRM",
    "RULE_OUT",
    "DISCRIMINATE",
}
_TYPED_TEST_PURPOSES = {
    "DISCONFIRM",
    "RULE_OUT",
    "CONFIRM",
    "DISCRIMINATE",
}
_MECHANISM_CATEGORIES = {item.value for item in MechanismCategory}
_DIAGNOSTIC_ROLES = {item.value for item in DiagnosticRole}
_DIAGNOSTIC_CERTAINTIES = {item.value for item in DiagnosticCertainty}
_REASONING_BASES = {item.value for item in DiagnosticReasoningBasis}
_EVIDENCE_REQUIRED_CERTAINTIES = {
    DiagnosticCertainty.PROBABLE.value,
    DiagnosticCertainty.HIGH_CONFIDENCE.value,
    DiagnosticCertainty.CONFIRMED.value,
}
_ACCEPTED_VERIFICATION_METHODS = {
    "EXACT_SNIPPET_MATCH",
    "NORMALIZED_SNIPPET_MATCH",
    "MANUAL_REVIEWER_CONFIRMATION",
}
_SOURCE_REVIEW_EVENT_FIELDS = {
    "adjudication_id",
    "manifest_digest",
    "document_id",
    "status",
    "de_identified",
    "independence_status",
    "source_group_id",
    "parent_document_id",
    "derivation_method",
    "reviewed_by",
    "reason",
    "reviewed_at",
}
_SOURCE_REVIEW_PROJECTION_FIELDS = {
    "coverage_status",
    "de_identified",
    "independence_status",
    "source_group_id",
    "parent_document_id",
    "derivation_method",
    "source_review_adjudication_id",
    "source_reviewed_by",
    "source_reviewed_at",
    "source_review_reason",
}


def evaluate_final_report_conformance(  # noqa: PLR0915
    report: Mapping[str, Any],
    *,
    approved_by: str | None = None,
    authorized_reviewers: Collection[str] | None = None,
) -> list[dict[str, Any]]:
    """Recompute all hard, content-dependent final-report checks.

    Authorization is an operator-context property.  When the allowlist is
    absent, the reviewer check fails closed even if the payload contains a
    syntactically valid name.
    """
    evidence = _mapping_list(report.get("evidence"))
    evidence_by_id = {
        evidence_id: item
        for item in evidence
        if (evidence_id := _stable_id(item.get("id")))
    }
    known_evidence_ids = set(evidence_by_id)
    hypotheses = _mapping_list(report.get("hypotheses"))
    source_inventory = _mapping_list(report.get("source_inventory"))
    source_review_ledger = report.get("source_review_ledger")
    inventory_document_ids = {
        str(item.get("document"))
        for item in source_inventory
        if item.get("document") not in {None, ""}
        and str(item.get("coverage_status") or "")
        not in {"not_in_manifest", "registered_evidence_only"}
    }
    checks: list[dict[str, Any]] = []

    readiness = _mapping(report.get("report_readiness"))
    readiness_failures = _guidance_readiness_recomputation_failures(
        report,
        readiness,
        evidence,
        hypotheses,
    )
    checks.append(
        _check(
            "GUIDANCE_READY",
            not readiness_failures,
            "Clinical workflow readiness is internally consistent with the report ledger.",
            "Clinical workflow readiness must be recomputable from evidence, DDx, explicit leading selection, uncertainty, bias, and checklist state.",
            readiness_failures or ["#/report_readiness"],
        )
    )

    gap_analysis = _mapping(report.get("gap_analysis"))
    gap_failures, recomputed_critical, recomputed_high = (
        _gap_analysis_recomputation_failures(gap_analysis)
    )
    checks.append(
        _check(
            "GAP_ANALYSIS_RECOMPUTABLE",
            not gap_failures,
            "Gap-analysis counts and safety flag exactly match the conflict ledger.",
            "Gap-analysis summary fields must be deterministically recomputable from the conflict ledger.",
            gap_failures or ["#/gap_analysis"],
        )
    )
    conflicts_clear = (
        not gap_failures and recomputed_critical == 0 and recomputed_high == 0
    )
    checks.append(
        _check(
            "NO_UNRESOLVED_SAFETY_CONFLICTS",
            conflicts_clear,
            "No critical/high conflict remains and safety invariants are met.",
            "Critical/high conflicts are unresolved or the safety audit is absent.",
            ["#/gap_analysis"],
        )
    )

    _, source_independence_failures = _evaluate_source_independence(source_inventory)
    clinical_source_inventory = [
        item
        for item in _manifest_source_records(source_inventory)
        if _is_clinical_case_source(item)
    ]
    clinical_source_groups, _clinical_source_failures = _evaluate_source_independence(
        clinical_source_inventory
    )
    multi_source = (
        len(clinical_source_inventory) >= 2 and len(clinical_source_groups) >= 2
    )
    checks.append(
        _check(
            "MULTI_SOURCE_MANIFEST",
            multi_source,
            "At least two host-declared independent clinical case-source roots/groups with distinct content lineages are represented.",
            "At least two host-declared independent clinical case-source roots/groups are required; literature/calibration references, derivatives, and identical SHA-256 content do not increase this floor.",
            ["#/rca_session/source_document_count", "#/source_inventory"],
            details={
                "independent_source_groups": sorted(clinical_source_groups),
                "minimum_required": 2,
                "independence_basis": ("HOST_DECLARED_WITH_SHA256_DEDUPLICATION"),
                "excluded_reference_documents": sorted(
                    str(item.get("document"))
                    for item in _manifest_source_records(source_inventory)
                    if not _is_clinical_case_source(item)
                ),
            },
        )
    )
    checks.append(
        _check(
            "SOURCE_INDEPENDENCE_LINEAGE",
            bool(source_inventory) and not source_independence_failures,
            "Every manifest source has coherent host-declared independent/derived lineage.",
            "Host-declared independence must be explicit and content-coherent; derivatives require an in-manifest parent, method, acyclic lineage, and matching source group, while identical SHA-256 roots cannot claim different groups.",
            source_independence_failures or ["#/source_inventory"],
        )
    )

    unreviewed_documents = sorted(
        str(item.get("document") or "<missing-document-id>")
        for item in source_inventory
        if str(item.get("coverage_status") or "")
        not in {"not_in_manifest", "registered_evidence_only"}
        and str(item.get("coverage_status") or "").casefold() != "reviewed"
    )
    all_sources_reviewed = bool(source_inventory) and not unreviewed_documents
    checks.append(
        _check(
            "MANIFEST_DOCUMENTS_REVIEWED",
            all_sources_reviewed,
            "Every manifest source is marked reviewed.",
            "Every manifest source must be marked reviewed before finalization.",
            unreviewed_documents or ["#/source_inventory"],
        )
    )
    source_review_failures = _source_review_adjudication_failures(
        source_inventory,
        source_review_ledger,
        _mapping(report.get("rca_session")),
        authorized_reviewers=authorized_reviewers,
    )
    checks.append(
        _check(
            "SOURCE_REVIEW_ADJUDICATION_AUTHORIZED",
            bool(source_inventory) and not source_review_failures,
            "The complete source-review ledger is manifest-bound, append-only, authorized, and exactly reproduces the source inventory projection.",
            "A source inventory projection is not review evidence: the complete manifest-bound SRV ledger must have unique ordered events, authorized reviewers, exact counts, and a matching latest projection for every manifest document.",
            source_review_failures or ["#/source_review_ledger", "#/source_inventory"],
        )
    )

    undeclared_evidence = sorted(
        evidence_id or "<missing-evidence-id>"
        for item in evidence
        if (
            (evidence_id := _stable_id(item.get("id"))) is None
            or str(_mapping(item.get("source")).get("document_id") or "")
            not in inventory_document_ids
        )
    )
    evidence_sources_declared = bool(evidence) and not undeclared_evidence
    checks.append(
        _check(
            "EVIDENCE_SOURCES_DECLARED",
            evidence_sources_declared,
            "Every evidence item resolves to a declared source document.",
            "Evidence is missing or references a source outside the manifest.",
            undeclared_evidence or ["#/evidence"],
        )
    )

    verification_failures = _evidence_verification_failures(
        evidence,
        authorized_reviewers=authorized_reviewers,
    )
    checks.append(
        _check(
            "EVIDENCE_VERIFICATION_COMPLETE",
            bool(evidence) and not verification_failures,
            "Every final evidence item has an accepted verification method and identified verifier.",
            "Every final evidence item must be verified by an identified verifier using an accepted positive verification method.",
            verification_failures or ["#/evidence"],
        )
    )

    inventory_count_failures = _source_inventory_count_failures(
        source_inventory,
        evidence,
    )
    checks.append(
        _check(
            "SOURCE_INVENTORY_COUNTS_RECOMPUTABLE",
            bool(source_inventory) and not inventory_count_failures,
            "Source inventory evidence and verification counts match the evidence ledger.",
            "Source inventory counts must be non-negative, internally coherent, and exactly recomputable from the evidence ledger.",
            inventory_count_failures or ["#/source_inventory"],
        )
    )

    timeline_failures = _timeline_lineage_failures(
        _mapping_list(_mapping(report.get("timeline")).get("events")),
        evidence_by_id,
        inventory_document_ids,
    )
    checks.append(
        _check(
            "TIMELINE_EVIDENCE_LINEAGE",
            not timeline_failures,
            "Every timeline event resolves to the same evidence, source, and typed temporal record.",
            "Every final timeline event needs exact evidence/source/typed-time lineage; partial and unknown time must remain unpositioned.",
            timeline_failures or ["#/timeline/events"],
        )
    )

    causation_temporal_failures = _causation_temporal_lineage_failures(
        _mapping_list(report.get("causation_verifications")),
        evidence_by_id,
    )
    checks.append(
        _check(
            "CAUSATION_TEMPORAL_LINEAGE",
            not causation_temporal_failures,
            "Every claimed causation timestamp is grounded in matching aware-instant evidence.",
            "Date, range, relative, unknown, naive, unlinked, or internally inconsistent time cannot support a causation-temporality disposition.",
            causation_temporal_failures
            or ["#/causation_verifications/*/tests/temporality"],
        )
    )

    omitted_sections = _missing_final_sections(report)
    checks.append(
        _check(
            "FINAL_REPORT_SECTIONS_INCLUDED",
            not omitted_sections,
            "All mandatory final report sections are included.",
            "Final reports cannot omit reasoning, thinking, graph, timeline, or metrics.",
            omitted_sections or ["#/"],
        )
    )

    fishbone = _mapping(report.get("fishbone"))
    fishbone_causes = [
        cause
        for category in _mapping_list(fishbone.get("categories"))
        for cause in _mapping_list(category.get("causes"))
    ]
    checks.append(
        _check(
            "FISHBONE_PRESENT",
            bool(fishbone_causes),
            "A persisted Fishbone analysis contains at least one cause.",
            "A persisted Fishbone analysis with at least one cause is required.",
            ["#/fishbone/categories"],
        )
    )

    hfacs_review_failures = _hfacs_review_lineage_failures(
        fishbone,
        _mapping_list(report.get("hfacs_classifications")),
        known_evidence_ids,
        authorized_reviewers=authorized_reviewers,
    )
    checks.append(
        _check(
            "HFACS_REVIEW_LINEAGE",
            bool(fishbone_causes) and not hfacs_review_failures,
            "Every Fishbone cause has one authorized, persisted, ledger-exact HFACS review.",
            "Every Fishbone cause requires one CONFIRMED or NOT_APPLICABLE HFACS review whose cause, category, evidence, code, reviewer, time, and reason exactly match the persisted Fishbone ledger.",
            hfacs_review_failures or ["#/hfacs_classifications"],
        )
    )

    why_tree = _mapping(report.get("why_tree"))
    why_roots = [
        node
        for node in _mapping_list(why_tree.get("nodes"))
        if node.get("is_root_cause") is True
    ]
    why_root_ids = {
        root_id
        for root in why_roots
        if (root_id := _stable_id(root.get("id"))) is not None
    }
    checks.append(
        _check(
            "WHY_ROOT_PRESENT",
            bool(why_roots) and len(why_root_ids) == len(why_roots),
            "At least one stable Why root is present.",
            "A persisted Why root with a stable ID is required.",
            ["#/why_tree/nodes"],
        )
    )

    root_records = _mapping_list(report.get("root_causes"))
    audits = _mapping_list(report.get("causation_verifications"))
    root_evidence_failures = _root_evidence_failures(
        why_roots,
        root_records,
        known_evidence_ids,
        audits,
    )
    checks.append(
        _check(
            "ROOT_EVIDENCE_LINEAGE",
            not root_evidence_failures,
            "Every root ID, description, and evidence set matches the Why/evidence ledgers.",
            "Root ID, description, or evidence differs from the Why/evidence ledgers.",
            root_evidence_failures or ["#/root_causes"],
        )
    )

    audit_lineage_failures = _root_audit_lineage_failures(
        why_roots,
        root_records,
        audits,
        known_evidence_ids,
    )
    checks.append(
        _check(
            "ROOT_CAUSATION_AUDIT_LINEAGE",
            not audit_lineage_failures,
            "Every Why root has a conservative, ledger-consistent causation audit.",
            "A root causation audit is missing, orphaned, or inconsistent with its ledgers.",
            audit_lineage_failures or ["#/causation_verifications"],
        )
    )

    disposition_failures = _root_disposition_failures(
        why_roots,
        root_records,
        audits,
    )
    checks.append(
        _check(
            "ROOT_CAUSE_DISPOSITION_SAFE",
            not disposition_failures,
            "Rejected claims are absent and insufficient-data roots remain proposed.",
            "Rejected or incorrectly promoted causal claims remain in the final snapshot.",
            disposition_failures or ["#/root_causes"],
        )
    )

    normalized_diagnoses = [normalize_diagnosis(item) for item in hypotheses]
    duplicate_diagnoses = sorted(
        {
            name
            for name in normalized_diagnoses
            if name and normalized_diagnoses.count(name) > 1
        }
    )
    differential_ok = (
        len(hypotheses) >= 3
        and len(set(normalized_diagnoses)) >= 3
        and all(normalized_diagnoses)
        and not duplicate_diagnoses
    )
    checks.append(
        _check(
            "DIFFERENTIAL_MINIMUM_UNIQUE",
            differential_ok,
            "The differential contains at least three normalized unique diagnoses.",
            "At least three nonblank, normalized unique diagnoses are required.",
            duplicate_diagnoses or ["#/hypotheses"],
        )
    )

    diagnosis_concept_failures = [
        _stable_id(hypothesis.get("id")) or "<missing-hypothesis-id>"
        for hypothesis in hypotheses
        if not all(
            str(_mapping(hypothesis.get("diagnosis")).get(field_name) or "").strip()
            for field_name in ("code", "system")
        )
    ]
    checks.append(
        _check(
            "DIAGNOSIS_CONCEPT_IDENTIFIED",
            bool(hypotheses) and not diagnosis_concept_failures,
            "Every diagnosis has a nonblank code and coding system.",
            "Every final diagnosis requires a nonblank code and coding system; a stable local CUSTOM code is acceptable.",
            diagnosis_concept_failures or ["#/hypotheses"],
        )
    )

    classification_failures: list[str] = []
    mechanism_categories: set[str] = set()
    for hypothesis in hypotheses:
        hypothesis_id = _stable_id(hypothesis.get("id")) or "<missing-hypothesis-id>"
        mechanism_category = str(hypothesis.get("mechanism_category") or "").upper()
        diagnostic_role = str(hypothesis.get("diagnostic_role") or "").upper()
        certainty = str(hypothesis.get("certainty") or "").upper()
        reasoning_basis = str(hypothesis.get("reasoning_basis") or "").upper()
        if (
            mechanism_category not in _MECHANISM_CATEGORIES
            or diagnostic_role not in _DIAGNOSTIC_ROLES
            or certainty not in _DIAGNOSTIC_CERTAINTIES
            or reasoning_basis not in _REASONING_BASES
        ):
            classification_failures.append(hypothesis_id)
        if mechanism_category in _MECHANISM_CATEGORIES - {
            MechanismCategory.UNKNOWN.value
        }:
            mechanism_categories.add(mechanism_category)
    checks.append(
        _check(
            "DIFFERENTIAL_TYPED_CLASSIFICATION",
            bool(hypotheses) and not classification_failures,
            "Every diagnosis has typed mechanism, role, certainty, and reasoning-basis labels.",
            "Every diagnosis needs valid typed mechanism, role, certainty, and reasoning-basis labels.",
            classification_failures or ["#/hypotheses"],
        )
    )
    checks.append(
        _check(
            "DIFFERENTIAL_MECHANISM_BREADTH",
            len(mechanism_categories) >= 2,
            "The final differential spans at least two explicit etiologic mechanisms.",
            "Final synthesis requires at least two non-UNKNOWN etiologic mechanism categories; this is a breadth floor, not a target or a preliminary investigation blocker.",
            ["#/hypotheses"],
            details={
                "distinct_non_unknown_categories": sorted(mechanism_categories),
                "minimum_required": 2,
                "scope": "FINAL_BROAD_COVERAGE_FLOOR",
            },
        )
    )
    breadth_audits = _mapping_list(report.get("differential_breadth_audits"))
    breadth_audit_failures, breadth_audit_details = (
        evaluate_differential_breadth_audits(breadth_audits, hypotheses)
    )
    checks.append(
        _check(
            "DIFFERENTIAL_BREADTH_AUDIT_COMPLETE",
            not breadth_audit_failures,
            "A complete primary systematic DDx framework audit covers every report diagnosis.",
            "Final synthesis requires a complete primary breadth audit, no NOT_ASSESSED cells, and hypothesis/category-consistent candidate linkage.",
            breadth_audit_failures or ["#/differential_breadth_audits"],
            details=breadth_audit_details,
        )
    )

    lr_calibration_failures = _likelihood_ratio_calibration_failures(
        hypotheses,
        evidence_by_id,
    )
    checks.append(
        _check(
            "LIKELIHOOD_RATIO_CALIBRATION_VALID",
            not lr_calibration_failures,
            "Every applied LR has explicit, coherent quantitative calibration metadata.",
            "Every LR link must declare SOURCE_CALIBRATED with a verifiable reference, or QUANTITATIVELY_UNKNOWN with LR=1.0; missing metadata and agent-estimated non-neutral LRs are invalid.",
            lr_calibration_failures or ["#/hypotheses"],
        )
    )

    active_failures: list[str] = []
    evidence_dispositions: dict[str, tuple[bool, bool, bool]] = {}
    for hypothesis in hypotheses:
        hypothesis_id = _stable_id(hypothesis.get("id")) or "<missing-hypothesis-id>"
        disposition = evaluate_hypothesis_disposition(hypothesis, evidence_by_id)
        evidence_dispositions[hypothesis_id] = disposition
        if str(hypothesis.get("status") or "").upper() != "ACTIVE":
            continue
        has_support, has_contradiction, has_disconfirming_plan = disposition
        has_rationale = (
            len(str(hypothesis.get("clinical_rationale") or "").strip()) >= 10
        )
        has_uncertainty = any(
            str(item).strip()
            for item in _sequence(hypothesis.get("uncertainty_factors"))
        )
        has_discriminating_plan = has_pending_discriminating_test(hypothesis)
        if not (
            has_rationale
            and has_uncertainty
            and (has_support or has_contradiction or has_discriminating_plan)
        ):
            active_failures.append(hypothesis_id)
    checks.append(
        _check(
            "ACTIVE_DIFFERENTIAL_DISPOSITION",
            not active_failures,
            "Every active diagnosis has rationale, uncertainty, and a genuine evidence or discriminating-test disposition.",
            "Every active diagnosis needs a clinical rationale, explicit uncertainty, and either genuine LR-not-equal-to-1 evidence or a typed pending DISCONFIRM/RULE_OUT/DISCRIMINATE test.",
            active_failures or ["#/hypotheses"],
        )
    )

    certainty_failures: list[str] = []
    for hypothesis in hypotheses:
        hypothesis_id = _stable_id(hypothesis.get("id")) or "<missing-hypothesis-id>"
        if not diagnostic_certainty_is_supported(hypothesis, evidence_by_id):
            certainty_failures.append(hypothesis_id)
    checks.append(
        _check(
            "DIAGNOSTIC_CERTAINTY_SUPPORTED",
            not certainty_failures,
            "Diagnostic certainty labels are evidence/test supported and lifecycle coherent.",
            "PROBABLE/HIGH_CONFIDENCE/CONFIRMED requires genuine evidence or a completed typed diagnostic test; CONFIRMED and EXCLUDED labels must match lifecycle status.",
            certainty_failures or ["#/hypotheses"],
        )
    )

    eligible = [
        item
        for item in hypotheses
        if str(item.get("status") or "").upper()
        not in {"EXCLUDED", "ON_HOLD", "RULED_OUT"}
    ]
    leading_id = _stable_id(report.get("leading_hypothesis_id"))
    leading = next(
        (item for item in eligible if _stable_id(item.get("id")) == leading_id),
        None,
    )
    leading_disposition = evidence_dispositions.get(
        leading_id or "",
        (False, False, False),
    )
    hypothesis_ids = _record_ids(hypotheses)
    eligible_ids = _record_ids(eligible)
    leading_selection_failures = _leading_selection_lineage_failures(
        report,
        leading_id=leading_id,
        hypothesis_ids=hypothesis_ids,
        eligible_ids=eligible_ids,
    )
    checks.append(
        _check(
            "LEADING_SELECTION_LINEAGE",
            not leading_selection_failures,
            "The leading diagnosis matches the latest complete selection-ledger event.",
            "Final reports require a coherent LEADING_HYPOTHESIS_SELECTION history with an actor, reason, aware timestamp, and latest hypothesis matching leading_hypothesis_id.",
            leading_selection_failures or [leading_id or "#/leading_hypothesis_id"],
        )
    )
    leading_ok = (
        leading is not None
        and leading_disposition[0]
        and (leading_disposition[1] or leading_disposition[2])
    )
    checks.append(
        _check(
            "LEADING_DIAGNOSIS_CHALLENGED",
            leading_ok,
            "The explicitly selected leading diagnosis has genuine support and contradiction or a typed rule-out plan.",
            "An eligible explicit leading_hypothesis_id with genuine support plus a refuting evidence/test disposition is required; no lead is inferred from order or numeric compatibility.",
            [leading_id] if leading_id else ["#/leading_hypothesis_id"],
        )
    )

    must_not_miss = [item for item in hypotheses if item.get("must_not_miss") is True]
    must_not_miss_failures: list[str] = []
    for hypothesis in must_not_miss:
        hypothesis_id = _stable_id(hypothesis.get("id")) or "<missing-hypothesis-id>"
        has_support, has_contradiction, has_disconfirming_plan = (
            evidence_dispositions.get(hypothesis_id)
            or evaluate_hypothesis_disposition(hypothesis, evidence_by_id)
        )
        if not has_support or not (has_contradiction or has_disconfirming_plan):
            must_not_miss_failures.append(hypothesis_id)
    checks.append(
        _check(
            "MUST_NOT_MISS_CHALLENGED",
            bool(must_not_miss) and not must_not_miss_failures,
            "Every must-not-miss diagnosis has support and a genuine refuting disposition.",
            "Each must-not-miss diagnosis needs support plus contradiction or a typed pending rule-out test.",
            must_not_miss_failures or ["#/hypotheses"],
        )
    )

    reviewer = (approved_by or str(report.get("approved_by") or "")).strip()
    authorized = {
        item.strip().casefold() for item in authorized_reviewers or [] if item.strip()
    }
    reviewer_ok = (
        bool(reviewer)
        and authorized_reviewers is not None
        and reviewer.casefold() in authorized
    )
    checks.append(
        _check(
            "REVIEWER_AUTHORIZED",
            reviewer_ok,
            "A named reviewer identity satisfies the operator allowlist boundary.",
            "A named, operator-authorized reviewer identity is required; the allowlist does not prove clinical qualification.",
            ["#/approved_by"],
        )
    )

    assert {item["code"] for item in checks} == HARD_CONFORMANCE_CODES
    return sorted(checks, key=lambda item: str(item["code"]))


def hard_failures(checks: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Return only failed hard checks, suitable for a finalization blocker list."""
    return [
        dict(check)
        for check in checks
        if str(check.get("status")) == "FAIL"
        and str(check.get("severity")) in {"HARD", "BLOCKER", "ERROR"}
    ]


def _leading_selection_lineage_failures(
    report: Mapping[str, Any],
    *,
    leading_id: str | None,
    hypothesis_ids: set[str],
    eligible_ids: set[str],
) -> list[str]:
    """Validate the append-only selection projection behind the final lead."""
    failures: list[str] = []
    selections: list[LeadingHypothesisSelection] = []
    seen_selection_ids: set[str] = set()

    for index, step in enumerate(_mapping_list(report.get("thinking_chain"))):
        structured_data = _mapping(step.get("structured_data"))
        if structured_data.get("record_type") != "LEADING_HYPOTHESIS_SELECTION":
            continue
        pointer = f"#/thinking_chain/{index}/structured_data/selection"
        payload = structured_data.get("selection")
        if not isinstance(payload, Mapping):
            failures.append(pointer)
            continue
        try:
            selection = LeadingHypothesisSelection.model_validate(dict(payload))
        except ValueError:
            failures.append(pointer)
            continue
        if selection.selection_id in seen_selection_ids:
            failures.append(f"{pointer}/selection_id")
        seen_selection_ids.add(selection.selection_id)
        expected_previous = selections[-1].hypothesis_id if selections else None
        if selection.previous_hypothesis_id != expected_previous:
            failures.append(f"{pointer}/previous_hypothesis_id")
        if selection.hypothesis_id not in hypothesis_ids:
            failures.append(f"{pointer}/hypothesis_id")
        if selections and selection.changed_at < selections[-1].changed_at:
            failures.append(f"{pointer}/changed_at")
        selections.append(selection)

    if not selections:
        failures.append("#/thinking_chain/LEADING_HYPOTHESIS_SELECTION")
    else:
        latest_hypothesis_id = selections[-1].hypothesis_id
        if latest_hypothesis_id != leading_id:
            failures.append("#/leading_hypothesis_id")
        if latest_hypothesis_id not in eligible_ids:
            failures.append("#/leading_hypothesis_id")
    return sorted(set(failures))


def _check(
    code: str,
    passed: bool,
    pass_message: str,
    fail_message: str,
    refs: Sequence[str],
    *,
    details: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "code": code,
        "status": "PASS" if passed else "FAIL",
        "severity": "HARD",
        "message": pass_message if passed else fail_message,
        "refs": sorted({str(ref) for ref in refs if ref}),
        "details": dict(details or {}),
    }


def _missing_final_sections(report: Mapping[str, Any]) -> list[str]:
    missing: list[str] = []
    required_nonempty_sequences = (
        "reasoning_chain",
        "thinking_chain",
    )
    for field_name in required_nonempty_sequences:
        if not _sequence(report.get(field_name)):
            missing.append(f"#/{field_name}")
    timeline = _mapping(report.get("timeline"))
    if not _sequence(timeline.get("events")):
        missing.append("#/timeline/events")
    if not _mapping(report.get("evidence_graph")):
        missing.append("#/evidence_graph")
    if not _mapping(report.get("evidence_metrics")):
        missing.append("#/evidence_metrics")
    if not _mapping(report.get("reasoning_metrics")):
        missing.append("#/reasoning_metrics")
    return missing


def _guidance_readiness_recomputation_failures(
    report: Mapping[str, Any],
    readiness: Mapping[str, Any],
    evidence: list[Mapping[str, Any]],
    hypotheses: list[Mapping[str, Any]],
) -> list[str]:
    """Reject a caller-authored readiness flag that contradicts the snapshot."""
    failures: list[str] = []
    checklist = _mapping(readiness.get("checklist"))
    score = _finite_float(readiness.get("completeness_score"))
    missing = readiness.get("missing_prerequisites")
    next_actions = readiness.get("next_recommended_actions")
    push_questions = readiness.get("push_questions")
    if readiness.get("is_ready_for_report") is not True:
        failures.append("#/report_readiness/is_ready_for_report")
    if str(readiness.get("current_stage") or "") != "READY_FOR_SYNTHESIS":
        failures.append("#/report_readiness/current_stage")
    if score is None or score < 0.9 or score > 1.0:
        failures.append("#/report_readiness/completeness_score")
    if not isinstance(missing, list) or missing:
        failures.append("#/report_readiness/missing_prerequisites")
    if not isinstance(next_actions, list) or not next_actions:
        failures.append("#/report_readiness/next_recommended_actions")
    if not isinstance(push_questions, list) or not push_questions:
        failures.append("#/report_readiness/push_questions")
    if not str(readiness.get("stage_display") or "").strip():
        failures.append("#/report_readiness/stage_display")
    if str(readiness.get("session_id") or "") != str(report.get("session_id") or ""):
        failures.append("#/report_readiness/session_id")

    normalized = [normalize_diagnosis(item) for item in hypotheses]
    unique_diagnoses = {item for item in normalized if item}
    duplicates = sorted(
        {item for item in normalized if item and normalized.count(item) > 1}
    )
    mechanisms = sorted(
        {
            str(item.get("mechanism_category") or "")
            for item in hypotheses
            if str(item.get("mechanism_category") or "") not in {"", "UNKNOWN"}
        }
    )
    active = [
        item
        for item in hypotheses
        if str(item.get("status") or "").upper()
        not in {"EXCLUDED", "ON_HOLD", "RULED_OUT"}
    ]
    must_not_miss = [item for item in hypotheses if item.get("must_not_miss") is True]
    case_evidence = [
        item
        for item in evidence
        if str(item.get("evidence_type") or "").upper() != "LITERATURE"
    ]
    verified_count = sum(item.get("verified") is True for item in case_evidence)
    sourced_count = sum(
        bool(str(_mapping(item.get("source")).get("document_id") or "").strip())
        for item in case_evidence
    )
    linked_ids = {
        str(evidence_id)
        for hypothesis in hypotheses
        for field_name in (
            "supporting_evidence_ids",
            "contradicting_evidence_ids",
        )
        for evidence_id in _sequence(hypothesis.get(field_name))
        if str(evidence_id).strip()
    }
    linked_ids.update(
        str(relationship.get("evidence_id"))
        for hypothesis in hypotheses
        for relationship in _mapping_list(hypothesis.get("likelihood_ratios"))
        if str(relationship.get("evidence_id") or "").strip()
    )
    evidence_ids = {
        evidence_id
        for item in case_evidence
        if (evidence_id := _stable_id(item.get("id"))) is not None
    }
    thinking = _mapping_list(report.get("thinking_chain"))
    has_uncertainty = any(
        any(str(value).strip() for value in _sequence(step.get("uncertainty_factors")))
        for step in thinking
    )
    has_bias_review = any(
        any(str(value).strip() for value in _sequence(step.get("potential_biases")))
        for step in thinking
    )
    leading_id = _stable_id(report.get("leading_hypothesis_id"))
    eligible_ids = {
        hypothesis_id
        for item in active
        if (hypothesis_id := _stable_id(item.get("id"))) is not None
    }

    expected_values: dict[str, Any] = {
        "evidence_count": len(case_evidence),
        "verified_evidence_count": verified_count,
        "evidence_with_sources": sourced_count,
        "hypotheses_count": len(hypotheses),
        "unique_hypotheses_count": len(unique_diagnoses),
        "duplicate_normalized_diagnoses": duplicates,
        "active_hypotheses_count": len(active),
        "min_hypotheses_met": (
            len(hypotheses) >= 3 and len(unique_diagnoses) >= 3 and not duplicates
        ),
        "mechanism_categories": mechanisms,
        "mechanism_categories_count": len(mechanisms),
        "mechanism_breadth_met": len(mechanisms) >= 2,
        "must_not_miss_hypotheses_count": len(must_not_miss),
        "unlinked_evidence_count": len(evidence_ids - linked_ids),
        "leading_hypothesis_id": leading_id,
        "explicit_leading_hypothesis_selected": leading_id is not None,
        "leading_selection_eligible": leading_id in eligible_ids,
        "uncertainty_acknowledged": has_uncertainty,
        "bias_reviewed": has_bias_review,
        "reasoning_steps_recorded": len(_mapping_list(report.get("reasoning_chain"))),
    }
    for key, expected in expected_values.items():
        if checklist.get(key) != expected:
            failures.append(f"#/report_readiness/checklist/{key}")

    required_true_flags = (
        "differential_breadth_audit_complete",
        "must_not_miss_reviewed",
        "disconfirming_evidence_tested",
        "active_differential_disposition_complete",
        "diagnostic_certainty_supported",
        "leading_diagnosis_challenged",
        "must_not_miss_disposition_complete",
    )
    failures.extend(
        f"#/report_readiness/checklist/{key}"
        for key in required_true_flags
        if checklist.get(key) is not True
    )
    return sorted(set(failures))


def _gap_analysis_recomputation_failures(
    gap_analysis: Mapping[str, Any],
) -> tuple[list[str], int, int]:
    """Recompute every safety-relevant summary from the conflict ledger."""
    raw_conflicts = gap_analysis.get("conflicts")
    if not isinstance(raw_conflicts, list):
        return ["#/gap_analysis/conflicts"], 0, 0
    conflicts = _mapping_list(raw_conflicts)
    failures: list[str] = []
    if len(conflicts) != len(raw_conflicts):
        failures.append("#/gap_analysis/conflicts:invalid-record")
    severities = [str(item.get("severity") or "").upper() for item in conflicts]
    if any(
        severity not in {"CRITICAL", "HIGH", "MODERATE", "LOW"}
        for severity in severities
    ):
        failures.append("#/gap_analysis/conflicts:invalid-severity")
    conflict_ids = [_stable_id(item.get("conflict_id")) for item in conflicts]
    if any(conflict_id is None for conflict_id in conflict_ids):
        failures.append("#/gap_analysis/conflicts:missing-id")
    if len({item for item in conflict_ids if item is not None}) != len(conflict_ids):
        failures.append("#/gap_analysis/conflicts:duplicate-id")

    critical_count = severities.count("CRITICAL")
    high_count = severities.count("HIGH")
    expected_safety = critical_count == 0 and high_count == 0
    declared_total = _strict_nonnegative_int(gap_analysis.get("total_conflicts"))
    declared_critical = _strict_nonnegative_int(gap_analysis.get("critical_count"))
    declared_high = _strict_nonnegative_int(gap_analysis.get("high_count"))
    if declared_total != len(conflicts):
        failures.append("#/gap_analysis/total_conflicts")
    if declared_critical != critical_count:
        failures.append("#/gap_analysis/critical_count")
    if declared_high != high_count:
        failures.append("#/gap_analysis/high_count")
    if gap_analysis.get("safety_invariants_met") is not expected_safety:
        failures.append("#/gap_analysis/safety_invariants_met")
    return sorted(set(failures)), critical_count, high_count


def _evidence_verification_failures(
    evidence: list[Mapping[str, Any]],
    *,
    authorized_reviewers: Collection[str] | None,
) -> list[str]:
    """Return evidence IDs whose asserted verification is not trustworthy."""
    authorized = {
        reviewer.strip().casefold()
        for reviewer in authorized_reviewers or []
        if reviewer.strip()
    }
    failures: list[str] = []
    for item in evidence:
        evidence_id = _stable_id(item.get("id")) or "<missing-evidence-id>"
        method = str(item.get("verification_method") or "").strip().upper()
        verifier = str(item.get("verifier") or "").strip()
        manual_verifier_authorized = not (
            method == "MANUAL_REVIEWER_CONFIRMATION"
            and authorized_reviewers is not None
            and verifier.casefold() not in authorized
        )
        if (
            item.get("verified") is not True
            or method not in _ACCEPTED_VERIFICATION_METHODS
            or not verifier
            or not manual_verifier_authorized
        ):
            failures.append(evidence_id)
    return sorted(set(failures))


def _source_inventory_count_failures(
    source_inventory: list[Mapping[str, Any]],
    evidence: list[Mapping[str, Any]],
) -> list[str]:
    """Recompute per-document total/verified evidence counts from the ledger."""
    expected: dict[str, list[int]] = {}
    for item in evidence:
        document_id = _stable_id(_mapping(item.get("source")).get("document_id"))
        if document_id is None:
            continue
        counts = expected.setdefault(document_id, [0, 0])
        counts[0] += 1
        counts[1] += int(item.get("verified") is True)

    failures: list[str] = []
    for item in _manifest_source_records(source_inventory):
        document_id = _stable_id(item.get("document"))
        if document_id is None:
            failures.append("#/source_inventory/<missing-document-id>")
            continue
        total = _strict_nonnegative_int(item.get("evidence_count"))
        verified = _strict_nonnegative_int(item.get("verified_count"))
        expected_total, expected_verified = expected.get(document_id, [0, 0])
        if (
            total is None
            or verified is None
            or verified > total
            or total != expected_total
            or verified != expected_verified
        ):
            failures.append(document_id)
    return sorted(set(failures))


def _source_review_adjudication_failures(
    source_inventory: list[Mapping[str, Any]],
    raw_source_review_ledger: Any,
    rca_session: Mapping[str, Any],
    *,
    authorized_reviewers: Collection[str] | None,
) -> list[str]:
    """Recompute the latest source projection from the portable SRV ledger."""
    records = _manifest_source_records(source_inventory)
    by_document, inventory_index_failures = _index_manifest_sources(records)
    failures: list[str] = list(inventory_index_failures)
    manifest_digest, event_records, binding_failures = (
        _source_review_session_binding_failures(
            records,
            raw_source_review_ledger,
            rca_session,
        )
    )
    failures.extend(binding_failures)
    latest_by_document, event_failures = _validated_source_review_events(
        event_records,
        manifest_digest=manifest_digest,
        manifest_document_ids=set(by_document),
        authorized_reviewers=authorized_reviewers,
    )
    failures.extend(event_failures)

    manifest_document_ids = set(by_document)
    failures.extend(
        f"{document_id}:missing-source-review-event"
        for document_id in sorted(manifest_document_ids - set(latest_by_document))
    )
    failures.extend(
        f"{document_id}:undeclared-source-review-event"
        for document_id in sorted(set(latest_by_document) - manifest_document_ids)
    )
    failures.extend(_source_review_projection_failures(by_document, latest_by_document))
    return sorted(set(failures))


def _source_review_session_binding_failures(
    records: list[Mapping[str, Any]],
    raw_source_review_ledger: Any,
    rca_session: Mapping[str, Any],
) -> tuple[str, list[Mapping[str, Any]], list[str]]:
    """Validate portable ledger shape, manifest binding, and declared counts."""
    failures: list[str] = []
    manifest_digest = str(rca_session.get("source_manifest_digest") or "").strip()
    if re.fullmatch(r"sha256:[a-fA-F0-9]{64}", manifest_digest) is None:
        failures.append("#/rca_session/source_manifest_digest")
    raw_events = _sequence(raw_source_review_ledger)
    event_records = _mapping_list(raw_source_review_ledger)
    if not isinstance(raw_source_review_ledger, list) or len(event_records) != len(
        raw_events
    ):
        failures.append("#/source_review_ledger:invalid-record")
    if _strict_nonnegative_int(rca_session.get("source_document_count")) != len(
        records
    ):
        failures.append("#/rca_session/source_document_count")
    if _strict_nonnegative_int(rca_session.get("source_review_event_count")) != len(
        raw_events
    ):
        failures.append("#/rca_session/source_review_event_count")
    return manifest_digest, event_records, failures


def _validated_source_review_events(
    event_records: list[Mapping[str, Any]],
    *,
    manifest_digest: str,
    manifest_document_ids: set[str],
    authorized_reviewers: Collection[str] | None,
) -> tuple[dict[str, SourceReviewAdjudication], list[str]]:
    """Validate ordered events and return their latest per-document state."""
    authorized = {
        reviewer.strip().casefold()
        for reviewer in authorized_reviewers or []
        if reviewer.strip()
    }
    seen_event_ids: set[str] = set()
    latest_by_document: dict[str, SourceReviewAdjudication] = {}
    previous_global_time: datetime | None = None
    failures: list[str] = []
    for index, raw_event in enumerate(event_records):
        pointer = f"#/source_review_ledger/{index}"
        if not _SOURCE_REVIEW_EVENT_FIELDS.issubset(raw_event):
            failures.append(f"{pointer}:incomplete-event")
        try:
            event = SourceReviewAdjudication.model_validate(dict(raw_event))
        except ValueError:
            failures.append(pointer)
            continue

        if event.adjudication_id in seen_event_ids:
            failures.append(f"{pointer}/adjudication_id:duplicate")
        seen_event_ids.add(event.adjudication_id)
        if event.manifest_digest != manifest_digest:
            failures.append(f"{pointer}/manifest_digest")
        if event.document_id not in manifest_document_ids:
            failures.append(f"{pointer}/document_id")
        if (
            event.parent_document_id is not None
            and event.parent_document_id not in manifest_document_ids
        ):
            failures.append(f"{pointer}/parent_document_id")
        if not event.reviewed_by.strip() or not event.reason.strip():
            failures.append(pointer)
        if (
            authorized_reviewers is None
            or event.reviewed_by.strip().casefold() not in authorized
        ):
            failures.append(f"{pointer}/reviewed_by")
        if (
            previous_global_time is not None
            and event.reviewed_at < previous_global_time
        ):
            failures.append(f"{pointer}/reviewed_at:ledger-reordered")
        previous_global_time = event.reviewed_at

        previous = latest_by_document.get(event.document_id)
        if (
            previous is not None
            and previous.status is SourceReviewStatus.REVIEWED
            and event.status is not SourceReviewStatus.REVIEWED
        ):
            failures.append(f"{pointer}/status:review-regression")
        latest_by_document[event.document_id] = event
    return latest_by_document, failures


def _source_review_projection_failures(
    by_document: Mapping[str, Mapping[str, Any]],
    latest_by_document: Mapping[str, SourceReviewAdjudication],
) -> list[str]:
    """Compare the caller-visible inventory to the ledger-derived latest state."""
    failures: list[str] = []
    for document_id, inventory_item in by_document.items():
        latest = latest_by_document.get(document_id)
        if latest is None:
            continue
        if not _SOURCE_REVIEW_PROJECTION_FIELDS.issubset(inventory_item):
            failures.append(f"{document_id}:incomplete-source-projection")
        projected_review_time = _canonical_instant(
            inventory_item.get("source_reviewed_at")
        )
        projection_matches = (
            latest.status is SourceReviewStatus.REVIEWED
            and inventory_item.get("coverage_status") == latest.status.value
            and inventory_item.get("de_identified") is latest.de_identified
            and inventory_item.get("independence_status")
            == latest.independence_status.value
            and inventory_item.get("source_group_id") == latest.source_group_id
            and inventory_item.get("parent_document_id") == latest.parent_document_id
            and inventory_item.get("derivation_method") == latest.derivation_method
            and inventory_item.get("source_review_adjudication_id")
            == latest.adjudication_id
            and inventory_item.get("source_reviewed_by") == latest.reviewed_by
            and projected_review_time == latest.reviewed_at.timestamp()
            and inventory_item.get("source_review_reason") == latest.reason
        )
        if not projection_matches:
            failures.append(f"{document_id}:source-projection-mismatch")
    return failures


def _timeline_lineage_failures(
    events: list[Mapping[str, Any]],
    evidence_by_id: Mapping[str, Mapping[str, Any]],
    manifest_document_ids: set[str],
) -> list[str]:
    """Require exact source and typed temporal lineage without inferred ordering."""
    failures: list[str] = []
    event_ids = [_stable_id(event.get("id")) for event in events]
    duplicate_ids = {
        event_id
        for event_id in event_ids
        if event_id is not None and event_ids.count(event_id) > 1
    }
    failures.extend(f"{event_id}:duplicate" for event_id in duplicate_ids)
    for index, event in enumerate(events):
        event_id = _stable_id(event.get("id"))
        evidence = evidence_by_id.get(event_id or "")
        if event_id is None or evidence is None:
            failures.append(event_id or f"#/timeline/events/{index}:missing-id")
            continue
        event_source = _stable_id(event.get("source_document"))
        evidence_source = _stable_id(
            _mapping(evidence.get("source")).get("document_id")
        )
        event_temporal = _canonical_temporal_record(event.get("temporal"))
        evidence_temporal = _canonical_temporal_record(evidence.get("temporal"))
        expected_chronology = (
            "ORDERED_INSTANT"
            if evidence_temporal is not None
            and evidence_temporal.kind is ClinicalTemporalKind.INSTANT
            else "UNPOSITIONED"
        )
        expected_display = (
            evidence_temporal.display_value() if evidence_temporal is not None else None
        )
        if (
            event_source is None
            or event_source != evidence_source
            or event_source not in manifest_document_ids
            or event_temporal is None
            or evidence_temporal is None
            or event_temporal.model_dump(mode="json")
            != evidence_temporal.model_dump(mode="json")
            or event.get("temporal") != event_temporal.model_dump(mode="json")
            or evidence.get("temporal") != evidence_temporal.model_dump(mode="json")
            or str(event.get("chronology_status") or "") != expected_chronology
            or str(event.get("time") or "") != expected_display
            or str(event.get("time") or "") == "T_Event"
            or not _evidence_timestamp_matches_temporal(
                evidence.get("event_timestamp"),
                evidence_temporal,
            )
        ):
            failures.append(event_id)
    return sorted(set(failures))


def _canonical_temporal_record(value: Any) -> ClinicalTemporal | None:
    """Validate one complete canonical typed temporal record."""
    if not isinstance(value, Mapping):
        return None
    try:
        return ClinicalTemporal.model_validate(dict(value))
    except ValueError:
        return None


def _evidence_timestamp_matches_temporal(
    event_timestamp: Any,
    temporal: ClinicalTemporal | None,
) -> bool:
    """Keep the legacy timestamp mirror null except for a matching aware instant."""
    if temporal is None:
        return False
    if temporal.kind is not ClinicalTemporalKind.INSTANT:
        return event_timestamp in {None, ""}
    timestamp = _canonical_instant(event_timestamp)
    instant = temporal.aware_instant
    return (
        timestamp is not None
        and instant is not None
        and timestamp == instant.timestamp()
    )


def _causation_temporal_lineage_failures(
    audits: list[Mapping[str, Any]],
    evidence_by_id: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    """Reject any causation time claim not backed by aware-instant evidence."""
    failures: list[str] = []
    for index, audit in enumerate(audits):
        temporality = _mapping(_mapping(audit.get("tests")).get("temporality"))
        verification_id = _stable_id(audit.get("verification_id")) or (
            f"#/causation_verifications/{index}"
        )
        cause = _mapping(audit.get("cause_event"))
        effect = _mapping(audit.get("effect_event"))
        cause_timestamp = cause.get("timestamp")
        effect_timestamp = effect.get("timestamp")
        test_cause_time = temporality.get("cause_time")
        test_effect_time = temporality.get("effect_time")
        cause_instant = _canonical_instant(cause_timestamp)
        effect_instant = _canonical_instant(effect_timestamp)
        test_cause_instant = _canonical_instant(test_cause_time)
        test_effect_instant = _canonical_instant(test_effect_time)
        cause_claimed = bool(str(cause_timestamp or "").strip())
        effect_claimed = bool(str(effect_timestamp or "").strip())
        test_cause_claimed = bool(str(test_cause_time or "").strip())
        test_effect_claimed = bool(str(test_effect_time or "").strip())
        both_events_timed = cause_instant is not None and effect_instant is not None
        invalid_lineage = (
            cause_claimed != (cause_instant is not None)
            or effect_claimed != (effect_instant is not None)
            or test_cause_claimed != (test_cause_instant is not None)
            or test_effect_claimed != (test_effect_instant is not None)
            or (
                cause_instant is not None
                and not _causal_event_has_matching_instant(
                    cause,
                    cause_instant,
                    evidence_by_id,
                )
            )
            or (
                effect_instant is not None
                and not _causal_event_has_matching_instant(
                    effect,
                    effect_instant,
                    evidence_by_id,
                )
            )
            or (
                both_events_timed
                and (
                    test_cause_instant != cause_instant
                    or test_effect_instant != effect_instant
                )
            )
            or (not both_events_timed and (test_cause_claimed or test_effect_claimed))
        )
        if invalid_lineage or (
            temporality.get("passed") is True
            and (
                not both_events_timed
                or cause_instant is None
                or effect_instant is None
                or cause_instant >= effect_instant
            )
        ):
            failures.append(f"{verification_id}:temporality")
            continue
        declared_minutes = temporality.get("time_diff_minutes")
        if temporality.get("passed") is True:
            if cause_instant is None or effect_instant is None:  # pragma: no cover
                failures.append(f"{verification_id}:temporality")
                continue
            expected_minutes = int((effect_instant - cause_instant) / 60)
            valid_duration = (
                not isinstance(declared_minutes, bool)
                and isinstance(declared_minutes, int)
                and declared_minutes == expected_minutes
            )
        else:
            valid_duration = declared_minutes is None
        if not valid_duration:
            failures.append(f"{verification_id}:temporality-duration")
    return sorted(set(failures))


def _causal_event_has_matching_instant(
    event: Mapping[str, Any],
    expected_instant: float,
    evidence_by_id: Mapping[str, Mapping[str, Any]],
) -> bool:
    """Return whether event evidence contains the exact claimed aware instant."""
    for evidence_id in _string_list(event.get("evidence")):
        evidence = evidence_by_id.get(evidence_id)
        if evidence is None:
            continue
        temporal = _canonical_temporal_record(evidence.get("temporal"))
        if (
            temporal is not None
            and temporal.kind is ClinicalTemporalKind.INSTANT
            and temporal.aware_instant is not None
            and temporal.aware_instant.timestamp() == expected_instant
            and _evidence_timestamp_matches_temporal(
                evidence.get("event_timestamp"),
                temporal,
            )
        ):
            return True
    return False


def _strict_nonnegative_int(value: Any) -> int | None:
    """Reject booleans/coercible strings instead of trusting caller counts."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return int(value)


def _canonical_instant(value: Any) -> float | None:
    """Normalize one timezone-aware ISO/RFC3339 instant for exact comparison."""
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.timestamp()


def _evaluate_source_independence(
    source_inventory: list[Mapping[str, Any]],
) -> tuple[set[str], list[str]]:
    """Return independent root/group IDs and deterministic lineage failures."""
    manifest_records = _manifest_source_records(source_inventory)
    if not manifest_records:
        return set(), ["#/source_inventory:no-manifest-source"]
    by_id, failures = _index_manifest_sources(manifest_records)
    independent_groups, status_failures = _classify_source_roots(by_id)
    failures.extend(status_failures)
    failures.extend(
        failure
        for document_id, item in by_id.items()
        if (failure := _derived_lineage_failure(document_id, item, by_id)) is not None
    )
    return independent_groups, sorted(set(failures))


def _manifest_source_records(
    source_inventory: list[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    """Exclude evidence-only rows that are not part of the pinned manifest."""
    return [
        item
        for item in source_inventory
        if str(item.get("coverage_status") or "")
        not in {"not_in_manifest", "registered_evidence_only"}
    ]


def _is_clinical_case_source(item: Mapping[str, Any]) -> bool:
    """Exclude literature/reference/calibration documents from the raw-case floor."""
    source_kind = str(item.get("source_kind") or "").strip().casefold()
    return source_kind not in {
        "literature",
        "reference",
        "guideline",
        "calibration",
    }


def _index_manifest_sources(
    manifest_records: list[Mapping[str, Any]],
) -> tuple[dict[str, Mapping[str, Any]], list[str]]:
    """Build a stable index and report missing/duplicate document identities."""
    failures: list[str] = []
    document_ids = [
        _stable_id(item.get("document")) or "<missing-document-id>"
        for item in manifest_records
    ]
    duplicate_ids = {
        document_id
        for document_id in document_ids
        if document_ids.count(document_id) > 1
    }
    failures.extend(f"{document_id}:duplicate" for document_id in duplicate_ids)
    by_id = {
        document_id: item
        for item in manifest_records
        if (document_id := _stable_id(item.get("document"))) is not None
    }
    if len(by_id) != len(manifest_records):
        failures.append("#/source_inventory/<missing-document-id>")
    return by_id, failures


def _classify_source_roots(
    by_id: Mapping[str, Mapping[str, Any]],
) -> tuple[set[str], list[str]]:
    """Classify independent roots and validate immediate derivation metadata."""
    independent_records: list[tuple[str, Mapping[str, Any]]] = []
    failures: list[str] = []
    for document_id, item in by_id.items():
        status = str(item.get("independence_status") or "").casefold()
        parent_id = _stable_id(item.get("parent_document_id"))
        method = str(item.get("derivation_method") or "").strip()
        if status == "independent":
            if parent_id is not None:
                failures.append(f"{document_id}:independent-has-parent")
            independent_records.append((document_id, item))
        elif status == "derived":
            if parent_id is None or parent_id not in by_id or not method:
                failures.append(f"{document_id}:incomplete-derivation")
        else:
            failures.append(f"{document_id}:independence-unknown")
    independent_groups, duplicate_content_failures = (
        _collapse_host_declared_independent_roots(independent_records)
    )
    failures.extend(duplicate_content_failures)
    return independent_groups, failures


def _collapse_host_declared_independent_roots(
    records: list[tuple[str, Mapping[str, Any]]],
) -> tuple[set[str], list[str]]:
    """Collapse roots connected by declared group or identical content hash."""
    adjacency: dict[str, set[str]] = {
        document_id: set() for document_id, _item in records
    }
    failures: list[str] = []
    for index, (left_id, left) in enumerate(records):
        left_group = _stable_id(left.get("source_group_id")) or left_id
        left_sha = _normalized_sha256(left.get("sha256"))
        for right_id, right in records[index + 1 :]:
            right_group = _stable_id(right.get("source_group_id")) or right_id
            right_sha = _normalized_sha256(right.get("sha256"))
            same_content = left_sha is not None and left_sha == right_sha
            if left_group == right_group or same_content:
                adjacency[left_id].add(right_id)
                adjacency[right_id].add(left_id)
            if same_content and left_group != right_group:
                failures.append(
                    f"{left_id},{right_id}:identical-sha256-different-host-groups"
                )

    collapsed_groups: set[str] = set()
    remaining = set(adjacency)
    by_id = dict(records)
    while remaining:
        seed = min(remaining)
        component: set[str] = set()
        pending = [seed]
        while pending:
            document_id = pending.pop()
            if document_id in component:
                continue
            component.add(document_id)
            pending.extend(adjacency[document_id] - component)
        remaining -= component
        declared_groups = {
            _stable_id(by_id[document_id].get("source_group_id")) or document_id
            for document_id in component
        }
        collapsed_groups.add(min(declared_groups))
    return collapsed_groups, failures


def _normalized_sha256(value: Any) -> str | None:
    """Return a comparable complete SHA-256 digest, ignoring absent legacy rows."""
    normalized = str(value or "").strip().casefold()
    if len(normalized) != 64 or any(
        character not in "0123456789abcdef" for character in normalized
    ):
        return None
    return normalized


def _derived_lineage_failure(
    document_id: str,
    item: Mapping[str, Any],
    by_id: Mapping[str, Mapping[str, Any]],
) -> str | None:
    """Return one deterministic failure for a derived document lineage."""
    if str(item.get("independence_status") or "").casefold() != "derived":
        return None
    root_id, lineage_failure = _resolve_independent_root(document_id, by_id)
    if lineage_failure is not None or root_id is None:
        return lineage_failure
    root = by_id[root_id]
    root_group = _stable_id(root.get("source_group_id")) or root_id
    derived_group = _stable_id(item.get("source_group_id"))
    if derived_group is not None and derived_group != root_group:
        return f"{document_id}:source-group-mismatch"
    return None


def _resolve_independent_root(
    document_id: str,
    by_id: Mapping[str, Mapping[str, Any]],
) -> tuple[str | None, str | None]:
    """Walk one derivation chain and return its independent root or failure."""
    seen: set[str] = set()
    cursor_id = document_id
    while cursor_id not in seen:
        seen.add(cursor_id)
        cursor = by_id.get(cursor_id)
        if cursor is None:
            return None, f"{document_id}:missing-parent"
        cursor_status = str(cursor.get("independence_status") or "").casefold()
        if cursor_status == "independent":
            return cursor_id, None
        if cursor_status != "derived":
            return None, f"{document_id}:root-not-independent"
        parent_id = _stable_id(cursor.get("parent_document_id"))
        if parent_id is None:
            return None, f"{document_id}:missing-parent"
        cursor_id = parent_id
    return None, f"{document_id}:derivation-cycle"


def _hfacs_review_lineage_failures(
    fishbone: Mapping[str, Any],
    classifications: list[Mapping[str, Any]],
    known_evidence_ids: set[str],
    *,
    authorized_reviewers: Collection[str] | None,
) -> list[str]:
    """Validate one authorized, exact HFACS review per persisted Fishbone cause."""
    failures: list[str] = []
    valid_categories = {category.value for category in FishboneCategoryType}
    fishbone_by_id: dict[str, tuple[str, Mapping[str, Any]]] = {}
    fishbone_ids: list[str] = []
    raw_categories = fishbone.get("categories")
    categories = _mapping_list(raw_categories)
    if not isinstance(raw_categories, list) or len(categories) != len(raw_categories):
        failures.append("#/fishbone/categories:invalid-record")
    for category_index, category in enumerate(categories):
        category_name = str(category.get("category") or "")
        raw_causes = category.get("causes")
        causes = _mapping_list(raw_causes)
        if (
            category_name not in valid_categories
            or not isinstance(raw_causes, list)
            or len(causes) != len(raw_causes)
        ):
            failures.append(f"#/fishbone/categories/{category_index}")
        for cause_index, cause in enumerate(causes):
            cause_id = _stable_id(cause.get("cause_id"))
            if cause_id is None:
                failures.append(
                    f"#/fishbone/categories/{category_index}/causes/{cause_index}"
                )
                continue
            fishbone_ids.append(cause_id)
            fishbone_by_id.setdefault(cause_id, (category_name, cause))
    failures.extend(
        f"{cause_id}:duplicate-fishbone-cause"
        for cause_id in sorted(
            {cause_id for cause_id in fishbone_ids if fishbone_ids.count(cause_id) > 1}
        )
    )

    classification_ids = [_stable_id(item.get("cause_id")) for item in classifications]
    failures.extend(
        f"{cause_id}:duplicate-hfacs-review"
        for cause_id in sorted(
            {
                cause_id
                for cause_id in classification_ids
                if cause_id is not None and classification_ids.count(cause_id) > 1
            }
        )
    )
    classifications_by_id = {
        cause_id: item
        for item in classifications
        if (cause_id := _stable_id(item.get("cause_id"))) is not None
    }
    if any(cause_id is None for cause_id in classification_ids):
        failures.append("#/hfacs_classifications/<missing-cause-id>")

    authorized = {
        reviewer.strip().casefold()
        for reviewer in authorized_reviewers or []
        if reviewer.strip()
    }
    for cause_id, (category_name, cause) in fishbone_by_id.items():
        classification = classifications_by_id.get(cause_id)
        if classification is None:
            failures.append(f"{cause_id}:missing-hfacs-review")
            continue
        status = str(cause.get("hfacs_review_status") or "").upper()
        classification_status = str(classification.get("review_status") or "").upper()
        code = _stable_id(cause.get("hfacs_code"))
        classification_code = _stable_id(classification.get("hfacs_code"))
        reviewed_by = str(cause.get("hfacs_reviewed_by") or "").strip()
        reviewed_at = cause.get("hfacs_reviewed_at")
        review_reason = str(cause.get("hfacs_review_reason") or "").strip()
        cause_evidence = _string_list(cause.get("evidence"))
        classification_evidence = _string_list(classification.get("evidence"))
        reviewer_authorized = authorized_reviewers is None or (
            reviewed_by.casefold() in authorized
        )
        status_semantics_valid = (
            status == "CONFIRMED" and code is not None and is_valid_hfacs_code(code)
        ) or (status == "NOT_APPLICABLE" and code is None)
        if (
            status not in {"CONFIRMED", "NOT_APPLICABLE"}
            or not status_semantics_valid
            or classification_status != status
            or classification_code != code
            or str(classification.get("cause") or "")
            != str(cause.get("description") or "")
            or str(classification.get("category") or "") != category_name
            or classification_evidence != cause_evidence
            or len(cause_evidence) != len(_sequence(cause.get("evidence")))
            or len(classification_evidence)
            != len(_sequence(classification.get("evidence")))
            or not set(cause_evidence).issubset(known_evidence_ids)
            or str(classification.get("reviewed_by") or "").strip() != reviewed_by
            or str(classification.get("reviewed_at") or "") != str(reviewed_at or "")
            or str(classification.get("review_reason") or "").strip() != review_reason
            or classification.get("source") != "fishbone_cause"
            or not str(cause.get("description") or "").strip()
            or not reviewed_by
            or _canonical_instant(reviewed_at) is None
            or not review_reason
            or not reviewer_authorized
        ):
            failures.append(cause_id)

    failures.extend(
        f"{cause_id}:orphan-hfacs-review"
        for cause_id in sorted(set(classifications_by_id) - set(fishbone_by_id))
    )
    return sorted(set(failures))


def _root_evidence_failures(
    why_roots: list[Mapping[str, Any]],
    root_records: list[Mapping[str, Any]],
    known_evidence_ids: set[str],
    audits: list[Mapping[str, Any]],
) -> list[str]:
    failures: list[str] = []
    root_by_id = {
        root_id: root
        for root in root_records
        if (root_id := _stable_id(root.get("id"))) is not None
    }
    latest_result_by_root: dict[str, str] = {}
    for audit in audits:
        audit_root_id = _stable_id(_mapping(audit.get("cause_event")).get("id"))
        if audit_root_id:
            latest_result_by_root[audit_root_id] = str(
                audit.get("overall_result") or ""
            ).upper()
    non_rejected_root_ids = {
        root_id
        for item in why_roots
        if (root_id := _stable_id(item.get("id"))) is not None
        and latest_result_by_root.get(root_id) != "REJECTED"
    }
    if non_rejected_root_ids and not root_by_id:
        failures.append("#/root_causes")
    for why_root in why_roots:
        root_id = _stable_id(why_root.get("id"))
        if root_id is None:
            failures.append("#/why_tree/nodes/<missing-id>")
            continue
        root_record = root_by_id.get(root_id)
        if latest_result_by_root.get(root_id) == "REJECTED":
            if root_record is not None:
                failures.append(f"{root_id}:rejected-in-root-bucket")
            continue
        if root_record is None:
            failures.append(root_id)
            continue
        why_evidence = _string_list(why_root.get("evidence"))
        record_evidence = _string_list(root_record.get("evidence"))
        if (
            str(root_record.get("answer") or "") != str(why_root.get("answer") or "")
            or not why_evidence
            or len(why_evidence) != len(set(why_evidence))
            or set(record_evidence) != set(why_evidence)
            or not set(why_evidence).issubset(known_evidence_ids)
        ):
            failures.append(root_id)
    if set(root_by_id) - {
        root_id
        for item in why_roots
        if (root_id := _stable_id(item.get("id"))) is not None
    }:
        failures.extend(
            sorted(set(root_by_id) - {str(item.get("id")) for item in why_roots})
        )
    return sorted(set(failures))


def _root_audit_lineage_failures(
    why_roots: list[Mapping[str, Any]],
    root_records: list[Mapping[str, Any]],
    audits: list[Mapping[str, Any]],
    known_evidence_ids: set[str],
) -> list[str]:
    failures: list[str] = []
    why_by_id = {
        root_id: root
        for root in why_roots
        if (root_id := _stable_id(root.get("id"))) is not None
    }
    audits_by_root: dict[str, list[Mapping[str, Any]]] = {}
    verification_ids = [
        str(audit.get("verification_id") or "").strip() for audit in audits
    ]
    if any(not verification_id for verification_id in verification_ids):
        failures.append("#/causation_verifications/<missing-verification-id>")
    duplicate_verification_ids = {
        verification_id
        for verification_id in verification_ids
        if verification_id and verification_ids.count(verification_id) > 1
    }
    failures.extend(
        f"verification_id:{verification_id}:duplicate"
        for verification_id in duplicate_verification_ids
    )
    root_record_by_id = {
        root_id: root
        for root in root_records
        if (root_id := _stable_id(root.get("id"))) is not None
    }
    for audit in audits:
        cause_event = _mapping(audit.get("cause_event"))
        root_id = _stable_id(cause_event.get("id"))
        if root_id is None or root_id not in why_by_id:
            failures.append(root_id or "#/causation_verifications/<missing-cause-id>")
            continue
        audits_by_root.setdefault(root_id, []).append(audit)

    for root_id, why_root in why_by_id.items():
        root_audits = audits_by_root.get(root_id, [])
        if not root_audits:
            failures.append(root_id)
            continue
        audit = root_audits[-1]
        cause_event = _mapping(audit.get("cause_event"))
        effect_event = _mapping(audit.get("effect_event"))
        cause_evidence = _string_list(cause_event.get("evidence"))
        effect_evidence = _string_list(effect_event.get("evidence"))
        why_evidence = _string_list(why_root.get("evidence"))
        result = str(audit.get("overall_result") or "").upper()
        root_record = root_record_by_id.get(root_id)
        expected_verification_id = str(audit.get("verification_id") or "").strip()
        root_verification_matches = result == "REJECTED" or (
            root_record is not None
            and str(root_record.get("causation_verification_id") or "").strip()
            == expected_verification_id
        )
        semantic_failure = _causation_audit_semantics_failure(audit)
        if (
            str(cause_event.get("description") or "")
            != str(why_root.get("answer") or "")
            or not cause_evidence
            or len(cause_evidence) != len(set(cause_evidence))
            or set(cause_evidence) != set(why_evidence)
            or not set(cause_evidence).issubset(known_evidence_ids)
            or not effect_evidence
            or len(effect_evidence) != len(set(effect_evidence))
            or not set(effect_evidence).issubset(known_evidence_ids)
            or result not in _AUDIT_RESULTS
            or not root_verification_matches
            or audit.get("audit_scope") != "CONSERVATIVE_CAUSATION_AUDIT"
            or audit.get("clinical_causality_established") is not False
            or semantic_failure is not None
        ):
            failures.append(
                f"{root_id}:{semantic_failure}" if semantic_failure else root_id
            )
    return sorted(set(failures))


def _causation_audit_semantics_failure(
    audit: Mapping[str, Any],
) -> str | None:
    """Re-derive dispositions emitted by the conservative MVP validator.

    The current validator can establish reverse chronology (REJECTED) or retain
    a claim as INSUFFICIENT_DATA.  It cannot produce clinical proof, and its
    necessity/mechanism/sufficiency checks deliberately never auto-pass.  A
    caller-supplied VERIFIED label is therefore always a forged state here.
    """
    level = str(audit.get("verification_level") or "").lower()
    result = str(audit.get("overall_result") or "").upper()
    header_failure = _causation_audit_header_failure(audit, result, level)
    if header_failure is not None:
        return header_failure

    tests = _mapping(audit.get("tests"))
    temporality = _mapping(tests.get("temporality"))
    if not _temporality_obligation_complete(temporality):
        return "incomplete-temporality"
    cause_instant = _canonical_instant(
        _mapping(audit.get("cause_event")).get("timestamp")
    )
    effect_instant = _canonical_instant(
        _mapping(audit.get("effect_event")).get("timestamp")
    )
    known_reverse = (
        cause_instant is not None
        and effect_instant is not None
        and cause_instant >= effect_instant
        and temporality.get("passed") is False
    )
    if known_reverse:
        return None if result == "REJECTED" else "reverse-chronology-result-mismatch"
    if result == "REJECTED":
        return "rejection-without-known-reverse-chronology"
    return _causation_test_obligations_failure(tests, level, result)


def _causation_audit_header_failure(
    audit: Mapping[str, Any],
    result: str,
    level: str,
) -> str | None:
    """Validate non-test fields before deriving the audit disposition."""
    failure: str | None = None
    if result in {"VERIFIED", "VERIFIED_WITH_CAVEATS"}:
        failure = "unsupported-audit-pass"
    elif level not in {"standard", "comprehensive"}:
        failure = "invalid-verification-level"
    elif not str(audit.get("interpretation") or "").strip():
        failure = "missing-interpretation"
    elif not _string_list(audit.get("next_steps")):
        failure = "missing-next-steps"
    return failure


def _causation_test_obligations_failure(
    tests: Mapping[str, Any],
    level: str,
    result: str,
) -> str | None:
    """Validate the level-specific obligations and recompute insufficiency."""
    temporality = _mapping(tests.get("temporality"))
    necessity = _mapping(tests.get("necessity"))
    failure: str | None = None
    required_results = [temporality.get("passed"), necessity.get("passed")]
    if not _necessity_obligation_complete(necessity):
        failure = "incomplete-necessity"
    elif level == "comprehensive":
        mechanism = _mapping(tests.get("mechanism"))
        sufficiency = _mapping(tests.get("sufficiency"))
        if not _mechanism_obligation_complete(mechanism):
            failure = "incomplete-mechanism"
        elif not _sufficiency_obligation_complete(sufficiency):
            failure = "incomplete-sufficiency"
        else:
            required_results.extend(
                [mechanism.get("passed"), sufficiency.get("passed")]
            )
    if failure is None and (
        result != "INSUFFICIENT_DATA" or all(item is True for item in required_results)
    ):
        failure = "overall-result-does-not-match-obligations"
    return failure


def _temporality_obligation_complete(test: Mapping[str, Any]) -> bool:
    return isinstance(test.get("passed"), bool) and bool(
        str(test.get("conclusion") or "").strip()
    )


def _necessity_obligation_complete(test: Mapping[str, Any]) -> bool:
    return isinstance(test.get("passed"), bool) and all(
        str(test.get(field_name) or "").strip()
        for field_name in (
            "counterfactual_question",
            "counterfactual_answer",
            "reasoning",
        )
    )


def _mechanism_obligation_complete(test: Mapping[str, Any]) -> bool:
    pathway = _string_list(test.get("causal_pathway"))
    return (
        isinstance(test.get("passed"), bool)
        and len(pathway) >= 2
        and bool(str(test.get("mechanism_plausibility") or "").strip())
        and isinstance(test.get("domain_knowledge_support"), bool)
    )


def _sufficiency_obligation_complete(test: Mapping[str, Any]) -> bool:
    return (
        isinstance(test.get("passed"), bool)
        and all(
            str(test.get(field_name) or "").strip()
            for field_name in ("analysis", "conclusion")
        )
        and isinstance(test.get("confounders_identified"), list)
    )


def _root_disposition_failures(
    why_roots: list[Mapping[str, Any]],
    root_records: list[Mapping[str, Any]],
    audits: list[Mapping[str, Any]],
) -> list[str]:
    failures: list[str] = []
    why_root_ids = {
        root_id
        for item in why_roots
        if (root_id := _stable_id(item.get("id"))) is not None
    }
    root_by_id = {
        root_id: root
        for root in root_records
        if (root_id := _stable_id(root.get("id"))) is not None
    }
    latest_audit_by_id: dict[str, Mapping[str, Any]] = {}
    for audit in audits:
        cause_id = _stable_id(_mapping(audit.get("cause_event")).get("id"))
        if cause_id:
            latest_audit_by_id[cause_id] = audit

    for root_id in why_root_ids:
        latest_audit = latest_audit_by_id.get(root_id)
        result = str((latest_audit or {}).get("overall_result") or "").upper()
        root_record = root_by_id.get(root_id)
        if result == "REJECTED":
            if root_record is not None:
                failures.append(f"{root_id}:rejected-in-root-bucket")
            continue
        if root_record is None:
            failures.append(f"{root_id}:missing-root-record")
            continue
        disposition = str(root_record.get("disposition") or "").upper()
        if result == "INSUFFICIENT_DATA" and disposition != "PROPOSED":
            failures.append(f"{root_id}:insufficient-not-proposed")
        if result in {"VERIFIED", "VERIFIED_WITH_CAVEATS"} and disposition != (
            "AUDIT_OBLIGATIONS_PASSED"
        ):
            failures.append(f"{root_id}:audit-pass-not-labeled")
        if str(root_record.get("causation_result") or "").upper() != result:
            failures.append(f"{root_id}:result-mismatch")

    for root_id, root_record in root_by_id.items():
        if root_id not in why_root_ids:
            failures.append(f"{root_id}:not-a-why-root")
        if str(root_record.get("causation_result") or "").upper() == "REJECTED":
            failures.append(f"{root_id}:rejected-in-root-bucket")
    return sorted(set(failures))


def _likelihood_ratio_calibration_failures(
    hypotheses: Sequence[Mapping[str, Any]],
    evidence_by_id: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    """Reject caller-asserted, incoherent, or non-ledger-calibrated LRs."""
    failures: list[str] = []
    for hypothesis in hypotheses:
        hypothesis_id = _stable_id(hypothesis.get("id")) or "<missing-hypothesis-id>"
        for index, relationship in enumerate(
            _mapping_list(hypothesis.get("likelihood_ratios"))
        ):
            status = str(relationship.get("calibration_status") or "").upper()
            applied_lr = _safe_float(relationship.get("applied_likelihood_ratio"))
            supports = relationship.get("supports")
            calibrated = _relationship_is_source_calibrated(
                relationship,
                evidence_by_id,
            )
            quantitatively_unknown = (
                status == LikelihoodRatioCalibrationStatus.QUANTITATIVELY_UNKNOWN.value
                and applied_lr is not None
                and math.isclose(applied_lr, 1.0)
                and supports is None
                and not str(relationship.get("calibration_source_ref") or "").strip()
            )
            direction_coherent = _likelihood_direction_is_coherent(
                applied_lr,
                supports,
            )
            target_evidence_id = _stable_id(relationship.get("evidence_id"))
            if (
                not str(relationship.get("rationale") or "").strip()
                or target_evidence_id not in evidence_by_id
                or not direction_coherent
                or (not calibrated and not quantitatively_unknown)
            ):
                failures.append(f"{hypothesis_id}:likelihood_ratios/{index}")
    return sorted(set(failures))


def _relationship_is_source_calibrated(
    relationship: Mapping[str, Any],
    evidence_by_id: Mapping[str, Mapping[str, Any]],
) -> bool:
    """Require calibration to resolve to a verified local literature record."""
    source_ref = _stable_id(relationship.get("calibration_source_ref"))
    calibration_evidence = evidence_by_id.get(source_ref or "")
    target_evidence_id = _stable_id(relationship.get("evidence_id"))
    target_evidence = evidence_by_id.get(target_evidence_id or "")
    return (
        str(relationship.get("calibration_status") or "").upper()
        == LikelihoodRatioCalibrationStatus.SOURCE_CALIBRATED.value
        and is_calibration_evidence_ref(source_ref)
        and _calibration_evidence_is_admissible(calibration_evidence)
        and target_evidence_id != source_ref
        and target_evidence is not None
        and target_evidence.get("verified") is True
        and str(target_evidence.get("evidence_type") or "").upper() != "LITERATURE"
        and _likelihood_direction_is_coherent(
            _safe_float(relationship.get("applied_likelihood_ratio")),
            relationship.get("supports"),
        )
    )


def _calibration_evidence_is_admissible(
    evidence: Mapping[str, Any] | None,
) -> bool:
    """Validate a report-local quantitative calibration evidence record."""
    if (
        evidence is None
        or str(evidence.get("evidence_type") or "").upper() != "LITERATURE"
    ):
        return False
    source = _mapping(evidence.get("source"))
    content_hash = str(source.get("content_hash") or "").removeprefix("sha256:")
    return bool(
        evidence.get("verified") is True
        and str(evidence.get("verifier") or "").strip()
        and str(evidence.get("verification_method") or "").strip().upper()
        in _ACCEPTED_VERIFICATION_METHODS
        and all(
            str(source.get(field_name) or "").strip()
            for field_name in (
                "document_id",
                "location",
                "raw_snippet",
                "extraction_method",
            )
        )
        and len(content_hash) == 64
        and all(character in "0123456789abcdefABCDEF" for character in content_hash)
    )


def _likelihood_direction_is_coherent(
    applied_lr: float | None,
    supports: Any,
) -> bool:
    """Enforce finite policy range and a non-ambiguous directional label."""
    if (
        applied_lr is None
        or not math.isfinite(applied_lr)
        or applied_lr <= 0
        or applied_lr > 100
    ):
        return False
    if math.isclose(applied_lr, 1.0):
        return supports is None
    if applied_lr > 1.0:
        return supports is True
    return supports is False


def evaluate_hypothesis_disposition(
    hypothesis: Mapping[str, Any],
    evidence_by_id: Mapping[str, Mapping[str, Any]],
) -> tuple[bool, bool, bool]:
    """Return genuine support, contradiction, and typed rule-out-plan flags."""
    hypothesis_id = _stable_id(hypothesis.get("id"))
    if hypothesis_id is None:
        return False, False, False
    supporting_ids = set(_string_list(hypothesis.get("supporting_evidence_ids")))
    contradicting_ids = set(_string_list(hypothesis.get("contradicting_evidence_ids")))
    has_support = False
    has_contradiction = False
    for relationship in _mapping_list(hypothesis.get("likelihood_ratios")):
        evidence_id = _stable_id(relationship.get("evidence_id"))
        evidence_item: Mapping[str, Any] | None = evidence_by_id.get(evidence_id or "")
        if evidence_id is None or evidence_item is None:
            continue
        applied_lr = _safe_float(relationship.get("applied_likelihood_ratio"))
        supports = relationship.get("supports")
        if (
            _relationship_is_source_calibrated(relationship, evidence_by_id)
            and evidence_item.get("verified") is True
            and supports is True
            and applied_lr is not None
            and applied_lr > 1.0
            and evidence_id in supporting_ids
            and hypothesis_id
            in set(_string_list(evidence_item.get("supports_hypothesis_ids")))
        ):
            has_support = True
        if (
            _relationship_is_source_calibrated(relationship, evidence_by_id)
            and evidence_item.get("verified") is True
            and supports is False
            and applied_lr is not None
            and applied_lr < 1.0
            and evidence_id in contradicting_ids
            and hypothesis_id
            in set(_string_list(evidence_item.get("contradicts_hypothesis_ids")))
        ):
            has_contradiction = True

    for planned_test in _mapping_list(hypothesis.get("planned_tests")):
        disposition = _completed_diagnostic_test_disposition(
            planned_test,
            hypothesis_id,
            evidence_by_id,
        )
        if disposition == "SUPPORTS_HYPOTHESIS":
            has_support = True
        elif disposition == "REFUTES_HYPOTHESIS":
            has_contradiction = True

    has_disconfirming_plan = any(
        _valid_disconfirming_plan(item, hypothesis_id)
        for item in _mapping_list(hypothesis.get("planned_tests"))
    )
    return has_support, has_contradiction, has_disconfirming_plan


def evaluate_differential_breadth_audits(
    audits: Sequence[Mapping[str, Any]],
    hypotheses: Sequence[Mapping[str, Any]],
) -> tuple[list[str], dict[str, Any]]:
    """Validate systematic breadth artifacts and candidate/category linkage."""
    if not audits:
        return ["#/differential_breadth_audits"], {
            "frameworks": [],
            "primary_audit_ids": [],
            "hypotheses_covered": [],
        }

    failures: list[str] = []
    raw_audit_ids = [
        _stable_id(item.get("audit_id")) or "<missing-audit-id>" for item in audits
    ]
    failures.extend(
        f"{audit_id}:duplicate"
        for audit_id in set(raw_audit_ids)
        if raw_audit_ids.count(audit_id) > 1
    )
    parsed: list[DifferentialBreadthAudit] = []
    for index, payload in enumerate(audits):
        try:
            parsed.append(DifferentialBreadthAudit.model_validate(payload))
        except ValueError:
            failures.append(f"#/differential_breadth_audits/{index}:invalid")

    hypotheses_by_id = {
        hypothesis_id: hypothesis
        for hypothesis in hypotheses
        if (hypothesis_id := _stable_id(hypothesis.get("id"))) is not None
    }
    covered_hypothesis_ids: set[str] = set()
    unassessed_cells: list[str] = []
    for audit in parsed:
        if (
            audit.role is DifferentialBreadthAuditRole.PRIMARY
            and audit.framework is DifferentialBreadthFramework.CUSTOM
        ):
            failures.append(f"{audit.audit_id}:custom-primary-not-admitted")
        for cell in audit.cells:
            if cell.status is BreadthCellStatus.NOT_ASSESSED:
                unassessed_cells.append(f"{audit.audit_id}:{cell.cell_id}")
            if cell.status is not BreadthCellStatus.CANDIDATES_PRESENT:
                continue
            permitted_categories = {item.value for item in cell.mechanism_categories}
            for hypothesis_id in cell.hypothesis_ids:
                hypothesis = hypotheses_by_id.get(hypothesis_id)
                if hypothesis is None:
                    failures.append(f"{audit.audit_id}:{cell.cell_id}:{hypothesis_id}")
                    continue
                mechanism = str(hypothesis.get("mechanism_category") or "").upper()
                if mechanism not in permitted_categories:
                    failures.append(
                        f"{audit.audit_id}:{cell.cell_id}:{hypothesis_id}:mechanism-mismatch"
                    )
                    continue
                covered_hypothesis_ids.add(hypothesis_id)

    failures.extend(f"{item}:not-assessed" for item in unassessed_cells)
    report_hypothesis_ids = set(hypotheses_by_id)
    failures.extend(
        f"{hypothesis_id}:not-covered"
        for hypothesis_id in sorted(report_hypothesis_ids - covered_hypothesis_ids)
    )
    primary_audits = [
        audit
        for audit in parsed
        if audit.role is DifferentialBreadthAuditRole.PRIMARY
        and audit.framework is not DifferentialBreadthFramework.CUSTOM
        and audit.is_complete
    ]
    if not primary_audits:
        failures.append("#/differential_breadth_audits:no-complete-primary")

    details: dict[str, Any] = {
        "frameworks": [audit.framework.value for audit in parsed],
        "primary_audit_ids": [audit.audit_id for audit in primary_audits],
        "hypotheses_covered": sorted(report_hypothesis_ids & covered_hypothesis_ids),
        "unassessed_cells": sorted(unassessed_cells),
    }
    return sorted(set(failures)), details


def has_pending_discriminating_test(hypothesis: Mapping[str, Any]) -> bool:
    """Return whether one typed pending test can discriminate the hypothesis."""
    hypothesis_id = _stable_id(hypothesis.get("id"))
    if hypothesis_id is None:
        return False
    return any(
        _valid_pending_discriminating_plan(item, hypothesis_id)
        for item in _mapping_list(hypothesis.get("planned_tests"))
    )


def diagnostic_certainty_is_supported(
    hypothesis: Mapping[str, Any],
    evidence_by_id: Mapping[str, Mapping[str, Any]],
) -> bool:
    """Check qualitative certainty without deriving it from numeric probability."""
    hypothesis_id = _stable_id(hypothesis.get("id"))
    if hypothesis_id is None:
        return False
    certainty = str(hypothesis.get("certainty") or "").upper()
    status = str(hypothesis.get("status") or "").upper()
    has_support, _has_contradiction, _ = evaluate_hypothesis_disposition(
        hypothesis,
        evidence_by_id,
    )
    completed_supporting_test = any(
        _valid_completed_diagnostic_test(item, hypothesis_id, evidence_by_id)
        for item in _mapping_list(hypothesis.get("planned_tests"))
    )
    high_certainty_supported = (
        certainty not in _EVIDENCE_REQUIRED_CERTAINTIES
        or has_support
        or completed_supporting_test
    )
    confirmed_label = certainty == DiagnosticCertainty.CONFIRMED.value
    confirmed_coherent = (confirmed_label == (status == "CONFIRMED")) and (
        not confirmed_label or has_support or completed_supporting_test
    )
    excluded_coherent = (certainty == DiagnosticCertainty.EXCLUDED.value) == (
        status == "EXCLUDED"
    )
    return high_certainty_supported and confirmed_coherent and excluded_coherent


def _valid_disconfirming_plan(
    planned_test: Mapping[str, Any],
    hypothesis_id: str,
) -> bool:
    return _valid_pending_test(
        planned_test,
        hypothesis_id,
        permitted_purposes=_DISCONFIRMING_TEST_PURPOSES,
    )


def _valid_pending_discriminating_plan(
    planned_test: Mapping[str, Any],
    hypothesis_id: str,
) -> bool:
    """Return whether a pending typed test can discriminate this candidate."""
    return _valid_pending_test(
        planned_test,
        hypothesis_id,
        permitted_purposes=_DISCRIMINATING_TEST_PURPOSES,
    )


def _valid_pending_test(
    planned_test: Mapping[str, Any],
    hypothesis_id: str,
    *,
    permitted_purposes: set[str],
) -> bool:
    return (
        _stable_id(planned_test.get("target_hypothesis_id")) == hypothesis_id
        and str(planned_test.get("purpose") or "").upper() in permitted_purposes
        and str(planned_test.get("status") or "").upper() in _PENDING_TEST_STATUSES
        and all(
            str(planned_test.get(field_name) or "").strip()
            for field_name in (
                "test_id",
                "name",
                "expected_supporting_result",
                "expected_refuting_result",
            )
        )
    )


def _valid_completed_diagnostic_test(
    planned_test: Mapping[str, Any],
    hypothesis_id: str,
    evidence_by_id: Mapping[str, Mapping[str, Any]],
) -> bool:
    """Require a completed test with a typed disposition supporting the diagnosis."""
    return (
        _completed_diagnostic_test_disposition(
            planned_test,
            hypothesis_id,
            evidence_by_id,
        )
        == "SUPPORTS_HYPOTHESIS"
    )


def _completed_diagnostic_test_disposition(
    planned_test: Mapping[str, Any],
    hypothesis_id: str,
    evidence_by_id: Mapping[str, Mapping[str, Any]],
) -> str | None:
    """Return a completed test disposition only with verified result evidence."""
    result_evidence_id = _stable_id(planned_test.get("result_evidence_id"))
    result_evidence = evidence_by_id.get(result_evidence_id or "")
    disposition = str(planned_test.get("result_disposition") or "").upper()
    valid = (
        _stable_id(planned_test.get("target_hypothesis_id")) == hypothesis_id
        and str(planned_test.get("purpose") or "").upper() in _TYPED_TEST_PURPOSES
        and str(planned_test.get("status") or "").upper() == "COMPLETED"
        and disposition in {"SUPPORTS_HYPOTHESIS", "REFUTES_HYPOTHESIS"}
        and result_evidence_id is not None
        and result_evidence is not None
        and result_evidence.get("verified") is True
        and str(result_evidence.get("evidence_type") or "").upper() != "LITERATURE"
        and all(
            str(planned_test.get(field_name) or "").strip()
            for field_name in (
                "test_id",
                "name",
                "expected_supporting_result",
                "expected_refuting_result",
                "result_summary",
            )
        )
    )
    return disposition if valid else None


def normalize_diagnosis(hypothesis: Mapping[str, Any]) -> str:
    """Normalize a diagnosis display for deterministic uniqueness checks."""
    diagnosis = _mapping(hypothesis.get("diagnosis"))
    display = unicodedata.normalize("NFKC", str(diagnosis.get("display") or ""))
    tokens: list[str] = []
    current: list[str] = []
    for character in display.casefold():
        if character.isalnum():
            current.append(character)
        elif current:
            tokens.append("".join(current))
            current = []
    if current:
        tokens.append("".join(current))
    return " ".join(tokens)


def _stable_id(value: Any) -> str | None:
    if isinstance(value, Mapping):
        value = value.get("value")
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _record_ids(records: Sequence[Mapping[str, Any]]) -> set[str]:
    """Return nonblank stable IDs without leaking loop branches into the evaluator."""
    identifiers: set[str] = set()
    for record in records:
        identifier = _stable_id(record.get("id"))
        if identifier is not None:
            identifiers.add(identifier)
    return identifiers


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _mapping_list(value: Any) -> list[Mapping[str, Any]]:
    return [item for item in _sequence(value) if isinstance(item, Mapping)]


def _sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return value
    return ()


def _string_list(value: Any) -> list[str]:
    return [
        normalized
        for item in _sequence(value)
        if (normalized := _stable_id(item)) is not None
    ]


def _safe_int(value: Any, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _finite_float(value: Any) -> float | None:
    """Return a finite numeric value without accepting booleans."""
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
