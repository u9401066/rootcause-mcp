"""
Verification Tool Definitions.

Defines 1 Causation Verification MCP tool:
- rc_verify_causation
"""

from mcp.types import Tool


def get_verification_tools() -> list[Tool]:
    """Return Verification tool definitions."""
    return [
        Tool(
            name="rc_verify_causation",
            description=(
                "Verify causal relationship between cause and effect using "
                "the Counterfactual Testing Framework. Tests: "
                "1) Temporality - Did cause precede effect? "
                "2) Necessity - Would effect occur without cause? "
                "3) Mechanism - Is there a plausible causal pathway? "
                "4) Sufficiency - Is cause alone sufficient for effect?"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "The session ID",
                    },
                    "cause": {
                        "type": "object",
                        "description": "The cause event",
                        "properties": {
                            "description": {
                                "type": "string",
                                "description": "Description of the cause",
                            },
                            "timestamp": {
                                "type": "string",
                                "description": "When the cause occurred (ISO format)",
                                "default": None,
                            },
                        },
                        "required": ["description"],
                    },
                    "effect": {
                        "type": "object",
                        "description": "The effect event",
                        "properties": {
                            "description": {
                                "type": "string",
                                "description": "Description of the effect",
                            },
                            "timestamp": {
                                "type": "string",
                                "description": "When the effect occurred (ISO format)",
                                "default": None,
                            },
                        },
                        "required": ["description"],
                    },
                    "verification_level": {
                        "type": "string",
                        "description": (
                            "'standard' tests Temporality+Necessity. "
                            "'comprehensive' tests all 4 criteria."
                        ),
                        "enum": ["standard", "comprehensive"],
                        "default": "standard",
                    },
                },
                "required": ["session_id", "cause", "effect"],
            },
        ),
    ]
