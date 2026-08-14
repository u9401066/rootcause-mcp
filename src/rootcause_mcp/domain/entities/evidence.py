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

    @classmethod
    def from_str(cls, val: str | EvidenceType) -> EvidenceType:
        """Parse or normalize string value to EvidenceType with alias support."""
        if isinstance(val, cls):
            return val
        norm = str(val).strip().upper().replace(" ", "_")
        aliases = {
            "DOC": cls.DOCUMENT,
            "DOCUMENT": cls.DOCUMENT,
            "FILE": cls.DOCUMENT,
            "CHART": cls.DOCUMENT,
            "OBSERVATION": cls.OBSERVATION,
            "PHYSICAL_EXAM": cls.OBSERVATION,
            "CLINICAL": cls.OBSERVATION,
            "LAB": cls.LAB_RESULT,
            "LABS": cls.LAB_RESULT,
            "LAB_RESULT": cls.LAB_RESULT,
            "IMAGE": cls.IMAGING,
            "IMAGING": cls.IMAGING,
            "ECHO": cls.IMAGING,
            "TEE": cls.IMAGING,
            "CT": cls.IMAGING,
            "XRAY": cls.IMAGING,
            "INTERVIEW": cls.INTERVIEW,
            "LOG": cls.DEVICE_LOG,
            "DEVICE_LOG": cls.DEVICE_LOG,
            "WAVEFORM": cls.DEVICE_LOG,
            "MONITOR": cls.DEVICE_LOG,
            "MED": cls.MEDICATION_RECORD,
            "MEDICATION": cls.MEDICATION_RECORD,
            "MEDICATION_RECORD": cls.MEDICATION_RECORD,
            "MAR": cls.MEDICATION_RECORD,
            "LITERATURE": cls.LITERATURE,
            "GUIDELINE": cls.LITERATURE,
            "EXPERT": cls.EXPERT_OPINION,
            "EXPERT_OPINION": cls.EXPERT_OPINION,
        }
        return aliases.get(norm, cls.OTHER)


class EvidenceSource(BaseModel):
    """
    Evidence source provenance.

    Tracks where the evidence came from, verbatim raw snippet, checksum, and who collected it.
    """

    document_id: str | None = Field(
        default=None, description="Document identifier (e.g., file path, record ID)"
    )
    location: str | None = Field(
        default=None,
        description="Specific location within document (e.g., 'Line 42', 'Page 3, Para 2')",
    )
    raw_snippet: str | None = Field(
        default=None,
        description="Exact literal quote or data text extracted verbatim from the source document",
    )
    content_hash: str | None = Field(
        default=None,
        description="SHA-256 cryptographic digest of the raw snippet or source record",
    )
    extraction_method: str | None = Field(
        default=None,
        description="Extraction method (e.g., 'verbatim_quote', 'table_cell', 'structured_field')",
    )
    collected_by: str = Field(
        ..., description="Person/system that collected this evidence"
    )
    collection_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When evidence was collected (UTC)",
    )
    source_system: str | None = Field(
        default=None,
        description="Source system (e.g., 'Epic', 'Cerner', 'Manual Entry')",
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
        ...         raw_snippet="08:30,BP,75/40,HR,120",
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
        default=None, description="Clinical context (e.g., 'Post-op Day 1 hypotension')"
    )

    # Quality
    quality: EvidenceQuality = Field(..., description="Evidence quality grading")

    # Source
    source: EvidenceSource = Field(..., description="Evidence provenance")

    # Temporal
    event_timestamp: datetime | None = Field(
        default=None, description="When the clinical event occurred (if applicable)"
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

    # Metadata & Verification
    verified: bool = Field(
        default=False, description="Has this evidence been independently verified?"
    )
    verifier: str | None = Field(default=None, description="Who verified this evidence")
    verification_method: str | None = Field(
        default=None,
        description="Method of verification (e.g., 'EXACT_SNIPPET_MATCH', 'MANUAL_REVIEWER')",
    )
    matched_lines: list[int] = Field(
        default_factory=list,
        description="1-based line numbers in the raw file where snippet was verified",
    )
    verification_timestamp: datetime | None = Field(default=None)

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

    def mark_verified(
        self,
        verifier: str,
        verification_method: str = "MANUAL_REVIEWER",
        matched_lines: list[int] | None = None,
        content_hash: str | None = None,
    ) -> Self:
        """
        Mark evidence as independently verified with provenance audit details.

        Args:
            verifier: ID/name of the person or automated service verifying
            verification_method: Verification method used
            matched_lines: 1-based line numbers where quote was located
            content_hash: SHA-256 hash of verified snippet

        Returns:
            New Evidence instance with verification status
        """
        updated_source = self.source
        if content_hash and self.source.content_hash != content_hash:
            updated_source = self.source.model_copy(
                update={"content_hash": content_hash}
            )

        return self.model_copy(
            update={
                "verified": True,
                "verifier": verifier,
                "verification_method": verification_method,
                "matched_lines": matched_lines or self.matched_lines,
                "verification_timestamp": datetime.now(UTC),
                "source": updated_source,
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
