"""
ReasoningStep Entity for Chain-of-Thought Tracking.

Records every reasoning step in the medical analysis process:
- What was thought (reasoning content)
- Why it was thought (rationale)
- What evidence was considered
- What action was taken
- Who performed the reasoning (Agent ID)
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from rootcause_mcp.domain.value_objects.identifiers import ReasoningStepId


class ReasoningStepType(str, Enum):
    """Type of reasoning step."""

    OBSERVATION = "OBSERVATION"  # Observing data/evidence
    HYPOTHESIS_GENERATION = "HYPOTHESIS_GENERATION"  # Proposing a hypothesis
    EVIDENCE_LINKING = "EVIDENCE_LINKING"  # Linking evidence to hypothesis
    BAYESIAN_UPDATE = "BAYESIAN_UPDATE"  # Updating probability
    HYPOTHESIS_ELIMINATION = "HYPOTHESIS_ELIMINATION"  # Ruling out a hypothesis
    HYPOTHESIS_CONFIRMATION = "HYPOTHESIS_CONFIRMATION"  # Confirming a hypothesis
    QUESTION_ASKING = "QUESTION_ASKING"  # Asking for more information
    DECISION = "DECISION"  # Making a clinical decision
    REFLECTION = "REFLECTION"  # Reflecting on reasoning process


class ReasoningStep(BaseModel):
    """
    A single step in the chain of medical reasoning.

    Examples:
        >>> step = ReasoningStep(
        ...     step_type=ReasoningStepType.HYPOTHESIS_GENERATION,
        ...     content="Considering cardiogenic shock due to recent CABG",
        ...     rationale="Patient had recent cardiac surgery, now hypotensive",
        ...     evidence_ids=["EVD-001", "EVD-002"],
        ...     hypothesis_ids=["HYP-001"],
        ...     agent_id="claude-sonnet-4.5",
        ...     sequence_number=3
        ... )
    """

    # Identity
    id: ReasoningStepId = Field(default_factory=lambda: ReasoningStepId(f"RS-{uuid4().hex[:8]}"))

    # Temporal ordering
    sequence_number: int = Field(..., ge=1, description="Order in reasoning chain (1-based)")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Content
    step_type: ReasoningStepType = Field(..., description="Type of reasoning step")
    content: str = Field(..., min_length=1, description="What was reasoned")
    rationale: str = Field(..., min_length=1, description="Why this reasoning step")

    # Context
    evidence_ids: list[str] = Field(
        default_factory=list, description="Evidence considered in this step"
    )
    hypothesis_ids: list[str] = Field(
        default_factory=list, description="Hypotheses affected by this step"
    )
    cause_ids: list[str] = Field(
        default_factory=list, description="Causes identified in this step"
    )

    # Actor
    agent_id: str = Field(..., description="ID of the AI agent performing reasoning")
    agent_model: str | None = Field(None, description="Model version (e.g., 'claude-sonnet-4.5')")

    # Metadata
    confidence: float | None = Field(
        None, ge=0, le=1, description="Agent's confidence in this reasoning step"
    )
    tokens_used: int | None = Field(None, ge=0, description="LLM tokens consumed")

    # Structured chain-of-thought (optional, for detailed tracking)
    chain_of_thought: dict[str, Any] | None = Field(
        None,
        description="Structured CoT data (e.g., intermediate calculations, alternatives considered)",
    )

    @field_validator("content", "rationale")
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """Ensure content and rationale are not empty."""
        if not v.strip():
            raise ValueError("Content and rationale cannot be empty")
        return v.strip()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return self.model_dump(mode="json", exclude_none=True)

    model_config = {"frozen": False}  # Mutable entity


class ReasoningChain(BaseModel):
    """
    Complete chain of reasoning steps for a clinical case.

    Provides:
    - Temporal ordering
    - Audit trail
    - Reasoning quality metrics
    """

    session_id: str = Field(..., description="RCA session ID")
    steps: list[ReasoningStep] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    finalized_at: datetime | None = Field(None)

    def add_step(self, step: ReasoningStep) -> None:
        """
        Add a reasoning step to the chain.

        Args:
            step: ReasoningStep to add

        Raises:
            ValueError: If chain is finalized or sequence number is wrong
        """
        if self.finalized_at is not None:
            raise ValueError("Cannot add step to finalized reasoning chain")

        expected_seq = len(self.steps) + 1
        if step.sequence_number != expected_seq:
            raise ValueError(
                f"Expected sequence_number={expected_seq}, got {step.sequence_number}"
            )

        self.steps.append(step)

    def finalize(self) -> None:
        """
        Finalize the reasoning chain (make immutable).

        After finalization, no more steps can be added.
        """
        if self.finalized_at is not None:
            raise ValueError("Reasoning chain already finalized")

        self.finalized_at = datetime.now(UTC)

    def get_steps_by_type(self, step_type: ReasoningStepType) -> list[ReasoningStep]:
        """Get all steps of a specific type."""
        return [s for s in self.steps if s.step_type == step_type]

    def get_steps_for_hypothesis(self, hypothesis_id: str) -> list[ReasoningStep]:
        """Get all steps that affected a specific hypothesis."""
        return [s for s in self.steps if hypothesis_id in s.hypothesis_ids]

    def get_steps_using_evidence(self, evidence_id: str) -> list[ReasoningStep]:
        """Get all steps that used a specific evidence."""
        return [s for s in self.steps if evidence_id in s.evidence_ids]

    def get_reasoning_duration_seconds(self) -> float:
        """Calculate total reasoning duration in seconds."""
        if not self.steps:
            return 0.0

        start = self.steps[0].timestamp
        end = self.steps[-1].timestamp
        return (end - start).total_seconds()

    def get_quality_metrics(self) -> dict[str, Any]:
        """
        Calculate reasoning quality metrics.

        Returns:
            Dictionary with metrics:
            - total_steps: Number of reasoning steps
            - unique_hypotheses: Number of unique hypotheses considered
            - unique_evidence: Number of unique evidence items used
            - avg_confidence: Average confidence across steps
            - hypothesis_coverage: Ratio of steps that reference hypotheses
            - evidence_coverage: Ratio of steps that reference evidence
        """
        if not self.steps:
            return {
                "total_steps": 0,
                "unique_hypotheses": 0,
                "unique_evidence": 0,
                "avg_confidence": None,
                "hypothesis_coverage": 0.0,
                "evidence_coverage": 0.0,
            }

        all_hypotheses = set()
        all_evidence = set()
        confidences = []
        steps_with_hypotheses = 0
        steps_with_evidence = 0

        for step in self.steps:
            all_hypotheses.update(step.hypothesis_ids)
            all_evidence.update(step.evidence_ids)

            if step.confidence is not None:
                confidences.append(step.confidence)

            if step.hypothesis_ids:
                steps_with_hypotheses += 1

            if step.evidence_ids:
                steps_with_evidence += 1

        return {
            "total_steps": len(self.steps),
            "unique_hypotheses": len(all_hypotheses),
            "unique_evidence": len(all_evidence),
            "avg_confidence": sum(confidences) / len(confidences) if confidences else None,
            "hypothesis_coverage": steps_with_hypotheses / len(self.steps),
            "evidence_coverage": steps_with_evidence / len(self.steps),
            "duration_seconds": self.get_reasoning_duration_seconds(),
        }

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return self.model_dump(mode="json", exclude_none=True)

    model_config = {"frozen": False}


# Convenience constructors
class ReasoningStepBuilder:
    """Builder for creating reasoning steps with auto-incremented sequence numbers."""

    def __init__(self, agent_id: str, agent_model: str | None = None):
        """Initialize builder."""
        self.agent_id = agent_id
        self.agent_model = agent_model
        self.sequence_counter = 0

    def observation(
        self,
        content: str,
        rationale: str,
        evidence_ids: list[str] | None = None,
        confidence: float | None = None,
    ) -> ReasoningStep:
        """Create an observation step."""
        self.sequence_counter += 1
        return ReasoningStep(
            step_type=ReasoningStepType.OBSERVATION,
            content=content,
            rationale=rationale,
            evidence_ids=evidence_ids or [],
            hypothesis_ids=[],
            cause_ids=[],
            agent_id=self.agent_id,
            agent_model=self.agent_model,
            sequence_number=self.sequence_counter,
            confidence=confidence,
            tokens_used=None,
            chain_of_thought=None,
        )

    def hypothesis_generation(
        self,
        content: str,
        rationale: str,
        hypothesis_ids: list[str],
        evidence_ids: list[str] | None = None,
        confidence: float | None = None,
    ) -> ReasoningStep:
        """Create a hypothesis generation step."""
        self.sequence_counter += 1
        return ReasoningStep(
            step_type=ReasoningStepType.HYPOTHESIS_GENERATION,
            content=content,
            rationale=rationale,
            evidence_ids=evidence_ids or [],
            hypothesis_ids=hypothesis_ids,
            cause_ids=[],
            agent_id=self.agent_id,
            agent_model=self.agent_model,
            sequence_number=self.sequence_counter,
            confidence=confidence,
            tokens_used=None,
            chain_of_thought=None,
        )

    def bayesian_update(
        self,
        content: str,
        rationale: str,
        hypothesis_ids: list[str],
        evidence_ids: list[str],
        confidence: float | None = None,
    ) -> ReasoningStep:
        """Create a Bayesian update step."""
        self.sequence_counter += 1
        return ReasoningStep(
            step_type=ReasoningStepType.BAYESIAN_UPDATE,
            content=content,
            rationale=rationale,
            evidence_ids=evidence_ids,
            hypothesis_ids=hypothesis_ids,
            cause_ids=[],
            agent_id=self.agent_id,
            agent_model=self.agent_model,
            sequence_number=self.sequence_counter,
            confidence=confidence,
            tokens_used=None,
            chain_of_thought=None,
        )
