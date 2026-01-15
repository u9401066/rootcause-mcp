"""
Cause Entity.

Represents a cause in the RCA analysis, which can be linked to
Fishbone categories and HFACS codes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from rootcause_mcp.domain.value_objects.identifiers import CauseId, SessionId
from rootcause_mcp.domain.value_objects.scores import ConfidenceScore
from rootcause_mcp.domain.value_objects.enums import FishboneCategoryType
from rootcause_mcp.domain.value_objects.hfacs import HFACSCode, is_valid_hfacs_code


@dataclass
class Cause:
    """
    Cause Entity.

    Represents a single cause identified during RCA analysis.
    Supports hierarchical structure (cause -> sub-causes).
    """

    # Identity
    id: CauseId
    session_id: SessionId

    # Core Content (Level 1 - Required)
    description: str
    category: FishboneCategoryType

    # HFACS Mapping (Level 2 - System Suggested)
    hfacs_code: str | None = None
    hfacs_confidence: ConfidenceScore | None = None

    # Evidence & Verification (Level 3 - Optional)
    evidence: list[str] = field(default_factory=list)
    verified: bool = False
    confidence: ConfidenceScore | None = None

    # Hierarchy
    parent_id: CauseId | None = None
    depth: int = 1  # Depth from problem statement (1-5)

    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        """Validate cause data."""
        if self.depth < 1 or self.depth > 5:
            raise ValueError(f"Cause depth must be 1-5, got: {self.depth}")
        if self.hfacs_code and not is_valid_hfacs_code(self.hfacs_code):
            raise ValueError(f"Invalid HFACS code: {self.hfacs_code}")

    # === HFACS Management ===

    def set_hfacs(self, code: str, confidence: float = 0.5) -> None:
        """Set HFACS code with confidence."""
        if not is_valid_hfacs_code(code):
            raise ValueError(f"Invalid HFACS code: {code}")
        self.hfacs_code = code
        self.hfacs_confidence = ConfidenceScore(confidence)
        self._touch()

    def get_hfacs(self) -> HFACSCode | None:
        """Get full HFACS code object."""
        if self.hfacs_code:
            return HFACSCode.from_code(self.hfacs_code)
        return None

    # === Evidence Management ===

    def add_evidence(self, evidence: str) -> None:
        """Add evidence supporting this cause."""
        if evidence not in self.evidence:
            self.evidence.append(evidence)
            self._touch()

    def remove_evidence(self, evidence: str) -> None:
        """Remove evidence."""
        if evidence in self.evidence:
            self.evidence.remove(evidence)
            self._touch()

    # === Verification ===

    def verify(self, confidence: float = 0.8) -> None:
        """Mark cause as verified."""
        self.verified = True
        self.confidence = ConfidenceScore(confidence)
        self._touch()

    def unverify(self) -> None:
        """Mark cause as unverified."""
        self.verified = False
        self.confidence = None
        self._touch()

    # === Queries ===

    @property
    def has_evidence(self) -> bool:
        """Check if cause has supporting evidence."""
        return len(self.evidence) > 0

    @property
    def is_root_cause(self) -> bool:
        """Check if this is at root level (no parent)."""
        return self.parent_id is None

    @property
    def confidence_level(self) -> str:
        """Get confidence level as string."""
        if self.confidence:
            return self.confidence.to_level()
        return "unknown"

    # === Private Methods ===

    def _touch(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now(timezone.utc)

    # === Factory Methods ===

    @classmethod
    def create(
        cls,
        session_id: SessionId,
        description: str,
        category: FishboneCategoryType,
        parent_id: CauseId | None = None,
        depth: int = 1,
    ) -> "Cause":
        """Factory method to create a new Cause."""
        return cls(
            id=CauseId.generate(),
            session_id=session_id,
            description=description,
            category=category,
            parent_id=parent_id,
            depth=depth,
        )
