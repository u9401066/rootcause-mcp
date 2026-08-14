"""
Root Cause Analysis MCP Server (SDK 2.0).

MCP Server entry point for medical reasoning and differential diagnosis.
Uses SDK 2.0 callback-based API.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Any

from mcp.server import Server, ServerRequestContext
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequestParams,
    CallToolResult,
    ListToolsResult,
    TextContent,
)

# Application layer
from rootcause_mcp.application.server_state import ServerState
from rootcause_mcp.application.session_progress import SessionProgressTracker

# Domain and Infrastructure
from rootcause_mcp.domain.services import HFACSSuggester, LearnedRulesService
from rootcause_mcp.infrastructure.persistence.database import Database
from rootcause_mcp.infrastructure.persistence.evidence_repository import (
    SQLiteEvidenceRepository,
)
from rootcause_mcp.infrastructure.persistence.fishbone_repository import (
    SQLiteFishboneRepository,
)
from rootcause_mcp.infrastructure.persistence.hypothesis_repository import (
    SQLiteHypothesisRepository,
)
from rootcause_mcp.infrastructure.persistence.reasoning_chain_repository import (
    SQLiteReasoningChainRepository,
)
from rootcause_mcp.infrastructure.persistence.session_repository import (
    SQLiteSessionRepository,
)
from rootcause_mcp.infrastructure.persistence.thinking_chain_repository import (
    SQLiteThinkingChainRepository,
)
from rootcause_mcp.infrastructure.persistence.why_tree_repository import (
    InMemoryWhyTreeRepository,
)

# Handlers
from rootcause_mcp.interface.handlers import (
    ContractHandlers,
    DDHandlers,
    EvidenceHandlers,
    FishboneHandlers,
    HFACSHandlers,
    ReasoningHandlers,
    SessionHandlers,
    ThinkingHandlers,
    VerificationHandlers,
    WhyTreeHandlers,
)

# Tool definitions
from rootcause_mcp.interface.tools import get_all_tools

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ServerRuntime:
    """Mutable resources owned by one MCP server lifespan."""

    tool_profile: str | None = None
    response_mode: str | None = None
    server_state: ServerState | None = None
    thinking_handlers: ThinkingHandlers | None = None
    evidence_handlers: EvidenceHandlers | None = None
    dd_handlers: DDHandlers | None = None
    reasoning_handlers: ReasoningHandlers | None = None
    contract_handlers: ContractHandlers | None = None
    hfacs_handlers: HFACSHandlers | None = None
    session_handlers: SessionHandlers | None = None
    fishbone_handlers: FishboneHandlers | None = None
    why_tree_handlers: WhyTreeHandlers | None = None
    verification_handlers: VerificationHandlers | None = None
    database: Database | None = None

    def clear(self) -> None:
        """Release references after lifespan shutdown."""
        for field_name in self.__dataclass_fields__:
            setattr(self, field_name, None)


_runtime = ServerRuntime()


def _get_config_path() -> Path:
    """Get the configuration directory path."""
    env_config = os.environ.get("ROOTCAUSE_CONFIG_DIR")
    if env_config:
        return Path(env_config)

    # Navigate from src/rootcause_mcp/server_v2.py to project root
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent
    return project_root / "config"


def _get_data_path() -> Path:
    """Get the data directory path."""
    env_data = os.environ.get("ROOTCAUSE_DATA_DIR")
    if env_data:
        return Path(env_data)

    # Navigate from src/rootcause_mcp/server_v2.py to project root
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent
    return project_root / "data"


def _get_tool_profile() -> str:
    """Return the configured MCP schema/dispatch profile."""
    return os.environ.get("ROOTCAUSE_TOOL_PROFILE", "all").strip().lower()


def _get_response_mode() -> str:
    """Return compact SDK 2.0 output mode or verbose compatibility mode."""
    mode = os.environ.get("ROOTCAUSE_RESPONSE_MODE", "compact").strip().lower()
    if mode not in {"compact", "verbose"}:
        raise ValueError(
            "ROOTCAUSE_RESPONSE_MODE must be either 'compact' or 'verbose'"
        )
    return mode


def _freeze_runtime_configuration() -> None:
    """Validate and freeze context-affecting settings for one lifespan."""
    tool_profile = _get_tool_profile()
    response_mode = _get_response_mode()
    get_all_tools(tool_profile)
    _runtime.tool_profile = tool_profile
    _runtime.response_mode = response_mode
    logger.info(
        "MCP tool profile=%s response mode=%s",
        tool_profile,
        response_mode,
    )
    if response_mode == "compact":
        logger.info(
            "Compact responses require host structuredContent support; "
            "set ROOTCAUSE_RESPONSE_MODE=verbose otherwise"
        )


@asynccontextmanager
async def lifespan(_server: Server) -> AsyncIterator[None]:
    """
    Lifespan context manager for SDK 2.0.

    Initializes all handlers and repositories on startup.
    """
    logger.info("Initializing RootCause MCP Server (SDK 2.0)...")
    _freeze_runtime_configuration()

    # Setup paths
    config_path = _get_config_path()
    data_path = _get_data_path()
    data_path.mkdir(parents=True, exist_ok=True)

    # Initialize database
    db_path = data_path / "rca_sessions.db"
    database = Database(db_path)
    database.create_tables()

    # Initialize repositories
    session_repo = SQLiteSessionRepository(database)
    fishbone_repo = SQLiteFishboneRepository(database)
    why_tree_repo = InMemoryWhyTreeRepository()
    evidence_repo = SQLiteEvidenceRepository(database)
    hypothesis_repo = SQLiteHypothesisRepository(database)
    thinking_repo = SQLiteThinkingChainRepository(database)
    reasoning_repo = SQLiteReasoningChainRepository(database)

    # Initialize services
    hfacs_suggester = HFACSSuggester(config_path / "hfacs")
    learned_rules_service = LearnedRulesService(config_path / "hfacs")

    # Initialize application layer
    progress_tracker = SessionProgressTracker()

    # Initialize ServerState (shared across handlers)
    server_state = ServerState(
        evidence_repository=evidence_repo,
        hypothesis_repository=hypothesis_repo,
        thinking_repository=thinking_repo,
        reasoning_repository=reasoning_repo,
    )

    # Initialize handlers
    # NEW in 2.0: Cognitive layer + Medical reasoning handlers (use ServerState)
    thinking_handlers = ThinkingHandlers(server_state)
    evidence_handlers = EvidenceHandlers(server_state)
    dd_handlers = DDHandlers(server_state)
    reasoning_handlers = ReasoningHandlers(server_state)
    contract_handlers = ContractHandlers(server_state)

    # Existing RCA handlers
    hfacs_handlers = HFACSHandlers(hfacs_suggester, learned_rules_service)
    session_handlers = SessionHandlers(session_repo, progress_tracker)
    fishbone_handlers = FishboneHandlers(
        fishbone_repo,
        session_repo,
        progress_tracker,
    )
    why_tree_handlers = WhyTreeHandlers(
        why_tree_repo,
        session_repo,
        progress_tracker,
    )
    verification_handlers = VerificationHandlers(progress_tracker)

    _runtime.server_state = server_state
    _runtime.thinking_handlers = thinking_handlers
    _runtime.evidence_handlers = evidence_handlers
    _runtime.dd_handlers = dd_handlers
    _runtime.reasoning_handlers = reasoning_handlers
    _runtime.contract_handlers = contract_handlers
    _runtime.hfacs_handlers = hfacs_handlers
    _runtime.session_handlers = session_handlers
    _runtime.fishbone_handlers = fishbone_handlers
    _runtime.why_tree_handlers = why_tree_handlers
    _runtime.verification_handlers = verification_handlers
    _runtime.database = database

    logger.info("✅ All handlers initialized")

    yield

    # Cleanup
    logger.info("Shutting down RootCause MCP Server...")
    database.close()
    _runtime.clear()


async def on_list_tools(_ctx: ServerRequestContext, _params: Any) -> ListToolsResult:
    """
    List all available MCP tools (SDK 2.0 callback).

    Returns:
        ListToolsResult with all tool definitions
    """
    profile = _runtime.tool_profile or _get_tool_profile()
    return ListToolsResult(tools=get_all_tools(profile))


ToolHandler = Callable[[dict[str, Any]], Awaitable[Any]]


async def _call_without_arguments(
    method: Callable[[], Awaitable[Any]], _arguments: dict[str, Any]
) -> Any:
    """Adapt a no-argument legacy handler to the common tool signature."""
    return await method()


def _build_tool_dispatch(profile: str | None = None) -> dict[str, ToolHandler]:
    """Build the explicit tool-to-handler registry for every advertised tool."""
    _thinking_handlers = _runtime.thinking_handlers
    _evidence_handlers = _runtime.evidence_handlers
    _dd_handlers = _runtime.dd_handlers
    _reasoning_handlers = _runtime.reasoning_handlers
    _contract_handlers = _runtime.contract_handlers
    _hfacs_handlers = _runtime.hfacs_handlers
    _session_handlers = _runtime.session_handlers
    _fishbone_handlers = _runtime.fishbone_handlers
    _why_tree_handlers = _runtime.why_tree_handlers
    _verification_handlers = _runtime.verification_handlers
    handlers = (
        _thinking_handlers,
        _evidence_handlers,
        _dd_handlers,
        _reasoning_handlers,
        _contract_handlers,
        _hfacs_handlers,
        _session_handlers,
        _fishbone_handlers,
        _why_tree_handlers,
        _verification_handlers,
    )
    if any(handler is None for handler in handlers):
        raise RuntimeError("Server handlers are not initialized")

    assert _thinking_handlers is not None
    assert _evidence_handlers is not None
    assert _dd_handlers is not None
    assert _reasoning_handlers is not None
    assert _contract_handlers is not None
    assert _hfacs_handlers is not None
    assert _session_handlers is not None
    assert _fishbone_handlers is not None
    assert _why_tree_handlers is not None
    assert _verification_handlers is not None

    dispatch: dict[str, ToolHandler] = {
        name: partial(_thinking_handlers.handle, name)
        for name in (
            "rc_think_aloud",
            "rc_reflect",
            "rc_identify_gaps",
            "rc_challenge_assumption",
            "rc_get_thinking_chain",
        )
    }
    dispatch.update(
        {
            name: partial(_evidence_handlers.handle, name)
            for name in (
                "rc_add_evidence",
                "rc_get_evidence",
                "rc_verify_evidence",
            )
        }
    )
    dispatch.update(
        {
            name: partial(_dd_handlers.handle, name)
            for name in (
                "rc_propose_hypothesis",
                "rc_link_evidence_to_hypothesis",
                "rc_get_differential_diagnosis",
                "rc_exclude_hypothesis",
            )
        }
    )
    dispatch.update(
        {
            name: partial(_reasoning_handlers.handle, name)
            for name in (
                "rc_get_reasoning_chain",
                "rc_export_reasoning_chain",
                "rc_audit_reasoning_state",
            )
        }
    )
    dispatch["rc_generate_contract_report"] = partial(
        _contract_handlers.handle, "rc_generate_contract_report"
    )
    dispatch.update(
        {
            "rc_suggest_hfacs": _hfacs_handlers.handle_suggest_hfacs,
            "rc_confirm_classification": (
                _hfacs_handlers.handle_confirm_classification
            ),
            "rc_get_hfacs_framework": _hfacs_handlers.handle_get_framework,
            "rc_get_6m_hfacs_mapping": (_hfacs_handlers.handle_get_6m_hfacs_mapping),
            "rc_list_learned_rules": _hfacs_handlers.handle_list_learned_rules,
            "rc_reload_rules": partial(
                _call_without_arguments, _hfacs_handlers.handle_reload_rules
            ),
            "rc_start_session": _session_handlers.handle_start_session,
            "rc_get_session": _session_handlers.handle_get_session,
            "rc_list_sessions": _session_handlers.handle_list_sessions,
            "rc_archive_session": _session_handlers.handle_archive_session,
            "rc_init_fishbone": _fishbone_handlers.handle_init_fishbone,
            "rc_add_cause": _fishbone_handlers.handle_add_cause,
            "rc_get_fishbone": _fishbone_handlers.handle_get_fishbone,
            "rc_export_fishbone": _fishbone_handlers.handle_export_fishbone,
            "rc_ask_why": _why_tree_handlers.handle_ask_why,
            "rc_get_why_tree": _why_tree_handlers.handle_get_why_tree,
            "rc_mark_root_cause": _why_tree_handlers.handle_mark_root_cause,
            "rc_add_causal_link": _why_tree_handlers.handle_add_causal_link,
            "rc_export_why_tree": _why_tree_handlers.handle_export_why_tree,
            "rc_build_teaching_case": _why_tree_handlers.handle_build_teaching_case,
            "rc_verify_causation": (_verification_handlers.handle_verify_causation),
        }
    )
    active_profile = profile or _runtime.tool_profile or _get_tool_profile()
    visible_tool_names = {tool.name for tool in get_all_tools(active_profile)}
    return {
        name: handler
        for name, handler in dispatch.items()
        if name in visible_tool_names
    }


def _compact_structured_text(result: dict[str, Any]) -> str:
    """Build a bounded text fallback without duplicating structured content."""
    summary: dict[str, Any] = {}
    preferred_keys = (
        "status",
        "message",
        "session_id",
        "report_id",
        "evidence_id",
        "hypothesis_id",
        "thinking_step_id",
        "reflection_id",
        "gap_id",
        "challenge_id",
        "format",
        "output_path",
        "finalized",
        "verified",
        "posterior_probability",
        "quality_score",
    )
    for key in preferred_keys:
        value = result.get(key)
        if isinstance(value, str):
            summary[key] = value if len(value) <= 240 else f"{value[:237]}..."
        elif key in result and (isinstance(value, int | float | bool) or value is None):
            summary[key] = value

    for key, value in result.items():
        is_count = key.startswith("total_") or key.endswith(
            ("_count", "_steps", "_nodes", "_edges")
        )
        if is_count and isinstance(value, int | float):
            summary.setdefault(key, value)

    if "guidance" in result and isinstance(result["guidance"], dict):
        g = result["guidance"]
        if "current_stage" in g:
            summary["stage"] = g["current_stage"]
        if "completeness_score" in g:
            with suppress(ValueError, TypeError):
                summary["completeness"] = f"{float(g['completeness_score']):.0%}"
        if g.get("next_recommended_actions") and isinstance(
            g["next_recommended_actions"], list
        ):
            summary["next_prompt"] = str(g["next_recommended_actions"][0])[:180]

    summary.setdefault("status", "success")
    summary["detail"] = "structuredContent"
    summary["fallback"] = (
        "Set ROOTCAUSE_RESPONSE_MODE=verbose if structuredContent is unavailable"
    )
    return json.dumps(summary, ensure_ascii=False, separators=(",", ":"), default=str)


def _to_call_tool_result(result: Any) -> CallToolResult:
    """Normalize modern dict and legacy content responses for MCP SDK 2.0."""
    if isinstance(result, CallToolResult):
        return result
    if isinstance(result, dict):
        response_mode = _runtime.response_mode or _get_response_mode()
        text = (
            json.dumps(result, ensure_ascii=False, indent=2, default=str)
            if response_mode == "verbose"
            else _compact_structured_text(result)
        )
        return CallToolResult(
            content=[TextContent(type="text", text=text)],
            structured_content=result,
        )
    if isinstance(result, (list, tuple)):
        content: list[Any] = [
            item
            if isinstance(item, TextContent)
            else TextContent(type="text", text=str(item))
            for item in result
        ]
        text_content = [
            item.text if isinstance(item, TextContent) else str(item)
            for item in content
        ]
        return CallToolResult(
            content=content,
            structured_content={"status": "success", "content": text_content},
        )
    return CallToolResult(content=[TextContent(type="text", text=str(result))])


async def on_call_tool(
    _ctx: ServerRequestContext, params: CallToolRequestParams
) -> CallToolResult:
    """
    Handle tool calls (SDK 2.0 callback).

    Routes tool calls to appropriate handlers based on tool name prefix.

    Args:
        ctx: Server request context
        params: Tool call parameters (name + arguments)

    Returns:
        CallToolResult with tool execution result
    """
    tool_name = params.name
    arguments = params.arguments or {}

    try:
        handler = _build_tool_dispatch().get(tool_name)
        if handler is None:
            return CallToolResult(
                content=[
                    TextContent(type="text", text=f"Error: Unknown tool '{tool_name}'")
                ],
                is_error=True,
            )
        return _to_call_tool_result(await handler(arguments))
    except Exception as exc:
        logger.exception("Error executing tool %s", tool_name)
        return CallToolResult(
            content=[
                TextContent(type="text", text=f"Error executing {tool_name}: {exc}")
            ],
            is_error=True,
        )


# Create server instance with SDK 2.0 API
server = Server(
    "rootcause-mcp",
    version="2.0.0a1",
    lifespan=lifespan,
    on_list_tools=on_list_tools,
    on_call_tool=on_call_tool,
)


async def main() -> None:
    """Main entry point for stdio transport."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
