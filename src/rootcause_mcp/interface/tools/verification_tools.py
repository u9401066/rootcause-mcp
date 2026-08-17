"""
Verification & Diagram Tool Definitions.

Defines Causation Verification and Diagram Rendering/Auditing MCP tools:
- rc_verify_causation
- rc_validate_diagram
- rc_render_timeline
"""

from mcp.types import Tool


def get_verification_tools() -> list[Tool]:
    """Return Verification and Diagram tool definitions."""
    return [
        Tool(
            name="rc_verify_causation",
            description=(
                "Compatibility name for a conservative causation audit; this tool "
                "does not establish clinical causality. It checks submitted "
                "obligations using the Counterfactual Testing Framework. Tests: "
                "1) Temporality - Did cause precede effect? "
                "2) Necessity - Would effect occur without cause? "
                "3) Mechanism - Is there a plausible causal pathway? "
                "4) Sufficiency - Is cause alone sufficient for effect?"
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "The session ID",
                    },
                    "cause": {
                        "type": "object",
                        "description": (
                            "Proposed root event. For a durable/final-eligible audit, "
                            "id, description, and evidence must exactly match the "
                            "persisted Why root and clinical evidence ledger."
                        ),
                        "properties": {
                            "id": {
                                "type": "string",
                                "description": "Stable Why/root-cause node ID when applicable",
                            },
                            "description": {
                                "type": "string",
                                "description": "Description of the cause",
                            },
                            "timestamp": {
                                "type": "string",
                                "format": "date-time",
                                "description": (
                                    "Canonical cause datetime containing 'T' and required "
                                    "Z or numeric timezone offset; omit for date-only or "
                                    "unknown/local time"
                                ),
                                "default": None,
                            },
                            "evidence": {
                                "type": "array",
                                "items": {"type": "string"},
                                "minItems": 1,
                                "uniqueItems": True,
                                "description": "Evidence IDs supporting the proposed cause event",
                            },
                        },
                        "required": ["id", "description", "evidence"],
                    },
                    "effect": {
                        "type": "object",
                        "description": (
                            "Effect event; every evidence reference must resolve in "
                            "the clinical evidence ledger"
                        ),
                        "properties": {
                            "id": {
                                "type": "string",
                                "description": "Stable effect/event ID when available",
                            },
                            "description": {
                                "type": "string",
                                "description": "Description of the effect",
                            },
                            "timestamp": {
                                "type": "string",
                                "format": "date-time",
                                "description": (
                                    "Canonical effect datetime containing 'T' and required "
                                    "Z or numeric timezone offset; omit for date-only or "
                                    "unknown/local time"
                                ),
                                "default": None,
                            },
                            "evidence": {
                                "type": "array",
                                "items": {"type": "string"},
                                "minItems": 1,
                                "uniqueItems": True,
                                "description": "Evidence IDs supporting the effect event",
                            },
                        },
                        "required": ["description", "evidence"],
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
        Tool(
            name="rc_validate_diagram",
            description=(
                "Audit, validate, and auto-sanitize Mermaid diagram syntax (flowchart, timeline, "
                "sequence, state, fishbone, why_tree). Checks delimiter balance, label quotes, "
                "colon formatting, and returns clean executable Mermaid source with diagnostics."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "mermaid_source": {
                        "type": "string",
                        "description": "Raw Mermaid source code or diagram definition to audit",
                    },
                    "diagram_type": {
                        "type": "string",
                        "enum": [
                            "flowchart",
                            "graph",
                            "timeline",
                            "sequenceDiagram",
                            "stateDiagram",
                            "erDiagram",
                            "gantt",
                            "pie",
                            "mindmap",
                        ],
                        "description": "Expected diagram type (optional, auto-detected if omitted)",
                    },
                    "auto_fix": {
                        "type": "boolean",
                        "description": "Automatically escape reserved characters, balance brackets, and fix syntax",
                        "default": True,
                    },
                },
                "required": ["mermaid_source"],
            },
        ),
        Tool(
            name="rc_render_timeline",
            description=(
                "Render structured chronological event timeline and Mermaid diagram using clinical patterns "
                "(perioperative_sequence, acute_crisis, delayed_diagnosis, barrier_failure, device_incident, auto, custom)."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "RCA session ID (optional, to load persisted clinical evidence)",
                    },
                    "events": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "time": {
                                    "type": "string",
                                    "description": "Timestamp or time label (e.g., '08:00', 'POD 1 16:00')",
                                },
                                "phase": {
                                    "type": "string",
                                    "description": "Clinical phase/stage for grouping (optional)",
                                },
                                "content": {
                                    "type": "string",
                                    "description": "Clinical event or finding description",
                                },
                                "source_document": {
                                    "type": "string",
                                    "description": "Source document ID (optional)",
                                },
                                "verified": {
                                    "type": "boolean",
                                    "description": "Whether evidence is verified (optional)",
                                },
                            },
                            "required": ["content"],
                        },
                        "description": "Custom list of timeline events (optional)",
                    },
                    "pattern": {
                        "type": "string",
                        "enum": [
                            "auto",
                            "perioperative_sequence",
                            "acute_crisis",
                            "delayed_diagnosis",
                            "barrier_failure",
                            "device_incident",
                            "custom",
                        ],
                        "description": "Clinical timeline pattern used for phase clustering",
                        "default": "auto",
                    },
                    "title": {
                        "type": "string",
                        "description": "Custom timeline title (optional)",
                    },
                    "include_table": {
                        "type": "boolean",
                        "description": "Include Markdown event matrix table in response",
                        "default": True,
                    },
                },
            },
        ),
    ]
