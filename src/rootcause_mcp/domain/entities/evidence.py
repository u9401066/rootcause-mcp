"""
Evidence Entity (First-Class Citizen).

Structured evidence with:
- Source tracking (file, line, timestamp, collector)
- Quality grading (Strength × Reliability)
- Chain of custody
- Many-to-many linking with Causes and Hypotheses
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any, Self
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from rootcause_mcp.domain.value_objects.evidence_quality import EvidenceQuality
from rootcause_mcp.domain.value_objects.identifiers import EvidenceId


class EvidenceType(str, Enum):
    """Type of evidence."""

    DOCUMENT = "DOCUMENT"  # Chart, flowsheet, report
    OBSERVATION = "OBSERVATION"  # Direct clinical observation
    LAB_RESULT = "LAB_RESULT"  # Laboratory test result
    IMAGING = "IMAGING"  # Radiology, pathology images
    INTERVIEW = "INTERVIEW"  # Staff/patient interview
    DEVICE_LOG = "DEVICE_LOG"  # Monitor, ventilator, pump log
    MEDICATION_RECORD = "MEDICATION_RECORD"  # MAR, e-prescribing
    LITERATURE = "LITERATURE"  # Published research, guideline
    EXPERT_OPINION = "EXPERT_OPINION"  # Expert consultation
    OTHER = "OTHER"


class EvidenceSource(BaseModel):
    """
    Evidence source provenance.

    Tracks where the evidence came from and who collected it.
    """

    document_id: str | None = Field(
        None, description="Document identifier (e.g., file path, record ID)"
    )
    location: str | None = Field(
        None,
        description="Specific location within document (e.g., 'Line 42', 'Page 3, Para 2')",
    )
    collected_by: str = Field(
        ..., description="Person/system that collected this evidence"
    )
    collection_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When evidence was collected (UTC)",
    )
    source_system: str | None = Field(
        None, description="Source system (e.g., 'Epic', 'Cerner', 'Manual Entry')"
    )

    model_config = {"frozen": True}


class Evidence(BaseModel):
    """
    First-class Evidence entity.

    Examples:
        >>> evidence = Evidence(
        ...     content="08:30 BP 75/40 mmHg, HR 120 bpm",
        ...     evidence_type=EvidenceType.DOCUMENT,
        ...     quality=EvidenceQuality(
        ...         strength=EvidenceStrength.STRONG,
        ...         reliability=EvidenceReliability.GRADE_A
        ...     ),
        ...     source=EvidenceSource(
        ...         document_id="nursing_flowsheet.csv",
        ...         location="Line 42",
        ...         collected_by="RN_CHEN"
        ...     ),
        ...     clinical_context="Post-op hypotension"
        ... )
    """

    # Identity
    id: EvidenceId = Field(default_factory=lambda: EvidenceId(f"EVD-{uuid4().hex[:8]}"))

    # Content
    content: str = Field(..., min_length=1, description="Evidence content/description")
    evidence_type: EvidenceType = Field(..., description="Type of evidence")
    clinical_context: str | None = Field(
        None, description="Clinical context (e.g., 'Post-op Day 1 hypotension')"
    )

    # Quality
    quality: EvidenceQuality = Field(..., description="Evidence quality grading")

    # Source
    source: EvidenceSource = Field(..., description="Evidence provenance")

    # Temporal
    event_timestamp: datetime | None = Field(
        None, description="When the clinical event occurred (if applicable)"
    )

    # Relationships (IDs only, actual linking done via repositories)
    supports_cause_ids: list[str] = Field(
        default_factory=list, description="Cause IDs this evidence supports"
    )
    supports_hypothesis_ids: list[str] = Field(
        default_factory=list, description="Hypothesis IDs this evidence supports"
    )
    contradicts_hypothesis_ids: list[str] = Field(
        default_factory=list, description="Hypothesis IDs this evidence contradicts"
    )

    # Metadata
    verified: bool = Field(
        False, description="Has this evidence been independently verified?"
    )
    verifier: str | None = Field(None, description="Who verified this evidence")
    verification_timestamp: datetime | None = Field(None)

    tags: list[str] = Field(
        default_factory=list, description="Custom tags for categorization"
    )

    @field_validator("content")
    @classmethod
    def validate_content_not_empty(cls, v: str) -> str:
        """Ensure content is not just whitespace."""
        if not v.strip():
            raise ValueError("Evidence content cannot be empty or whitespace")
        return v.strip()

    def link_to_cause(self, cause_id: str) -> Self:
        """
        Link this evidence to a cause (returns new instance).

        Args:
            cause_id: ID of the cause to link

        Returns:
            New Evidence instance with updated supports_cause_ids
        """
        if cause_id not in self.supports_cause_ids:
            updated_ids = [*self.supports_cause_ids, cause_id]
            return self.model_copy(update={"supports_cause_ids": updated_ids})
        return self

    def link_to_hypothesis(self, hypothesis_id: str, supports: bool = True) -> Self:
        """
        Link this evidence to a hypothesis (supports or contradicts).

        Args:
            hypothesis_id: ID of the hypothesis
            supports: If True, evidence supports hypothesis; if False, contradicts it

        Returns:
            New Evidence instance with updated links
        """
        if supports:
            if hypothesis_id not in self.supports_hypothesis_ids:
                updated_ids = [*self.supports_hypothesis_ids, hypothesis_id]
                return self.model_copy(update={"supports_hypothesis_ids": updated_ids})
        elif hypothesis_id not in self.contradicts_hypothesis_ids:
            updated_ids = [*self.contradicts_hypothesis_ids, hypothesis_id]
            return self.model_copy(update={"contradicts_hypothesis_ids": updated_ids})
        return self

    def mark_verified(self, verifier: str) -> Self:
        """
        Mark evidence as independently verified.

        Args:
            verifier: ID/name of the person verifying

        Returns:
            New Evidence instance with verification status
        """
        return self.model_copy(
            update={
                "verified": True,
                "verifier": verifier,
                "verification_timestamp": datetime.now(UTC),
            }
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return self.model_dump(mode="json", exclude_none=True)

    model_config = {"frozen": False}  # Mutable entity (ID-based identity)


# Convenience constructors
class DocumentEvidence:
    """Pre-configured document evidence builder."""

    @staticmethod
    def from_chart(
        content: str,
        document_id: str,
        location: str,
        collected_by: str,
        event_timestamp: datetime | None = None,
    ) -> Evidence:
        """Create evidence from clinical chart/flowsheet."""
        from rootcause_mcp.domain.value_objects.evidence_quality import (
            EvidenceQuality,
            EvidenceReliability,
            EvidenceStrength,
        )

        return Evidence(
            content=content,
            evidence_type=EvidenceType.DOCUMENT,
            clinical_context=None,
            quality=EvidenceQuality(
                strength=EvidenceStrength.STRONG,
                reliability=EvidenceReliability.GRADE_A,
            ),
            source=EvidenceSource(
                document_id=document_id,
                location=location,
                collected_by=collected_by,
                source_system=None,
            ),
            event_timestamp=event_timestamp,
            verified=False,
            verifier=None,
            verification_timestamp=None,
        )
