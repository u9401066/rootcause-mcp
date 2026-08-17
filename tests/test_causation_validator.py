"""Safety-focused tests for counterfactual causation verification."""

from datetime import UTC, datetime, timedelta

from rootcause_mcp.domain.services.causation_validator import (
    CausationValidator,
    CauseEvent,
    VerificationLevel,
)
from rootcause_mcp.domain.value_objects.enums import VerificationResult
from rootcause_mcp.interface.handlers.verification_handlers import (
    VerificationHandlers,
)


def test_reverse_temporality_rejects_causal_claim() -> None:
    now = datetime.now(UTC)
    result = CausationValidator().validate(
        cause=CauseEvent(description="Proposed cause", timestamp=now),
        effect=CauseEvent(
            description="Observed effect",
            timestamp=now - timedelta(minutes=5),
        ),
    )

    assert result.overall_result is VerificationResult.REJECTED
    assert result.tests.temporality is not None
    assert not result.tests.temporality.passed


def test_unsubstantiated_counterfactual_is_not_fully_verified() -> None:
    result = CausationValidator().validate(
        cause=CauseEvent(description="Proposed cause"),
        effect=CauseEvent(description="Observed effect"),
        level=VerificationLevel.COMPREHENSIVE,
    )

    assert result.overall_result is VerificationResult.INSUFFICIENT_DATA
    assert result.tests.temporality is not None
    assert not result.tests.temporality.passed
    assert result.tests.necessity is not None
    assert not result.tests.necessity.passed
    assert result.tests.mechanism is not None
    assert not result.tests.mechanism.passed
    assert result.caveats


async def test_mcp_handler_uses_domain_validator() -> None:
    content = await VerificationHandlers().handle_verify_causation(
        {
            "session_id": "case-001",
            "cause": {"description": "Proposed cause"},
            "effect": {"description": "Observed effect"},
            "verification_level": "comprehensive",
        }
    )

    text = content[0].text
    assert "INSUFFICIENT_DATA" in text
    assert "**Necessity:** False" in text
    assert "**Mechanism:** False" in text
