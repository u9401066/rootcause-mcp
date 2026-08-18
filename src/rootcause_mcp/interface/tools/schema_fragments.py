"""Reusable JSON Schema fragments shared by discrete and condensed tools."""

from __future__ import annotations

from typing import Any

from rootcause_mcp.domain.value_objects.case_manifest import CaseInputManifest


def case_input_manifest_schema() -> dict[str, Any]:
    """Return a fresh JSON Schema for the versioned multi-source handoff."""
    return CaseInputManifest.model_json_schema()


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
