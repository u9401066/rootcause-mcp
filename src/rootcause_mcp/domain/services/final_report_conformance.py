"""Pure deterministic conformance checks for final clinical/RCA reports.

The evaluator consumes only a report-shaped mapping.  It is intentionally
independent from ``ContractReport`` so both the interface handler and the
domain finalization boundary can recompute the same hard checks instead of
trusting caller-supplied PASS records.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Collection, Mapping, Sequence
from typing import Any

HARD_CONFORMANCE_CODES = frozenset(
    {
        "GUIDANCE_READY",
        "NO_UNRESOLVED_SAFETY_CONFLICTS",
        "MULTI_SOURCE_MANIFEST",
        "MANIFEST_DOCUMENTS_REVIEWED",
        "EVIDENCE_SOURCES_DECLARED",
        "FINAL_REPORT_SECTIONS_INCLUDED",
        "FISHBONE_PRESENT",
        "WHY_ROOT_PRESENT",
        "ROOT_EVIDENCE_LINEAGE",
        "ROOT_CAUSATION_AUDIT_LINEAGE",
        "ROOT_CAUSE_DISPOSITION_SAFE",
        "DIFFERENTIAL_MINIMUM_UNIQUE",
        "ACTIVE_DIFFERENTIAL_DISPOSITION",
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


def evaluate_final_report_conformance(  # noqa: PLR0915
    report: Mapping[str, Any],
    *,
    approved_by: str | None = None,
    authorized_reviewers: Collection[str] | None = None,
) -> list[dict[str, Any]]:
    """Recompute all hard, content-dependent final-report checks.

    ``authorized_reviewers=None`` is useful at the portable domain boundary and
    still requires a named reviewer.  The public handler supplies the operator
    allowlist, making authorization fail closed for MCP finalization.
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
    inventory_document_ids = {
        str(item.get("document"))
        for item in source_inventory
        if item.get("document") not in {None, ""}
        and str(item.get("coverage_status") or "")
        not in {"not_in_manifest", "registered_evidence_only"}
    }
    checks: list[dict[str, Any]] = []

    readiness = _mapping(report.get("report_readiness"))
    guidance_ready = readiness.get("is_ready_for_report") is True
    checks.append(
        _check(
            "GUIDANCE_READY",
            guidance_ready,
            "Clinical workflow readiness is satisfied.",
            "Clinical workflow readiness is absent or false.",
            ["#/report_readiness"],
        )
    )

    gap_analysis = _mapping(report.get("gap_analysis"))
    critical_count = _safe_int(gap_analysis.get("critical_count"), default=-1)
    high_count = _safe_int(gap_analysis.get("high_count"), default=-1)
    conflicts_clear = (
        critical_count == 0
        and high_count == 0
        and gap_analysis.get("safety_invariants_met") is True
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

    rca_session = _mapping(report.get("rca_session"))
    source_count = _safe_int(rca_session.get("source_document_count"), default=0)
    multi_source = source_count >= 2 and len(inventory_document_ids) >= 2
    checks.append(
        _check(
            "MULTI_SOURCE_MANIFEST",
            multi_source,
            "At least two manifest sources are represented in the report.",
            "A pinned multi-source manifest with at least two sources is required.",
            ["#/rca_session/source_document_count", "#/source_inventory"],
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

    active_failures: list[str] = []
    evidence_dispositions: dict[str, tuple[bool, bool, bool]] = {}
    for hypothesis in hypotheses:
        hypothesis_id = _stable_id(hypothesis.get("id")) or "<missing-hypothesis-id>"
        disposition = evaluate_hypothesis_disposition(hypothesis, evidence_by_id)
        evidence_dispositions[hypothesis_id] = disposition
        if str(hypothesis.get("status") or "").upper() != "ACTIVE":
            continue
        has_support, has_contradiction, has_disconfirming_plan = disposition
        if not (has_support or has_contradiction) or not (
            has_contradiction or has_disconfirming_plan
        ):
            active_failures.append(hypothesis_id)
    checks.append(
        _check(
            "ACTIVE_DIFFERENTIAL_DISPOSITION",
            not active_failures,
            "Every active diagnosis has genuine evidence and a refuting disposition.",
            "Every active diagnosis needs a genuine evidence link plus contradiction or typed pending rule-out test.",
            active_failures or ["#/hypotheses"],
        )
    )

    eligible = [
        item
        for item in hypotheses
        if str(item.get("status") or "").upper()
        not in {"EXCLUDED", "ON_HOLD", "RULED_OUT"}
    ]
    leading = max(eligible, key=_probability, default=None)
    leading_id = _stable_id(leading.get("id")) if leading is not None else None
    leading_disposition = evidence_dispositions.get(
        leading_id or "",
        (False, False, False),
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
            "The leading diagnosis has genuine support and contradiction or a typed rule-out plan.",
            "The leading diagnosis lacks genuine support or a refuting evidence/test disposition.",
            [leading_id] if leading_id else ["#/hypotheses"],
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
    reviewer_ok = bool(reviewer) and (
        authorized_reviewers is None or reviewer.casefold() in authorized
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


def _check(
    code: str,
    passed: bool,
    pass_message: str,
    fail_message: str,
    refs: Sequence[str],
) -> dict[str, Any]:
    return {
        "code": code,
        "status": "PASS" if passed else "FAIL",
        "severity": "HARD",
        "message": pass_message if passed else fail_message,
        "refs": sorted({str(ref) for ref in refs if ref}),
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
    if not root_by_id:
        failures.append("#/root_causes")
    latest_result_by_root: dict[str, str] = {}
    for audit in audits:
        audit_root_id = _stable_id(_mapping(audit.get("cause_event")).get("id"))
        if audit_root_id:
            latest_result_by_root[audit_root_id] = str(
                audit.get("overall_result") or ""
            ).upper()
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
        ):
            failures.append(root_id)
    return sorted(set(failures))


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
            supports is True
            and applied_lr is not None
            and applied_lr > 1.0
            and evidence_id in supporting_ids
            and hypothesis_id
            in set(_string_list(evidence_item.get("supports_hypothesis_ids")))
        ):
            has_support = True
        if (
            supports is False
            and applied_lr is not None
            and applied_lr < 1.0
            and evidence_id in contradicting_ids
            and hypothesis_id
            in set(_string_list(evidence_item.get("contradicts_hypothesis_ids")))
        ):
            has_contradiction = True

    has_disconfirming_plan = any(
        _valid_disconfirming_plan(item, hypothesis_id)
        for item in _mapping_list(hypothesis.get("planned_tests"))
    )
    return has_support, has_contradiction, has_disconfirming_plan


def _valid_disconfirming_plan(
    planned_test: Mapping[str, Any],
    hypothesis_id: str,
) -> bool:
    return (
        _stable_id(planned_test.get("target_hypothesis_id")) == hypothesis_id
        and str(planned_test.get("purpose") or "").upper()
        in _DISCONFIRMING_TEST_PURPOSES
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


def _probability(hypothesis: Mapping[str, Any]) -> float:
    value = _safe_float(hypothesis.get("current_probability"))
    return value if value is not None else 0.0


def _stable_id(value: Any) -> str | None:
    if isinstance(value, Mapping):
        value = value.get("value")
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


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


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
