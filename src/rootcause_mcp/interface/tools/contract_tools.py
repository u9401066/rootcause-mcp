"""
CONTRACT Report MCP Tools.

Tools for generating auditable, CONTRACT-level reports.
"""

from __future__ import annotations

from mcp.types import Tool


def get_contract_tools() -> list[Tool]:
    """Get all CONTRACT report tools."""
    return [
        Tool(
            name="rc_generate_contract_report",
            description="Generate CONTRACT-level auditable report with evidence chain and reasoning",
            input_schema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "RCA session ID",
                    },
                    "include_reasoning_chain": {
                        "type": "boolean",
                        "description": "Include orchestrator-generated reasoning chain",
                        "default": True,
                    },
                    "include_thinking_chain": {
                        "type": "boolean",
                        "description": "Include agent-authored rationale/thinking chain",
                        "default": True,
                    },
                    "include_evidence_graph": {
                        "type": "boolean",
                        "description": "Include evidence relationship graph",
                        "default": True,
                    },
                    "include_quality_metrics": {
                        "type": "boolean",
                        "description": "Include evidence coverage and quality metrics",
                        "default": True,
                    },
                    "format": {
                        "type": "string",
                        "enum": ["json", "fhir", "markdown"],
                        "description": "Output format",
                        "default": "json",
                    },
                    "detail_level": {
                        "type": "string",
                        "enum": ["brief", "standard", "full"],
                        "description": "Markdown artifact detail; ignored by JSON/FHIR",
                        "default": "standard",
                    },
                    "template_file": {
                        "type": "string",
                        "description": "Optional path to custom Markdown report template file (e.g. 'config/templates/clinical_reasoning_report_template.md')",
                    },
                    "finalize": {
                        "type": "boolean",
                        "description": "Finalize report (make immutable)",
                        "default": False,
                    },
                },
                "required": ["session_id"],
            },
        ),
    ]
