"""
Root Cause Analysis MCP Server (DDD Refactored).

MCP Server entry point for healthcare root cause analysis.
Delegates to modular handlers organized by domain.
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any, AsyncIterator, Sequence

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    GetPromptResult,
    Prompt,
    PromptArgument,
    PromptMessage,
    TextContent,
    Tool,
)

# Tool definitions
from rootcause_mcp.interface.tools import (
    get_hfacs_tools,
    get_session_tools,
    get_fishbone_tools,
    get_why_tree_tools,
    get_verification_tools,
)

# Handlers
from rootcause_mcp.interface.handlers import (
    HFACSHandlers,
    SessionHandlers,
    FishboneHandlers,
    WhyTreeHandlers,
    VerificationHandlers,
)

# Domain and Infrastructure
from rootcause_mcp.domain.services import HFACSSuggester, LearnedRulesService
from rootcause_mcp.infrastructure.persistence.database import Database
from rootcause_mcp.infrastructure.persistence.session_repository import (
    SQLiteSessionRepository,
)
from rootcause_mcp.infrastructure.persistence.fishbone_repository import (
    SQLiteFishboneRepository,
)
from rootcause_mcp.infrastructure.persistence.why_tree_repository import (
    InMemoryWhyTreeRepository,
)

# Application layer
from rootcause_mcp.application.session_progress import SessionProgressTracker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Server instance
server = Server("rootcause-mcp")

# Handler instances (initialized on startup)
_hfacs_handlers: HFACSHandlers | None = None
_session_handlers: SessionHandlers | None = None
_fishbone_handlers: FishboneHandlers | None = None
_why_tree_handlers: WhyTreeHandlers | None = None
_verification_handlers: VerificationHandlers | None = None

# Repository instances
_database: Database | None = None


def _get_config_path() -> Path:
    """Get the configuration directory path."""
    env_config = os.environ.get("ROOTCAUSE_CONFIG_DIR")
    if env_config:
        return Path(env_config)
    
    # Navigate from src/rootcause_mcp/server.py to project root
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent
    return project_root / "config"


def _get_data_path() -> Path:
    """Get the data directory path."""
    env_data = os.environ.get("ROOTCAUSE_DATA_DIR")
    if env_data:
        return Path(env_data)
    
    # Navigate from src/rootcause_mcp/server.py to project root
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent
    return project_root / "data"


def _initialize_services() -> None:
    """Initialize all services and handlers."""
    global _hfacs_handlers, _session_handlers, _fishbone_handlers
    global _why_tree_handlers, _verification_handlers, _database
    
    config_path = _get_config_path()
    data_path = _get_data_path()
    hfacs_config_path = config_path / "hfacs"
    
    # Initialize Domain Services
    hfacs_suggester = HFACSSuggester(config_dir=hfacs_config_path)
    learned_rules = LearnedRulesService(config_dir=hfacs_config_path)
    
    # Initialize Database and Repositories
    db_path = data_path / "rca_sessions.db"
    _database = Database(db_path)
    _database.create_tables()
    
    session_repo = SQLiteSessionRepository(_database)
    fishbone_repo = SQLiteFishboneRepository(_database)
    why_tree_repo = InMemoryWhyTreeRepository(_database)
    
    # Initialize Progress Tracker
    progress_tracker = SessionProgressTracker()
    
    # Initialize Handlers with dependencies
    _hfacs_handlers = HFACSHandlers(
        hfacs_suggester=hfacs_suggester,
        learned_rules_service=learned_rules,
    )
    
    _session_handlers = SessionHandlers(
        session_repository=session_repo,
        progress_tracker=progress_tracker,
    )
    
    _fishbone_handlers = FishboneHandlers(
        fishbone_repository=fishbone_repo,
        session_repository=session_repo,
        progress_tracker=progress_tracker,
    )
    
    _why_tree_handlers = WhyTreeHandlers(
        why_tree_repository=why_tree_repo,
        session_repository=session_repo,
        progress_tracker=progress_tracker,
    )
    
    _verification_handlers = VerificationHandlers(
        progress_tracker=progress_tracker,
    )
    
    logger.info("Services initialized with config path: %s", hfacs_config_path)
    logger.info("Database initialized at: %s", db_path)


# ============================================================================
# MCP Tools
# ============================================================================

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available MCP tools."""
    tools = []
    tools.extend(get_hfacs_tools())
    tools.extend(get_session_tools())
    tools.extend(get_fishbone_tools())
    tools.extend(get_why_tree_tools())
    tools.extend(get_verification_tools())
    return tools


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> Sequence[TextContent]:
    """Route tool calls to appropriate handlers."""
    # Ensure services are initialized
    if _hfacs_handlers is None or _session_handlers is None:
        _initialize_services()
    
    try:
        # HFACS Tools
        if name == "rc_suggest_hfacs":
            assert _hfacs_handlers is not None
            return await _hfacs_handlers.handle_suggest_hfacs(arguments)
        elif name == "rc_confirm_classification":
            assert _hfacs_handlers is not None
            return await _hfacs_handlers.handle_confirm_classification(arguments)
        elif name == "rc_get_hfacs_framework":
            assert _hfacs_handlers is not None
            return await _hfacs_handlers.handle_get_framework(arguments)
        elif name == "rc_list_learned_rules":
            assert _hfacs_handlers is not None
            return await _hfacs_handlers.handle_list_learned_rules(arguments)
        elif name == "rc_reload_rules":
            assert _hfacs_handlers is not None
            return await _hfacs_handlers.handle_reload_rules()
        elif name == "rc_get_6m_hfacs_mapping":
            assert _hfacs_handlers is not None
            return await _hfacs_handlers.handle_get_6m_hfacs_mapping(arguments)
        
        # Session Tools
        elif name == "rc_start_session":
            assert _session_handlers is not None
            return await _session_handlers.handle_start_session(arguments)
        elif name == "rc_get_session":
            assert _session_handlers is not None
            return await _session_handlers.handle_get_session(arguments)
        elif name == "rc_list_sessions":
            assert _session_handlers is not None
            return await _session_handlers.handle_list_sessions(arguments)
        elif name == "rc_archive_session":
            assert _session_handlers is not None
            return await _session_handlers.handle_archive_session(arguments)
        
        # Fishbone Tools
        elif name == "rc_init_fishbone":
            assert _fishbone_handlers is not None
            return await _fishbone_handlers.handle_init_fishbone(arguments)
        elif name == "rc_add_cause":
            assert _fishbone_handlers is not None
            return await _fishbone_handlers.handle_add_cause(arguments)
        elif name == "rc_get_fishbone":
            assert _fishbone_handlers is not None
            return await _fishbone_handlers.handle_get_fishbone(arguments)
        elif name == "rc_export_fishbone":
            assert _fishbone_handlers is not None
            return await _fishbone_handlers.handle_export_fishbone(arguments)
        
        # Why Tree Tools
        elif name == "rc_ask_why":
            assert _why_tree_handlers is not None
            return await _why_tree_handlers.handle_ask_why(arguments)
        elif name == "rc_get_why_tree":
            assert _why_tree_handlers is not None
            return await _why_tree_handlers.handle_get_why_tree(arguments)
        elif name == "rc_mark_root_cause":
            assert _why_tree_handlers is not None
            return await _why_tree_handlers.handle_mark_root_cause(arguments)
        elif name == "rc_export_why_tree":
            assert _why_tree_handlers is not None
            return await _why_tree_handlers.handle_export_why_tree(arguments)
        
        # Verification Tools
        elif name == "rc_verify_causation":
            assert _verification_handlers is not None
            return await _verification_handlers.handle_verify_causation(arguments)
        
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
            
    except Exception as e:
        logger.exception("Error in tool %s", name)
        return [TextContent(type="text", text=f"Error: {e!s}")]


