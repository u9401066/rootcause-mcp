"""
Differential Diagnosis MCP Tools.

Tools for proposing hypotheses, linking evidence, and getting ranked diagnoses.
"""

from __future__ import annotations

from mcp.types import Tool


def get_dd_tools() -> list[Tool]:
    """Get all differential diagnosis tools."""
    return [
        Tool(
            name="rc_propose_hypothesis",
            description="Propose a differential diagnosis hypothesis with Bayesian prior",
            input_schema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "RCA session ID",
                    },
                    "diagnosis": {
                        "type": "string",
                        "description": "Diagnosis name (e.g., 'Acute myocardial infarction')",
                    },
                    "icd10_code": {
                        "type": "string",
                        "description": "ICD-10 code (optional, e.g., 'I21.9')",
                    },
                    "snomed_code": {
                        "type": "string",
                        "description": "SNOMED CT code (optional)",
                    },
                    "prior_probability": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "Prior probability P(H) before evidence (0-1)",
                        "default": 0.1,
                    },
                    "rationale": {
                        "type": "string",
                        "description": "Why this hypothesis is being considered",
                    },
                    "inclusion_criteria": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Criteria that support this diagnosis",
                    },
                    "exclusion_criteria": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Criteria that rule out this diagnosis",
                    },
                },
                "required": ["session_id", "diagnosis"],
            },
        ),
        Tool(
            name="rc_link_evidence_to_hypothesis",
            description="Link evidence to hypothesis with Bayesian updating",
            input_schema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "RCA session ID",
                    },
                    "evidence_id": {
                        "type": "string",
                        "description": "Evidence ID (e.g., 'EVD-abc123')",
                    },
                    "hypothesis_id": {
                        "type": "string",
                        "description": "Hypothesis ID (e.g., 'HYP-def456')",
                    },
                    "likelihood_ratio": {
                        "type": "number",
                        "minimum": 0.01,
                        "maximum": 100,
                        "description": "Likelihood ratio (LR+ if supports, LR- if contradicts)",
                        "default": 1.0,
                    },
                    "supports": {
                        "type": "boolean",
                        "description": "True if evidence supports hypothesis, False if contradicts",
                        "default": True,
                    },
                    "rationale": {
                        "type": "string",
                        "description": "Clinical justification for this LR",
                    },
                },
                "required": ["session_id", "evidence_id", "hypothesis_id"],
            },
        ),
        Tool(
            name="rc_get_differential_diagnosis",
            description="Get probability-ranked differential diagnosis tree",
            input_schema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "RCA session ID",
                    },
                    "status_filter": {
                        "type": "string",
                        "enum": ["ACTIVE", "CONFIRMED", "EXCLUDED", "ON_HOLD"],
                        "description": "Filter by hypothesis status",
                        "default": "ACTIVE",
                    },
                    "min_probability": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "Minimum probability threshold",
                        "default": 0.01,
                    },
                },
                "required": ["session_id"],
            },
        ),
        Tool(
            name="rc_exclude_hypothesis",
            description="Rule out a hypothesis based on evidence",
            input_schema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "RCA session ID",
                    },
                    "hypothesis_id": {
                        "type": "string",
                        "description": "Hypothesis ID to exclude",
                    },
                    "exclusion_reason": {
                        "type": "string",
                        "description": "Why this hypothesis is being excluded",
                    },
                    "excluded_by": {
                        "type": "string",
                        "description": "Who excluded this hypothesis",
                    },
                },
                "required": ["session_id", "hypothesis_id", "exclusion_reason", "excluded_by"],
            },
        ),
    ]
