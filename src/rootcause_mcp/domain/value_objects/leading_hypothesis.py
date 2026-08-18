"""Typed, auditable selection of the current leading diagnosis."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LeadingHypothesisSelection(BaseModel):
    """One explicit change to the clinician/agent-maintained leading diagnosis."""

    selection_id: str = Field(
        default_factory=lambda: f"LHS-{uuid4().hex[:8]}",
        pattern=r"^LHS-[A-Za-z0-9_-]+$",
        max_length=64,
    )
    hypothesis_id: str = Field(
        ...,
        pattern=r"^HYP-[A-Za-z0-9_-]+$",
        max_length=64,
    )
    previous_hypothesis_id: str | None = Field(
        default=None,
        pattern=r"^HYP-[A-Za-z0-9_-]+$",
        max_length=64,
    )
    reason: str = Field(..., min_length=10, max_length=1000)
    changed_by: str = Field(..., min_length=1, max_length=128)
    changed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("reason", "changed_by")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        """Reject whitespace-only audit fields."""
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("Leading-hypothesis selection fields cannot be blank")
        return normalized

    @field_validator("changed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        """Keep selection history chronologically portable."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("changed_at must include a timezone offset")
        return value

    model_config = ConfigDict(frozen=True, extra="forbid")
