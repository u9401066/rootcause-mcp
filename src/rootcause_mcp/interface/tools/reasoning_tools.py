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
        Tool(
            name="rc_detect_conflicts",
            description=(
                "Automatically detect clinical contradictions, paradoxical treatment reactions, "
                "guideline monitoring gaps (e.g. MTP without K+/ABG, high Propofol without lipids), "
                "and cognitive anchoring pitfalls across all evidence and hypotheses."
            ),
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
        Tool(
            name="rc_create_checkpoint",
            description=(
                "Create an integrity-checked, timestamped snapshot of active clinical reasoning state "
                "(evidence, hypotheses, Bayesian history, thinking steps, reasoning chain) "
                "to prevent context loss or enable branching investigation."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "RCA session ID",
                    },
                    "tag": {
                        "type": "string",
                        "description": "Optional human-readable tag (e.g., 'post_tee_evaluation', 'pre_cpr_baseline')",
                    },
                    "notes": {
                        "type": "string",
                        "description": "Optional notes describing the reason for this snapshot",
                    },
                    "created_by": {
                        "type": "string",
                        "description": "Agent or reviewer creating the checkpoint",
                        "default": "agent",
                    },
                },
                "required": ["session_id"],
            },
        ),
        Tool(
            name="rc_restore_checkpoint",
            description="Restore clinical reasoning aggregate and database state from a saved checkpoint.",
            input_schema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "RCA session ID",
                    },
                    "checkpoint_id": {
                        "type": "string",
                        "description": "Checkpoint ID (e.g. 'CP-abc12345-20260814_120000-baseline')",
                    },
                    "checkpoint_file": {
                        "type": "string",
                        "description": (
                            "Checkpoint JSON filename or path inside this session's "
                            "checkpoint directory (optional)"
                        ),
                    },
                },
                "required": ["session_id"],
            },
        ),
        Tool(
            name="rc_list_checkpoints",
            description="List all available case checkpoints and snapshot metadata for a session.",
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
