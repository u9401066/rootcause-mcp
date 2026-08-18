"""
Thinking/Reasoning Transparency MCP Tools.

Tools for capturing Agent's internal thought process.
"""

from __future__ import annotations

from mcp.types import Tool


def get_thinking_tools() -> list[Tool]:
    """Get all thinking transparency tools."""
    return [
        Tool(
            name="rc_think_aloud",
            description="Record Agent's thinking process (what and why)",
            input_schema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "RCA session ID",
                    },
                    "thinking_type": {
                        "type": "string",
                        "enum": [
                            "HYPOTHESIS_CONSIDERED",
                            "HYPOTHESIS_REJECTED",
                            "HYPOTHESIS_DEFERRED",
                            "EVIDENCE_WEIGHTED",
                            "EVIDENCE_CONFLICTED",
                            "EVIDENCE_GAP_IDENTIFIED",
                            "ANALOGY_USED",
                            "PATTERN_RECOGNIZED",
                            "RULE_APPLIED",
                            "HEURISTIC_USED",
                            "UNCERTAINTY_ACKNOWLEDGED",
                            "ASSUMPTION_QUESTIONED",
                            "BIAS_IDENTIFIED",
                            "ALTERNATIVE_CONSIDERED",
                            "DECISION_POINT",
                            "BRANCH_EXPLORED",
                            "BRANCH_PRUNED",
                        ],
                        "description": "Type of thinking step",
                    },
                    "content": {
                        "type": "string",
                        "description": "What the Agent is thinking (e.g., 'Considering PE due to sudden dyspnea')",
                    },
                    "internal_reasoning": {
                        "type": "string",
                        "description": "Why Agent thinks this way (detailed reasoning process)",
                    },
                    "alternatives": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "alternative": {"type": "string"},
                                "reason_rejected": {"type": "string"},
                                "confidence_if_chosen": {
                                    "type": "number",
                                    "minimum": 0,
                                    "maximum": 1,
                                },
                            },
                            "required": ["alternative", "reason_rejected"],
                        },
                        "description": "Alternatives considered but not chosen",
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": (
                            "Optional caller-supplied compatibility metadata; not "
                            "clinical probability or calibrated confidence"
                        ),
                    },
                    "uncertainty_factors": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Factors contributing to uncertainty",
                    },
                    "related_evidence_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Evidence IDs being considered",
                    },
                    "related_hypothesis_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Hypothesis IDs being evaluated",
                    },
                    "assumptions_made": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Assumptions underlying this thinking",
                    },
                    "potential_biases": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Cognitive biases that might affect this thinking",
                    },
                },
                "required": [
                    "session_id",
                    "thinking_type",
                    "content",
                    "internal_reasoning",
                ],
            },
        ),
        Tool(
            name="rc_reflect",
            description="Agent reflects on its own reasoning process (meta-cognition)",
            input_schema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "RCA session ID",
                    },
                    "reflection_content": {
                        "type": "string",
                        "description": "What the Agent realized during reflection",
                    },
                    "identified_gaps": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Knowledge/evidence gaps identified",
                    },
                    "identified_biases": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Cognitive biases identified in own reasoning",
                    },
                    "alternative_approaches": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Alternative reasoning approaches to consider",
                    },
                },
                "required": ["session_id", "reflection_content"],
            },
        ),
        Tool(
            name="rc_identify_gaps",
            description="Agent proactively identifies knowledge/evidence gaps",
            input_schema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "RCA session ID",
                    },
                    "gap_type": {
                        "type": "string",
                        "enum": [
                            "MISSING_EVIDENCE",
                            "MISSING_KNOWLEDGE",
                            "AMBIGUOUS_DATA",
                            "CONFLICTING_EVIDENCE",
                            "INSUFFICIENT_DATA",
                        ],
                        "description": "Type of gap identified",
                    },
                    "gap_description": {
                        "type": "string",
                        "description": "Description of the gap",
                    },
                    "impact_on_diagnosis": {
                        "type": "string",
                        "description": "How this gap affects diagnostic confidence",
                    },
                    "suggested_actions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Suggested actions to fill the gap",
                    },
                },
                "required": ["session_id", "gap_type", "gap_description"],
            },
        ),
        Tool(
            name="rc_challenge_assumption",
            description="Agent challenges its own assumptions (devil's advocate)",
            input_schema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "RCA session ID",
                    },
                    "assumption": {
                        "type": "string",
                        "description": "The assumption being challenged",
                    },
                    "challenge_reasoning": {
                        "type": "string",
                        "description": "Why this assumption might be wrong",
                    },
                    "alternative_scenario": {
                        "type": "string",
                        "description": "Alternative scenario if assumption is false",
                    },
                    "impact_if_wrong": {
                        "type": "string",
                        "description": "Impact on diagnosis if assumption is wrong",
                    },
                },
                "required": ["session_id", "assumption", "challenge_reasoning"],
            },
        ),
        Tool(
            name="rc_get_thinking_chain",
            description="Get complete thinking chain (cognitive audit trail)",
            input_schema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "RCA session ID",
                    },
                    "include_alternatives": {
                        "type": "boolean",
                        "description": "Include alternatives that were considered but rejected",
                        "default": True,
                    },
                    "include_uncertainties": {
                        "type": "boolean",
                        "description": "Include uncertainty analysis",
                        "default": True,
                    },
                    "include_biases": {
                        "type": "boolean",
                        "description": "Include cognitive bias analysis",
                        "default": True,
                    },
                },
                "required": ["session_id"],
            },
        ),
    ]
