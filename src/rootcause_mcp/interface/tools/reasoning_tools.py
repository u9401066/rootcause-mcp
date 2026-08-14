"""
Reasoning Chain MCP Tools.

Tools for retrieving and exporting reasoning chains.
"""

from __future__ import annotations

from mcp.types import Tool


def get_reasoning_tools() -> list[Tool]:
    """Get all reasoning chain tools."""
    return [
        Tool(
            name="rc_get_reasoning_chain",
            description="Get complete reasoning chain with audit trail",
            input_schema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "RCA session ID",
                    },
                    "include_metrics": {
                        "type": "boolean",
                        "description": "Include quality metrics",
                        "default": True,
                    },
                },
                "required": ["session_id"],
            },
        ),
        Tool(
            name="rc_export_reasoning_chain",
            description="Export reasoning chain to JSON or Mermaid format",
            input_schema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "RCA session ID",
                    },
                    "format": {
                        "type": "string",
                        "enum": ["json", "mermaid", "markdown"],
                        "description": "Export format",
                        "default": "json",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Output file path (optional, auto-generated if not provided)",
                    },
                },
                "required": ["session_id"],
            },
        ),
        Tool(
            name="rc_audit_reasoning_state",
            description="Audit clinical reasoning completeness, stage progression, missing prerequisites, and next recommended actions for AI agents",
            input_schema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "RCA session ID",
                    },
                },
                "required": ["session_id"],
            },
        ),
    ]
