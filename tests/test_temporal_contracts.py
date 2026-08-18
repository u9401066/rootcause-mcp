"""Regression tests for canonical clinical and causal temporality inputs."""

from __future__ import annotations

import pytest

from rootcause_mcp import server_v2
from rootcause_mcp.application.server_state import ServerState
from rootcause_mcp.interface.handlers.evidence_handlers import EvidenceHandlers
from rootcause_mcp.interface.handlers.verification_handlers import VerificationHandlers
from rootcause_mcp.interface.tools.condensed_tools import get_condensed_tools
from rootcause_mcp.interface.tools.evidence_tools import get_evidence_tools
from rootcause_mcp.interface.tools.verification_tools import get_verification_tools


@pytest.mark.parametrize(
    "invalid_timestamp",
    ["2026-08-17", "2026-08-17T08:15:00"],
)
@pytest.mark.asyncio
async def test_evidence_rejects_date_only_and_naive_canonical_timestamp(
    invalid_timestamp: str,
) -> None:
    handler = EvidenceHandlers(ServerState())

    response = await handler.handle_add_evidence(
        {
            "session_id": "invalid-event-time",
            "content": "Timing is not known precisely",
            "event_timestamp": invalid_timestamp,
            "auto_verify": False,
        }
    )
    mcp_result = server_v2._to_call_tool_result(response)

    assert response["status"] == "error"
    assert mcp_result.is_error is True
    assert "containing 'T'" in response["message"]
    assert "timezone offset" in response["message"]
    assert "use temporal.kind" in response["message"]


@pytest.mark.parametrize(
    ("invalid_event", "expected_field"),
    [
        ("cause", "cause.timestamp"),
        ("effect", "effect.timestamp"),
    ],
)
@pytest.mark.asyncio
async def test_causation_rejects_unreliable_temporality_as_explicit_mcp_error(
    invalid_event: str,
    expected_field: str,
) -> None:
    cause_timestamp = "2026-08-17T08:00:00Z"
    effect_timestamp = "2026-08-17T08:15:00+00:00"
    if invalid_event == "cause":
        cause_timestamp = "2026-08-17"
    else:
        effect_timestamp = "2026-08-17T08:15:00"

    response = await VerificationHandlers().handle_verify_causation(
        {
            "session_id": "invalid-causal-time",
            "cause": {
                "description": "Potential exposure",
                "timestamp": cause_timestamp,
            },
            "effect": {
                "description": "Observed deterioration",
                "timestamp": effect_timestamp,
            },
        }
    )
    mcp_result = server_v2._to_call_tool_result(response)

    assert mcp_result.is_error is True
    assert mcp_result.structured_content is not None
    assert mcp_result.structured_content["status"] == "error"
    assert response[0].text.startswith(f"Error: {expected_field} must be")
    assert "timezone offset" in response[0].text


def test_discrete_and_condensed_schemas_describe_strict_temporality() -> None:
    evidence_schema = next(
        tool for tool in get_evidence_tools() if tool.name == "rc_add_evidence"
    ).input_schema
    causation_schema = next(
        tool for tool in get_verification_tools() if tool.name == "rc_verify_causation"
    ).input_schema
    timeline_schema = next(
        tool for tool in get_verification_tools() if tool.name == "rc_render_timeline"
    ).input_schema
    condensed = {tool.name: tool for tool in get_condensed_tools()}

    descriptions = [
        evidence_schema["properties"]["event_timestamp"]["description"],
        causation_schema["properties"]["cause"]["properties"]["timestamp"][
            "description"
        ],
        causation_schema["properties"]["effect"]["properties"]["timestamp"][
            "description"
        ],
        condensed["rc_evidence"].input_schema["properties"]["event_timestamp"][
            "description"
        ],
        condensed["rc_audit"].input_schema["properties"]["cause"]["description"],
        condensed["rc_audit"].input_schema["properties"]["effect"]["description"],
    ]

    assert all("'T'" in description for description in descriptions)
    assert all("timezone offset" in description for description in descriptions)

    for tool_schema in (
        evidence_schema,
        condensed["rc_evidence"].input_schema,
    ):
        temporal = tool_schema["properties"]["temporal"]
        assert temporal["additionalProperties"] is False
        assert temporal["properties"]["kind"]["enum"] == [
            "instant",
            "date",
            "range",
            "relative",
            "unknown",
        ]

    for event_schema in (
        timeline_schema["properties"]["events"]["items"],
        condensed["rc_diagram"].input_schema["properties"]["events"]["items"],
    ):
        assert event_schema["additionalProperties"] is False
        assert event_schema["properties"]["temporal"]["properties"]["kind"]["enum"] == [
            "instant",
            "date",
            "range",
            "relative",
            "unknown",
        ]
