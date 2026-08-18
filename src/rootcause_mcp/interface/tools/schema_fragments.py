"""Reusable JSON Schema fragments shared by discrete and condensed tools."""

from __future__ import annotations

from typing import Any

from rootcause_mcp.domain.entities.hypothesis import (
    DiagnosticCertainty,
    DiagnosticReasoningBasis,
    DiagnosticRole,
    LikelihoodRatioCalibrationStatus,
    MechanismCategory,
)
from rootcause_mcp.domain.value_objects.case_manifest import CaseInputManifest
from rootcause_mcp.domain.value_objects.clinical_temporal import (
    ClinicalTemporalKind,
    ClinicalTemporalPrecision,
    TimezoneProvenance,
)
from rootcause_mcp.domain.value_objects.differential_breadth import (
    DifferentialBreadthAudit,
)


def case_input_manifest_schema() -> dict[str, Any]:
    """Return a fresh JSON Schema for the versioned multi-source handoff."""
    return CaseInputManifest.model_json_schema()


def differential_breadth_audit_input_schema() -> dict[str, Any]:
    """Return the authoritative typed systematic-DDx audit schema."""
    return DifferentialBreadthAudit.model_json_schema()


def clinical_temporal_input_schema() -> dict[str, Any]:
    """Return the shared source-faithful clinical temporal input schema."""
    nullable_string = {
        "anyOf": [
            {"type": "string", "minLength": 1, "maxLength": 1000},
            {"type": "null"},
        ]
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "description": (
            "Typed source time. Only kind='instant' with an explicit source "
            "timezone offset is chronologically sortable or can support a "
            "causation-temporality check. Date, range, relative, and unknown "
            "remain valid evidence without negative or ordering inference."
        ),
        "properties": {
            "kind": {
                "type": "string",
                "enum": [item.value for item in ClinicalTemporalKind],
            },
            "raw_value": {
                **nullable_string,
                "description": (
                    "Exact source time expression; null only when the source "
                    "contains no time expression and kind='unknown'."
                ),
            },
            "precision": {
                "type": "string",
                "enum": [item.value for item in ClinicalTemporalPrecision],
                "description": (
                    "Optional caller hint; the server derives and emits canonical "
                    "precision from the supplied representation."
                ),
            },
            "normalized_start": {
                **nullable_string,
                "description": (
                    "Required for a range when raw_value is not an ISO start/end "
                    "pair; use YYYY-MM-DD or an aware ISO datetime."
                ),
            },
            "normalized_end": {
                **nullable_string,
                "description": (
                    "Required for a range when raw_value is not an ISO start/end "
                    "pair; use the same date/aware-datetime domain as start."
                ),
            },
            "timezone_provenance": {
                "type": "string",
                "enum": [item.value for item in TimezoneProvenance],
                "description": (
                    "Optional caller declaration; the server derives the safe "
                    "canonical value and never assumes a timezone."
                ),
            },
        },
        "required": ["kind", "raw_value"],
        "allOf": [
            {
                "if": {"properties": {"kind": {"const": "instant"}}},
                "then": {
                    "properties": {
                        "raw_value": {
                            "type": "string",
                            "pattern": (
                                r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}"
                                r"(?::\d{2}(?:\.\d{1,9})?)?"
                                r"(?:Z|[+-]\d{2}:\d{2})$"
                            ),
                        }
                    }
                },
            },
            {
                "if": {"properties": {"kind": {"const": "date"}}},
                "then": {
                    "properties": {
                        "raw_value": {
                            "type": "string",
                            "format": "date",
                        }
                    }
                },
            },
            {
                "if": {"properties": {"kind": {"const": "range"}}},
                "then": {
                    "properties": {"raw_value": {"type": "string"}},
                },
            },
            {
                "if": {"properties": {"kind": {"const": "relative"}}},
                "then": {
                    "properties": {"raw_value": {"type": "string"}},
                },
            },
        ],
    }


