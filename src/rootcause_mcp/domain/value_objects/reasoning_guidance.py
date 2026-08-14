"""
Reasoning Guidance Value Object.

Provides structured, actionable next steps and completeness checklists
to guide AI agents (especially lighter Flash/mini models) through multi-loop clinical reasoning.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ReasoningStage(str, Enum):
    """Clinical reasoning progression stages."""

    EVIDENCE_COLLECTION = "EVIDENCE_COLLECTION"
    DIFFERENTIAL_EXPANSION = "DIFFERENTIAL_EXPANSION"
    BAYESIAN_EVALUATION = "BAYESIAN_EVALUATION"
    COGNITIVE_AUDIT = "COGNITIVE_AUDIT"
    READY_FOR_SYNTHESIS = "READY_FOR_SYNTHESIS"


class ReasoningGuidance(BaseModel):
    """
    Actionable guidance contract for AI agents.

    Harnesses lower-tier / Flash-level models by providing explicit checklists,
    missing prerequisites, push questions, and recommended next tool calls.
    """

    session_id: str = Field(..., description="RCA session ID")
    current_stage: ReasoningStage = Field(..., description="Current reasoning stage")
    stage_display: str = Field(..., description="Human-readable stage title")
    completeness_score: float = Field(
        ..., ge=0.0, le=1.0, description="Overall progress toward defensible reasoning (0.0 - 1.0)"
    )
    checklist: dict[str, Any] = Field(
        default_factory=dict, description="Detailed readiness checklist items"
    )
    missing_prerequisites: list[str] = Field(
        default_factory=list, description="Missing steps required for a complete reasoning chain"
    )
    next_recommended_actions: list[str] = Field(
        default_factory=list, description="Explicit tool call instructions for the agent's next turn"
    )
    push_questions: list[str] = Field(
        default_factory=list, description="Socratic clinical push questions to deepen reasoning"
    )
    is_ready_for_report: bool = Field(
        False, description="True if the reasoning state fulfills minimal audit requirements"
    )

    model_config = {"frozen": True}
