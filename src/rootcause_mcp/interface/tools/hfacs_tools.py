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
                "Returns heuristic keyword-rule matches; their internal compatibility "
                "values are not calibrated confidence or clinical probability. "
                "HFACS-MES has 5 levels: External Factors, Organizational Influences, "
                "Unsafe Supervision, Preconditions, Unsafe Acts."
            ),
            input_schema={
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
                "Persist an operator-authorized HFACS review for exactly one Fishbone "
                "cause in one session. CONFIRMED requires a recognized HFACS code; "
                "NOT_APPLICABLE forbids a code. A code supplied to rc_add_cause remains "
                "UNREVIEWED and cannot satisfy final conformance."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session owning the persisted Fishbone",
                    },
                    "cause_id": {
                        "type": "string",
                        "description": "Exact persisted Fishbone cause ID",
                    },
                    "description": {
                        "type": "string",
                        "description": (
                            "Optional exact cause description for an additional stale-data check"
                        ),
                    },
                    "hfacs_code": {
                        "type": "string",
                        "description": (
                            "Recognized HFACS-MES code; required only for CONFIRMED"
                        ),
                    },
                    "review_status": {
                        "type": "string",
                        "enum": ["CONFIRMED", "NOT_APPLICABLE"],
                    },
                    "reviewed_by": {
                        "type": "string",
                        "description": (
                            "Named reviewer in ROOTCAUSE_AUTHORIZED_REVIEWERS"
                        ),
                    },
                    "reason": {
                        "type": "string",
                        "description": "Auditable reason for the review disposition",
                    },
                    "confidence": {
                        "type": "number",
                        "description": (
                            "Optional caller-supplied heuristic compatibility metadata; "
                            "not clinical probability or calibrated confidence"
                        ),
                        "minimum": 0.0,
                        "maximum": 1.0,
                    },
                },
                "required": [
                    "session_id",
                    "cause_id",
                    "review_status",
                    "reviewed_by",
                    "reason",
                ],
                "allOf": [
                    {
                        "if": {"properties": {"review_status": {"const": "CONFIRMED"}}},
                        "then": {"required": ["hfacs_code"]},
                        "else": {"properties": {"hfacs_code": {"type": "null"}}},
                    }
                ],
            },
        ),
        Tool(
            name="rc_get_hfacs_framework",
            description=(
                "Get HFACS-MES framework structure and category definitions. "
                "Use this to understand the classification hierarchy and criteria."
            ),
            input_schema={
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
            input_schema={
                "type": "object",
                "properties": {
                    "hfacs_code": {
                        "type": "string",
                        "description": "Optional: filter by specific HFACS code",
                        "default": None,
                    },
                    "min_confidence": {
                        "type": "number",
                        "description": (
                            "Legacy heuristic-rule compatibility threshold; not "
                            "calibrated confidence or clinical probability"
                        ),
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
            input_schema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="rc_get_6m_hfacs_mapping",
            description=(
                "Get mapping between 6M Fishbone categories and HFACS codes. "
                "Shows how Fishbone categories (Personnel, Equipment, Material, Process, "
                "Environment, Monitoring) correspond to HFACS levels. "
                "Useful for cross-framework analysis and ensuring comprehensive coverage. "
                "Also provides Why Tree depth guidance for each category."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": (
                            "Optional: specific 6M category to retrieve mapping for. "
                            "If not specified, returns all mappings."
                        ),
                        "enum": [
                            "Personnel",
                            "Equipment",
                            "Material",
                            "Process",
                            "Environment",
                            "Monitoring",
                        ],
                        "default": None,
                    },
                },
                "required": [],
            },
        ),
    ]
