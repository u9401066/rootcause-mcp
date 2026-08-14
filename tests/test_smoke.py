"""
Smoke test for all 36 MCP tools.

Verifies that:
1. All tools can be loaded
2. All tools have valid schemas
3. Server can be created
4. Handlers can be instantiated
"""

import json

import pytest

from rootcause_mcp.interface.handlers import (
    ContractHandlers,
    DDHandlers,
    EvidenceHandlers,
    ReasoningHandlers,
    ThinkingHandlers,
)
from rootcause_mcp.interface.tools import get_all_tools


def test_all_tools_loadable() -> None:
    """Test that all 37 tools can be loaded."""
    tools = get_all_tools()
    assert len(tools) == 37, f"Expected 37 tools, got {len(tools)}"


def test_tool_profiles_reduce_advertised_schema_context() -> None:
    """Clinical and RCA agents should not need the complete schema catalog."""
    all_tools = get_all_tools("all")
    clinical_tools = get_all_tools("clinical")
    rca_tools = get_all_tools("rca")

    assert len(clinical_tools) == 17
    assert len(rca_tools) == 21
    assert {tool.name for tool in clinical_tools} & {tool.name for tool in rca_tools} == {
        "rc_verify_causation"
    }

    all_bytes = len(
        json.dumps(
            [tool.model_dump(mode="json") for tool in all_tools],
            ensure_ascii=False,
        ).encode()
    )
    clinical_bytes = len(
        json.dumps(
            [tool.model_dump(mode="json") for tool in clinical_tools],
            ensure_ascii=False,
        ).encode()
    )
    rca_bytes = len(
        json.dumps(
            [tool.model_dump(mode="json") for tool in rca_tools],
            ensure_ascii=False,
        ).encode()
    )
    assert clinical_bytes < all_bytes * 0.6
    assert rca_bytes < all_bytes * 0.6


def test_all_tools_have_valid_schemas() -> None:
    """Test that all tools have valid input schemas."""
    tools = get_all_tools()

    for tool in tools:
        # Check required fields
        assert tool.name, "Tool must have a name"
        assert tool.description, f"Tool {tool.name} must have a description"
        assert hasattr(tool, "input_schema"), f"Tool {tool.name} must have input_schema"
        assert tool.output_schema is not None
        assert tool.output_schema.get("required") == ["status"]

        # Check schema structure
        schema = tool.input_schema
        assert schema.get("type") == "object", (
            f"Tool {tool.name} schema must be object type"
        )
        assert "properties" in schema, f"Tool {tool.name} schema must have properties"


def test_tool_categories() -> None:
    """Test that all tool categories are present."""
    tools = get_all_tools()
    tool_names = [t.name for t in tools]

    # Cognitive Layer (5)
    assert "rc_think_aloud" in tool_names
    assert "rc_reflect" in tool_names
    assert "rc_identify_gaps" in tool_names
    assert "rc_challenge_assumption" in tool_names
    assert "rc_get_thinking_chain" in tool_names

    # Evidence (3)
    assert "rc_add_evidence" in tool_names
    assert "rc_get_evidence" in tool_names
    assert "rc_verify_evidence" in tool_names

    # Differential Diagnosis (4)
    assert "rc_propose_hypothesis" in tool_names
    assert "rc_link_evidence_to_hypothesis" in tool_names
    assert "rc_get_differential_diagnosis" in tool_names
    assert "rc_exclude_hypothesis" in tool_names

    # Reasoning Chain (3)
    assert "rc_get_reasoning_chain" in tool_names
    assert "rc_export_reasoning_chain" in tool_names
    assert "rc_audit_reasoning_state" in tool_names

    # CONTRACT (1)
    assert "rc_generate_contract_report" in tool_names


def test_handlers_instantiable() -> None:
    """Test that all new handlers can be instantiated."""
    from rootcause_mcp.application.server_state import ServerState

    # New handlers (no dependencies)
    state = ServerState()
    thinking = ThinkingHandlers(state)
    assert thinking is not None

    # Handlers with ServerState
    evidence = EvidenceHandlers(state)
    assert evidence is not None

    dd = DDHandlers(state)
    assert dd is not None

    reasoning = ReasoningHandlers(state)
    assert reasoning is not None

    contract = ContractHandlers(state)
    assert contract is not None


@pytest.mark.asyncio
async def test_thinking_handler_basic() -> None:
    """Test basic thinking handler functionality."""
    from rootcause_mcp.application.server_state import ServerState

    handler = ThinkingHandlers(ServerState())

    result = await handler.handle(
        "rc_think_aloud",
        {
            "session_id": "test_session",
            "thinking_type": "HYPOTHESIS_CONSIDERED",
            "content": "Test thinking",
            "internal_reasoning": "Test reasoning for smoke test",
            "confidence": 0.8,
        },
    )

    assert result["status"] == "success"
    assert "thinking_step_id" in result


@pytest.mark.asyncio
async def test_evidence_handler_basic() -> None:
    """Test basic evidence handler functionality."""
    from rootcause_mcp.application.server_state import ServerState

    handler = EvidenceHandlers(ServerState())

    result = await handler.handle(
        "rc_add_evidence",
        {
            "session_id": "test_session",
            "content": "Test evidence",
        },
    )

    assert result["status"] == "success"
    assert "evidence_id" in result


@pytest.mark.asyncio
async def test_dd_handler_basic() -> None:
    """Test basic DD handler functionality."""
    from rootcause_mcp.application.server_state import ServerState

    handler = DDHandlers(ServerState())

    result = await handler.handle(
        "rc_propose_hypothesis",
        {
            "session_id": "test_session",
            "diagnosis": "Test diagnosis",
            "clinical_reasoning": "Test reasoning for smoke test",
            "differential_diagnoses_considered": [],
            "evidence_supporting": [],
            "uncertainty_factors": [],
            "confidence_rationale": "Test rationale",
        },
    )

    assert result["status"] == "success"
    assert "hypothesis_id" in result


def test_server_v2_importable() -> None:
    """Test that server_v2 can be imported."""
    from rootcause_mcp.server_v2 import server

    assert server.name == "rootcause-mcp"
    assert server.version == "2.0.0a1"
