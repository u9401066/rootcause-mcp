"""
MCP Tool definitions package.

Contains tool schema definitions organized by domain:
- Evidence management tools (3 tools) - NEW in 2.0
- Differential diagnosis tools (4 tools) - NEW in 2.0
- Reasoning chain tools (2 tools) - NEW in 2.0
- CONTRACT report tools (1 tool) - NEW in 2.0
- Cognitive transparency tools (5 tools)
- HFACS classification tools (6 tools)
- Session management tools (4 tools)
- Fishbone diagram tools (4 tools)
- Why Tree analysis tools (6 tools)
- Verification tools (1 tool)

Total: 36 MCP tools (15 medical reasoning/cognitive tools)
"""

from mcp.types import Tool

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


def get_all_tools() -> list[Tool]:
    """Get all 36 MCP tool definitions."""
    tools = []
    # NEW in 2.0: Cognitive Layer (Deep Reasoning)
    tools.extend(get_thinking_tools())  # 5 tools - rc_think_aloud, rc_reflect, etc.
    # NEW in 2.0: Medical Reasoning Tools
    tools.extend(get_evidence_tools())  # 3 tools
    tools.extend(get_dd_tools())  # 4 tools
    tools.extend(get_reasoning_tools())  # 2 tools
    tools.extend(get_contract_tools())  # 1 tool
    # Existing RCA Tools
    tools.extend(get_hfacs_tools())  # 6 tools
    tools.extend(get_session_tools())  # 4 tools
    tools.extend(get_fishbone_tools())  # 4 tools
    tools.extend(get_why_tree_tools())  # 6 tools
    tools.extend(get_verification_tools())  # 1 tool
    return [
        tool.model_copy(update={"output_schema": TOOL_OUTPUT_SCHEMA})
        for tool in tools
    ]


__all__ = [
    "get_all_tools",
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
