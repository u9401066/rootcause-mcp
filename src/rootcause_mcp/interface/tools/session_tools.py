"""
Session Tool Definitions.

Defines 4 Session management MCP tools:
- rc_start_session
- rc_get_session
- rc_list_sessions
- rc_archive_session
"""

from mcp.types import Tool


def get_session_tools() -> list[Tool]:
    """Return Session management tool definitions."""
    return [
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
    ]
