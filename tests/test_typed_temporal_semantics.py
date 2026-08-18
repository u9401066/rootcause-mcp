"""P0 regression coverage for source-faithful clinical temporal semantics."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from rootcause_mcp.application.clinical_reasoning_orchestrator import (
    ClinicalReasoningOrchestrator,
)
from rootcause_mcp.application.server_state import ServerState
from rootcause_mcp.domain.entities.evidence import Evidence
from rootcause_mcp.domain.services.final_report_conformance import (
    evaluate_final_report_conformance,
    hard_failures,
)
from rootcause_mcp.domain.value_objects.clinical_temporal import (
    ClinicalTemporal,
    ClinicalTemporalKind,
)
from rootcause_mcp.domain.value_objects.contract_report import ContractReport
from rootcause_mcp.infrastructure.persistence.database import Database
from rootcause_mcp.infrastructure.persistence.evidence_repository import (
    SQLiteEvidenceRepository,
)
from rootcause_mcp.interface.handlers.evidence_handlers import EvidenceHandlers
from rootcause_mcp.interface.mermaid import build_timeline
from test_p0_final_report_conformance import _valid_report

_NON_INSTANT_CASES = [
    (
        {
            "kind": "date",
            "raw_value": "2026-08-17",
        },
        {
            "kind": "date",
            "raw_value": "2026-08-17",
            "precision": "day",
            "normalized_start": "2026-08-17",
            "normalized_end": "2026-08-17",
            "timezone_provenance": "not_applicable",
        },
    ),
    (
        {
            "kind": "range",
            "raw_value": "2026-08-17/2026-08-18",
            "normalized_start": "2026-08-17",
            "normalized_end": "2026-08-18",
        },
        {
            "kind": "range",
            "raw_value": "2026-08-17/2026-08-18",
            "precision": "day",
            "normalized_start": "2026-08-17",
            "normalized_end": "2026-08-18",
            "timezone_provenance": "not_applicable",
        },
    ),
    (
        {
            "kind": "relative",
            "raw_value": "post-op day 1",
        },
        {
            "kind": "relative",
            "raw_value": "post-op day 1",
            "precision": "relative",
            "normalized_start": None,
            "normalized_end": None,
            "timezone_provenance": "not_applicable",
        },
    ),
    (
        {
            "kind": "unknown",
            "raw_value": None,
        },
        {
            "kind": "unknown",
            "raw_value": None,
            "precision": "unknown",
            "normalized_start": None,
            "normalized_end": None,
            "timezone_provenance": "unknown",
        },
    ),
]


@pytest.mark.parametrize(("supplied", "expected"), _NON_INSTANT_CASES)
def test_non_instant_temporal_records_preserve_semantics_without_timestamp(
    supplied: dict[str, Any],
    expected: dict[str, Any],
) -> None:
    evidence = _minimal_evidence(temporal=supplied)

    assert evidence.temporal.model_dump(mode="json") == expected
    assert evidence.event_timestamp is None
    assert evidence.temporal.aware_instant is None
    assert evidence.temporal.is_chronologically_sortable is False


def test_legacy_aware_timestamp_maps_to_instant_but_weak_timestamp_is_rejected() -> (
    None
):
    source_value = "2026-08-17T08:15:00+08:00"
    evidence = _minimal_evidence(event_timestamp=source_value)

    assert evidence.temporal.kind is ClinicalTemporalKind.INSTANT
    assert evidence.temporal.raw_value == source_value
    assert evidence.temporal.normalized_start == "2026-08-17T00:15:00+00:00"
    assert evidence.event_timestamp == datetime.fromisoformat(source_value)

    for unsafe in ("2026-08-17", "2026-08-17T08:15:00"):
        with pytest.raises(ValidationError, match="explicit timezone offset"):
            _minimal_evidence(event_timestamp=unsafe)


@pytest.mark.parametrize(("supplied", "expected"), _NON_INSTANT_CASES)
@pytest.mark.asyncio
async def test_mcp_add_accepts_typed_non_instant_time_and_returns_canonical_record(
    supplied: dict[str, Any],
    expected: dict[str, Any],
) -> None:
    response = await EvidenceHandlers(ServerState()).handle_add_evidence(
        {
            "session_id": "typed-time",
            "content": "Source-linked finding with partial time",
            "temporal": supplied,
            "auto_verify": False,
        }
    )

    assert response["status"] == "success"
    assert response["temporal"] == expected
    assert response["event_timestamp"] is None


@pytest.mark.asyncio
async def test_sqlite_round_trip_retains_typed_time_without_schema_migration(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "typed-time.db")
    database.create_tables()
    repository = SQLiteEvidenceRepository(database)
    evidence = _minimal_evidence(
        temporal={
            "kind": "range",
            "raw_value": "overnight window",
            "normalized_start": "2026-08-17T22:00:00+08:00",
            "normalized_end": "2026-08-18T06:00:00+08:00",
            "precision": "minute",
        }
    )

    await repository.save("temporal-session", evidence)
    restored = await repository.get_by_id("temporal-session", evidence.id.value)

    assert restored is not None
    assert restored.temporal == evidence.temporal
    assert restored.event_timestamp is None
    database.close()


def test_timeline_sorts_only_aware_instants_and_never_fabricates_t_event() -> None:
    orchestrator = ClinicalReasoningOrchestrator("mixed-temporal")
    orchestrator.add_evidence(
        "Later absolute event",
        temporal={"kind": "instant", "raw_value": "2026-08-18T09:30:00Z"},
    )
    orchestrator.add_evidence(
        "Date-only event",
        temporal={"kind": "date", "raw_value": "2026-08-17"},
    )
    orchestrator.add_evidence(
        "Earlier absolute event",
        temporal={"kind": "instant", "raw_value": "2026-08-18T09:00:00Z"},
    )
    orchestrator.add_evidence(
        "Relative event",
        temporal={"kind": "relative", "raw_value": "post-op day 1"},
    )
    orchestrator.add_evidence(
        "Unknown-time event",
        temporal={"kind": "unknown", "raw_value": None},
    )

    timeline = build_timeline(orchestrator.evidence_store.values())

    assert [event["content"] for event in timeline["events"]] == [
        "Earlier absolute event",
        "Later absolute event",
        "Date-only event",
        "Relative event",
        "Unknown-time event",
    ]
    assert timeline["timed_event_count"] == 2
    assert timeline["untimed_event_count"] == 3
    assert [event["chronology_status"] for event in timeline["events"]] == [
        "ORDERED_INSTANT",
        "ORDERED_INSTANT",
        "UNPOSITIONED",
        "UNPOSITIONED",
        "UNPOSITIONED",
    ]
    assert "T_Event" not in str(timeline)
    assert "UNPOSITIONED" in timeline["table"]


@pytest.mark.parametrize(
    "temporal_payload",
    [expected for _supplied, expected in _NON_INSTANT_CASES],
    ids=["date", "range", "relative", "unknown"],
)
def test_non_instant_evidence_can_finalize_without_claiming_chronology(
    temporal_payload: dict[str, Any],
) -> None:
    report = _guidance_ready_report()
    report["evidence"][0]["temporal"] = temporal_payload
    report["evidence"][0]["event_timestamp"] = None
    report["timeline"]["events"][0]["temporal"] = temporal_payload
    report["timeline"]["events"][0]["chronology_status"] = "UNPOSITIONED"
    report["timeline"]["events"][0]["time"] = (
        temporal_payload["raw_value"] or "Unknown time"
    )

    checks = evaluate_final_report_conformance(
        report,
        approved_by="reviewer",
        authorized_reviewers={"reviewer"},
    )

    assert hard_failures(checks) == []
    finalized = ContractReport.model_validate(report)
    finalized.finalize("reviewer", authorized_reviewers={"reviewer"})
    assert finalized.is_finalized is True


def test_date_evidence_cannot_back_a_passed_causation_temporality_claim() -> None:
    report = _guidance_ready_report()
    date_temporal = _NON_INSTANT_CASES[0][1]
    report["evidence"][0]["temporal"] = date_temporal
    report["evidence"][0]["event_timestamp"] = None
    report["timeline"]["events"][0].update(
        temporal=date_temporal,
        chronology_status="UNPOSITIONED",
        time="2026-08-17",
    )
    audit = report["causation_verifications"][0]
    audit["cause_event"]["timestamp"] = "2026-08-18T09:00:00Z"
    audit["effect_event"]["timestamp"] = "2026-08-18T09:10:00Z"
    audit["tests"]["temporality"] = {
        "passed": True,
        "cause_time": "2026-08-18T09:00:00Z",
        "effect_time": "2026-08-18T09:10:00Z",
        "time_diff_minutes": 10,
        "conclusion": "Caller asserted chronology",
    }

    checks = evaluate_final_report_conformance(
        report,
        approved_by="reviewer",
        authorized_reviewers={"reviewer"},
    )
    temporal_check = next(
        item for item in checks if item["code"] == "CAUSATION_TEMPORAL_LINEAGE"
    )

    assert temporal_check["status"] == "FAIL"
    assert temporal_check["severity"] == "HARD"


def test_unlinked_timestamp_cannot_drive_a_negative_causation_disposition() -> None:
    report = _guidance_ready_report()
    audit = report["causation_verifications"][0]
    audit["cause_event"]["timestamp"] = "2026-08-18T12:00:00Z"

    checks = evaluate_final_report_conformance(
        report,
        approved_by="reviewer",
        authorized_reviewers={"reviewer"},
    )
    temporal_check = next(
        item for item in checks if item["code"] == "CAUSATION_TEMPORAL_LINEAGE"
    )

    assert temporal_check["status"] == "FAIL"
    assert temporal_check["severity"] == "HARD"


def _guidance_ready_report() -> dict[str, Any]:
    """Keep this temporal probe valid under independently recomputed readiness."""
    report = deepcopy(_valid_report())
    report["report_readiness"] = {
        "session_id": "rc_sess_test",
        "current_stage": "READY_FOR_SYNTHESIS",
        "stage_display": "Ready for synthesis",
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
            "must_not_miss_hypotheses_count": 1,
            "unlinked_evidence_count": 0,
            "leading_hypothesis_id": "HYP-1",
            "explicit_leading_hypothesis_selected": True,
            "leading_selection_eligible": True,
            "uncertainty_acknowledged": True,
            "bias_reviewed": True,
            "reasoning_steps_recorded": 1,
            "differential_breadth_audit_complete": True,
            "must_not_miss_reviewed": True,
            "disconfirming_evidence_tested": True,
            "active_differential_disposition_complete": True,
            "diagnostic_certainty_supported": True,
            "leading_diagnosis_challenged": True,
            "must_not_miss_disposition_complete": True,
        },
        "missing_prerequisites": [],
        "next_recommended_actions": ["Proceed to qualified-human review."],
        "push_questions": ["Does the reviewer accept remaining uncertainty?"],
        "is_ready_for_report": True,
    }
    return report


def _minimal_evidence(
    *,
    temporal: dict[str, Any] | ClinicalTemporal | None = None,
    event_timestamp: datetime | str | None = None,
) -> Evidence:
    return Evidence.model_validate(
        {
            "content": "Atomic source observation",
            "evidence_type": "OBSERVATION",
            "quality": {"strength": "MODERATE", "reliability": "GRADE_B"},
            "source": {"document_id": "SRC-1", "collected_by": "test"},
            "temporal": temporal,
            "event_timestamp": event_timestamp,
        }
    )
