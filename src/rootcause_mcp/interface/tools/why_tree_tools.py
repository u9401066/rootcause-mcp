"""
Why Tree Tool Definitions.

Defines 4 Why Tree (5-Why Analysis) MCP tools:
- rc_ask_why
- rc_get_why_tree
- rc_mark_root_cause
- rc_export_why_tree
"""

from mcp.types import Tool


def get_why_tree_tools() -> list[Tool]:
    """Return Why Tree tool definitions."""
    return [
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
    ]
