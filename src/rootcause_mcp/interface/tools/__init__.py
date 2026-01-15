"""
MCP Tool definitions package.

Contains tool schema definitions organized by domain:
- HFACS classification tools (5 tools)
- Session management tools (4 tools)
- Fishbone diagram tools (4 tools)
- Why Tree analysis tools (4 tools)
- Verification tools (1 tool)

Total: 18 MCP tools
"""

from mcp.types import Tool

from rootcause_mcp.interface.tools.hfacs_tools import get_hfacs_tools
from rootcause_mcp.interface.tools.session_tools import get_session_tools
from rootcause_mcp.interface.tools.fishbone_tools import get_fishbone_tools
from rootcause_mcp.interface.tools.why_tree_tools import get_why_tree_tools
from rootcause_mcp.interface.tools.verification_tools import get_verification_tools


def get_all_tools() -> list[Tool]:
    """Get all 18 MCP tool definitions."""
    tools = []
    tools.extend(get_hfacs_tools())      # 5 tools
    tools.extend(get_session_tools())     # 4 tools
    tools.extend(get_fishbone_tools())    # 4 tools
    tools.extend(get_why_tree_tools())    # 4 tools
    tools.extend(get_verification_tools()) # 1 tool
    return tools


__all__ = [
    "get_hfacs_tools",
    "get_session_tools",
    "get_fishbone_tools",
    "get_why_tree_tools",
    "get_verification_tools",
    "get_all_tools",
]
