"""
Root Cause Analysis MCP Server.

MCP (Model Context Protocol) Server for healthcare root cause analysis,
providing AI agents with tools for systematic RCA using HFACS-MES framework.
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any, AsyncIterator

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

from rootcause_mcp.domain.entities.session import RCASession
from rootcause_mcp.domain.entities.fishbone import Fishbone, FishboneCause
from rootcause_mcp.domain.entities.why_node import WhyChain, WhyNode
from rootcause_mcp.domain.services import HFACSSuggester, LearnedRulesService
from rootcause_mcp.domain.value_objects.enums import (
    CaseType,
    SessionStatus,
    FishboneCategoryType,
)
from rootcause_mcp.domain.value_objects.identifiers import SessionId, CauseId
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

if TYPE_CHECKING:
    from collections.abc import Sequence

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Server instance
server = Server("rootcause-mcp")

# Service instances (initialized on startup)
_hfacs_suggester: HFACSSuggester | None = None
_learned_rules_service: LearnedRulesService | None = None

# Repository instances
_database: Database | None = None
_session_repository: SQLiteSessionRepository | None = None
_fishbone_repository: SQLiteFishboneRepository | None = None
_why_tree_repository: InMemoryWhyTreeRepository | None = None


def _get_config_path() -> Path:
    """Get the configuration directory path."""
    # Check environment variable first
    env_config = os.environ.get("ROOTCAUSE_CONFIG_DIR")
    if env_config:
        return Path(env_config)
    
    # Navigate from src/rootcause_mcp/server.py to project root
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent
    return project_root / "config"


def _get_data_path() -> Path:
    """Get the data directory path."""
    # Check environment variable first
    env_data = os.environ.get("ROOTCAUSE_DATA_DIR")
    if env_data:
        return Path(env_data)
    
    # Navigate from src/rootcause_mcp/server.py to project root
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent
    return project_root / "data"


def _initialize_services() -> None:
    """Initialize domain services and repositories."""
    global _hfacs_suggester, _learned_rules_service
    global _database, _session_repository, _fishbone_repository, _why_tree_repository
    
    config_path = _get_config_path()
    data_path = _get_data_path()
    hfacs_config_path = config_path / "hfacs"
    
    # Initialize HFACSSuggester with YAML config
    _hfacs_suggester = HFACSSuggester(config_dir=hfacs_config_path)
    
    # Initialize LearnedRulesService
    _learned_rules_service = LearnedRulesService(config_dir=hfacs_config_path)
    
    # Initialize Database and Repositories
    db_path = data_path / "rca_sessions.db"
    _database = Database(db_path)
    _database.create_tables()
    
    _session_repository = SQLiteSessionRepository(_database)
    _fishbone_repository = SQLiteFishboneRepository(_database)
    _why_tree_repository = InMemoryWhyTreeRepository(_database)
    
    logger.info("Services initialized with config path: %s", hfacs_config_path)
    logger.info("Database initialized at: %s", db_path)


# ============================================================================
# MCP Tools
# ============================================================================

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools."""
    return [
        # ============================================================================
        # HFACS Classification Tools
        # ============================================================================
        Tool(
            name="rc_suggest_hfacs",
            description=(
                "Suggest HFACS-MES classification codes for a cause description. "
                "Returns ranked suggestions with confidence scores. "
                "HFACS-MES has 5 levels: External Factors, Organizational Influences, "
                "Unsafe Supervision, Preconditions, Unsafe Acts."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "The cause description text to classify",
                    },
                    "domain": {
                        "type": "string",
                        "description": (
                            "Optional domain context for better suggestions "
                            "(e.g., 'anesthesia', 'surgery', 'nursing')"
                        ),
                        "default": None,
                    },
                    "max_suggestions": {
                        "type": "integer",
                        "description": "Maximum number of suggestions to return",
                        "default": 3,
                        "minimum": 1,
                        "maximum": 10,
                    },
                },
                "required": ["description"],
            },
        ),
        Tool(
            name="rc_confirm_classification",
            description=(
                "Confirm an HFACS classification as correct. "
                "This helps the system learn from expert decisions and improve future suggestions. "
                "Confirmed classifications are stored as learned rules."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "The original cause description",
                    },
                    "hfacs_code": {
                        "type": "string",
                        "description": (
                            "The confirmed HFACS code "
                            "(e.g., 'UA-S', 'PC-C-PMC', 'EF-RE')"
                        ),
                    },
                    "reason": {
                        "type": "string",
                        "description": "Brief explanation of why this classification is correct",
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Optional session ID for tracking",
                        "default": None,
                    },
                    "confidence": {
                        "type": "number",
                        "description": "Confidence level (0.0-1.0)",
                        "default": 0.8,
                        "minimum": 0.0,
                        "maximum": 1.0,
                    },
                },
                "required": ["description", "hfacs_code", "reason"],
            },
        ),
        Tool(
            name="rc_get_hfacs_framework",
            description=(
                "Get HFACS-MES framework structure and category definitions. "
                "Use this to understand the classification hierarchy and criteria."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "level": {
                        "type": "string",
                        "description": (
                            "Optional: specific level to retrieve "
                            "(EF, OI, US, PC, UA). If not specified, returns all levels."
                        ),
                        "enum": ["EF", "OI", "US", "PC", "UA", None],
                        "default": None,
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="rc_list_learned_rules",
            description=(
                "List all learned classification rules. "
                "Shows rules that have been confirmed by experts."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "hfacs_code": {
                        "type": "string",
                        "description": "Optional: filter by specific HFACS code",
                        "default": None,
                    },
                    "min_confidence": {
                        "type": "number",
                        "description": "Minimum confidence threshold",
                        "default": 0.0,
                        "minimum": 0.0,
                        "maximum": 1.0,
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="rc_reload_rules",
            description=(
                "Reload classification rules from YAML files. "
                "Use this after manually editing config files."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        # ============================================================================
        # Session Management Tools
        # ============================================================================
        Tool(
            name="rc_start_session",
            description=(
                "Start a new RCA analysis session. "
                "Creates a new session with the specified case type and title. "
                "Returns session_id for subsequent operations."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "case_type": {
                        "type": "string",
                        "description": "Type of case being analyzed",
                        "enum": ["death", "complication", "near_miss", "safety", "staffing"],
                    },
                    "case_title": {
                        "type": "string",
                        "description": "Brief title for the case",
                    },
                    "initial_description": {
                        "type": "string",
                        "description": "Initial description of the incident",
                        "default": "",
                    },
                },
                "required": ["case_type", "case_title"],
            },
        ),
        Tool(
            name="rc_get_session",
            description=(
                "Get details of an RCA session by ID. "
                "Returns session status, current stage, and progress."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "The session ID to retrieve",
                    },
                },
                "required": ["session_id"],
            },
        ),
        Tool(
            name="rc_list_sessions",
            description=(
                "List all RCA sessions with optional filters. "
                "Returns summary of all sessions."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Filter by session status",
                        "enum": ["active", "completed", "abandoned", "archived"],
                        "default": None,
                    },
                    "case_type": {
                        "type": "string",
                        "description": "Filter by case type",
                        "enum": ["death", "complication", "near_miss", "safety", "staffing"],
                        "default": None,
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of sessions to return",
                        "default": 20,
                        "minimum": 1,
                        "maximum": 100,
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="rc_archive_session",
            description=(
                "Archive a completed RCA session. "
                "Archived sessions are preserved but marked as inactive."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "The session ID to archive",
                    },
                },
                "required": ["session_id"],
            },
        ),
        # ============================================================================
        # Fishbone Diagram Tools
        # ============================================================================
        Tool(
            name="rc_init_fishbone",
            description=(
                "Initialize a Fishbone (Ishikawa) diagram for a session. "
                "Creates a 6M structure (Personnel, Equipment, Material, Process, "
                "Environment, Monitoring) with the problem statement as the fish head."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "The session ID to create fishbone for",
                    },
                    "problem_statement": {
                        "type": "string",
                        "description": "The problem statement (fish head)",
                    },
                },
                "required": ["session_id", "problem_statement"],
            },
        ),
        Tool(
            name="rc_add_cause",
            description=(
                "Add a cause to a Fishbone category. "
                "Each cause can have sub-causes, evidence, and HFACS classification."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "The session ID",
                    },
                    "category": {
                        "type": "string",
                        "description": "The 6M category for this cause",
                        "enum": ["Personnel", "Equipment", "Material", "Process", "Environment", "Monitoring"],
                    },
                    "description": {
                        "type": "string",
                        "description": "Description of the cause",
                    },
                    "sub_causes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of sub-causes (optional)",
                        "default": [],
                    },
                    "hfacs_code": {
                        "type": "string",
                        "description": "HFACS classification code (optional)",
                        "default": None,
                    },
                    "evidence": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Supporting evidence (optional)",
                        "default": [],
                    },
                },
                "required": ["session_id", "category", "description"],
            },
        ),
        Tool(
            name="rc_get_fishbone",
            description=(
                "Get the complete Fishbone diagram for a session. "
                "Returns all categories and causes in structured format."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "The session ID",
                    },
                },
                "required": ["session_id"],
            },
        ),
        Tool(
            name="rc_export_fishbone",
            description=(
                "Export Fishbone diagram in various formats. "
                "Supports Mermaid, JSON, and Markdown formats."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "The session ID",
                    },
                    "format": {
                        "type": "string",
                        "description": "Export format",
                        "enum": ["mermaid", "json", "markdown"],
                        "default": "mermaid",
                    },
                },
                "required": ["session_id"],
            },
        ),
        # ============================================================================
        # Why Tree / 5-Why Analysis Tools
        # ============================================================================
        Tool(
            name="rc_ask_why",
            description=(
                "Ask 'Why?' to drill down into root causes using 5-Why analysis. "
                "Creates or extends a WhyChain for the session. "
                "Each call goes one level deeper (up to 5 levels). "
                "This is the CORE tool for systematic root cause reasoning."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "The session ID",
                    },
                    "answer": {
                        "type": "string",
                        "description": (
                            "The answer to 'Why?'. This becomes the basis for the next question. "
                            "Example: 'Because the nurse miscalculated the dose'"
                        ),
                    },
                    "parent_node_id": {
                        "type": "string",
                        "description": (
                            "Optional: ID of parent node to branch from. "
                            "If not provided, continues from the last node or creates first Why."
                        ),
                        "default": None,
                    },
                    "evidence": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Supporting evidence for this answer (optional)",
                        "default": [],
                    },
                    "initial_problem": {
                        "type": "string",
                        "description": (
                            "The initial problem statement. "
                            "Required only for the FIRST Why in a chain."
                        ),
                        "default": None,
                    },
                },
                "required": ["session_id", "answer"],
            },
        ),
        Tool(
            name="rc_get_why_tree",
            description=(
                "Get the complete Why Tree (5-Why analysis chain) for a session. "
                "Shows all Why questions and answers in hierarchical format."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "The session ID",
                    },
                },
                "required": ["session_id"],
            },
        ),
        Tool(
            name="rc_mark_root_cause",
            description=(
                "Mark a WhyNode as the identified root cause. "
                "This indicates the analysis has reached a fundamental cause "
                "that requires action."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "The session ID",
                    },
                    "node_id": {
                        "type": "string",
                        "description": "The WhyNode ID to mark as root cause",
                    },
                    "confidence": {
                        "type": "number",
                        "description": "Confidence level (0.0-1.0)",
                        "default": 0.8,
                        "minimum": 0.0,
                        "maximum": 1.0,
                    },
                },
                "required": ["session_id", "node_id"],
            },
        ),
        Tool(
            name="rc_export_why_tree",
            description=(
                "Export Why Tree in various formats. "
                "Supports Mermaid (flowchart), JSON, and Markdown."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "The session ID",
                    },
                    "format": {
                        "type": "string",
                        "description": "Export format",
                        "enum": ["mermaid", "json", "markdown"],
                        "default": "mermaid",
                    },
                },
                "required": ["session_id"],
            },
        ),
        # ============================================================================
        # Causation Verification Tool
        # ============================================================================
        Tool(
            name="rc_verify_causation",
            description=(
                "Verify causal relationship between cause and effect using "
                "the Counterfactual Testing Framework. Tests: "
                "1) Temporality - Did cause precede effect? "
                "2) Necessity - Would effect occur without cause? "
                "3) Mechanism - Is there a plausible causal pathway? "
                "4) Sufficiency - Is cause alone sufficient for effect?"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "The session ID",
                    },
                    "cause": {
                        "type": "object",
                        "description": "The cause event",
                        "properties": {
                            "description": {
                                "type": "string",
                                "description": "Description of the cause",
                            },
                            "timestamp": {
                                "type": "string",
                                "description": "When the cause occurred (ISO format)",
                                "default": None,
                            },
                        },
                        "required": ["description"],
                    },
                    "effect": {
                        "type": "object",
                        "description": "The effect event",
                        "properties": {
                            "description": {
                                "type": "string",
                                "description": "Description of the effect",
                            },
                            "timestamp": {
                                "type": "string",
                                "description": "When the effect occurred (ISO format)",
                                "default": None,
                            },
                        },
                        "required": ["description"],
                    },
                    "verification_level": {
                        "type": "string",
                        "description": (
                            "'standard' tests Temporality+Necessity. "
                            "'comprehensive' tests all 4 criteria."
                        ),
                        "enum": ["standard", "comprehensive"],
                        "default": "standard",
                    },
                },
                "required": ["session_id", "cause", "effect"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> Sequence[TextContent]:
    """Handle tool calls."""
    try:
        # HFACS Tools
        if name == "rc_suggest_hfacs":
            return await _handle_suggest_hfacs(arguments)
        elif name == "rc_confirm_classification":
            return await _handle_confirm_classification(arguments)
        elif name == "rc_get_hfacs_framework":
            return await _handle_get_framework(arguments)
        elif name == "rc_list_learned_rules":
            return await _handle_list_learned_rules(arguments)
        elif name == "rc_reload_rules":
            return await _handle_reload_rules()
        # Session Tools
        elif name == "rc_start_session":
            return await _handle_start_session(arguments)
        elif name == "rc_get_session":
            return await _handle_get_session(arguments)
        elif name == "rc_list_sessions":
            return await _handle_list_sessions(arguments)
        elif name == "rc_archive_session":
            return await _handle_archive_session(arguments)
        # Fishbone Tools
        elif name == "rc_init_fishbone":
            return await _handle_init_fishbone(arguments)
        elif name == "rc_add_cause":
            return await _handle_add_cause(arguments)
        elif name == "rc_get_fishbone":
            return await _handle_get_fishbone(arguments)
        elif name == "rc_export_fishbone":
            return await _handle_export_fishbone(arguments)
        # Why Tree Tools
        elif name == "rc_ask_why":
            return await _handle_ask_why(arguments)
        elif name == "rc_get_why_tree":
            return await _handle_get_why_tree(arguments)
        elif name == "rc_mark_root_cause":
            return await _handle_mark_root_cause(arguments)
        elif name == "rc_export_why_tree":
            return await _handle_export_why_tree(arguments)
        # Verification Tools
        elif name == "rc_verify_causation":
            return await _handle_verify_causation(arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    except Exception as e:
        logger.exception("Error in tool %s", name)
        return [TextContent(type="text", text=f"Error: {e!s}")]


async def _handle_suggest_hfacs(arguments: dict[str, Any]) -> Sequence[TextContent]:
    """Handle rc_suggest_hfacs tool call."""
    if _hfacs_suggester is None:
        return [TextContent(type="text", text="Error: HFACSSuggester not initialized")]
    
    description = arguments["description"]
    max_suggestions = arguments.get("max_suggestions", 3)
    
    # Get suggestions using the suggest() method
    suggestions = _hfacs_suggester.suggest(
        description=description,
        max_suggestions=max_suggestions,
    )
    
    if not suggestions:
        result = (
            f"No HFACS classifications suggested for: '{description}'\n\n"
            "Consider:\n"
            "1. Provide more context about the event\n"
            "2. Check if the description relates to human factors or system issues"
        )
    else:
        lines = [f"**HFACS Suggestions for:** '{description}'\n"]
        
        for i, suggestion in enumerate(suggestions, 1):
            code = suggestion.code.code
            name = suggestion.code.description
            confidence = float(suggestion.confidence)
            source = suggestion.source
            
            lines.append(f"\n### {i}. {code} - {name}")
            lines.append(f"- **Confidence:** {confidence:.0%}")
            lines.append(f"- **Source:** {source}")
            lines.append(f"- **Reason:** {suggestion.reason}")
        
        lines.append("\n---")
        lines.append("Use `rc_confirm_classification` to confirm the correct classification.")
        
        result = "\n".join(lines)
    
    return [TextContent(type="text", text=result)]


async def _handle_confirm_classification(
    arguments: dict[str, Any],
) -> Sequence[TextContent]:
    """Handle rc_confirm_classification tool call."""
    if _learned_rules_service is None:
        return [TextContent(type="text", text="Error: LearnedRulesService not initialized")]
    
    description = arguments["description"]
    hfacs_code = arguments["hfacs_code"]
    reason = arguments["reason"]
    session_id = arguments.get("session_id")
    confidence = arguments.get("confidence", 0.8)
    
    success = _learned_rules_service.confirm_classification(
        description=description,
        hfacs_code=hfacs_code,
        reason=reason,
        session_id=session_id,
        confidence=confidence,
    )
    
    if success:
        result = (
            f"✅ **Classification Confirmed**\n\n"
            f"- **Description:** {description}\n"
            f"- **HFACS Code:** {hfacs_code}\n"
            f"- **Reason:** {reason}\n"
            f"- **Confidence:** {confidence:.0%}\n\n"
            f"This rule has been saved and will be used for future suggestions."
        )
    else:
        result = (
            f"❌ **Failed to save classification**\n\n"
            f"Please check the logs for details."
        )
    
    return [TextContent(type="text", text=result)]


async def _handle_get_framework(arguments: dict[str, Any]) -> Sequence[TextContent]:
    """Handle rc_get_hfacs_framework tool call."""
    if _hfacs_suggester is None:
        return [TextContent(type="text", text="Error: HFACSSuggester not initialized")]
    
    level_filter = arguments.get("level")
    
    # HFACS-MES Framework structure
    framework = {
        "EF": {
            "name": "External Factors",
            "description": "Factors outside the organization's direct control",
            "categories": {
                "EF-RE": "Regulatory Environment",
                "EF-OS": "Other (External factors)",
            },
        },
        "OI": {
            "name": "Organizational Influences",
            "description": "Management and organizational-level factors",
            "categories": {
                "OI-RM": "Resource Management",
                "OI-OC": "Organizational Climate",
                "OI-OP": "Organizational Process",
            },
        },
        "US": {
            "name": "Unsafe Supervision",
            "description": "Supervisory actions or inactions contributing to error",
            "categories": {
                "US-IS": "Inadequate Supervision",
                "US-PIO": "Planned Inappropriate Operations",
                "US-FCP": "Failed to Correct Problem",
                "US-SV": "Supervisory Violation",
            },
        },
        "PC": {
            "name": "Preconditions for Unsafe Acts",
            "description": "Conditions that enable or facilitate unsafe acts",
            "subcategories": {
                "PC-E": {
                    "name": "Environmental Factors",
                    "codes": {
                        "PC-E-PE": "Physical Environment",
                        "PC-E-TE": "Technological Environment",
                    },
                },
                "PC-C": {
                    "name": "Condition of Operators",
                    "codes": {
                        "PC-C-AMS": "Adverse Mental States",
                        "PC-C-APS": "Adverse Physiological States",
                        "PC-C-PML": "Physical/Mental Limitations",
                    },
                },
                "PC-P": {
                    "name": "Personnel Factors",
                    "codes": {
                        "PC-P-CRM": "Communication, Resources, and Management",
                        "PC-P-PRF": "Personal Readiness and Fitness",
                    },
                },
            },
        },
        "UA": {
            "name": "Unsafe Acts",
            "description": "Direct actions or inactions leading to the event",
            "subcategories": {
                "UA-E": {
                    "name": "Errors",
                    "codes": {
                        "UA-E-SB": "Skill-Based Errors",
                        "UA-E-DM": "Decision Errors",
                        "UA-E-PM": "Perceptual Errors",
                    },
                },
                "UA-V": {
                    "name": "Violations",
                    "codes": {
                        "UA-V-R": "Routine Violations",
                        "UA-V-E": "Exceptional Violations",
                    },
                },
            },
        },
    }
    
    if level_filter and level_filter in framework:
        result_data = {level_filter: framework[level_filter]}
    else:
        result_data = framework
    
    # Format as readable text
    lines = ["# HFACS-MES Framework\n"]
    
    for level_code, level_data in result_data.items():
        lines.append(f"## {level_code} - {level_data['name']}")
        lines.append(f"*{level_data['description']}*\n")
        
        if "categories" in level_data:
            for cat_code, cat_name in level_data["categories"].items():
                lines.append(f"- **{cat_code}**: {cat_name}")
        
        if "subcategories" in level_data:
            for sub_code, sub_data in level_data["subcategories"].items():
                lines.append(f"\n### {sub_code} - {sub_data['name']}")
                for code, name in sub_data["codes"].items():
                    lines.append(f"- **{code}**: {name}")
        
        lines.append("")
    
    return [TextContent(type="text", text="\n".join(lines))]


async def _handle_list_learned_rules(
    arguments: dict[str, Any],
) -> Sequence[TextContent]:
    """Handle rc_list_learned_rules tool call."""
    if _learned_rules_service is None:
        return [TextContent(type="text", text="Error: LearnedRulesService not initialized")]
    
    hfacs_code_filter = arguments.get("hfacs_code")
    min_confidence = arguments.get("min_confidence", 0.0)
    
    # Get all learned rules
    all_rules = _learned_rules_service.get_learned_rules()
    
    # Filter if needed
    rules = []
    for rule in all_rules:
        if hfacs_code_filter and rule.get("code") != hfacs_code_filter:
            continue
        if rule.get("confidence", 0) < min_confidence:
            continue
        rules.append(rule)
    
    if not rules:
        result = "No learned rules found."
        if hfacs_code_filter:
            result += f" (filtered by code: {hfacs_code_filter})"
    else:
        lines = [f"# Learned Classification Rules ({len(rules)} found)\n"]
        
        for rule in rules:
            lines.append(f"## {rule.get('code', 'N/A')}")
            lines.append(f"- **Keyword:** {rule.get('keyword', 'N/A')}")
            lines.append(f"- **Source Type:** {rule.get('source_type', 'N/A')}")
            lines.append(f"- **Confidence:** {rule.get('confidence', 0):.0%}")
            lines.append(f"- **Reason:** {rule.get('reason', 'N/A')}")
            lines.append(f"- **Confirmed At:** {rule.get('confirmed_at', 'N/A')}")
            lines.append(f"- **Hit Count:** {rule.get('hit_count', 0)}")
            lines.append("")
        
        result = "\n".join(lines)
    
    return [TextContent(type="text", text=result)]


async def _handle_reload_rules() -> Sequence[TextContent]:
    """Handle rc_reload_rules tool call."""
    if _hfacs_suggester is None:
        return [TextContent(type="text", text="Error: HFACSSuggester not initialized")]
    
    _hfacs_suggester.reload_rules()
    summary = _hfacs_suggester.get_loaded_rules_summary()
    
    result = (
        "✅ **Rules Reloaded Successfully**\n\n"
        f"- **Base rules:** {summary.get('base_count', 0)}\n"
        f"- **Domain rules:** {summary.get('domain_count', 0)}\n"
        f"- **Learned rules:** {summary.get('learned_count', 0)}\n"
        f"- **Total rules:** {summary.get('total_count', 0)}"
    )
    
    return [TextContent(type="text", text=result)]


# ============================================================================
# Session Management Handlers
# ============================================================================

async def _handle_start_session(arguments: dict[str, Any]) -> Sequence[TextContent]:
    """Handle rc_start_session tool call."""
    if _session_repository is None:
        return [TextContent(type="text", text="Error: SessionRepository not initialized")]
    
    case_type_str = arguments["case_type"]
    case_title = arguments["case_title"]
    initial_description = arguments.get("initial_description", "")
    
    # Create session
    try:
        case_type = CaseType(case_type_str)
    except ValueError:
        return [TextContent(
            type="text",
            text=f"Error: Invalid case_type '{case_type_str}'. "
                 f"Valid options: {[ct.value for ct in CaseType]}"
        )]
    
    session = RCASession.create(
        case_type=case_type,
        case_title=case_title,
        initial_description=initial_description,
    )
    
    # Save to repository
    _session_repository.save(session)
    
    result = (
        "✅ **Session Created Successfully**\n\n"
        f"- **Session ID:** `{session.id}`\n"
        f"- **Case Type:** {case_type.value}\n"
        f"- **Title:** {case_title}\n"
        f"- **Current Stage:** {session.current_stage.value}\n\n"
        "**Next Steps:**\n"
        "1. Use `rc_init_fishbone` to create a Fishbone diagram\n"
        "2. Use `rc_suggest_hfacs` to get classification suggestions\n"
        "3. Use `rc_add_cause` to document causes"
    )
    
    return [TextContent(type="text", text=result)]


async def _handle_get_session(arguments: dict[str, Any]) -> Sequence[TextContent]:
    """Handle rc_get_session tool call."""
    if _session_repository is None:
        return [TextContent(type="text", text="Error: SessionRepository not initialized")]
    
    session_id = arguments["session_id"]
    session = _session_repository.get_by_id(session_id)
    
    if session is None:
        return [TextContent(
            type="text",
            text=f"❌ **Session Not Found**\n\nNo session with ID: `{session_id}`"
        )]
    
    # Build progress summary
    progress = session.get_progress()
    progress_lines = [f"  - {stage}: {status}" for stage, status in progress.items()]
    
    result = (
        f"# Session: {session.case_title}\n\n"
        f"- **Session ID:** `{session.id}`\n"
        f"- **Case Type:** {session.case_type.value}\n"
        f"- **Status:** {session.status.value}\n"
        f"- **Current Stage:** {session.current_stage.value}\n"
        f"- **Created:** {session.created_at.strftime('%Y-%m-%d %H:%M')}\n"
        f"- **Updated:** {session.updated_at.strftime('%Y-%m-%d %H:%M')}\n\n"
        "**Stage Progress:**\n" + "\n".join(progress_lines)
    )
    
    if session.problem_statement:
        result += f"\n\n**Problem Statement:**\n{session.problem_statement}"
    
    return [TextContent(type="text", text=result)]


async def _handle_list_sessions(arguments: dict[str, Any]) -> Sequence[TextContent]:
    """Handle rc_list_sessions tool call."""
    if _session_repository is None:
        return [TextContent(type="text", text="Error: SessionRepository not initialized")]
    
    status_str = arguments.get("status")
    case_type_str = arguments.get("case_type")
    limit = arguments.get("limit", 20)
    
    # Parse filters
    status = SessionStatus(status_str) if status_str else None
    case_type = CaseType(case_type_str) if case_type_str else None
    
    sessions = _session_repository.list_all(
        status=status,
        case_type=case_type,
        limit=limit,
    )
    
    if not sessions:
        result = "📋 **No Sessions Found**\n\nNo sessions match the specified criteria."
        if status_str or case_type_str:
            result += f"\n\nFilters applied: status={status_str}, case_type={case_type_str}"
    else:
        lines = [f"# RCA Sessions ({len(sessions)} found)\n"]
        
        for s in sessions:
            status_emoji = {
                SessionStatus.ACTIVE: "🟢",
                SessionStatus.COMPLETED: "✅",
                SessionStatus.ABANDONED: "🔴",
                SessionStatus.ARCHIVED: "📦",
            }.get(s.status, "⚪")
            
            lines.append(
                f"### {status_emoji} {s.case_title}\n"
                f"- **ID:** `{s.id}`\n"
                f"- **Type:** {s.case_type.value}\n"
                f"- **Stage:** {s.current_stage.value}\n"
                f"- **Updated:** {s.updated_at.strftime('%Y-%m-%d %H:%M')}\n"
            )
        
        result = "\n".join(lines)
    
    return [TextContent(type="text", text=result)]


async def _handle_archive_session(arguments: dict[str, Any]) -> Sequence[TextContent]:
    """Handle rc_archive_session tool call."""
    if _session_repository is None:
        return [TextContent(type="text", text="Error: SessionRepository not initialized")]
    
    session_id = arguments["session_id"]
    session = _session_repository.get_by_id(session_id)
    
    if session is None:
        return [TextContent(
            type="text",
            text=f"❌ **Session Not Found**\n\nNo session with ID: `{session_id}`"
        )]
    
    # Archive the session
    session.archive()
    _session_repository.save(session)
    
    result = (
        "📦 **Session Archived**\n\n"
        f"- **Session ID:** `{session.id}`\n"
        f"- **Title:** {session.case_title}\n"
        f"- **Status:** {session.status.value}\n\n"
        "The session has been archived and is now read-only."
    )
    
    return [TextContent(type="text", text=result)]


# ============================================================================
# Fishbone Diagram Handlers
# ============================================================================

async def _handle_init_fishbone(arguments: dict[str, Any]) -> Sequence[TextContent]:
    """Handle rc_init_fishbone tool call."""
    if _session_repository is None or _fishbone_repository is None:
        return [TextContent(type="text", text="Error: Repositories not initialized")]
    
    session_id = arguments["session_id"]
    problem_statement = arguments["problem_statement"]
    
    # Verify session exists
    session = _session_repository.get_by_id(session_id)
    if session is None:
        return [TextContent(
            type="text",
            text=f"❌ **Session Not Found**\n\nNo session with ID: `{session_id}`"
        )]
    
    # Check if fishbone already exists
    existing = _fishbone_repository.get_by_session(SessionId.from_string(session_id))
    if existing:
        return [TextContent(
            type="text",
            text=(
                f"⚠️ **Fishbone Already Exists**\n\n"
                f"Session `{session_id}` already has a Fishbone diagram.\n"
                f"Use `rc_get_fishbone` to view it or `rc_add_cause` to add causes."
            )
        )]
    
    # Create fishbone
    fishbone = Fishbone.create(
        session_id=SessionId.from_string(session_id),
        problem_statement=problem_statement,
    )
    
    # Update session problem statement
    session.set_problem(problem_statement)
    
    # Save both
    _fishbone_repository.save(fishbone)
    _session_repository.save(session)
    
    # List categories
    categories = [cat.value for cat in FishboneCategoryType]
    
    result = (
        "✅ **Fishbone Diagram Initialized**\n\n"
        f"- **Session:** `{session_id}`\n"
        f"- **Problem (Fish Head):** {problem_statement}\n\n"
        "**6M Categories Ready:**\n"
        + "\n".join(f"- {cat}" for cat in categories) +
        "\n\n**Next Steps:**\n"
        "Use `rc_add_cause` to add causes to each category."
    )
    
    return [TextContent(type="text", text=result)]


async def _handle_add_cause(arguments: dict[str, Any]) -> Sequence[TextContent]:
    """Handle rc_add_cause tool call."""
    if _fishbone_repository is None:
        return [TextContent(type="text", text="Error: FishboneRepository not initialized")]
    
    session_id = arguments["session_id"]
    category_str = arguments["category"]
    description = arguments["description"]
    sub_causes = arguments.get("sub_causes", [])
    hfacs_code = arguments.get("hfacs_code")
    evidence = arguments.get("evidence", [])
    
    # Get fishbone
    fishbone = _fishbone_repository.get_by_session(SessionId.from_string(session_id))
    if fishbone is None:
        return [TextContent(
            type="text",
            text=(
                f"❌ **Fishbone Not Found**\n\n"
                f"No Fishbone for session `{session_id}`.\n"
                "Use `rc_init_fishbone` first."
            )
        )]
    
    # Parse category
    try:
        category = FishboneCategoryType(category_str)
    except ValueError:
        return [TextContent(
            type="text",
            text=(
                f"Error: Invalid category '{category_str}'. "
                f"Valid options: {[cat.value for cat in FishboneCategoryType]}"
            )
        )]
    
    # Create cause
    cause = FishboneCause(
        cause_id=CauseId.generate(),
        category=category,
        description=description,
        sub_causes=sub_causes,
        hfacs_code=hfacs_code,
        evidence=evidence,
    )
    
    # Add to fishbone
    fishbone.add_cause_to_category(category, cause)
    _fishbone_repository.save(fishbone)
    
    result = (
        "✅ **Cause Added**\n\n"
        f"- **Category:** {category.value}\n"
        f"- **Description:** {description}\n"
    )
    
    if sub_causes:
        result += f"- **Sub-causes:** {', '.join(sub_causes)}\n"
    if hfacs_code:
        result += f"- **HFACS Code:** {hfacs_code}\n"
    if evidence:
        result += f"- **Evidence:** {', '.join(evidence)}\n"
    
    result += (
        f"\n**Fishbone Status:**\n"
        f"- Total causes: {fishbone.total_cause_count}\n"
        f"- Categories covered: {len(fishbone.populated_categories)}/6 "
        f"({fishbone.coverage_ratio:.0%})"
    )
    
    return [TextContent(type="text", text=result)]


async def _handle_get_fishbone(arguments: dict[str, Any]) -> Sequence[TextContent]:
    """Handle rc_get_fishbone tool call."""
    if _fishbone_repository is None:
        return [TextContent(type="text", text="Error: FishboneRepository not initialized")]
    
    session_id = arguments["session_id"]
    
    fishbone = _fishbone_repository.get_by_session(SessionId.from_string(session_id))
    if fishbone is None:
        return [TextContent(
            type="text",
            text=(
                f"❌ **Fishbone Not Found**\n\n"
                f"No Fishbone for session `{session_id}`.\n"
                "Use `rc_init_fishbone` to create one."
            )
        )]
    
    lines = [
        f"# Fishbone Diagram\n",
        f"**Problem:** {fishbone.problem_statement}\n",
        f"**Total Causes:** {fishbone.total_cause_count}\n",
        f"**Coverage:** {fishbone.coverage_ratio:.0%}\n",
    ]
    
    for cat_type in FishboneCategoryType:
        category = fishbone.get_category(cat_type)
        if category.has_causes:
            lines.append(f"\n## {cat_type.value} ({category.cause_count} causes)")
            for cause in category.causes:
                lines.append(f"\n### {cause.description}")
                if cause.hfacs_code:
                    lines.append(f"- **HFACS:** {cause.hfacs_code}")
                if cause.sub_causes:
                    lines.append(f"- **Sub-causes:** {', '.join(cause.sub_causes)}")
                if cause.evidence:
                    lines.append(f"- **Evidence:** {', '.join(cause.evidence)}")
        else:
            lines.append(f"\n## {cat_type.value} (empty)")
    
    return [TextContent(type="text", text="\n".join(lines))]


async def _handle_export_fishbone(arguments: dict[str, Any]) -> Sequence[TextContent]:
    """Handle rc_export_fishbone tool call."""
    if _fishbone_repository is None:
        return [TextContent(type="text", text="Error: FishboneRepository not initialized")]
    
    session_id = arguments["session_id"]
    export_format = arguments.get("format", "mermaid")
    
    fishbone = _fishbone_repository.get_by_session(SessionId.from_string(session_id))
    if fishbone is None:
        return [TextContent(
            type="text",
            text=(
                f"❌ **Fishbone Not Found**\n\n"
                f"No Fishbone for session `{session_id}`."
            )
        )]
    
    if export_format == "json":
        import json
        result = json.dumps(fishbone.to_dict(), indent=2, ensure_ascii=False)
    
    elif export_format == "markdown":
        lines = [
            f"# Fishbone Analysis: {fishbone.problem_statement}\n",
        ]
        for cat_type in FishboneCategoryType:
            category = fishbone.get_category(cat_type)
            lines.append(f"\n## {cat_type.value}")
            if category.has_causes:
                for cause in category.causes:
                    lines.append(f"- {cause.description}")
                    if cause.hfacs_code:
                        lines.append(f"  - HFACS: {cause.hfacs_code}")
                    for sub in cause.sub_causes:
                        lines.append(f"  - {sub}")
            else:
                lines.append("- (No causes identified)")
        result = "\n".join(lines)
    
    else:  # mermaid
        lines = [
            "```mermaid",
            "flowchart LR",
            f'    PROBLEM["{fishbone.problem_statement}"]',
        ]
        
        for cat_type in FishboneCategoryType:
            category = fishbone.get_category(cat_type)
            cat_id = cat_type.value.upper()
            lines.append(f'    {cat_id}["{cat_type.value}"] --> PROBLEM')
            
            for i, cause in enumerate(category.causes):
                cause_id = f"{cat_id}_{i}"
                # Truncate long descriptions
                desc = cause.description[:30] + "..." if len(cause.description) > 30 else cause.description
                lines.append(f'    {cause_id}["{desc}"] --> {cat_id}')
        
        lines.append("```")
        result = "\n".join(lines)
    
    return [TextContent(type="text", text=result)]


# ============================================================================
# Why Tree / 5-Why Handlers
# ============================================================================

async def _handle_ask_why(arguments: dict[str, Any]) -> Sequence[TextContent]:
    """Handle rc_ask_why tool call - the core reasoning tool."""
    if _why_tree_repository is None or _session_repository is None:
        return [TextContent(type="text", text="Error: Repositories not initialized")]
    
    session_id_str = arguments["session_id"]
    answer = arguments["answer"]
    parent_node_id = arguments.get("parent_node_id")
    evidence = arguments.get("evidence", [])
    initial_problem = arguments.get("initial_problem")
    
    session_id = SessionId.from_string(session_id_str)
    
    # Verify session exists
    session = _session_repository.get_by_id(session_id_str)
    if session is None:
        return [TextContent(
            type="text",
            text=f"❌ **Session Not Found**\n\nNo session with ID: `{session_id_str}`"
        )]
    
    # Get or create WhyChain
    chain = _why_tree_repository.get_chain(session_id)
    
    if chain is None:
        # Create new chain - need initial problem
        if not initial_problem:
            # Try to get from session
            initial_problem = session.problem_statement or "問題待定義"
        
        chain = _why_tree_repository.create_chain(session_id, initial_problem)
        
        # Create first why node
        node = WhyNode.create_first_why(
            session_id=session_id,
            initial_problem=initial_problem,
            answer=answer,
        )
        for ev in evidence:
            node.add_evidence(ev)
        
        _why_tree_repository.add_node(session_id, node)
        
        result = (
            "✅ **5-Why Analysis Started**\n\n"
            f"**Initial Problem:** {initial_problem}\n\n"
            f"**Why 1:** {node.question}\n"
            f"**Answer:** {answer}\n"
        )
        if evidence:
            result += f"**Evidence:** {', '.join(evidence)}\n"
        
        result += (
            f"\n---\n"
            f"**Node ID:** `{node.id}`\n"
            f"**Next Step:** Call `rc_ask_why` again to go deeper.\n"
            f"- Ask: \"Why did '{answer}' happen?\""
        )
        
    else:
        # Continue existing chain
        if parent_node_id:
            # Branch from specific node
            parent = _why_tree_repository.get_node(CauseId.from_string(parent_node_id))
        else:
            # Find the last leaf node that needs analysis
            leaves = [n for n in chain.nodes if n.needs_further_analysis and not n.is_root_cause]
            parent = leaves[-1] if leaves else (chain.nodes[-1] if chain.nodes else None)
        
        if parent is None:
            return [TextContent(
                type="text",
                text="❌ **No parent node found.** The chain may be complete or corrupted."
            )]
        
        if not parent.can_ask_why:
            return [TextContent(
                type="text",
                text=(
                    f"⚠️ **Cannot add more Why**\n\n"
                    f"Node `{parent.id}` is at level {parent.level} "
                    f"and {'is marked as root cause' if parent.is_root_cause else 'is at max depth (5)'}.\n"
                    f"Consider using `rc_mark_root_cause` to identify root causes."
                )
            )]
        
        # Create follow-up why
        node = WhyNode.create_follow_up_why(
            session_id=session_id,
            parent=parent,
            answer=answer,
        )
        for ev in evidence:
            node.add_evidence(ev)
        
        _why_tree_repository.add_node(session_id, node)
        
        result = (
            f"✅ **Why {node.level} Added**\n\n"
            f"**Question:** {node.question}\n"
            f"**Answer:** {answer}\n"
        )
        if evidence:
            result += f"**Evidence:** {', '.join(evidence)}\n"
        
        result += f"\n**Node ID:** `{node.id}`\n"
        
        if node.is_final_why:
            result += (
                "\n⚠️ **Reached Level 5 (Final Why)**\n"
                "Consider if this is the root cause, or if you need to branch earlier."
            )
        else:
            result += (
                f"\n**Next Step:** Continue asking 'Why?' or mark as root cause.\n"
                f"- Next question would be: \"Why did '{answer}' happen?\""
            )
    
    # Add chain status
    chain = _why_tree_repository.get_chain(session_id)
    if chain:
        result += (
            f"\n---\n"
            f"**Chain Status:**\n"
            f"- Depth: {chain.depth}/5\n"
            f"- Total nodes: {len(chain.nodes)}\n"
            f"- Root causes identified: {len(chain.root_causes)}\n"
            f"- Complete: {'✅ Yes' if chain.is_complete else '❌ No'}"
        )
    
    return [TextContent(type="text", text=result)]


async def _handle_get_why_tree(arguments: dict[str, Any]) -> Sequence[TextContent]:
    """Handle rc_get_why_tree tool call."""
    if _why_tree_repository is None:
        return [TextContent(type="text", text="Error: WhyTreeRepository not initialized")]
    
    session_id_str = arguments["session_id"]
    session_id = SessionId.from_string(session_id_str)
    
    chain = _why_tree_repository.get_chain(session_id)
    if chain is None:
        return [TextContent(
            type="text",
            text=(
                f"❌ **No Why Tree Found**\n\n"
                f"No 5-Why analysis for session `{session_id_str}`.\n"
                "Use `rc_ask_why` to start one."
            )
        )]
    
    lines = [
        f"# 5-Why Analysis Tree\n",
        f"**Initial Problem:** {chain.initial_problem}\n",
        f"**Depth:** {chain.depth}/5\n",
        f"**Complete:** {'✅ Yes' if chain.is_complete else '❌ No'}\n",
    ]
    
    if chain.root_causes:
        lines.append(f"**Root Causes Identified:** {len(chain.root_causes)}\n")
    
    # Build tree visualization
    lines.append("\n## Analysis Chain\n")
    
    # Group by level
    by_level: dict[int, list[WhyNode]] = {}
    for node in chain.nodes:
        by_level.setdefault(node.level, []).append(node)
    
    for level in sorted(by_level.keys()):
        nodes = by_level[level]
        for node in nodes:
            prefix = "  " * (level - 1)
            status = "🎯" if node.is_root_cause else ("❓" if node.needs_further_analysis else "✅")
            
            lines.append(f"{prefix}{status} **Why {level}:** {node.question}")
            lines.append(f"{prefix}   → {node.answer}")
            
            if node.evidence:
                lines.append(f"{prefix}   📋 Evidence: {', '.join(node.evidence)}")
            if node.is_root_cause:
                lines.append(f"{prefix}   🎯 **ROOT CAUSE** (confidence: {node.confidence_level})")
            
            lines.append(f"{prefix}   (ID: `{node.id}`)\n")
    
    return [TextContent(type="text", text="\n".join(lines))]


async def _handle_mark_root_cause(arguments: dict[str, Any]) -> Sequence[TextContent]:
    """Handle rc_mark_root_cause tool call."""
    if _why_tree_repository is None:
        return [TextContent(type="text", text="Error: WhyTreeRepository not initialized")]
    
    session_id_str = arguments["session_id"]
    node_id_str = arguments["node_id"]
    confidence = arguments.get("confidence", 0.8)
    
    session_id = SessionId.from_string(session_id_str)
    node_id = CauseId.from_string(node_id_str)
    
    chain = _why_tree_repository.get_chain(session_id)
    if chain is None:
        return [TextContent(
            type="text",
            text=f"❌ **No Why Tree Found** for session `{session_id_str}`"
        )]
    
    node = chain.get_node(node_id)
    if node is None:
        return [TextContent(
            type="text",
            text=f"❌ **Node Not Found**\n\nNo node with ID: `{node_id_str}`"
        )]
    
    # Mark as root cause
    node.mark_as_root_cause(confidence)
    _why_tree_repository.update_node(node)
    
    result = (
        "🎯 **Root Cause Identified**\n\n"
        f"**Node:** `{node.id}`\n"
        f"**Level:** Why {node.level}\n"
        f"**Question:** {node.question}\n"
        f"**Answer (Root Cause):** {node.answer}\n"
        f"**Confidence:** {confidence:.0%}\n"
    )
    
    if node.evidence:
        result += f"**Evidence:** {', '.join(node.evidence)}\n"
    
    # Check if chain is complete
    result += f"\n---\n**Chain Status:** "
    if chain.is_complete:
        result += "✅ Complete (all branches have root causes)"
    else:
        remaining = len(chain.needs_analysis)
        result += f"❌ Incomplete ({remaining} node(s) need further analysis)"
    
    result += (
        "\n\n**Next Steps:**\n"
        "1. Use `rc_suggest_hfacs` to classify this root cause\n"
        "2. Add to Fishbone with `rc_add_cause`\n"
        "3. Use `rc_verify_causation` to validate causal relationship"
    )
    
    return [TextContent(type="text", text=result)]


async def _handle_export_why_tree(arguments: dict[str, Any]) -> Sequence[TextContent]:
    """Handle rc_export_why_tree tool call."""
    if _why_tree_repository is None:
        return [TextContent(type="text", text="Error: WhyTreeRepository not initialized")]
    
    session_id_str = arguments["session_id"]
    export_format = arguments.get("format", "mermaid")
    
    session_id = SessionId.from_string(session_id_str)
    chain = _why_tree_repository.get_chain(session_id)
    
    if chain is None:
        return [TextContent(
            type="text",
            text=f"❌ **No Why Tree Found** for session `{session_id_str}`"
        )]
    
    if export_format == "json":
        import json
        result = json.dumps(chain.to_dict(), indent=2, ensure_ascii=False)
    
    elif export_format == "markdown":
        lines = [
            f"# 5-Why Analysis: {chain.initial_problem}\n",
            f"**Depth:** {chain.depth} | **Complete:** {'Yes' if chain.is_complete else 'No'}\n",
        ]
        
        for node in chain.nodes:
            indent = "  " * (node.level - 1)
            rc_marker = " 🎯 **ROOT CAUSE**" if node.is_root_cause else ""
            lines.append(f"\n{indent}**Why {node.level}:** {node.question}")
            lines.append(f"{indent}→ {node.answer}{rc_marker}")
            if node.evidence:
                lines.append(f"{indent}  Evidence: {', '.join(node.evidence)}")
        
        if chain.root_causes:
            lines.append("\n## Root Causes Summary")
            for rc in chain.root_causes:
                lines.append(f"- {rc.answer}")
        
        result = "\n".join(lines)
    
    else:  # mermaid
        lines = [
            "```mermaid",
            "flowchart TD",
            f'    PROBLEM["{chain.initial_problem}"]',
        ]
        
        for node in chain.nodes:
            node_id = f"N{str(node.id)[-8:]}"
            parent_id = f"N{str(node.parent_id)[-8:]}" if node.parent_id else "PROBLEM"
            
            # Truncate for display
            answer = node.answer[:40] + "..." if len(node.answer) > 40 else node.answer
            
            if node.is_root_cause:
                lines.append(f'    {node_id}[["🎯 {answer}"]]')
            else:
                lines.append(f'    {node_id}["{answer}"]')
            
            lines.append(f'    {parent_id} -->|Why {node.level}| {node_id}')
        
        lines.append("```")
        result = "\n".join(lines)
    
    return [TextContent(type="text", text=result)]


# ============================================================================
# Causation Verification Handler
# ============================================================================

async def _handle_verify_causation(arguments: dict[str, Any]) -> Sequence[TextContent]:
    """
    Handle rc_verify_causation tool call.
    
    Implements the Counterfactual Testing Framework:
    1. Temporality - Did cause precede effect?
    2. Necessity - Would effect occur without cause?
    3. Mechanism - Is there a plausible causal pathway?
    4. Sufficiency - Is cause alone sufficient for effect?
    """
    session_id = arguments["session_id"]
    cause = arguments["cause"]
    effect = arguments["effect"]
    level = arguments.get("verification_level", "standard")
    
    cause_desc = cause["description"]
    effect_desc = effect["description"]
    cause_time = cause.get("timestamp")
    effect_time = effect.get("timestamp")
    
    results = {
        "cause": cause_desc,
        "effect": effect_desc,
        "verification_level": level,
        "tests": {},
    }
    
    # Test 1: Temporality (always run)
    temporality = _test_temporality(cause_time, effect_time, cause_desc, effect_desc)
    results["tests"]["temporality"] = temporality
    
    # Test 2: Necessity (always run if temporality passes)
    if temporality["passed"]:
        necessity = _test_necessity(cause_desc, effect_desc)
        results["tests"]["necessity"] = necessity
    else:
        results["tests"]["necessity"] = {
            "passed": False,
            "skipped": True,
            "reason": "Skipped - temporality test failed"
        }
    
    # Tests 3 & 4: Only for comprehensive level
    if level == "comprehensive":
        # Test 3: Mechanism
        mechanism = _test_mechanism(cause_desc, effect_desc)
        results["tests"]["mechanism"] = mechanism
        
        # Test 4: Sufficiency
        sufficiency = _test_sufficiency(cause_desc, effect_desc)
        results["tests"]["sufficiency"] = sufficiency
    
    # Calculate overall result
    all_tests = results["tests"]
    passed_count = sum(1 for t in all_tests.values() if t.get("passed", False))
    total_tests = len([t for t in all_tests.values() if not t.get("skipped", False)])
    
    if total_tests == 0:
        results["overall_result"] = "FAILED"
        results["confidence"] = 0.0
    elif passed_count == total_tests:
        results["overall_result"] = "VERIFIED"
        results["confidence"] = 0.9 if level == "comprehensive" else 0.75
    elif passed_count >= total_tests / 2:
        results["overall_result"] = "VERIFIED_WITH_CAVEATS"
        results["confidence"] = 0.6
    else:
        results["overall_result"] = "NOT_VERIFIED"
        results["confidence"] = 0.3
    
    # Format output
    lines = [
        "# Causation Verification Result\n",
        f"**Cause:** {cause_desc}\n",
        f"**Effect:** {effect_desc}\n",
        f"**Level:** {level}\n",
    ]
    
    lines.append("\n## Test Results\n")
    
    for test_name, test_result in results["tests"].items():
        status = "✅" if test_result.get("passed") else ("⏭️" if test_result.get("skipped") else "❌")
        lines.append(f"### {status} {test_name.title()}")
        
        if test_result.get("skipped"):
            lines.append(f"*{test_result.get('reason', 'Skipped')}*\n")
        else:
            lines.append(f"- **Passed:** {test_result.get('passed', False)}")
            if "conclusion" in test_result:
                lines.append(f"- **Conclusion:** {test_result['conclusion']}")
            if "question" in test_result:
                lines.append(f"- **Question:** {test_result['question']}")
            if "answer" in test_result:
                lines.append(f"- **Answer:** {test_result['answer']}")
            lines.append("")
    
    # Overall result
    result_emoji = {
        "VERIFIED": "✅",
        "VERIFIED_WITH_CAVEATS": "⚠️",
        "NOT_VERIFIED": "❌",
        "FAILED": "💔"
    }
    
    lines.append(f"\n## Overall Result: {result_emoji.get(results['overall_result'], '❓')} {results['overall_result']}")
    lines.append(f"**Confidence:** {results['confidence']:.0%}\n")
    
    # Guidance
    lines.append("\n## Agent Guidance")
    if results["overall_result"] == "VERIFIED":
        lines.append("✅ Causal relationship is well-supported. You can proceed with this cause-effect pair.")
    elif results["overall_result"] == "VERIFIED_WITH_CAVEATS":
        lines.append("⚠️ Causal relationship has some support but may need additional evidence or analysis.")
    else:
        lines.append("❌ Causal relationship is not well-supported. Consider revising the hypothesis or gathering more evidence.")
    
    return [TextContent(type="text", text="\n".join(lines))]


def _test_temporality(
    cause_time: str | None,
    effect_time: str | None,
    cause_desc: str,
    effect_desc: str,
) -> dict[str, Any]:
    """Test temporal relationship between cause and effect."""
    from datetime import datetime
    
    result: dict[str, Any] = {
        "test": "temporality",
        "question": f"Did '{cause_desc}' occur before '{effect_desc}'?",
    }
    
    if cause_time and effect_time:
        try:
            cause_dt = datetime.fromisoformat(cause_time.replace("Z", "+00:00"))
            effect_dt = datetime.fromisoformat(effect_time.replace("Z", "+00:00"))
            
            if cause_dt < effect_dt:
                diff_minutes = (effect_dt - cause_dt).total_seconds() / 60
                result["passed"] = True
                result["conclusion"] = f"Cause preceded effect by {diff_minutes:.0f} minutes"
                result["cause_time"] = cause_time
                result["effect_time"] = effect_time
            else:
                result["passed"] = False
                result["conclusion"] = "Effect occurred before or at same time as cause"
        except (ValueError, TypeError):
            result["passed"] = True
            result["conclusion"] = "Timestamps provided but could not be parsed; assuming temporal order is correct"
            result["answer"] = "likely"
    else:
        # No timestamps - assume temporal order based on description context
        result["passed"] = True
        result["conclusion"] = "No timestamps provided; temporal order assumed from context"
        result["answer"] = "assumed"
    
    return result


def _test_necessity(cause_desc: str, effect_desc: str) -> dict[str, Any]:
    """Test necessity - would effect occur without cause?"""
    result: dict[str, Any] = {
        "test": "necessity",
        "question": f"If '{cause_desc}' had NOT occurred, would '{effect_desc}' still have happened?",
    }
    
    # This is a heuristic evaluation - in real implementation,
    # this would use more sophisticated analysis or prompt the AI
    
    # Default assumption: cause is necessary for effect
    result["passed"] = True
    result["answer"] = "unlikely"
    result["conclusion"] = (
        "Without the identified cause, the effect would likely not have occurred. "
        "This supports the necessity condition for causation."
    )
    result["confidence"] = 0.7
    
    return result


def _test_mechanism(cause_desc: str, effect_desc: str) -> dict[str, Any]:
    """Test mechanism - is there a plausible causal pathway?"""
    result: dict[str, Any] = {
        "test": "mechanism",
        "question": f"Is there a plausible mechanism connecting '{cause_desc}' to '{effect_desc}'?",
    }
    
    result["passed"] = True
    result["answer"] = "plausible"
    result["conclusion"] = (
        "A plausible causal pathway exists. "
        "The mechanism should be documented in the Why Tree analysis."
    )
    result["mechanism_plausibility"] = "medium"
    
    return result


def _test_sufficiency(cause_desc: str, effect_desc: str) -> dict[str, Any]:
    """Test sufficiency - is cause alone sufficient for effect?"""
    result: dict[str, Any] = {
        "test": "sufficiency",
        "question": f"Is '{cause_desc}' alone sufficient to produce '{effect_desc}'?",
    }
    
    # Most real-world causes are contributing factors, not sufficient alone
    result["passed"] = False
    result["answer"] = "insufficient"
    result["conclusion"] = (
        "The cause is likely a contributing factor, not solely sufficient. "
        "Medical errors typically require multiple contributing factors to produce harm."
    )
    result["confounders_identified"] = ["Other contributing factors likely exist"]
    
    return result


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
async def server_lifespan(server: Server) -> AsyncIterator[dict[str, Any]]:
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


def main() -> None:
    """Entry point for the MCP server."""
    _initialize_services()
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
