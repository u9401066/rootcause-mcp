"""Tests for bidirectional causality and teaching-case generation."""

from __future__ import annotations

import json

from rootcause_mcp.application.session_progress import SessionProgressTracker
from rootcause_mcp.domain.entities.session import RCASession
from rootcause_mcp.domain.value_objects.enums import CaseType
from rootcause_mcp.infrastructure.persistence.database import Database
from rootcause_mcp.infrastructure.persistence.session_repository import (
    SQLiteSessionRepository,
)
from rootcause_mcp.infrastructure.persistence.why_tree_repository import (
    InMemoryWhyTreeRepository,
)
from rootcause_mcp.interface.handlers.why_tree_handlers import WhyTreeHandlers


def _build_handlers() -> tuple[str, WhyTreeHandlers]:
    """Create a lightweight handler stack for testing."""
    database = Database(":memory:")
    database.create_tables()

    session_repo = SQLiteSessionRepository(database)
    why_repo = InMemoryWhyTreeRepository(database)
    progress_tracker = SessionProgressTracker()

    session = RCASession.create(
        case_type=CaseType.DEATH,
        case_title="Delayed sepsis escalation",
        initial_description="Ward team delayed recognition of shock progression",
    )
    session.set_problem("敗血症惡化未及時升級處置")
    session_repo.save(session)

    handlers = WhyTreeHandlers(
        why_tree_repository=why_repo,
        session_repository=session_repo,
        progress_tracker=progress_tracker,
    )
    return str(session.id), handlers


async def test_add_causal_link_detects_feedback_loop() -> None:
    """Adding a backward causal link should surface a feedback loop."""
    session_id, handlers = _build_handlers()

    first = await handlers.handle_ask_why(
        {
            "session_id": session_id,
            "initial_problem": "敗血症惡化未及時升級處置",
            "answer": "第一線團隊低估病人休克風險",
        }
    )
    first_node_id = first[0].text.split("**Node ID:** `", maxsplit=1)[1].split("`", maxsplit=1)[0]

    second = await handlers.handle_ask_why(
        {
            "session_id": session_id,
            "answer": "缺乏明確 escalation trigger 與交班提醒",
        }
    )
    second_node_id = second[0].text.split("**Node ID:** `", maxsplit=1)[1].split("`", maxsplit=1)[0]

    result = await handlers.handle_add_causal_link(
        {
            "session_id": session_id,
            "source_node_id": second_node_id,
            "target_node_id": first_node_id,
            "relationship": "feedback",
            "strength": 0.9,
            "note": "低估風險會延後 escalation，延後 escalation 又讓團隊更低估病況",
        }
    )

    assert "Feedback Loops Detected:** 1" in result[0].text

    tree = await handlers.handle_get_why_tree({"session_id": session_id})
    assert "## Feedback Loops" in tree[0].text
    assert "第一線團隊低估病人休克風險" in tree[0].text
    assert "缺乏明確 escalation trigger 與交班提醒" in tree[0].text


async def test_build_teaching_case_outputs_learning_artifacts() -> None:
    """RCA chain should be convertible into a teaching-ready lesson plan."""
    session_id, handlers = _build_handlers()

    first = await handlers.handle_ask_why(
        {
            "session_id": session_id,
            "initial_problem": "敗血症惡化未及時升級處置",
            "answer": "住院醫師未即時辨識 shock pattern",
        }
    )
    first_node_id = first[0].text.split("**Node ID:** `", maxsplit=1)[1].split("`", maxsplit=1)[0]

    second = await handlers.handle_ask_why(
        {
            "session_id": session_id,
            "answer": "晨會與值班交接沒有固定討論 red flags",
        }
    )
    second_node_id = second[0].text.split("**Node ID:** `", maxsplit=1)[1].split("`", maxsplit=1)[0]

    await handlers.handle_mark_root_cause(
        {
            "session_id": session_id,
            "node_id": second_node_id,
            "confidence": 0.85,
        }
    )
    await handlers.handle_add_causal_link(
        {
            "session_id": session_id,
            "source_node_id": second_node_id,
            "target_node_id": first_node_id,
            "relationship": "feedback",
            "strength": 0.8,
        }
    )

    markdown = await handlers.handle_build_teaching_case(
        {
            "session_id": session_id,
            "learner_level": "medical_student",
            "format": "markdown",
        }
    )
    assert "## Learning Objectives" in markdown[0].text
    assert "## Feedback Loops" in markdown[0].text
    assert "## Reverse-Causality Prompts" in markdown[0].text

    json_result = await handlers.handle_build_teaching_case(
        {
            "session_id": session_id,
            "learner_level": "resident",
            "format": "json",
        }
    )
    payload = json.loads(json_result[0].text)
    teaching_case = payload["teaching_case"]

    assert teaching_case["learner_level"] == "resident"
    assert teaching_case["feedback_loops"]
    assert any("倒推出" in prompt for prompt in teaching_case["reverse_causality_prompts"])
    assert teaching_case["learning_objectives"]
