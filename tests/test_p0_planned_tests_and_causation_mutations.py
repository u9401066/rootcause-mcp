"""P0 tests for typed test plans and fail-closed causation-audit mutations."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest

from rootcause_mcp.application.server_state import ServerState
from rootcause_mcp.domain.entities.session import RCASession
from rootcause_mcp.domain.entities.why_node import WhyChain, WhyNode
from rootcause_mcp.domain.services.causation_validator import (
    CausationValidator,
    CauseEvent,
    MechanismResult,
    NecessityResult,
    SufficiencyResult,
    TemporalityResult,
    VerificationLevel,
    VerificationTestResults,
)
from rootcause_mcp.domain.value_objects.differential_breadth import (
    CANONICAL_FRAMEWORK_CELLS,
    DifferentialBreadthAudit,
    DifferentialBreadthFramework,
)
from rootcause_mcp.domain.value_objects.enums import CaseType, Stage, VerificationResult
from rootcause_mcp.domain.value_objects.scores import ConfidenceScore
from rootcause_mcp.infrastructure.persistence.database import Database
from rootcause_mcp.infrastructure.persistence.hypothesis_repository import (
    SQLiteHypothesisRepository,
)
from rootcause_mcp.infrastructure.persistence.session_repository import (
    SQLiteSessionRepository,
)
from rootcause_mcp.infrastructure.persistence.why_tree_repository import (
    SQLiteWhyTreeRepository,
)
from rootcause_mcp.interface.handlers.dd_handlers import DDHandlers
from rootcause_mcp.interface.handlers.facade_handlers import FacadeHandlers
from rootcause_mcp.interface.handlers.verification_handlers import VerificationHandlers
from rootcause_mcp.interface.tools.condensed_tools import get_condensed_tools
from rootcause_mcp.interface.tools.dd_tools import get_dd_tools
from rootcause_mcp.interface.tools.verification_tools import get_verification_tools


def _planned_test_input() -> dict[str, str]:
    return {
        "name": "CT pulmonary angiography",
        "purpose": "RULE_OUT",
        "expected_supporting_result": "Pulmonary arterial filling defect",
        "expected_refuting_result": "Adequate study without filling defect",
        "status": "PLANNED",
    }


def _hypothesis_args(session_id: str) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "diagnosis": "Acute pulmonary embolism",
        "prior_probability": 0.2,
        "must_not_miss": True,
        "mechanism_category": "VASCULAR",
        "diagnostic_role": "ETIOLOGIC",
        "certainty": "POSSIBLE",
        "reasoning_basis": "MECHANISM_INFERENCE",
        "clinical_reasoning": "Acute hypotension requires explicit embolic evaluation.",
        "differential_diagnoses_considered": [],
        "uncertainty_factors": ["Definitive imaging pending"],
        "confidence_rationale": "Transparent fixture prior",
        "planned_tests": [_planned_test_input()],
    }


def _verified_calibration_evidence(orchestrator: Any, lr: float = 2.5) -> str:
    evidence = orchestrator.add_evidence(
        content=f"Published validation table reports direct LR {lr}.",
        evidence_type="LITERATURE",
        source_document="calibration-literature.txt",
        source_location="Table 2",
        raw_snippet=f"Index finding likelihood ratio {lr}",
        extraction_method="verbatim_quote",
        auto_verify=False,
    ).mark_verified(
        verifier="SYSTEM_PROVENANCE_VERIFIER",
        verification_method="EXACT_SNIPPET_MATCH",
        content_hash="sha256:" + "a" * 64,
    )
    orchestrator.evidence_store[evidence.id.value] = evidence
    return evidence.id.value


def _breadth_audit(hypothesis_id: str) -> dict[str, Any]:
    return {
        "audit_id": "DBA-transport",
        "framework": "CUSTOM",
        "framework_name": "Acute hypotension mechanism matrix",
        "framework_rationale": (
            "The acute hypotension syndrome requires explicit mechanism coverage."
        ),
        "role": "PRIMARY",
        "cells": [
            {
                "cell_id": "VASCULAR_CANDIDATES",
                "status": "CANDIDATES_PRESENT",
                "hypothesis_ids": [hypothesis_id],
                "mechanism_categories": ["VASCULAR"],
                "rationale": "The embolic candidate represents vascular mechanisms.",
                "unknowns": [],
                "planned_discriminators": [],
            },
            {
                "cell_id": "INFECTIOUS_REVIEW",
                "status": "REVIEWED_NO_PLAUSIBLE_CANDIDATE",
                "hypothesis_ids": [],
                "mechanism_categories": ["INFECTIOUS"],
                "rationale": "No infectious candidate is supported by supplied findings.",
                "unknowns": [],
                "planned_discriminators": [],
            },
            {
                "cell_id": "METABOLIC_REVIEW",
                "status": "REVIEWED_NO_PLAUSIBLE_CANDIDATE",
                "hypothesis_ids": [],
                "mechanism_categories": ["METABOLIC_ENDOCRINE"],
                "rationale": "No metabolic candidate is supported by supplied findings.",
                "unknowns": [],
                "planned_discriminators": [],
            },
        ],
        "stop_rationale": (
            "Both custom framework cells were reviewed before stopping expansion."
        ),
        "recorded_by": "test-agent",
    }


@pytest.mark.asyncio
async def test_discrete_and_condensed_propose_bind_typed_planned_test() -> None:
    discrete_state = ServerState()
    discrete = await DDHandlers(discrete_state).handle_propose_hypothesis(
        _hypothesis_args("discrete-session")
    )
    assert discrete["status"] == "success"
    assert (
        discrete["planned_tests"][0]["target_hypothesis_id"]
        == (discrete["hypothesis_id"])
    )
    assert discrete["planned_tests"][0]["purpose"] == "RULE_OUT"
    assert discrete["mechanism_category"] == "VASCULAR"
    assert discrete["diagnostic_role"] == "ETIOLOGIC"
    assert discrete["certainty"] == "POSSIBLE"
    assert discrete["reasoning_basis"] == "MECHANISM_INFERENCE"
    discrete_audit = await DDHandlers(discrete_state).handle_audit_differential_breadth(
        {
            "session_id": "discrete-session",
            "audit": _breadth_audit(discrete["hypothesis_id"]),
        }
    )
    assert discrete_audit["status"] == "success"
    assert discrete_audit["differential_breadth_audit"]["framework"] == "CUSTOM"

    condensed_state = ServerState()
    dd_handler = DDHandlers(condensed_state)
    any_handler: Any = dd_handler
    facade = FacadeHandlers(
        evidence_handlers=any_handler,
        dd_handlers=dd_handler,
        thinking_handlers=any_handler,
        reasoning_handlers=any_handler,
        contract_handlers=any_handler,
        verification_handlers=any_handler,
        session_handlers=any_handler,
        fishbone_handlers=any_handler,
        why_tree_handlers=any_handler,
        hfacs_handlers=any_handler,
    )
    condensed = await facade.handle_hypothesis(
        {"action": "propose", **_hypothesis_args("condensed-session")}
    )
    assert condensed["status"] == "success"
    assert (
        condensed["planned_tests"][0]["target_hypothesis_id"]
        == (condensed["hypothesis_id"])
    )
    assert condensed["mechanism_category"] == discrete["mechanism_category"]
    assert condensed["diagnostic_role"] == discrete["diagnostic_role"]
    assert condensed["certainty"] == discrete["certainty"]
    assert condensed["reasoning_basis"] == discrete["reasoning_basis"]
    condensed_audit = await facade.handle_hypothesis(
        {
            "action": "audit_breadth",
            "session_id": "condensed-session",
            "breadth_audit": _breadth_audit(condensed["hypothesis_id"]),
        }
    )
    assert condensed_audit["status"] == "success"
    assert (
        condensed_audit["differential_breadth_audit"]["audit_id"]
        == discrete_audit["differential_breadth_audit"]["audit_id"]
    )


def test_discrete_and_condensed_schemas_advertise_typed_test_plan() -> None:
    discrete = next(
        tool for tool in get_dd_tools() if tool.name == "rc_propose_hypothesis"
    )
    condensed = next(
        tool for tool in get_condensed_tools() if tool.name == "rc_hypothesis"
    )

    for tool in (discrete, condensed):
        test_schema = tool.input_schema["properties"]["planned_tests"]["items"]
        assert test_schema["additionalProperties"] is False
        assert test_schema["properties"]["purpose"]["enum"] == [
            "DISCONFIRM",
            "RULE_OUT",
            "CONFIRM",
            "DISCRIMINATE",
        ]
        assert test_schema["properties"]["status"]["enum"] == [
            "PLANNED",
            "ORDERED",
        ]
        assert {
            "name",
            "purpose",
            "expected_supporting_result",
            "expected_refuting_result",
            "status",
        } <= set(test_schema["required"])
        properties = tool.input_schema["properties"]
        assert "UNKNOWN" in properties["mechanism_category"]["enum"]
        assert properties["diagnostic_role"]["enum"] == [
            "ETIOLOGIC",
            "SYNDROMIC",
            "COMPLICATION",
            "MIMIC",
            "UNKNOWN",
        ]
        assert properties["certainty"]["enum"] == [
            "UNKNOWN",
            "POSSIBLE",
            "PROBABLE",
            "HIGH_CONFIDENCE",
            "CONFIRMED",
            "EXCLUDED",
        ]
        assert properties["reasoning_basis"]["enum"] == [
            "OBSERVED_DIAGNOSIS",
            "MECHANISM_INFERENCE",
            "UNKNOWN",
        ]
        alternatives_description = properties["differential_diagnoses_considered"][
            "description"
        ]
        assert "DEPRECATED context-only" in alternatives_description
        assert "every plausible" in alternatives_description

    assert "differential_diagnoses_considered" not in set(
        discrete.input_schema["required"]
    )
    assert "weight" not in condensed.input_schema["properties"]
    assert (
        "direct applied likelihood ratio"
        in condensed.input_schema["properties"]["likelihood_ratio"][
            "description"
        ].lower()
    )


def test_discrete_and_condensed_schemas_advertise_breadth_audit() -> None:
    discrete = next(
        tool for tool in get_dd_tools() if tool.name == "rc_audit_differential_breadth"
    )
    condensed = next(
        tool for tool in get_condensed_tools() if tool.name == "rc_hypothesis"
    )

    discrete_schema = discrete.input_schema["properties"]["audit"]
    condensed_schema = condensed.input_schema["properties"]["breadth_audit"]
    for schema in (discrete_schema, condensed_schema):
        assert schema["properties"]["cells"]["minItems"] == 3
        framework_ref = schema["properties"]["framework"]["$ref"].rsplit("/", 1)[-1]
        assert schema["$defs"][framework_ref]["enum"] == [
            "VINDICATE",
            "FIVE_H_FIVE_T",
            "ANATOMIC_SYSTEM",
            "MEDICATION_DEVICE_EXPOSURE",
            "CUSTOM",
        ]
        cell_schema = schema["$defs"]["DifferentialBreadthCell"]
        status_ref = cell_schema["properties"]["status"]["$ref"].rsplit("/", 1)[-1]
        assert schema["$defs"][status_ref]["enum"] == [
            "CANDIDATES_PRESENT",
            "REVIEWED_NO_PLAUSIBLE_CANDIDATE",
            "REVIEWED_INSUFFICIENT_DATA",
            "NOT_ASSESSED",
        ]


def test_discrete_and_condensed_link_schemas_require_lr_calibration() -> None:
    discrete = next(
        tool for tool in get_dd_tools() if tool.name == "rc_link_evidence_to_hypothesis"
    )
    condensed = next(
        tool for tool in get_condensed_tools() if tool.name == "rc_hypothesis"
    )

    assert "calibration_status" in discrete.input_schema["required"]
    assert discrete.input_schema["properties"]["calibration_status"]["enum"] == [
        "SOURCE_CALIBRATED",
        "QUANTITATIVELY_UNKNOWN",
    ]
    assert "weight" not in condensed.input_schema["properties"]
    assert condensed.input_schema["properties"]["calibration_status"]["enum"] == [
        "SOURCE_CALIBRATED",
        "QUANTITATIVELY_UNKNOWN",
    ]
    link_requirement = next(
        branch["then"]["required"]
        for branch in condensed.input_schema["allOf"]
        if branch["if"]["properties"].get("action") == {"const": "link"}
    )
    assert "calibration_status" in link_requirement


def test_builtin_breadth_framework_requires_every_canonical_cell() -> None:
    payload = _breadth_audit("HYP-placeholder")
    payload.update(
        {
            "framework": "FIVE_H_FIVE_T",
            "framework_name": None,
            "cells": payload["cells"],
        }
    )

    with pytest.raises(ValueError, match="requires exact canonical cells"):
        DifferentialBreadthAudit.model_validate(payload)

    assert (
        len(CANONICAL_FRAMEWORK_CELLS[DifferentialBreadthFramework.FIVE_H_FIVE_T]) == 10
    )


def test_reviewed_insufficient_data_requires_unknowns_and_planned_discriminator() -> (
    None
):
    payload = _breadth_audit("HYP-placeholder")
    insufficient = payload["cells"][1]
    insufficient["status"] = "REVIEWED_INSUFFICIENT_DATA"

    with pytest.raises(ValueError, match="unknowns and planned_discriminators"):
        DifferentialBreadthAudit.model_validate(payload)

    insufficient["unknowns"] = ["Original telemetry waveform is unavailable"]
    insufficient["planned_discriminators"] = [
        {
            "name": "Retrieve original telemetry waveform",
            "kind": "DATA_RETRIEVAL",
            "expected_supporting_result": "Rhythm morphology supports the mechanism",
            "expected_refuting_result": "Adequate tracing refutes the mechanism",
            "status": "PLANNED",
        }
    ]

    audit = DifferentialBreadthAudit.model_validate(payload)

    assert audit.is_complete is True


def test_reviewed_no_candidate_cannot_hide_unknowns_or_pending_work() -> None:
    payload = _breadth_audit("HYP-placeholder")
    reviewed_empty = payload["cells"][1]
    reviewed_empty["unknowns"] = ["Medication history remains unavailable"]
    reviewed_empty["planned_discriminators"] = [
        {
            "name": "Retrieve medication administration record",
            "kind": "DATA_RETRIEVAL",
            "expected_supporting_result": "A relevant exposure is documented",
            "expected_refuting_result": "No relevant exposure is documented",
            "status": "PLANNED",
        }
    ]

    with pytest.raises(
        ValueError,
        match="unknowns and planned_discriminators require REVIEWED_INSUFFICIENT_DATA",
    ):
        DifferentialBreadthAudit.model_validate(payload)


@pytest.mark.parametrize("framework", ["VINDICATE", "FIVE_H_FIVE_T"])
def test_builtin_framework_rejects_unrelated_mechanism_reused_for_every_cell(
    framework: str,
) -> None:
    framework_enum = DifferentialBreadthFramework(framework)
    payload = _breadth_audit("HYP-placeholder")
    payload.update(
        {
            "framework": framework,
            "framework_name": None,
            "cells": [
                {
                    "cell_id": cell_id,
                    "status": "CANDIDATES_PRESENT",
                    "hypothesis_ids": ["HYP-placeholder"],
                    "mechanism_categories": ["INFECTIOUS"],
                    "rationale": "The same mechanism is adversarially reused here.",
                    "unknowns": [],
                    "planned_discriminators": [],
                }
                for cell_id in sorted(CANONICAL_FRAMEWORK_CELLS[framework_enum])
            ],
        }
    )

    with pytest.raises(ValueError, match=r"canonical cell.*mechanism"):
        DifferentialBreadthAudit.model_validate(payload)


@pytest.mark.asyncio
async def test_planned_test_survives_hypothesis_repository_round_trip(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "planned-test.db")
    database.create_tables()
    repository = SQLiteHypothesisRepository(database)
    state = ServerState(hypothesis_repository=repository)
    result = await DDHandlers(state).handle_propose_hypothesis(
        _hypothesis_args("persistent-session")
    )
    assert result["status"] == "success"

    restored = await repository.get_by_id(
        "persistent-session",
        result["hypothesis_id"],
    )
    assert restored is not None
    assert restored.planned_tests[0].target_hypothesis_id == restored.id.value
    assert restored.planned_tests[0].purpose.value == "RULE_OUT"
    assert restored.planned_tests[0].status.value == "PLANNED"
    assert restored.mechanism_category.value == "VASCULAR"
    assert restored.diagnostic_role.value == "ETIOLOGIC"
    assert restored.certainty.value == "POSSIBLE"
    assert restored.reasoning_basis.value == "MECHANISM_INFERENCE"
    database.close()


@pytest.mark.asyncio
async def test_invalid_free_text_test_purpose_is_rejected() -> None:
    args = _hypothesis_args("invalid-plan-session")
    args["planned_tests"][0]["purpose"] = "please disconfirm this"

    result = await DDHandlers(ServerState()).handle_propose_hypothesis(args)

    assert result["status"] == "error"
    assert "purpose" in result["message"]


@pytest.mark.asyncio
async def test_invalid_hypothesis_classification_is_rejected() -> None:
    args = _hypothesis_args("invalid-classification-session")
    args["mechanism_category"] = "CARDIAC_BUT_UNTYPED"

    result = await DDHandlers(ServerState()).handle_propose_hypothesis(args)

    assert result["status"] == "error"
    assert "mechanism_category" in result["message"]


@pytest.mark.asyncio
async def test_omitted_prior_is_neutral_uncalibrated_baseline() -> None:
    args = _hypothesis_args("neutral-prior-session")
    args.pop("prior_probability")

    result = await DDHandlers(ServerState()).handle_propose_hypothesis(args)

    assert result["status"] == "success"
    assert result["prior_probability"] == 0.5


@pytest.mark.asyncio
async def test_non_neutral_lr_requires_explicit_rationale() -> None:
    state = ServerState()
    handler = DDHandlers(state)
    proposed = await handler.handle_propose_hypothesis(
        _hypothesis_args("lr-rationale-session")
    )
    orchestrator = await state.get_orchestrator("lr-rationale-session")
    assert orchestrator is not None
    evidence = orchestrator.add_evidence(
        content="Acute hypotension was observed",
        source_document="SRC-1",
        auto_verify=False,
    )

    rejected = await handler.handle_link_evidence(
        {
            "session_id": "lr-rationale-session",
            "hypothesis_id": proposed["hypothesis_id"],
            "evidence_id": evidence.id.value,
            "likelihood_ratio": 2.0,
            "supports": True,
            "calibration_status": "SOURCE_CALIBRATED",
            "calibration_source_ref": "PMID:12345678",
        }
    )

    assert rejected["status"] == "error"
    assert "non-neutral likelihood_ratio" in rejected["message"]


@pytest.mark.asyncio
async def test_agent_estimate_cannot_be_admitted_as_a_non_neutral_lr() -> None:
    state = ServerState()
    handler = DDHandlers(state)
    proposed = await handler.handle_propose_hypothesis(
        _hypothesis_args("lr-agent-estimate-session")
    )
    orchestrator = await state.get_orchestrator("lr-agent-estimate-session")
    assert orchestrator is not None
    evidence = orchestrator.add_evidence(
        content="A nonspecific observation was recorded",
        source_document="SRC-1",
        auto_verify=False,
    )

    rejected = await handler.handle_link_evidence(
        {
            "session_id": "lr-agent-estimate-session",
            "hypothesis_id": proposed["hypothesis_id"],
            "evidence_id": evidence.id.value,
            "likelihood_ratio": 99.0,
            "supports": True,
            "rationale": "Agent-estimated strength without a quantitative source.",
            "calibration_status": "QUANTITATIVELY_UNKNOWN",
        }
    )

    assert rejected["status"] == "error"
    assert "QUANTITATIVELY_UNKNOWN requires likelihood_ratio=1.0" in rejected["message"]
    unchanged = orchestrator.hypothesis_store[proposed["hypothesis_id"]]
    assert unchanged.bayesian_history == []


@pytest.mark.asyncio
async def test_source_calibrated_direct_lr_requires_local_verified_literature() -> None:
    state = ServerState()
    handler = DDHandlers(state)
    proposed = await handler.handle_propose_hypothesis(
        _hypothesis_args("lr-source-calibrated-session")
    )
    orchestrator = await state.get_orchestrator("lr-source-calibrated-session")
    assert orchestrator is not None
    evidence = orchestrator.add_evidence(
        content="A validated diagnostic finding was recorded",
        source_document="SRC-1",
        auto_verify=False,
    ).mark_verified(
        verifier="SYSTEM_PROVENANCE_VERIFIER",
        verification_method="EXACT_SNIPPET_MATCH",
    )
    orchestrator.evidence_store[evidence.id.value] = evidence
    calibration_evidence_id = _verified_calibration_evidence(orchestrator)

    accepted = await handler.handle_link_evidence(
        {
            "session_id": "lr-source-calibrated-session",
            "hypothesis_id": proposed["hypothesis_id"],
            "evidence_id": evidence.id.value,
            "likelihood_ratio": 2.5,
            "supports": True,
            "rationale": "Published diagnostic performance supports this direct LR.",
            "calibration_status": "SOURCE_CALIBRATED",
            "calibration_source_ref": calibration_evidence_id,
        }
    )

    assert accepted["status"] == "success"
    assert accepted["applied_likelihood_ratio"] == 2.5
    linked = orchestrator.hypothesis_store[proposed["hypothesis_id"]]
    assert linked.likelihood_ratios[0].calibration_status.value == "SOURCE_CALIBRATED"
    assert linked.likelihood_ratios[0].calibration_source_ref == calibration_evidence_id


@pytest.mark.asyncio
async def test_citation_looking_string_cannot_replace_calibration_evidence() -> None:
    state = ServerState()
    handler = DDHandlers(state)
    proposed = await handler.handle_propose_hypothesis(
        _hypothesis_args("lr-fake-citation-session")
    )
    orchestrator = await state.get_orchestrator("lr-fake-citation-session")
    assert orchestrator is not None
    evidence = orchestrator.add_evidence(
        content="A finding was observed",
        source_document="SRC-1",
        auto_verify=False,
    ).mark_verified(
        verifier="SYSTEM_PROVENANCE_VERIFIER",
        verification_method="EXACT_SNIPPET_MATCH",
    )
    orchestrator.evidence_store[evidence.id.value] = evidence

    rejected = await handler.handle_link_evidence(
        {
            "session_id": "lr-fake-citation-session",
            "hypothesis_id": proposed["hypothesis_id"],
            "evidence_id": evidence.id.value,
            "likelihood_ratio": 99.0,
            "supports": True,
            "rationale": "Caller supplied a citation-looking token.",
            "calibration_status": "SOURCE_CALIBRATED",
            "calibration_source_ref": "PMID:NOT-A-REAL-ID",
        }
    )

    assert rejected["status"] == "error"
    assert "EVD-*" in rejected["message"] or "evidence record" in rejected["message"]
    assert (
        orchestrator.hypothesis_store[proposed["hypothesis_id"]].bayesian_history == []
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("likelihood_ratio", "supports"),
    [(-5.0, False), (float("inf"), True), (2.0, False), (0.5, True), (1.0, True)],
)
async def test_invalid_or_directionally_incoherent_lr_is_rejected_without_mutation(
    likelihood_ratio: float,
    supports: bool,
) -> None:
    state = ServerState()
    handler = DDHandlers(state)
    session_id = f"lr-invalid-{likelihood_ratio!s}-{supports}"
    proposed = await handler.handle_propose_hypothesis(_hypothesis_args(session_id))
    orchestrator = await state.get_orchestrator(session_id)
    assert orchestrator is not None
    evidence = orchestrator.add_evidence(
        content="A finding was observed",
        source_document="SRC-1",
        auto_verify=False,
    ).mark_verified(
        verifier="SYSTEM_PROVENANCE_VERIFIER",
        verification_method="EXACT_SNIPPET_MATCH",
    )
    orchestrator.evidence_store[evidence.id.value] = evidence
    calibration_evidence_id = _verified_calibration_evidence(orchestrator, 2.0)

    rejected = await handler.handle_link_evidence(
        {
            "session_id": session_id,
            "hypothesis_id": proposed["hypothesis_id"],
            "evidence_id": evidence.id.value,
            "likelihood_ratio": likelihood_ratio,
            "supports": supports,
            "rationale": "Direction and finite range must be checked before mutation.",
            "calibration_status": "SOURCE_CALIBRATED",
            "calibration_source_ref": calibration_evidence_id,
        }
    )

    assert rejected["status"] == "error"
    assert (
        orchestrator.hypothesis_store[proposed["hypothesis_id"]].bayesian_history == []
    )


@pytest.mark.asyncio
async def test_missing_lr_calibration_status_returns_migration_error() -> None:
    state = ServerState()
    handler = DDHandlers(state)
    proposed = await handler.handle_propose_hypothesis(
        _hypothesis_args("lr-missing-calibration-session")
    )
    orchestrator = await state.get_orchestrator("lr-missing-calibration-session")
    assert orchestrator is not None
    evidence = orchestrator.add_evidence(
        content="A finding requiring qualitative linkage",
        source_document="SRC-1",
        auto_verify=False,
    )

    rejected = await handler.handle_link_evidence(
        {
            "session_id": "lr-missing-calibration-session",
            "hypothesis_id": proposed["hypothesis_id"],
            "evidence_id": evidence.id.value,
            "likelihood_ratio": 1.0,
        }
    )

    assert rejected["status"] == "error"
    assert "calibration_status is required" in rejected["message"]


@pytest.fixture
async def causation_runtime(
    tmp_path: Path,
) -> AsyncIterator[
    tuple[
        VerificationHandlers,
        SQLiteSessionRepository,
        Database,
        str,
        str,
        str,
        str,
    ]
]:
    database = Database(tmp_path / "causation-lineage.db")
    database.create_tables()
    session_repository = SQLiteSessionRepository(database)
    why_repository = SQLiteWhyTreeRepository(database)
    session = RCASession.create(
        case_type=CaseType.NEAR_MISS,
        case_title="Causation lineage boundary",
    )
    session_repository.save(session)
    session_id = str(session.id)

    state = ServerState()
    orchestrator = await state.get_or_create_orchestrator(session_id)
    first = orchestrator.add_evidence(
        content="The escalation trigger was absent.",
        source_document="SRC-1",
        temporal={"kind": "instant", "raw_value": "2026-08-17T09:00:00Z"},
        auto_verify=False,
    )
    second = orchestrator.add_evidence(
        content="Escalation was delayed.",
        source_document="SRC-2",
        temporal={"kind": "instant", "raw_value": "2026-08-17T09:05:00Z"},
        auto_verify=False,
    )
    node = WhyNode.create_first_why(
        session_id=session.id,
        initial_problem="Delayed escalation",
        answer="The escalation trigger was absent",
    )
    node.add_evidence(first.id.value)
    node.mark_as_root_cause()
    why_repository.save_chain(
        WhyChain(
            session_id=session.id,
            initial_problem="Delayed escalation",
            nodes=[node],
        )
    )
    handler = VerificationHandlers(
        server_state=state,
        session_repository=session_repository,
        why_tree_repository=why_repository,
    )
    yield (
        handler,
        session_repository,
        database,
        session_id,
        str(node.id),
        first.id.value,
        second.id.value,
    )
    database.close()


def _valid_causation_args(
    session_id: str,
    root_id: str,
    cause_evidence_id: str,
    effect_evidence_id: str,
) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "cause": {
            "id": root_id,
            "description": "The escalation trigger was absent",
            "timestamp": "2026-08-17T09:00:00+00:00",
            "evidence": [cause_evidence_id],
        },
        "effect": {
            "description": "Escalation was delayed",
            "timestamp": "2026-08-17T09:05:00+00:00",
            "evidence": [effect_evidence_id],
        },
        "verification_level": "comprehensive",
    }


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_id",
        "wrong_id",
        "wrong_description",
        "missing_cause_evidence",
        "wrong_cause_evidence",
        "unknown_cause_evidence",
        "missing_effect_evidence",
        "unknown_effect_evidence",
    ],
)
@pytest.mark.asyncio
async def test_invalid_causation_lineage_is_blocked_before_persistence(
    causation_runtime: tuple[
        VerificationHandlers,
        SQLiteSessionRepository,
        Database,
        str,
        str,
        str,
        str,
    ],
    mutation: str,
) -> None:
    handler, repository, _database, session_id, root_id, first_id, second_id = (
        causation_runtime
    )
    args = _valid_causation_args(session_id, root_id, first_id, second_id)
    if mutation == "missing_id":
        args["cause"].pop("id")
    elif mutation == "wrong_id":
        args["cause"]["id"] = "c_wrong"
    elif mutation == "wrong_description":
        args["cause"]["description"] = "Different description"
    elif mutation == "missing_cause_evidence":
        args["cause"]["evidence"] = []
    elif mutation == "wrong_cause_evidence":
        args["cause"]["evidence"] = [second_id]
    elif mutation == "unknown_cause_evidence":
        args["cause"]["evidence"] = ["EVD-unknown"]
    elif mutation == "missing_effect_evidence":
        args["effect"]["evidence"] = []
    elif mutation == "unknown_effect_evidence":
        args["effect"]["evidence"] = ["EVD-unknown"]

    response = await handler.handle_verify_causation(args)
    session = repository.get_by_id(session_id)

    assert response[0].text.startswith("Error:")
    assert session is not None
    assert session.get_stage_data(Stage.VERIFY).get("causation_verifications", []) == []


@pytest.mark.asyncio
async def test_valid_causation_audit_persists_non_proof_scope(
    causation_runtime: tuple[
        VerificationHandlers,
        SQLiteSessionRepository,
        Database,
        str,
        str,
        str,
        str,
    ],
) -> None:
    handler, repository, _database, session_id, root_id, first_id, second_id = (
        causation_runtime
    )

    response = await handler.handle_verify_causation(
        _valid_causation_args(session_id, root_id, first_id, second_id)
    )
    session = repository.get_by_id(session_id)

    assert "Conservative Causation Audit" in response[0].text
    assert "does not establish clinical causality" in response[0].text
    assert session is not None
    audit = session.get_stage_data(Stage.VERIFY)["causation_verifications"][0]
    assert audit["audit_scope"] == "CONSERVATIVE_CAUSATION_AUDIT"
    assert audit["clinical_causality_established"] is False
    assert audit["cause_event"]["id"] == root_id


def test_all_submitted_audit_obligations_pass_without_causal_strength() -> None:
    validator = CausationValidator()
    cause = CauseEvent(description="Submitted cause")
    effect = CauseEvent(description="Submitted effect")
    tests = VerificationTestResults(
        temporality=TemporalityResult(passed=True),
        necessity=NecessityResult(
            passed=True,
            counterfactual_question="Counterfactual?",
            counterfactual_answer="unlikely",
            confidence=ConfidenceScore(0.8),
            reasoning="Submitted assessment",
        ),
        mechanism=MechanismResult(
            passed=True,
            causal_pathway=["cause", "effect"],
            mechanism_plausibility="high",
            domain_knowledge_support=True,
        ),
        sufficiency=SufficiencyResult(
            passed=True,
            analysis="Submitted sufficiency assessment",
            confounders_identified=[],
            conclusion="Submitted assessment passed",
        ),
    )

    result = validator._build_result(
        "ver_all_pass",
        VerificationLevel.COMPREHENSIVE,
        cause,
        effect,
        tests,
    )

    assert result.overall_result is VerificationResult.VERIFIED
    assert result.causal_strength is None
    assert "不是臨床因果關係的證明" in result.interpretation


def test_causation_tool_descriptions_state_non_proof_boundary() -> None:
    discrete = next(
        tool for tool in get_verification_tools() if tool.name == "rc_verify_causation"
    )
    condensed = next(tool for tool in get_condensed_tools() if tool.name == "rc_audit")

    assert "does not establish clinical causality" in discrete.description
    assert "does not establish clinical causality" in condensed.description
    assert set(discrete.input_schema["properties"]["cause"]["required"]) == {
        "id",
        "description",
        "evidence",
    }
    for event_name in ("cause", "effect"):
        evidence_schema = discrete.input_schema["properties"][event_name]["properties"][
            "evidence"
        ]
        assert evidence_schema["minItems"] == 1
        assert evidence_schema["uniqueItems"] is True
