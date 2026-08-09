"""
Root Cause Analysis MCP Server (SDK 2.0).

MCP Server entry point for medical reasoning and differential diagnosis.
Uses SDK 2.0 callback-based API.
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from mcp.server import Server, ServerRequestContext
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequestParams,
    CallToolResult,
    ListToolsResult,
    TextContent,
    Tool,
)

# Tool definitions
from rootcause_mcp.interface.tools import (
    get_contract_tools,
    get_dd_tools,
    get_evidence_tools,
    get_fishbone_tools,
    get_hfacs_tools,
    get_reasoning_tools,
    get_session_tools,
    get_thinking_tools,
    get_verification_tools,
    get_why_tree_tools,
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

# Domain and Infrastructure
from rootcause_mcp.domain.services import HFACSSuggester, LearnedRulesService
from rootcause_mcp.infrastructure.persistence.database import Database
from rootcause_mcp.infrastructure.persistence.fishbone_repository import (
    SQLiteFishboneRepository,
)
from rootcause_mcp.infrastructure.persistence.session_repository import (
    SQLiteSessionRepository,
)
from rootcause_mcp.infrastructure.persistence.why_tree_repository import (
    InMemoryWhyTreeRepository,
)

# Application layer
from rootcause_mcp.application.clinical_reasoning_orchestrator import (
    ClinicalReasoningOrchestrator,
)
from rootcause_mcp.application.session_progress import SessionProgressTracker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global handler instances (initialized in lifespan)
_thinking_handlers: ThinkingHandlers | None = None
_evidence_handlers: EvidenceHandlers | None = None
_dd_handlers: DDHandlers | None = None
_reasoning_handlers: ReasoningHandlers | None = None
_contract_handlers: ContractHandlers | None = None
_hfacs_handlers: HFACSHandlers | None = None
_session_handlers: SessionHandlers | None = None
_fishbone_handlers: FishboneHandlers | None = None
_why_tree_handlers: WhyTreeHandlers | None = None
_verification_handlers: VerificationHandlers | None = None
_database: Database | None = None


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


@asynccontextmanager
async def lifespan(server: Server):
    """
    Lifespan context manager for SDK 2.0.

    Initializes all handlers and repositories on startup.
    """
    global _thinking_handlers, _evidence_handlers, _dd_handlers
    global _reasoning_handlers, _contract_handlers
    global _hfacs_handlers, _session_handlers, _fishbone_handlers
    global _why_tree_handlers, _verification_handlers, _database

    logger.info("Initializing RootCause MCP Server (SDK 2.0)...")

    # Setup paths
    config_path = _get_config_path()
    data_path = _get_data_path()
    data_path.mkdir(parents=True, exist_ok=True)

    # Initialize database
    db_path = data_path / "rca_sessions.db"
    _database = Database(db_path)
    await _database.initialize()

    # Initialize repositories
    session_repo = SQLiteSessionRepository(_database)
    fishbone_repo = SQLiteFishboneRepository(_database)
    why_tree_repo = InMemoryWhyTreeRepository()

    # Initialize services
    hfacs_suggester = HFACSSuggester(config_path / "hfacs")
    learned_rules_service = LearnedRulesService(config_path / "hfacs" / "learned_rules.yaml")

    # Initialize application layer
    progress_tracker = SessionProgressTracker()

    # Initialize handlers
    # NEW in 2.0: Cognitive layer + Medical reasoning handlers
    _thinking_handlers = ThinkingHandlers()
    _evidence_handlers = EvidenceHandlers()
    _dd_handlers = DDHandlers()
    _reasoning_handlers = ReasoningHandlers()
    _contract_handlers = ContractHandlers()
    
    # Existing RCA handlers
    _hfacs_handlers = HFACSHandlers(hfacs_suggester, learned_rules_service)
    _session_handlers = SessionHandlers(session_repo, progress_tracker)
    _fishbone_handlers = FishboneHandlers(fishbone_repo, session_repo, progress_tracker)
    _why_tree_handlers = WhyTreeHandlers(why_tree_repo, session_repo, progress_tracker)
    _verification_handlers = VerificationHandlers(progress_tracker)

    logger.info("✅ All handlers initialized")

    yield

    # Cleanup
    logger.info("Shutting down RootCause MCP Server...")
    if _database:
        await _database.close()


async def on_list_tools(
    ctx: ServerRequestContext, params: Any
) -> ListToolsResult:
    """
    List all available MCP tools (SDK 2.0 callback).

    Returns:
        ListToolsResult with all tool definitions
    """
    tools: list[Tool] = []
    # NEW in 2.0: Cognitive Layer
    tools.extend(get_thinking_tools())
    # NEW in 2.0: Medical Reasoning
    tools.extend(get_evidence_tools())
    tools.extend(get_dd_tools())
    tools.extend(get_reasoning_tools())
    tools.extend(get_contract_tools())
    # Existing RCA Tools
    tools.extend(get_hfacs_tools())
    tools.extend(get_session_tools())
    tools.extend(get_fishbone_tools())
    tools.extend(get_why_tree_tools())
    tools.extend(get_verification_tools())

    return ListToolsResult(tools=tools)


async def _legacy_adapter(handler: Any, method_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """
    Adapter for legacy handlers that return Sequence[TextContent].

    Converts legacy handler output to dict format expected by SDK 2.0.
    """
    import json

    method = getattr(handler, method_name)
    result = await method(arguments)

    # Convert Sequence[TextContent] to dict
    if isinstance(result, (list, tuple)):
        texts = []
        for item in result:
            if isinstance(item, TextContent):
                texts.append(item.text)
            else:
                texts.append(str(item))

        combined_text = "\n".join(texts)

        # Try to parse as JSON
        try:
            return json.loads(combined_text)
        except (json.JSONDecodeError, ValueError):
            return {"result": combined_text}

    # Already a dict
    return result


async def on_call_tool(
    ctx: ServerRequestContext, params: CallToolRequestParams
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
    if _hfacs_handlers is None or _session_handlers is None:
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text="Error: Server not initialized. Please wait for startup to complete.",
                )
            ],
            is_error=True,
        )

    tool_name = params.name
    arguments = params.arguments or {}

    try:
        # Route to appropriate handler based on tool name
        # NEW in 2.0: Cognitive Layer + Medical Reasoning (already have handle() method)
        if tool_name.startswith(("rc_think", "rc_reflect", "rc_identify", "rc_challenge")):
            result = await _thinking_handlers.handle(tool_name, arguments)
        elif tool_name.startswith(("rc_add_evidence", "rc_get_evidence", "rc_verify_evidence")):
            result = await _evidence_handlers.handle(tool_name, arguments)
        elif tool_name.startswith(("rc_propose", "rc_link", "rc_get_differential", "rc_exclude")):
            result = await _dd_handlers.handle(tool_name, arguments)
        elif tool_name.startswith(("rc_get_reasoning", "rc_export_reasoning")):
            result = await _reasoning_handlers.handle(tool_name, arguments)
        elif tool_name.startswith("rc_generate_contract"):
            result = await _contract_handlers.handle(tool_name, arguments)

        # Legacy RCA Tools (use adapter to convert to dict)
        elif tool_name.startswith("rc_suggest_hfacs"):
            result = await _legacy_adapter(_hfacs_handlers, "handle_suggest_hfacs", arguments)
        elif tool_name.startswith("rc_confirm_classification"):
            result = await _legacy_adapter(_hfacs_handlers, "handle_confirm_classification", arguments)
        elif tool_name.startswith("rc_get_hfacs_framework"):
            result = await _legacy_adapter(_hfacs_handlers, "handle_get_framework", arguments)
        elif tool_name.startswith("rc_get_6m"):
            result = await _legacy_adapter(_hfacs_handlers, "handle_get_6m_hfacs_mapping", arguments)
        elif tool_name.startswith("rc_list_learned"):
            result = await _legacy_adapter(_hfacs_handlers, "handle_list_learned_rules", arguments)
        elif tool_name.startswith("rc_reload"):
            result = await _legacy_adapter(_hfacs_handlers, "handle_reload_rules", arguments)

        elif tool_name.startswith("rc_start_session"):
            result = await _legacy_adapter(_session_handlers, "handle_start_session", arguments)
        elif tool_name.startswith("rc_get_session"):
            result = await _legacy_adapter(_session_handlers, "handle_get_session", arguments)
        elif tool_name.startswith("rc_list_sessions"):
            result = await _legacy_adapter(_session_handlers, "handle_list_sessions", arguments)
        elif tool_name.startswith("rc_archive"):
            result = await _legacy_adapter(_session_handlers, "handle_archive_session", arguments)

        elif tool_name.startswith("rc_init_fishbone"):
            result = await _legacy_adapter(_fishbone_handlers, "handle_init_fishbone", arguments)
        elif tool_name.startswith("rc_add_cause"):
            result = await _legacy_adapter(_fishbone_handlers, "handle_add_cause", arguments)
        elif tool_name.startswith("rc_get_fishbone"):
            result = await _legacy_adapter(_fishbone_handlers, "handle_get_fishbone", arguments)
        elif tool_name.startswith("rc_export_fishbone"):
            result = await _legacy_adapter(_fishbone_handlers, "handle_export_fishbone", arguments)

        elif tool_name.startswith("rc_ask_why"):
            result = await _legacy_adapter(_why_tree_handlers, "handle_ask_why", arguments)
        elif tool_name.startswith("rc_get_why"):
            result = await _legacy_adapter(_why_tree_handlers, "handle_get_why_tree", arguments)
        elif tool_name.startswith("rc_mark_root"):
            result = await _legacy_adapter(_why_tree_handlers, "handle_mark_root_cause", arguments)
        elif tool_name.startswith("rc_export_why"):
            result = await _legacy_adapter(_why_tree_handlers, "handle_export_why_tree", arguments)

        elif tool_name.startswith("rc_verify"):
            result = await _legacy_adapter(_verification_handlers, "handle_verify_causation", arguments)
        else:
            return CallToolResult(
                content=[
                    TextContent(
                        type="text", text=f"Error: Unknown tool '{tool_name}'"
                    )
                ],
                is_error=True,
            )

        # Convert result to CallToolResult
        if isinstance(result, dict):
            import json

            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(result, indent=2))]
            )
        else:
            return CallToolResult(
                content=[TextContent(type="text", text=str(result))]
            )

    except Exception as e:
        logger.exception(f"Error executing tool {tool_name}")
        return CallToolResult(
            content=[
                TextContent(
                    type="text", text=f"Error executing {tool_name}: {str(e)}"
                )
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


async def main():
    """Main entry point for stdio transport."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
