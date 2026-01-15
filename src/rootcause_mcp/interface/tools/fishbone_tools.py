"""
Fishbone Tool Definitions.

Defines 4 Fishbone diagram MCP tools:
- rc_init_fishbone
- rc_add_cause
- rc_get_fishbone
- rc_export_fishbone
"""

from mcp.types import Tool


def get_fishbone_tools() -> list[Tool]:
    """Return Fishbone diagram tool definitions."""
    return [
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
    ]
