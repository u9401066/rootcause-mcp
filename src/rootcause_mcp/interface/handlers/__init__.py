"""
MCP Tool handlers package.

Contains tool request handlers organized by domain.
Each handler processes tool calls and returns results.
"""

from rootcause_mcp.interface.handlers.contract_handlers import ContractHandlers
from rootcause_mcp.interface.handlers.dd_handlers import DDHandlers
from rootcause_mcp.interface.handlers.evidence_handlers import EvidenceHandlers
from rootcause_mcp.interface.handlers.fishbone_handlers import FishboneHandlers
from rootcause_mcp.interface.handlers.hfacs_handlers import HFACSHandlers
from rootcause_mcp.interface.handlers.reasoning_handlers import ReasoningHandlers
from rootcause_mcp.interface.handlers.session_handlers import SessionHandlers
from rootcause_mcp.interface.handlers.thinking_handlers import ThinkingHandlers
from rootcause_mcp.interface.handlers.verification_handlers import VerificationHandlers
from rootcause_mcp.interface.handlers.why_tree_handlers import WhyTreeHandlers

__all__ = [
    "ContractHandlers",
    "DDHandlers",
    "EvidenceHandlers",
    "FishboneHandlers",
    "HFACSHandlers",
    "ReasoningHandlers",
    "SessionHandlers",
    "ThinkingHandlers",
    "VerificationHandlers",
    "WhyTreeHandlers",
]
