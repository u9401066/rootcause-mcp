"""
Thinking Step Entity (Deep Reasoning Tracking).

Captures the Agent's internal thought process, not just the final conclusion.
This is the key to transforming "thin MCP" into "cognitive MCP".
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ThinkingType(str, Enum):
    """Type of thinking step."""

    # Hypothesis space exploration
    HYPOTHESIS_CONSIDERED = "HYPOTHESIS_CONSIDERED"  # Considering a hypothesis
    HYPOTHESIS_REJECTED = "HYPOTHESIS_REJECTED"  # Rejecting a hypothesis
    HYPOTHESIS_DEFERRED = "HYPOTHESIS_DEFERRED"  # Deferring judgment

    # Evidence evaluation
    EVIDENCE_WEIGHTED = "EVIDENCE_WEIGHTED"  # Evaluating evidence importance
    EVIDENCE_CONFLICTED = "EVIDENCE_CONFLICTED"  # Handling conflicting evidence
    EVIDENCE_GAP_IDENTIFIED = "EVIDENCE_GAP_IDENTIFIED"  # Missing evidence

    # Reasoning strategies
    ANALOGY_USED = "ANALOGY_USED"  # Using clinical analogy
    PATTERN_RECOGNIZED = "PATTERN_RECOGNIZED"  # Pattern matching
    RULE_APPLIED = "RULE_APPLIED"  # Applying clinical rule
    HEURISTIC_USED = "HEURISTIC_USED"  # Using heuristic

    # Meta-cognition
    UNCERTAINTY_ACKNOWLEDGED = "UNCERTAINTY_ACKNOWLEDGED"  # Acknowledging uncertainty
    ASSUMPTION_QUESTIONED = "ASSUMPTION_QUESTIONED"  # Questioning assumptions
    BIAS_IDENTIFIED = "BIAS_IDENTIFIED"  # Identifying cognitive bias
    ALTERNATIVE_CONSIDERED = "ALTERNATIVE_CONSIDERED"  # Considering alternatives

    # Decision points
    DECISION_POINT = "DECISION_POINT"  # Critical decision point
    BRANCH_EXPLORED = "BRANCH_EXPLORED"  # Exploring a reasoning branch
    BRANCH_PRUNED = "BRANCH_PRUNED"  # Pruning a reasoning branch


class AlternativeConsidered(BaseModel):
    """An alternative that was considered but not chosen."""

    alternative: str = Field(..., description="The alternative option")
    reason_rejected: str = Field(..., description="Why this alternative was rejected")
    confidence_if_chosen: float | None = Field(
        None, ge=0, le=1, description="Confidence if this alternative was chosen"
    )

    model_config = {"frozen": True}


class ThinkingStep(BaseModel):
    """
    A single step in the Agent's thinking process.

    This captures the "why" behind decisions, not just the "what".

    Examples:
        >>> step = ThinkingStep(
        ...     thinking_type=ThinkingType.HYPOTHESIS_CONSIDERED,
        ...     content="Considering pulmonary embolism due to sudden dyspnea",
        ...     internal_reasoning="Dyspnea + tachycardia + recent surgery → PE risk factors present",
        ...     alternatives=[
        ...         AlternativeConsidered(
        ...             alternative="Pneumonia",
        ...             reason_rejected="No fever, no productive cough",
        ...             confidence_if_chosen=0.3
        ...         )
        ...     ],
        ...     confidence=0.65,
        ...     uncertainty_factors=["No D-dimer yet", "No CT-PA"]
        ... )
    """

    # Identity
    id: str = Field(default_factory=lambda: f"THINK-{uuid4().hex[:8]}")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Type
    thinking_type: ThinkingType = Field(..., description="Type of thinking step")

    # Content (what Agent is thinking)
    content: str = Field(..., min_length=1, description="What the Agent is thinking")

    # Internal reasoning (why Agent thinks this way)
    internal_reasoning: str = Field(
        ..., min_length=10, description="Agent's internal reasoning process"
    )

    # Alternatives considered (what else Agent thought about)
    alternatives: list[AlternativeConsidered] = Field(
        default_factory=list, description="Alternatives considered but not chosen"
    )

    # Confidence & Uncertainty
    confidence: float | None = Field(
        default=None,
        ge=0,
        le=1,
        description=(
            "Optional caller-supplied compatibility metadata; never inferred or "
            "presented as clinical confidence"
        ),
    )
    uncertainty_factors: list[str] = Field(
        default_factory=list, description="Factors contributing to uncertainty"
    )

    # Context
    related_evidence_ids: list[str] = Field(
        default_factory=list, description="Evidence being considered"
    )
    related_hypothesis_ids: list[str] = Field(
        default_factory=list, description="Hypotheses being evaluated"
    )

    # Meta-cognition
    assumptions_made: list[str] = Field(
        default_factory=list, description="Assumptions underlying this thinking"
    )
    potential_biases: list[str] = Field(
        default_factory=list,
        description="Cognitive biases that might affect this thinking",
    )

    # Structured data (for machine processing)
    structured_data: dict[str, Any] = Field(
        default_factory=dict, description="Additional structured data"
    )

    def to_human_readable(self) -> str:
        """
        Convert to human-readable format.

        Returns:
            Formatted string for clinicians to review
        """
        lines = [
            f"💭 {self.thinking_type.value}",
            f"   {self.content}",
            "",
            f"   Reasoning: {self.internal_reasoning}",
        ]

        if self.alternatives:
            lines.append("")
            lines.append("   Alternatives Considered:")
            for alt in self.alternatives:
                lines.append(f"     - {alt.alternative}")
                lines.append(f"       Rejected because: {alt.reason_rejected}")

        if self.uncertainty_factors:
            lines.append("")
            lines.append("   Uncertainty Factors:")
            for factor in self.uncertainty_factors:
                lines.append(f"     - {factor}")

        if self.assumptions_made:
            lines.append("")
            lines.append("   Assumptions:")
            for assumption in self.assumptions_made:
                lines.append(f"     - {assumption}")

        if self.potential_biases:
            lines.append("")
            lines.append("   ⚠️  Potential Biases:")
            for bias in self.potential_biases:
                lines.append(f"     - {bias}")

        return "\n".join(lines)

    model_config = {"frozen": False}


class ThinkingChain(BaseModel):
    """
    Complete chain of thinking steps.

    This is the "cognitive layer" that makes Agent reasoning transparent.
    """

    session_id: str = Field(..., description="RCA session ID")
    steps: list[ThinkingStep] = Field(default_factory=list)

    def add_step(self, step: ThinkingStep) -> None:
        """Add a thinking step."""
        self.steps.append(step)

    def get_decision_points(self) -> list[ThinkingStep]:
        """Get all critical decision points."""
        return [s for s in self.steps if s.thinking_type == ThinkingType.DECISION_POINT]

    def get_rejected_hypotheses(self) -> list[str]:
        """Get all hypotheses that were considered but rejected."""
        rejected = []
        for step in self.steps:
            if step.thinking_type == ThinkingType.HYPOTHESIS_REJECTED:
                rejected.append(step.content)
        return rejected

    def get_uncertainty_map(self) -> dict[str, list[str]]:
        """
        Get map of uncertainties by hypothesis.

        Returns:
            Dict mapping hypothesis_id → list of uncertainty factors
        """
        uncertainty_map: dict[str, list[str]] = {}

        for step in self.steps:
            for hyp_id in step.related_hypothesis_ids:
                if hyp_id not in uncertainty_map:
                    uncertainty_map[hyp_id] = []
                uncertainty_map[hyp_id].extend(step.uncertainty_factors)

        return uncertainty_map

    def get_bias_report(self) -> list[str]:
        """Get all identified potential biases."""
        all_biases = []
        for step in self.steps:
            all_biases.extend(step.potential_biases)
        return list(set(all_biases))  # Unique biases

    def get_assumption_report(self) -> list[str]:
        """Get all assumptions made during reasoning."""
        all_assumptions = []
        for step in self.steps:
            all_assumptions.extend(step.assumptions_made)
        return list(set(all_assumptions))  # Unique assumptions

    def export_for_review(self) -> str:
        """
        Export thinking chain for human expert review.

        Returns:
            Formatted report suitable for M&M conference presentation
        """
        lines = [
            "=" * 80,
            "CLINICAL REASONING AUDIT TRAIL",
            "=" * 80,
            f"Session: {self.session_id}",
            f"Total Thinking Steps: {len(self.steps)}",
            "",
        ]

        # Decision points
        decision_points = self.get_decision_points()
        if decision_points:
            lines.append("🎯 KEY DECISION POINTS:")
            for i, dp in enumerate(decision_points, 1):
                lines.append(f"  {i}. {dp.content}")
            lines.append("")

        # Rejected hypotheses
        rejected = self.get_rejected_hypotheses()
        if rejected:
            lines.append("❌ HYPOTHESES CONSIDERED BUT REJECTED:")
            for hyp in rejected:
                lines.append(f"  - {hyp}")
            lines.append("")

        # Uncertainties
        uncertainty_map = self.get_uncertainty_map()
        if uncertainty_map:
            lines.append("⚠️  UNCERTAINTY MAP:")
            for hyp_id, factors in uncertainty_map.items():
                lines.append(f"  {hyp_id}:")
                for factor in factors:
                    lines.append(f"    - {factor}")
            lines.append("")

        # Biases
        biases = self.get_bias_report()
        if biases:
            lines.append("🧠 POTENTIAL COGNITIVE BIASES IDENTIFIED:")
            for bias in biases:
                lines.append(f"  - {bias}")
            lines.append("")

        # Assumptions
        assumptions = self.get_assumption_report()
        if assumptions:
            lines.append("📋 ASSUMPTIONS MADE:")
            for assumption in assumptions:
                lines.append(f"  - {assumption}")
            lines.append("")

        # Detailed steps
        lines.append("=" * 80)
        lines.append("DETAILED THINKING STEPS")
        lines.append("=" * 80)
        lines.append("")

        for i, step in enumerate(self.steps, 1):
            lines.append(f"Step {i} [{step.timestamp.strftime('%H:%M:%S')}]:")
            lines.append(step.to_human_readable())
            lines.append("")

        return "\n".join(lines)

    model_config = {"frozen": False}
