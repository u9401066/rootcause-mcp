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
        "clinical_reasoning": "Acute hypotension requires explicit embolic evaluation.",
        "differential_diagnoses_considered": [],
        "uncertainty_factors": ["Definitive imaging pending"],
        "confidence_rationale": "Transparent fixture prior",
        "planned_tests": [_planned_test_input()],
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
    database.close()


@pytest.mark.asyncio
async def test_invalid_free_text_test_purpose_is_rejected() -> None:
    args = _hypothesis_args("invalid-plan-session")
    args["planned_tests"][0]["purpose"] = "please disconfirm this"

    result = await DDHandlers(ServerState()).handle_propose_hypothesis(args)

    assert result["status"] == "error"
    assert "purpose" in result["message"]


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
        auto_verify=False,
    )
    second = orchestrator.add_evidence(
        content="Escalation was delayed.",
        source_document="SRC-2",
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
