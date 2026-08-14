"""Integration tests for the MCP SDK 2.0 server entry point."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from rootcause_mcp import server_v2
from rootcause_mcp.server_v2 import lifespan, on_list_tools, server

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.asyncio
async def test_sdk2_lifespan_exposes_complete_tool_catalog(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """The production entry point starts and exposes every registered tool."""
    monkeypatch.setenv("ROOTCAUSE_DATA_DIR", str(tmp_path))

    async with lifespan(server):
        context: Any = None
        result = await on_list_tools(context, None)
        dispatch = server_v2._build_tool_dispatch()

    tool_names = {tool.name for tool in result.tools}
    assert len(tool_names) == 37
    assert set(dispatch) == tool_names
    assert {
        "rc_add_evidence",
        "rc_propose_hypothesis",
        "rc_think_aloud",
        "rc_audit_reasoning_state",
        "rc_generate_contract_report",
        "rc_verify_causation",
    } <= tool_names
    assert (tmp_path / "rca_sessions.db").exists()


@pytest.mark.asyncio
async def test_sdk2_clinical_profile_matches_dispatch_surface(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A profile must reduce both advertised and executable tools."""
    monkeypatch.setenv("ROOTCAUSE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ROOTCAUSE_TOOL_PROFILE", "clinical")

    async with lifespan(server):
        context: Any = None
        result = await on_list_tools(context, None)
        monkeypatch.setenv("ROOTCAUSE_TOOL_PROFILE", "all")
        dispatch = server_v2._build_tool_dispatch()
        frozen_result = await on_list_tools(context, None)

    tool_names = {tool.name for tool in result.tools}
    assert len(tool_names) == 17
    assert set(dispatch) == tool_names
    assert {tool.name for tool in frozen_result.tools} == tool_names
    assert "rc_add_evidence" in tool_names
    assert "rc_export_fishbone" not in tool_names


def test_sdk2_server_metadata() -> None:
    """The package advertises the SDK 2.0 server and alpha release version."""
    assert server.name == "rootcause-mcp"
    assert server.version == "2.0.0a1"
