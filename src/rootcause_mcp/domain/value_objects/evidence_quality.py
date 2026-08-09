"""
Evidence Quality Value Object.

Implements Oxford CEBM-inspired evidence grading:
- Strength: How strong is the evidence itself?
- Reliability: How trustworthy is the source?
"""

from __future__ import annotations

from enum import Enum
from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator


class EvidenceStrength(str, Enum):
    """Evidence strength based on study design / source type."""

    STRONG = "STRONG"  # RCT, systematic review, direct observation
    MODERATE = "MODERATE"  # Cohort study, case-control, documented record
    WEAK = "WEAK"  # Case report, expert opinion, hearsay
    ANECDOTAL = "ANECDOTAL"  # Informal observation, unverified claim


class EvidenceReliability(str, Enum):
    """Source reliability grading."""

    GRADE_A = "GRADE_A"  # Primary source, verified, timestamped
    GRADE_B = "GRADE_B"  # Secondary source, documented
    GRADE_C = "GRADE_C"  # Tertiary source, unverified
    GRADE_D = "GRADE_D"  # Hearsay, rumor, unverifiable


class EvidenceQuality(BaseModel):
    """
    Evidence quality as Strength × Reliability matrix.

    Examples:
        - STRONG + GRADE_A = High-quality RCT data
        - WEAK + GRADE_D = Unverified rumor (logically contradictory, should raise error)
    """

    strength: EvidenceStrength = Field(
        ..., description="Evidence strength (internal validity)"
    )
    reliability: EvidenceReliability = Field(
        ..., description="Source reliability (external validity)"
    )

    @model_validator(mode="after")
    def check_logical_consistency(self) -> Self:
        """
        Ensure logical consistency between strength and reliability.

        Raises:
            ValueError: If combination is logically contradictory
        """
        # STRONG evidence cannot come from GRADE_D (hearsay) source
        if (
            self.strength == EvidenceStrength.STRONG
            and self.reliability == EvidenceReliability.GRADE_D
        ):
            raise ValueError(
                "Logically contradictory: STRONG evidence cannot come from GRADE_D source"
            )

        return self

    @property
    def overall_score(self) -> float:
        """
        Calculate overall evidence quality score (0.0 - 1.0).

        Returns:
            Weighted score: strength (60%) + reliability (40%)
        """
        strength_scores = {
            EvidenceStrength.STRONG: 1.0,
            EvidenceStrength.MODERATE: 0.7,
            EvidenceStrength.WEAK: 0.4,
            EvidenceStrength.ANECDOTAL: 0.1,
        }

        reliability_scores = {
            EvidenceReliability.GRADE_A: 1.0,
            EvidenceReliability.GRADE_B: 0.75,
            EvidenceReliability.GRADE_C: 0.5,
            EvidenceReliability.GRADE_D: 0.25,
        }

        s_score = strength_scores[self.strength]
        r_score = reliability_scores[self.reliability]

        return 0.6 * s_score + 0.4 * r_score

    model_config = {"frozen": True}  # Immutable value object


# Convenience constructors
class HighQualityEvidence:
    """Pre-configured high-quality evidence."""

    @staticmethod
    def rct() -> EvidenceQuality:
        """Randomized controlled trial quality."""
        return EvidenceQuality(
            strength=EvidenceStrength.STRONG,
            reliability=EvidenceReliability.GRADE_A,
        )

    @staticmethod
    def systematic_review() -> EvidenceQuality:
        """Systematic review quality."""
        return EvidenceQuality(
            strength=EvidenceStrength.STRONG,
            reliability=EvidenceReliability.GRADE_A,
        )


class LowQualityEvidence:
    """Pre-configured low-quality evidence."""

    @staticmethod
    def hearsay() -> EvidenceQuality:
        """Unverified hearsay."""
        return EvidenceQuality(
            strength=EvidenceStrength.ANECDOTAL,
            reliability=EvidenceReliability.GRADE_D,
        )

    @staticmethod
    def expert_opinion() -> EvidenceQuality:
        """Expert opinion without supporting data."""
        return EvidenceQuality(
            strength=EvidenceStrength.WEAK,
            reliability=EvidenceReliability.GRADE_C,
        )