def timeline_event_input_schema() -> dict[str, Any]:
    """Return a custom timeline-event shape with explicit temporal semantics."""
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "id": {"type": "string"},
            "content": {
                "type": "string",
                "description": "Clinical event or finding description",
            },
            "temporal": clinical_temporal_input_schema(),
            "event_timestamp": {
                "type": "string",
                "format": "date-time",
                "description": (
                    "Legacy alias for an aware temporal.kind='instant' only."
                ),
            },
            "time": {
                "type": "string",
                "description": (
                    "Legacy display label. Without temporal/event_timestamp it is "
                    "retained as unknown local time and is never chronologically sorted."
                ),
            },
            "phase": {
                "type": "string",
                "description": "Clinical phase/stage for grouping (optional)",
            },
            "source_document": {
                "type": "string",
                "description": "Source document ID (optional)",
            },
            "verified": {
                "type": "boolean",
                "description": "Whether source provenance was checked (optional)",
            },
            "evidence_type": {"type": "string"},
        },
        "required": ["content"],
    }


def planned_diagnostic_test_input_schema() -> dict[str, Any]:
    """Return the proposal-time shape for a typed diagnostic test disposition."""
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "name": {
                "type": "string",
                "minLength": 1,
                "maxLength": 200,
                "description": "Diagnostic test or observation to obtain",
            },
            "purpose": {
                "type": "string",
                "enum": ["DISCONFIRM", "RULE_OUT", "CONFIRM", "DISCRIMINATE"],
                "description": "Typed relationship of the test to the hypothesis",
            },
            "expected_supporting_result": {
                "type": "string",
                "minLength": 1,
                "maxLength": 500,
                "description": "Result pattern that would support the hypothesis",
            },
            "expected_refuting_result": {
                "type": "string",
                "minLength": 1,
                "maxLength": 500,
                "description": "Result pattern that would refute the hypothesis",
            },
            "status": {
                "type": "string",
                "enum": ["PLANNED", "ORDERED"],
                "default": "PLANNED",
                "description": "Pending test lifecycle state",
            },
        },
        "required": [
            "name",
            "purpose",
            "expected_supporting_result",
            "expected_refuting_result",
            "status",
        ],
    }


def likelihood_ratio_calibration_input_properties() -> dict[str, Any]:
    """Return direct-LR admission metadata shared by both tool surfaces."""
    return {
        "calibration_status": {
            "type": "string",
            "enum": [item.value for item in LikelihoodRatioCalibrationStatus],
            "description": (
                "SOURCE_CALIBRATED requires a verified local evidence-ledger "
                "calibration record; "
                "QUANTITATIVELY_UNKNOWN requires direct likelihood_ratio=1.0 and "
                "does not count as support/refutation."
            ),
        },
        "calibration_source_ref": {
            "type": "string",
            "pattern": "^EVD-[A-Za-z0-9_-]+$",
            "maxLength": 64,
            "description": (
                "EVD-* ID of a verified LITERATURE record in this case evidence "
                "ledger. The record must preserve the exact quantitative snippet, "
                "document location, extraction method, and content hash. Citation-"
                "looking caller strings are not admitted."
            ),
        },
    }


def hypothesis_classification_input_properties() -> dict[str, Any]:
    """Return shared typed DDx-classification properties for proposal tools."""
    return {
        "mechanism_category": {
            "type": "string",
            "enum": [item.value for item in MechanismCategory],
            "default": MechanismCategory.UNKNOWN.value,
            "description": (
                "Broad etiologic mechanism. UNKNOWN is valid during preliminary "
                "investigation but does not count toward final DDx breadth."
            ),
        },
        "diagnostic_role": {
            "type": "string",
            "enum": [item.value for item in DiagnosticRole],
            "default": DiagnosticRole.UNKNOWN.value,
            "description": (
                "Role of the candidate: etiologic disease/process, observed "
                "syndrome, downstream complication, mimic, or unknown."
            ),
        },
        "certainty": {
            "type": "string",
            "enum": [item.value for item in DiagnosticCertainty],
            "default": DiagnosticCertainty.UNKNOWN.value,
            "description": (
                "Explicit qualitative certainty. It is never inferred from a "
                "default or uncalibrated numeric probability."
            ),
        },
        "reasoning_basis": {
            "type": "string",
            "enum": [item.value for item in DiagnosticReasoningBasis],
            "default": DiagnosticReasoningBasis.UNKNOWN.value,
            "description": (
                "Whether the diagnosis itself is source-documented, is a "
                "mechanism inference from observations, or has unknown basis."
            ),
        },
    }
