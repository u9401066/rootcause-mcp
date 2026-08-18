"""
Differential Diagnosis MCP Tools.

Tools for proposing hypotheses, linking evidence, and getting ranked diagnoses.
"""

from __future__ import annotations

from mcp.types import Tool

from rootcause_mcp.interface.tools.schema_fragments import (
    differential_breadth_audit_input_schema,
    hypothesis_classification_input_properties,
    likelihood_ratio_calibration_input_properties,
    planned_diagnostic_test_input_schema,
)


def get_dd_tools() -> list[Tool]:
    """Get all differential diagnosis tools."""
    return [
        Tool(
            name="rc_propose_hypothesis",
            description=(
                "Propose one differential diagnosis with explicit reasoning and "
                "uncertainty. Omission of prior_probability uses a neutral 0.5 "
                "UNCALIBRATED implementation baseline; it is not a patient-specific "
                "clinical probability or certainty label."
            ),
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
                        "description": (
                            "Numeric Bayesian starting value. Omission uses a neutral "
                            "0.5 UNCALIBRATED implementation baseline, not a clinical "
                            "probability or certainty label."
                        ),
                        "default": 0.5,
                    },
                    "must_not_miss": {
                        "type": "boolean",
                        "description": "Mark an explicitly reviewed high-harm diagnosis that must be ruled out",
                        "default": False,
                    },
                    **hypothesis_classification_input_properties(),
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
                                "disposition": {
                                    "type": "string",
                                    "enum": ["CONTEXT_ONLY", "REJECTED", "UNKNOWN"],
                                },
                                "rationale": {"type": "string"},
                                "reason_rejected": {
                                    "type": "string",
                                    "description": "Deprecated legacy field",
                                },
                                "likelihood_if_not_rejected": {
                                    "type": "string",
                                    "enum": ["high", "moderate", "low"],
                                    "description": "Deprecated uncalibrated legacy field",
                                },
                            },
                        },
                        "description": (
                            "DEPRECATED context-only notes. Propose every plausible "
                            "candidate as its own hypothesis. This array cannot replace "
                            "rc_audit_differential_breadth or justify exclusion."
                        ),
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
                        "description": (
                            "REQUIRED: Why the candidate is considered and the "
                            "calibration/source limitations of any numeric prior"
                        ),
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
                    "uncertainty_factors",
                    "confidence_rationale",
                ],
            },
        ),
        Tool(
            name="rc_audit_differential_breadth",
            description=(
                "Persist a systematic differential-breadth audit. Select a "
                "syndrome-appropriate framework, review every canonical cell, "
                "retain insufficient data with planned discriminators, and record "
                "why expansion stopped. This proves coverage, not diagnostic truth."
            ),
            input_schema={
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "RCA session ID",
                    },
                    "audit": differential_breadth_audit_input_schema(),
                },
                "required": ["session_id", "audit"],
            },
        ),
        Tool(
            name="rc_link_evidence_to_hypothesis",
            description=(
                "Link one evidence item to one hypothesis with Bayesian updating. "
                "The supplied LR is applied directly: >1 supports, <1 refutes, "
                "and 1.0 is neutral. A non-neutral LR additionally needs a verified "
                "local literature calibration evidence record."
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
                        "type": ["boolean", "null"],
                        "description": (
                            "True only with LR>1, false only with LR<1, and null "
                            "with neutral LR=1. Omit to derive this direction from LR."
                        ),
                        "default": None,
                    },
                    "rationale": {
                        "type": "string",
                        "description": (
                            "Clinical justification plus source/calibration limitation; "
                            "required by the handler whenever LR is not neutral 1.0"
                        ),
                    },
                    **likelihood_ratio_calibration_input_properties(),
                },
                "required": [
                    "session_id",
                    "evidence_id",
                    "hypothesis_id",
                    "calibration_status",
                ],
                "allOf": [
                    {
                        "if": {
                            "properties": {
                                "calibration_status": {"const": "SOURCE_CALIBRATED"}
                            },
                            "required": ["calibration_status"],
                        },
                        "then": {"required": ["calibration_source_ref"]},
                    }
                ],
            },
        ),
        Tool(
            name="rc_get_differential_diagnosis",
            description=(
                "Get the differential diagnosis in stable working-ledger order; "
                "uncalibrated compatibility values are never used for rank or filtering"
            ),
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
                        "description": (
                            "Deprecated compatibility argument; accepted but ignored "
                            "because no calibrated clinical probability is established"
                        ),
                        "default": 0.01,
                    },
                },
                "required": ["session_id"],
            },
        ),
        Tool(
            name="rc_select_leading_hypothesis",
            description=(
                "Explicitly select one ACTIVE or CONFIRMED hypothesis as the "
                "current leading diagnosis. This appends a typed audit record; "
                "numeric compatibility values and array order never select a lead."
            ),
            input_schema={
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "session_id": {"type": "string"},
                    "hypothesis_id": {
                        "type": "string",
                        "pattern": "^HYP-[A-Za-z0-9_-]+$",
                    },
                    "reason": {
                        "type": "string",
                        "minLength": 10,
                        "maxLength": 1000,
                        "description": "Why this candidate is selected as leading now",
                    },
                    "changed_by": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 128,
                        "description": "Auditable agent/reviewer identity",
                    },
                },
                "required": [
                    "session_id",
                    "hypothesis_id",
                    "reason",
                    "changed_by",
                ],
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
