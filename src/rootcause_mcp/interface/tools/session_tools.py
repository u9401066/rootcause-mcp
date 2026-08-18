"""
Session Tool Definitions.

Defines 5 Session management MCP tools:
- rc_start_session
- rc_get_session
- rc_list_sessions
- rc_archive_session
- rc_adjudicate_source
"""

from mcp.types import Tool

from rootcause_mcp.interface.tools.schema_fragments import case_input_manifest_schema


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
            input_schema={
                "type": "object",
                "properties": {
                    "case_type": {
                        "type": "string",
                        "description": "Type of case being analyzed",
                        "enum": [
                            "death",
                            "complication",
                            "near_miss",
                            "safety",
                            "staffing",
                        ],
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
                    "source_manifest": {
                        **case_input_manifest_schema(),
                        "description": (
                            "Versioned manifest for every raw record in scope. Register all "
                            "sources, including documents from which no finding was extracted."
                        ),
                    },
                },
                "required": ["case_type", "case_title"],
            },
        ),
        Tool(
            name="rc_adjudicate_source",
            description=(
                "Append an authorized source-processing and independence review "
                "event without mutating the pinned source manifest or its digest. "
                "Use after extraction/review; reviewer must be allowlisted."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "document_id": {
                        "type": "string",
                        "description": "Stable document_id in the pinned manifest",
                    },
                    "source_status": {
                        "type": "string",
                        "enum": ["extracted", "reviewed", "failed"],
                    },
                    "de_identified": {
                        "type": "boolean",
                        "description": (
                            "Human attestation; must be true for reviewed sources"
                        ),
                    },
                    "independence_status": {
                        "type": "string",
                        "enum": ["unknown", "independent", "derived"],
                    },
                    "source_group_id": {
                        "type": "string",
                        "description": "Host-adjudicated source root/group",
                    },
                    "parent_document_id": {
                        "type": "string",
                        "description": "Manifest parent for a derived source",
                    },
                    "derivation_method": {
                        "type": "string",
                        "description": "Transformation/extraction method for a derivative",
                    },
                    "reviewed_by": {
                        "type": "string",
                        "description": (
                            "Named member of ROOTCAUSE_AUTHORIZED_REVIEWERS"
                        ),
                    },
                    "reason": {
                        "type": "string",
                        "description": "Source-linked rationale for this transition",
                    },
                },
                "required": [
                    "session_id",
                    "document_id",
                    "source_status",
                    "reviewed_by",
                    "reason",
                ],
            },
        ),
        Tool(
            name="rc_get_session",
            description=(
                "Get details of an RCA session by ID. "
                "Returns session status, current stage, and progress."
            ),
            input_schema={
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
            input_schema={
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
                        "enum": [
                            "death",
                            "complication",
                            "near_miss",
                            "safety",
                            "staffing",
                        ],
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
            input_schema={
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
