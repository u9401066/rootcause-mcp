"""
Hypothesis Entity for Differential Diagnosis.

Implements Bayesian reasoning with:
- Prior probability estimation
- Likelihood ratio (LR) updating
- Evidence-based posterior probability
- Inclusion/exclusion criteria tracking
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Self
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from rootcause_mcp.domain.value_objects.clinical_concept import ClinicalConcept
from rootcause_mcp.domain.value_objects.identifiers import HypothesisId


class HypothesisStatus(str, Enum):
    """Hypothesis lifecycle status."""

    ACTIVE = "ACTIVE"  # Currently being considered
    CONFIRMED = "CONFIRMED"  # Confirmed as the actual diagnosis
    EXCLUDED = "EXCLUDED"  # Ruled out by evidence
    ON_HOLD = "ON_HOLD"  # Temporarily suspended (insufficient evidence)


class LikelihoodRatio(BaseModel):
    """
    Likelihood ratio for evidence given hypothesis.

    LR+ = P(Evidence | Hypothesis True) / P(Evidence | Hypothesis False)
    LR- = P(No Evidence | Hypothesis True) / P(No Evidence | Hypothesis False)
    """

    evidence_id: str = Field(..., description="Evidence ID")
    lr_positive: float = Field(..., gt=0, description="LR+ (evidence present)")
    lr_negative: float | None = Field(None, gt=0, description="LR- (evidence absent)")
    rationale: str = Field(..., description="Why this LR value?")

    @field_validator("lr_positive", "lr_negative")
    @classmethod
    def validate_lr_range(cls, v: float | None) -> float | None:
        """Validate LR is in reasonable range."""
        if v is not None and (v < 0.01 or v > 100):
            raise ValueError(f"LR {v} outside reasonable range [0.01, 100]")
        return v

    model_config = {"frozen": True}


class BayesianUpdate(BaseModel):
    """Record of a single Bayesian update."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    evidence_id: str = Field(..., description="Evidence used for update")
    prior_probability: float = Field(..., ge=0, le=1, description="P(H) before update")
    likelihood_ratio: float = Field(..., gt=0, description="LR applied")
    posterior_probability: float = Field(..., ge=0, le=1, description="P(H|E) after update")
    updated_by: str = Field(..., description="Who performed this update")

    model_config = {"frozen": True}


