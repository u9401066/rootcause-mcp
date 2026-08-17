"""
Differential Diagnosis MCP Tools.

Tools for proposing hypotheses, linking evidence, and getting ranked diagnoses.
"""

from __future__ import annotations

from mcp.types import Tool

from rootcause_mcp.interface.tools.schema_fragments import (
    planned_diagnostic_test_input_schema,
)


def get_dd_tools() -> list[Tool]:
    """Get all differential diagnosis tools."""
    return [
        Tool(
            name="rc_propose_hypothesis",
            description="Propose a differential diagnosis hypothesis with Bayesian prior. REQUIRES detailed clinical reasoning to ensure transparency.",
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
                    "must_not_miss": {
                        "type": "boolean",
                        "description": "Mark an explicitly reviewed high-harm diagnosis that must be ruled out",
                        "default": False,
                    },
                    "clinical_reasoning": {
                        "type": "string",
                        "description": "REQUIRED: Detailed clinical reasoning for why this diagnosis is being considered (e.g., 'Patient has chest pain + elevated troponin + ECG changes')",
                    },
                    "differential_diagnoses_considered": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "diagnosis": {"type": "string"},
                                "reason_rejected": {"type": "string"},
                                "likelihood_if_not_rejected": {
                                    "type": "string",
                                    "enum": ["high", "moderate", "low"],
                                },
                            },
                            "required": ["diagnosis", "reason_rejected"],
                        },
                        "description": "REQUIRED: Other diagnoses considered but rejected, with reasons",
                    },
                    "evidence_supporting": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "DEPRECATED context-only input; it is not persisted and does "
                            "not create evidence links. Use rc_link_evidence_to_hypothesis "
                            "once per supporting evidence association."
                        ),
                    },
                    "evidence_contradicting": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "DEPRECATED context-only input; it is not persisted and does "
                            "not create evidence links. Use rc_link_evidence_to_hypothesis "
                            "once per contradicting evidence association."
                        ),
                    },
                    "uncertainty_factors": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "REQUIRED: Factors contributing to diagnostic uncertainty (e.g., 'Troponin trend pending')",
                    },
                    "confidence_rationale": {
                        "type": "string",
                        "description": "REQUIRED: Explanation of why you assigned this prior probability",
                    },
                    "inclusion_criteria": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Criteria that support this diagnosis",
                    },
                    "exclusion_criteria": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Criteria that would rule out this diagnosis",
                    },
                    "planned_tests": {
                        "type": "array",
                        "items": planned_diagnostic_test_input_schema(),
                        "description": (
                            "Typed pending tests bound by the server to the newly "
                            "created hypothesis; free-text gaps are not equivalent"
                        ),
                    },
                },
                "required": [
                    "session_id",
                    "diagnosis",
                    "clinical_reasoning",
                    "differential_diagnoses_considered",
                    "uncertainty_factors",
                    "confidence_rationale",
                ],
            },
        ),
        Tool(
            name="rc_link_evidence_to_hypothesis",
            description=(
                "Link one evidence item to one hypothesis with Bayesian updating. "
                "The supplied LR is applied directly: normally >1 for supports and <1 for contradicts."
            ),
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
                        "description": (
                            "Applied likelihood ratio: LR+ (>1) if supports, "
                            "LR- (<1) if contradicts; it is never inverted by the server"
                        ),
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
                "required": [
                    "session_id",
                    "hypothesis_id",
                    "exclusion_reason",
                    "excluded_by",
                ],
            },
        ),
    ]
