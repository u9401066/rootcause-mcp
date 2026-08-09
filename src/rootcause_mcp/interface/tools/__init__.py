"""
MCP Tool definitions package.

Contains tool schema definitions organized by domain:
- Evidence management tools (3 tools) - NEW in 2.0
- Differential diagnosis tools (4 tools) - NEW in 2.0
- Reasoning chain tools (2 tools) - NEW in 2.0
- CONTRACT report tools (1 tool) - NEW in 2.0
- HFACS classification tools (5 tools)
- Session management tools (4 tools)
- Fishbone diagram tools (4 tools)
- Why Tree analysis tools (6 tools)
- Verification tools (1 tool)

Total: 29 MCP tools (10 new in v2.0)
"""

from mcp.types import Tool

from rootcause_mcp.interface.tools.contract_tools import get_contract_tools
from rootcause_mcp.interface.tools.dd_tools import get_dd_tools
from rootcause_mcp.interface.tools.evidence_tools import get_evidence_tools
from rootcause_mcp.interface.tools.fishbone_tools import get_fishbone_tools
from rootcause_mcp.interface.tools.hfacs_tools import get_hfacs_tools
from rootcause_mcp.interface.tools.reasoning_tools import get_reasoning_tools
from rootcause_mcp.interface.tools.session_tools import get_session_tools
from rootcause_mcp.interface.tools.verification_tools import get_verification_tools
from rootcause_mcp.interface.tools.why_tree_tools import get_why_tree_tools


def get_all_tools() -> list[Tool]:
    """Get all 29 MCP tool definitions."""
    tools = []
    # NEW in 2.0: Medical Reasoning Tools
    tools.extend(get_evidence_tools())      # 3 tools
    tools.extend(get_dd_tools())            # 4 tools
    tools.extend(get_reasoning_tools())     # 2 tools
    tools.extend(get_contract_tools())      # 1 tool
    # Existing RCA Tools
    tools.extend(get_hfacs_tools())         # 5 tools
    tools.extend(get_session_tools())       # 4 tools
    tools.extend(get_fishbone_tools())      # 4 tools
    tools.extend(get_why_tree_tools())      # 4 tools (actually 6 in why_tree_tools.py)
    tools.extend(get_verification_tools())  # 1 tool
    return tools


__all__ = [
    "get_evidence_tools",
    "get_dd_tools",
    "get_reasoning_tools",
    "get_contract_tools",
    "get_hfacs_tools",
    "get_session_tools",
    "get_fishbone_tools",
    "get_why_tree_tools",
    "get_verification_tools",
    "get_all_tools",
]