class Hypothesis(BaseModel):
    """
    Differential Diagnosis Hypothesis with Bayesian updating.

    Examples:
        >>> hyp = Hypothesis(
        ...     diagnosis=ClinicalConcept(
        ...         code="I21.9",
        ...         display="Acute MI",
        ...         system=CodingSystem.ICD_10
        ...     ),
        ...     prior_probability=0.15,
        ...     inclusion_criteria=["Chest pain", "Elevated troponin"],
        ...     exclusion_criteria=["Normal ECG", "Age < 30"]
        ... )
        >>>
        >>> # Apply evidence with LR+ = 5.0
        >>> hyp_updated = hyp.bayesian_update(
        ...     evidence_id="EVD-001",
        ...     likelihood_ratio=5.0,
        ...     updated_by="DR_SMITH"
        ... )
    """

    # Identity
    id: HypothesisId = Field(default_factory=lambda: HypothesisId(f"HYP-{uuid4().hex[:8]}"))

    # Diagnosis
    diagnosis: ClinicalConcept = Field(..., description="Clinical diagnosis concept")

    # Bayesian reasoning
    prior_probability: float = Field(
        ..., ge=0, le=1, description="Prior probability P(H) before any evidence"
    )
    current_probability: float = Field(
        ..., ge=0, le=1, description="Current posterior probability P(H|E)"
    )

    # Criteria
    inclusion_criteria: list[str] = Field(
        default_factory=list, description="Criteria that support this diagnosis"
    )
    exclusion_criteria: list[str] = Field(
        default_factory=list, description="Criteria that rule out this diagnosis"
    )

    # Evidence linking
    likelihood_ratios: list[LikelihoodRatio] = Field(
        default_factory=list, description="LR for each evidence"
    )
    supporting_evidence_ids: list[str] = Field(
        default_factory=list, description="Evidence IDs supporting this hypothesis"
    )
    contradicting_evidence_ids: list[str] = Field(
        default_factory=list, description="Evidence IDs contradicting this hypothesis"
    )

    # Audit trail
    status: HypothesisStatus = Field(default=HypothesisStatus.ACTIVE)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    created_by: str = Field(..., description="Who proposed this hypothesis")

    bayesian_history: list[BayesianUpdate] = Field(
        default_factory=list, description="History of Bayesian updates"
    )

    # Reasoning
    clinical_rationale: str = Field(
        ..., min_length=10, description="Why is this hypothesis being considered?"
    )

    @field_validator("current_probability")
    @classmethod
    def validate_current_matches_prior_on_creation(cls, v: float, info) -> float:
        """Ensure current_probability matches prior on initial creation."""
        # On first creation, current should equal prior
        if "prior_probability" in info.data and not info.data.get("bayesian_history"):
            if abs(v - info.data["prior_probability"]) > 0.001:
                raise ValueError(
                    f"Initial current_probability ({v}) must equal prior_probability "
                    f"({info.data['prior_probability']}) when no Bayesian history exists"
                )
        return v

    def bayesian_update(
        self,
        evidence_id: str,
        likelihood_ratio: float,
        updated_by: str,
        supports: bool = True,
    ) -> Self:
        """
        Perform Bayesian update with new evidence.

        Args:
            evidence_id: ID of evidence
            likelihood_ratio: LR+ or LR- depending on evidence presence
            updated_by: Who performed this update
            supports: If True, use LR+; if False, use 1/LR (or LR-)

        Returns:
            New Hypothesis instance with updated probability

        Mathematical formula:
            Posterior Odds = Prior Odds × LR
            Posterior P = Posterior Odds / (1 + Posterior Odds)
        """
        # Convert probability to odds
        prior_odds = self.current_probability / (1 - self.current_probability)

        # Apply likelihood ratio
        lr = likelihood_ratio if supports else (1.0 / likelihood_ratio)
        posterior_odds = prior_odds * lr

        # Convert back to probability
        posterior_prob = posterior_odds / (1 + posterior_odds)

        # Clamp to [0, 1] to avoid numerical issues
        posterior_prob = max(0.0, min(1.0, posterior_prob))

        # Create update record
        update = BayesianUpdate(
            evidence_id=evidence_id,
            prior_probability=self.current_probability,
            likelihood_ratio=lr,
            posterior_probability=posterior_prob,
            updated_by=updated_by,
        )

        # Update evidence lists
        if supports:
            updated_supporting = [*self.supporting_evidence_ids, evidence_id]
            updated_contradicting = self.contradicting_evidence_ids
        else:
            updated_supporting = self.supporting_evidence_ids
            updated_contradicting = [*self.contradicting_evidence_ids, evidence_id]

        # Return new instance
        return self.model_copy(
            update={
                "current_probability": posterior_prob,
                "bayesian_history": [*self.bayesian_history, update],
                "supporting_evidence_ids": updated_supporting,
                "contradicting_evidence_ids": updated_contradicting,
            }
        )

    def add_likelihood_ratio(
        self,
        evidence_id: str,
        lr_positive: float,
        lr_negative: float | None,
        rationale: str,
    ) -> Self:
        """
        Add likelihood ratio for a piece of evidence.

        Args:
            evidence_id: Evidence ID
            lr_positive: LR when evidence is present
            lr_negative: LR when evidence is absent (optional)
            rationale: Clinical justification for this LR

        Returns:
            New Hypothesis instance with added LR
        """
        lr = LikelihoodRatio(
            evidence_id=evidence_id,
            lr_positive=lr_positive,
            lr_negative=lr_negative,
            rationale=rationale,
        )

        return self.model_copy(update={"likelihood_ratios": [*self.likelihood_ratios, lr]})

    def mark_confirmed(self, confirmed_by: str) -> Self:
        """Mark hypothesis as confirmed."""
        return self.model_copy(update={"status": HypothesisStatus.CONFIRMED})

    def mark_excluded(self, excluded_by: str, reason: str) -> Self:
        """Mark hypothesis as excluded."""
        return self.model_copy(update={"status": HypothesisStatus.EXCLUDED})

    def get_confidence_interval(self, confidence_level: float = 0.95) -> tuple[float, float]:
        """
        Calculate confidence interval for current probability.

        Args:
            confidence_level: Confidence level (default 95%)

        Returns:
            (lower_bound, upper_bound)

        Note:
            This is a simplified approximation. For rigorous CI,
            use Beta distribution based on number of updates.
        """
        n_updates = len(self.bayesian_history)

        if n_updates == 0:
            # No updates yet, wide interval
            return (0.0, 1.0)

        # Approximate standard error (decreases with more updates)
        # This is a heuristic, not a rigorous statistical CI
        se = 1.0 / math.sqrt(n_updates + 1)
        z_score = 1.96 if confidence_level == 0.95 else 2.576  # 95% or 99%

        lower = max(0.0, self.current_probability - z_score * se)
        upper = min(1.0, self.current_probability + z_score * se)

        return (lower, upper)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return self.model_dump(mode="json", exclude_none=True)

    model_config = {"frozen": False}  # Mutable entity


# Convenience constructors
class CardiologyHypotheses:
    """Pre-configured cardiology differential diagnoses."""

    @staticmethod
    def acute_mi(prior: float = 0.15, created_by: str = "system") -> Hypothesis:
        """Acute myocardial infarction hypothesis."""
        from rootcause_mcp.domain.value_objects.clinical_concept import (
            ClinicalConcept,
            CodingSystem,
        )

        return Hypothesis(
            diagnosis=ClinicalConcept(
                code="I21.9",
                display="Acute myocardial infarction, unspecified",
                system=CodingSystem.ICD_10,
                version=None,
            ),
            prior_probability=prior,
            current_probability=prior,
            inclusion_criteria=[
                "Chest pain or angina equivalent",
                "Elevated cardiac biomarkers (troponin)",
                "ECG changes (ST elevation, depression, or Q waves)",
            ],
            exclusion_criteria=[
                "Normal serial troponins",
                "Alternative diagnosis explains symptoms",
            ],
            created_by=created_by,
            clinical_rationale="Acute myocardial infarction should be considered in patients with chest pain and cardiac risk factors.",
        )
