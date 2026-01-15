"""
Fishbone Diagram Entities.

Represents the Fishbone (Ishikawa) diagram structure with 6M categories.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from rootcause_mcp.domain.value_objects.identifiers import (
    FishboneId,
    SessionId,
    CauseId,
)
from rootcause_mcp.domain.value_objects.enums import FishboneCategoryType
from rootcause_mcp.domain.value_objects.scores import ConfidenceScore


@dataclass
class FishboneCause:
    """
    A cause within a Fishbone category.

    Supports hierarchical structure for sub-causes.
    """

    # Identity
    cause_id: CauseId
    category: FishboneCategoryType

    # Content
    description: str
    sub_causes: list[str] = field(default_factory=list)

    # HFACS Mapping
    hfacs_code: str | None = None
    hfacs_confidence: ConfidenceScore | None = None

    # Evidence & Verification
    evidence: list[str] = field(default_factory=list)
    confidence: ConfidenceScore | None = None
    verified: bool = False

    # Hierarchy
    depth: int = 1

    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class FishboneCategory:
    """
    A category (bone) in the Fishbone diagram.

    Represents one of the 6M categories containing multiple causes.
    """

    category: FishboneCategoryType
    causes: list[FishboneCause] = field(default_factory=list)

    def add_cause(self, cause: FishboneCause) -> None:
        """Add a cause to this category."""
        self.causes.append(cause)

    def remove_cause(self, cause_id: CauseId) -> bool:
        """Remove a cause by ID."""
        for i, cause in enumerate(self.causes):
            if cause.cause_id == cause_id:
                self.causes.pop(i)
                return True
        return False

    def get_cause(self, cause_id: CauseId) -> FishboneCause | None:
        """Get a cause by ID."""
        for cause in self.causes:
            if cause.cause_id == cause_id:
                return cause
        return None

    @property
    def cause_count(self) -> int:
        """Get number of causes in this category."""
        return len(self.causes)

    @property
    def has_causes(self) -> bool:
        """Check if category has any causes."""
        return len(self.causes) > 0


@dataclass
class Fishbone:
    """
    Complete Fishbone Diagram.

    Contains all 6M categories and their causes.
    """

    # Identity
    id: FishboneId
    session_id: SessionId

    # Content
    problem_statement: str  # The "fish head"
    categories: dict[FishboneCategoryType, FishboneCategory] = field(
        default_factory=dict
    )

    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        """Initialize all 6M categories."""
        if not self.categories:
            for cat_type in FishboneCategoryType:
                self.categories[cat_type] = FishboneCategory(category=cat_type)

    # === Category Management ===

    def get_category(self, category: FishboneCategoryType) -> FishboneCategory:
        """Get a specific category."""
        return self.categories[category]

    def add_cause_to_category(
        self,
        category: FishboneCategoryType,
        cause: FishboneCause,
    ) -> None:
        """Add a cause to a specific category."""
        self.categories[category].add_cause(cause)
        self._touch()

    def remove_cause(
        self,
        category: FishboneCategoryType,
        cause_id: CauseId,
    ) -> bool:
        """Remove a cause from a category."""
        result = self.categories[category].remove_cause(cause_id)
        if result:
            self._touch()
        return result

    # === Queries ===

    @property
    def total_cause_count(self) -> int:
        """Get total number of causes across all categories."""
        return sum(cat.cause_count for cat in self.categories.values())

    @property
    def populated_categories(self) -> list[FishboneCategoryType]:
        """Get list of categories that have causes."""
        return [
            cat_type
            for cat_type, cat in self.categories.items()
            if cat.has_causes
        ]

    @property
    def empty_categories(self) -> list[FishboneCategoryType]:
        """Get list of categories without causes."""
        return [
            cat_type
            for cat_type, cat in self.categories.items()
            if not cat.has_causes
        ]

    @property
    def coverage_ratio(self) -> float:
        """Get ratio of populated categories (0.0 - 1.0)."""
        return len(self.populated_categories) / len(FishboneCategoryType)

    def get_all_causes(self) -> list[FishboneCause]:
        """Get all causes from all categories."""
        causes: list[FishboneCause] = []
        for category in self.categories.values():
            causes.extend(category.causes)
        return causes

    def get_verified_causes(self) -> list[FishboneCause]:
        """Get all verified causes."""
        return [cause for cause in self.get_all_causes() if cause.verified]

    def get_causes_by_hfacs_level(self, level_prefix: str) -> list[FishboneCause]:
        """Get causes filtered by HFACS level prefix (e.g., 'OI', 'US', 'PC', 'UA')."""
        return [
            cause
            for cause in self.get_all_causes()
            if cause.hfacs_code and cause.hfacs_code.startswith(level_prefix)
        ]

    # === Private Methods ===

    def _touch(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now(timezone.utc)

    # === Factory Methods ===

    @classmethod
    def create(
        cls,
        session_id: SessionId,
        problem_statement: str,
    ) -> "Fishbone":
        """Factory method to create a new Fishbone diagram."""
        return cls(
            id=FishboneId.generate(),
            session_id=session_id,
            problem_statement=problem_statement,
        )

    # === Export ===

    def to_dict(self) -> dict[str, object]:
        """Export Fishbone to dictionary format."""
        return {
            "fishbone_id": str(self.id),
            "problem_statement": self.problem_statement,
            "categories": [
                {
                    "category": cat_type.value,
                    "causes": [
                        {
                            "cause_id": str(cause.cause_id),
                            "description": cause.description,
                            "sub_causes": cause.sub_causes,
                            "hfacs_code": cause.hfacs_code,
                            "evidence": cause.evidence,
                            "verified": cause.verified,
                        }
                        for cause in cat.causes
                    ],
                }
                for cat_type, cat in self.categories.items()
                if cat.has_causes
            ],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
