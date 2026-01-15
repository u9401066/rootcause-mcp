"""
Interface Layer - MCP Tool definitions and handlers.

This layer handles:
- Tool definitions (schemas)
- Tool handlers (request processing)

Note: server.py is now at rootcause_mcp.server (not in interface/)
"""

from rootcause_mcp.interface.tools import (
    get_hfacs_tools,
    get_session_tools,
    get_fishbone_tools,
    get_why_tree_tools,
    get_verification_tools,
    get_all_tools,
)

from rootcause_mcp.interface.handlers import (
    HFACSHandlers,
    SessionHandlers,
    FishboneHandlers,
    WhyTreeHandlers,
    VerificationHandlers,
)

__all__ = [
    # Tools
    "get_hfacs_tools",
    "get_session_tools",
    "get_fishbone_tools",
    "get_why_tree_tools",
    "get_verification_tools",
    "get_all_tools",
    # Handlers
    "HFACSHandlers",
    "SessionHandlers",
    "FishboneHandlers",
    "WhyTreeHandlers",
    "VerificationHandlers",
]
