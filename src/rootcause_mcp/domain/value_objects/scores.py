"""
Score Value Objects.

Numeric value objects with domain constraints.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Self


@dataclass(frozen=True, slots=True)
class ConfidenceScore:
    """
    Confidence score between 0.0 and 1.0.

    Represents the confidence level of a cause or analysis result.
    """

    value: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.value <= 1.0:
            raise ValueError(
                f"ConfidenceScore must be between 0.0 and 1.0, got: {self.value}"
            )

    @classmethod
    def high(cls) -> Self:
        """Create a high confidence score (0.8)."""
        return cls(0.8)

    @classmethod
    def medium(cls) -> Self:
        """Create a medium confidence score (0.5)."""
        return cls(0.5)

    @classmethod
    def low(cls) -> Self:
        """Create a low confidence score (0.3)."""
        return cls(0.3)

    @classmethod
    def from_string(cls, level: str) -> Self:
        """Create ConfidenceScore from string level."""
        mapping = {
            "high": 0.8,
            "medium": 0.5,
            "low": 0.3,
        }
        if level.lower() not in mapping:
            raise ValueError(f"Unknown confidence level: {level}")
        return cls(mapping[level.lower()])

    def to_level(self) -> str:
        """Convert to string level."""
        if self.value >= 0.7:
            result: str = "high"
        elif self.value >= 0.4:
            result = "medium"
        else:
            result = "low"
        return result

    def __str__(self) -> str:
        return f"{self.value:.2f}"

    def __float__(self) -> float:
        return self.value


@dataclass(frozen=True, slots=True)
class QualityScore:
    """
    Quality score between 0 and 100.

    Used for RCA quality evaluation across multiple dimensions.
    """

    value: int

    def __post_init__(self) -> None:
        if not 0 <= self.value <= 100:
            raise ValueError(
                f"QualityScore must be between 0 and 100, got: {self.value}"
            )

    @classmethod
    def from_percentage(cls, percentage: float) -> Self:
        """Create from percentage (0.0 to 1.0)."""
        return cls(int(percentage * 100))

    def to_grade(self) -> str:
        """Convert to letter grade."""
        if self.value >= 90:
            return "A"
        if self.value >= 80:
            return "B"
        if self.value >= 70:
            return "C"
        if self.value >= 60:
            return "D"
        return "F"

    def __str__(self) -> str:
        return f"{self.value}/100"

    def __int__(self) -> int:
        return self.value
