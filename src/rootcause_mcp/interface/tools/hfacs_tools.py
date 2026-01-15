"""
HFACS Tool Definitions.

Defines 5 HFACS-related MCP tools:
- rc_suggest_hfacs
- rc_confirm_classification
- rc_get_hfacs_framework
- rc_list_learned_rules
- rc_reload_rules
"""

from mcp.types import Tool


def get_hfacs_tools() -> list[Tool]:
    """Return HFACS-related tool definitions."""
    return [
        Tool(
            name="rc_suggest_hfacs",
            description=(
                "Suggest HFACS-MES classification codes for a cause description. "
                "Returns ranked suggestions with confidence scores. "
                "HFACS-MES has 5 levels: External Factors, Organizational Influences, "
                "Unsafe Supervision, Preconditions, Unsafe Acts."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "The cause description text to classify",
                    },
                    "domain": {
                        "type": "string",
                        "description": (
                            "Optional domain context for better suggestions "
                            "(e.g., 'anesthesia', 'surgery', 'nursing')"
                        ),
                        "default": None,
                    },
                    "max_suggestions": {
                        "type": "integer",
                        "description": "Maximum number of suggestions to return",
                        "default": 3,
                        "minimum": 1,
                        "maximum": 10,
                    },
                },
                "required": ["description"],
            },
        ),
        Tool(
            name="rc_confirm_classification",
            description=(
                "Confirm an HFACS classification as correct. "
                "This helps the system learn from expert decisions and improve future suggestions. "
                "Confirmed classifications are stored as learned rules."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "The original cause description",
                    },
                    "hfacs_code": {
                        "type": "string",
                        "description": (
                            "The confirmed HFACS code "
                            "(e.g., 'UA-S', 'PC-C-PMC', 'EF-RE')"
                        ),
                    },
                    "reason": {
                        "type": "string",
                        "description": "Brief explanation of why this classification is correct",
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Optional session ID for tracking",
                        "default": None,
                    },
                    "confidence": {
                        "type": "number",
                        "description": "Confidence level (0.0-1.0)",
                        "default": 0.8,
                        "minimum": 0.0,
                        "maximum": 1.0,
                    },
                },
                "required": ["description", "hfacs_code", "reason"],
            },
        ),
        Tool(
            name="rc_get_hfacs_framework",
            description=(
                "Get HFACS-MES framework structure and category definitions. "
                "Use this to understand the classification hierarchy and criteria."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "level": {
                        "type": "string",
                        "description": (
                            "Optional: specific level to retrieve "
                            "(EF, OI, US, PC, UA). If not specified, returns all levels."
                        ),
                        "enum": ["EF", "OI", "US", "PC", "UA"],
                        "default": None,
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="rc_list_learned_rules",
            description=(
                "List all learned classification rules. "
                "Shows rules that have been confirmed by experts."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "hfacs_code": {
                        "type": "string",
                        "description": "Optional: filter by specific HFACS code",
                        "default": None,
                    },
                    "min_confidence": {
                        "type": "number",
                        "description": "Minimum confidence threshold",
                        "default": 0.0,
                        "minimum": 0.0,
                        "maximum": 1.0,
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="rc_reload_rules",
            description=(
                "Reload classification rules from YAML files. "
                "Use this after manually editing config files."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
    ]