# ============================================================================
# MCP Prompts
# ============================================================================

@server.list_prompts()
async def list_prompts() -> list[Prompt]:
    """List available MCP prompts."""
    return [
        Prompt(
            name="analyze_incident",
            description=(
                "Analyze a clinical incident using systematic RCA methodology. "
                "Guides through 5-Why analysis and HFACS classification."
            ),
            arguments=[
                PromptArgument(
                    name="incident_description",
                    description="Brief description of the incident",
                    required=True,
                ),
                PromptArgument(
                    name="domain",
                    description="Clinical domain (e.g., anesthesia, surgery, nursing)",
                    required=False,
                ),
            ],
        ),
    ]


@server.get_prompt()
async def get_prompt(name: str, arguments: dict[str, str] | None) -> GetPromptResult:
    """Get a prompt by name."""
    if name == "analyze_incident":
        return await _get_analyze_incident_prompt(arguments or {})
    
    raise ValueError(f"Unknown prompt: {name}")


async def _get_analyze_incident_prompt(
    arguments: dict[str, str],
) -> GetPromptResult:
    """Generate the analyze_incident prompt."""
    incident = arguments.get("incident_description", "")
    domain = arguments.get("domain", "")
    
    domain_context = f" in the {domain} domain" if domain else ""
    
    prompt_text = f"""# Clinical Incident Root Cause Analysis

## Incident Description
{incident}

## Analysis Framework
You are conducting a systematic root cause analysis{domain_context} using:
1. **5-Why Analysis** - Iteratively ask "why" to find root causes
2. **HFACS-MES Classification** - Categorize causes using the Human Factors framework

## Instructions

### Step 1: Initial Analysis
Summarize the key facts of the incident:
- What happened?
- When and where?
- Who was involved?
- What was the immediate outcome?

### Step 2: 5-Why Analysis
For each contributing factor, ask "why" up to 5 times:
1. Why did [event] happen? → [cause 1]
2. Why did [cause 1] happen? → [cause 2]
... continue until root cause is reached

### Step 3: HFACS Classification
Use `rc_suggest_hfacs` to get classification suggestions for each cause.
Consider all 5 HFACS levels:
- **EF** - External Factors (regulatory, external pressures)
- **OI** - Organizational Influences (management, resources)
- **US** - Unsafe Supervision (supervisory failures)
- **PC** - Preconditions (environmental, personal conditions)
- **UA** - Unsafe Acts (errors, violations)

### Step 4: Confirm Classifications
Use `rc_confirm_classification` to confirm correct classifications.
This helps improve future suggestions.

### Step 5: Recommendations
Based on the analysis, suggest:
1. Immediate corrective actions
2. Systemic improvements
3. Training needs
4. Process changes

---
Begin your analysis by summarizing the key facts."""

    return GetPromptResult(
        description="Clinical incident analysis prompt",
        messages=[
            PromptMessage(
                role="user",
                content=TextContent(type="text", text=prompt_text),
            ),
        ],
    )


# ============================================================================
# Server Lifecycle
# ============================================================================

@asynccontextmanager
async def server_lifespan(server_instance: Server) -> AsyncIterator[dict[str, Any]]:
    """Manage server lifecycle."""
    logger.info("Starting Root Cause Analysis MCP Server...")
    _initialize_services()
    
    yield {}
    
    logger.info("Shutting down Root Cause Analysis MCP Server...")


async def run_server() -> None:
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def create_server() -> Server:
    """Create and return the server instance."""
    _initialize_services()
    return server


def main() -> None:
    """Entry point for the MCP server."""
    _initialize_services()
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
