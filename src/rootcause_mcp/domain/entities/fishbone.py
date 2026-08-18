"""
Fishbone Diagram Entities.

Represents the Fishbone (Ishikawa) diagram structure with 6M categories.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from rootcause_mcp.domain.value_objects.enums import (
    FishboneCategoryType,
    HFACSReviewStatus,
)
from rootcause_mcp.domain.value_objects.hfacs import is_valid_hfacs_code
from rootcause_mcp.domain.value_objects.identifiers import (
    CauseId,
    FishboneId,
    SessionId,
)
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
    hfacs_review_status: HFACSReviewStatus = HFACSReviewStatus.UNREVIEWED
    hfacs_reviewed_by: str | None = None
    hfacs_reviewed_at: datetime | None = None
    hfacs_review_reason: str | None = None

    # Evidence & Verification
    evidence: list[str] = field(default_factory=list)
    confidence: ConfidenceScore | None = None
    verified: bool = False

    # Hierarchy
    depth: int = 1

    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        """Reject impossible persisted HFACS review states."""
        self.hfacs_review_status = HFACSReviewStatus(self.hfacs_review_status)
        if self.hfacs_review_status is HFACSReviewStatus.UNREVIEWED:
            if any(
                value is not None
                for value in (
                    self.hfacs_reviewed_by,
                    self.hfacs_reviewed_at,
                    self.hfacs_review_reason,
                )
            ):
                raise ValueError("UNREVIEWED HFACS state cannot carry review metadata")
            return
        if not self.hfacs_reviewed_by or not self.hfacs_reviewed_by.strip():
            raise ValueError("Reviewed HFACS state requires reviewed_by")
        if self.hfacs_reviewed_at is None or (
            self.hfacs_reviewed_at.tzinfo is None
            or self.hfacs_reviewed_at.utcoffset() is None
        ):
            raise ValueError("Reviewed HFACS state requires timezone-aware reviewed_at")
        if not self.hfacs_review_reason or not self.hfacs_review_reason.strip():
            raise ValueError("Reviewed HFACS state requires a review reason")
        if self.hfacs_review_status is HFACSReviewStatus.CONFIRMED:
            if not self.hfacs_code or not is_valid_hfacs_code(self.hfacs_code):
                raise ValueError(
                    "CONFIRMED HFACS state requires a recognized HFACS code"
                )
        elif (
            self.hfacs_review_status is HFACSReviewStatus.NOT_APPLICABLE
            and self.hfacs_code is not None
        ):
            raise ValueError("NOT_APPLICABLE HFACS state cannot carry a code")

    def review_hfacs(
        self,
        *,
        status: HFACSReviewStatus,
        hfacs_code: str | None,
        reviewed_by: str,
        reason: str,
        reviewed_at: datetime | None = None,
    ) -> None:
        """Persist an identified human disposition for this cause's HFACS mapping."""
        if status is HFACSReviewStatus.UNREVIEWED:
            raise ValueError("HFACS review cannot be persisted as UNREVIEWED")
        timestamp = reviewed_at or datetime.now(UTC)
        candidate = FishboneCause(
            cause_id=self.cause_id,
            category=self.category,
            description=self.description,
            sub_causes=list(self.sub_causes),
            hfacs_code=hfacs_code,
            hfacs_confidence=self.hfacs_confidence,
            hfacs_review_status=status,
            hfacs_reviewed_by=reviewed_by,
            hfacs_reviewed_at=timestamp,
            hfacs_review_reason=reason,
            evidence=list(self.evidence),
            confidence=self.confidence,
            verified=self.verified,
            depth=self.depth,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )
        self.hfacs_code = candidate.hfacs_code
        self.hfacs_review_status = candidate.hfacs_review_status
        self.hfacs_reviewed_by = candidate.hfacs_reviewed_by
        self.hfacs_reviewed_at = candidate.hfacs_reviewed_at
        self.hfacs_review_reason = candidate.hfacs_review_reason
        self.updated_at = timestamp


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
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

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
        return [cat_type for cat_type, cat in self.categories.items() if cat.has_causes]

    @property
    def empty_categories(self) -> list[FishboneCategoryType]:
        """Get list of categories without causes."""
        return [
            cat_type for cat_type, cat in self.categories.items() if not cat.has_causes
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

    def review_cause_hfacs(
        self,
        cause_id: CauseId,
        *,
        status: HFACSReviewStatus,
        hfacs_code: str | None,
        reviewed_by: str,
        reason: str,
        reviewed_at: datetime | None = None,
    ) -> FishboneCause:
        """Apply one identified HFACS review to exactly one persisted cause."""
        matches = [
            cause for cause in self.get_all_causes() if cause.cause_id == cause_id
        ]
        if len(matches) != 1:
            raise ValueError(
                f"Expected exactly one Fishbone cause {cause_id}; found {len(matches)}"
            )
        cause = matches[0]
        cause.review_hfacs(
            status=status,
            hfacs_code=hfacs_code,
            reviewed_by=reviewed_by,
            reason=reason,
            reviewed_at=reviewed_at,
        )
        self._touch()
        return cause

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
        self.updated_at = datetime.now(UTC)

    # === Factory Methods ===

    @classmethod
    def create(
        cls,
        session_id: SessionId,
        problem_statement: str,
    ) -> Fishbone:
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
                            "hfacs_review_status": cause.hfacs_review_status.value,
                            "hfacs_reviewed_by": cause.hfacs_reviewed_by,
                            "hfacs_reviewed_at": (
                                cause.hfacs_reviewed_at.isoformat()
                                if cause.hfacs_reviewed_at
                                else None
                            ),
                            "hfacs_review_reason": cause.hfacs_review_reason,
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
