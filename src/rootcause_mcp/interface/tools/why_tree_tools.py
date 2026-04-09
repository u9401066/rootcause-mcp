"""
Why Tree Tool Definitions.

Defines Why Tree (5-Why Analysis) MCP tools:
- rc_ask_why
- rc_get_why_tree
- rc_mark_root_cause
- rc_export_why_tree
- rc_add_causal_link
- rc_build_teaching_case
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
        Tool(
            name="rc_add_causal_link",
            description=(
                "Add a directed or bidirectional causal relationship between Why nodes. "
                "Use this to capture escalation loops, feedback cycles, or mitigation links "
                "that are not visible in a simple linear 5-Why chain."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "The session ID",
                    },
                    "source_node_id": {
                        "type": "string",
                        "description": "The source WhyNode ID",
                    },
                    "target_node_id": {
                        "type": "string",
                        "description": "The target WhyNode ID",
                    },
                    "relationship": {
                        "type": "string",
                        "description": "Type of causal relationship",
                        "enum": ["contributes_to", "feedback", "escalates", "mitigates"],
                        "default": "feedback",
                    },
                    "strength": {
                        "type": "number",
                        "description": "Relationship strength (0.0-1.0)",
                        "default": 0.5,
                        "minimum": 0.0,
                        "maximum": 1.0,
                    },
                    "bidirectional": {
                        "type": "boolean",
                        "description": "Whether the influence also goes from target back to source",
                        "default": False,
                    },
                    "note": {
                        "type": "string",
                        "description": "Optional explanatory note for this link",
                        "default": "",
                    },
                    "evidence": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional evidence supporting the link",
                        "default": [],
                    },
                },
                "required": ["session_id", "source_node_id", "target_node_id"],
            },
        ),
        Tool(
            name="rc_build_teaching_case",
            description=(
                "Transform a completed Why Tree into a teaching-ready lesson plan. "
                "Generates learning objectives, common pitfalls, discussion prompts, "
                "and reverse-causality questions for medical learners."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "The session ID",
                    },
                    "learner_level": {
                        "type": "string",
                        "description": "Target learner level",
                        "enum": ["medical_student", "intern", "resident", "fellow"],
                        "default": "medical_student",
                    },
                    "format": {
                        "type": "string",
                        "description": "Output format",
                        "enum": ["markdown", "json"],
                        "default": "markdown",
                    },
                },
                "required": ["session_id"],
            },
        ),
    ]
