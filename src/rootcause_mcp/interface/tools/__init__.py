"""
MCP Tool definitions package.

Contains tool schema definitions organized by domain:
- Condensed facade tools (8 unified tools) - NEW for ultra-low token budget
- Evidence management tools (3 tools)
- Differential diagnosis tools (4 tools)
- Reasoning chain, conflict detection & checkpoint tools (7 tools)
- CONTRACT report tools (1 tool)
- Cognitive transparency tools (5 tools)
- HFACS classification tools (6 tools)
- Session management tools (4 tools)
- Fishbone diagram tools (4 tools)
- Why Tree analysis tools (6 tools)
- Verification & diagram tools (3 tools)

Total: 43 discrete tools across clinical (23), RCA (23), all (43), or condensed (8 unified facade tools).
"""

from mcp.types import Tool

from rootcause_mcp.interface.tools.condensed_tools import get_condensed_tools
from rootcause_mcp.interface.tools.contract_tools import get_contract_tools
from rootcause_mcp.interface.tools.dd_tools import get_dd_tools
from rootcause_mcp.interface.tools.evidence_tools import get_evidence_tools
from rootcause_mcp.interface.tools.fishbone_tools import get_fishbone_tools
from rootcause_mcp.interface.tools.hfacs_tools import get_hfacs_tools
from rootcause_mcp.interface.tools.reasoning_tools import get_reasoning_tools
from rootcause_mcp.interface.tools.session_tools import get_session_tools
from rootcause_mcp.interface.tools.thinking_tools import get_thinking_tools
from rootcause_mcp.interface.tools.verification_tools import get_verification_tools
from rootcause_mcp.interface.tools.why_tree_tools import get_why_tree_tools

TOOL_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {
            "type": "string",
            "description": "success, error, or not_found",
        },
        "content": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Human-readable content returned by legacy RCA tools",
        },
    },
    "required": ["status"],
    "additionalProperties": True,
}


def get_all_tools(profile: str = "all") -> list[Tool]:
    """Get tool definitions for the configured context profile."""
    normalized_profile = profile.strip().lower()
    if normalized_profile not in {"all", "clinical", "rca", "condensed", "facade"}:
        raise ValueError(
            f"Unsupported tool profile {profile!r}; expected all, clinical, rca, or condensed"
        )

    if normalized_profile in {"condensed", "facade"}:
        return [
            tool.model_copy(update={"output_schema": TOOL_OUTPUT_SCHEMA})
            for tool in get_condensed_tools()
        ]

    clinical_tools = [
        *get_thinking_tools(),
        *get_evidence_tools(),
        *get_dd_tools(),
        *get_reasoning_tools(),
        *get_contract_tools(),
        *get_verification_tools(),
    ]
    rca_tools = [
        *get_hfacs_tools(),
        *get_session_tools(),
        *get_fishbone_tools(),
        *get_why_tree_tools(),
        *get_verification_tools(),
    ]

    if normalized_profile == "clinical":
        tools = clinical_tools
    elif normalized_profile == "rca":
        tools = rca_tools
    else:
        tools_by_name = {tool.name: tool for tool in [*clinical_tools, *rca_tools]}
        tools = list(tools_by_name.values())

    return [
        tool.model_copy(update={"output_schema": TOOL_OUTPUT_SCHEMA}) for tool in tools
    ]


__all__ = [
    "get_all_tools",
    "get_condensed_tools",
    "get_contract_tools",
    "get_dd_tools",
    "get_evidence_tools",
    "get_fishbone_tools",
    "get_hfacs_tools",
    "get_reasoning_tools",
    "get_session_tools",
    "get_thinking_tools",
    "get_verification_tools",
    "get_why_tree_tools",
]
