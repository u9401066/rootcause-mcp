"""
SQLModel Database Models.

ORM models for SQLite persistence.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlmodel import Field, SQLModel, Column, JSON


class SessionModel(SQLModel, table=True):
    """SQLModel for RCA Session."""

    __tablename__ = "sessions"  # type: ignore[assignment]

    # Primary Key
    id: str = Field(primary_key=True)  # SessionId string value

    # Core Fields
    case_type: str  # CaseType enum value
    case_title: str
    current_stage: str  # Stage enum value
    status: str  # SessionStatus enum value

    # Content
    problem_statement: str = ""
    initial_description: str = ""

    # Stage data stored as JSON
    stage_data: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = ""


class CauseModel(SQLModel, table=True):
    """SQLModel for Cause."""

    __tablename__ = "causes"  # type: ignore[assignment]

    # Primary Key
    id: str = Field(primary_key=True)  # CauseId string value

    # Foreign Key
    session_id: str = Field(index=True)  # SessionId string value

    # Core Fields
    description: str
    category: str  # FishboneCategoryType enum value

    # HFACS
    hfacs_code: str | None = None
    hfacs_confidence: float | None = None

    # Evidence (stored as JSON array)
    evidence: list[str] = Field(default_factory=list, sa_column=Column(JSON))

    # Verification
    verified: bool = False
    confidence: float | None = None

    # Hierarchy
    parent_id: str | None = Field(default=None, index=True)
    depth: int = 1

    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FishboneModel(SQLModel, table=True):
    """SQLModel for Fishbone diagram."""

    __tablename__ = "fishbones"  # type: ignore[assignment]

    # Primary Key
    id: str = Field(primary_key=True)  # FishboneId string value

    # Foreign Key
    session_id: str = Field(unique=True, index=True)  # One fishbone per session

    # Content
    problem_statement: str

    # Categories data stored as JSON
    categories_data: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON)
    )

    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WhyNodeModel(SQLModel, table=True):
    """SQLModel for 5-Why Node."""

    __tablename__ = "why_nodes"  # type: ignore[assignment]

    # Primary Key
    id: str = Field(primary_key=True)  # CauseId string value

    # Foreign Keys
    session_id: str = Field(index=True)
    parent_id: str | None = Field(default=None, index=True)

    # Content
    question: str
    answer: str
    level: int  # 1-5

    # Evidence (stored as JSON array)
    evidence: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    confidence: float | None = None


# ============================================================================
# NEW in v2.0: Medical Reasoning Models
# ============================================================================


class EvidenceModel(SQLModel, table=True):
    """SQLModel for Evidence entity."""

    __tablename__ = "evidence"  # type: ignore[assignment]

    # Primary Key
    id: str = Field(primary_key=True)  # EvidenceId string value

    # Foreign Key
    session_id: str = Field(index=True)

    # Content
    content: str
    evidence_type: str  # EvidenceType enum value
    clinical_context: str | None = None

    # Quality (stored as JSON)
    quality_data: dict[str, Any] = Field(sa_column=Column(JSON))

    # Source (stored as JSON)
    source_data: dict[str, Any] = Field(sa_column=Column(JSON))

    # Temporal
    event_timestamp: datetime | None = None

    # Relationships (stored as JSON arrays)
    supports_cause_ids: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    supports_hypothesis_ids: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    contradicts_hypothesis_ids: list[str] = Field(default_factory=list, sa_column=Column(JSON))

    # Verification
    verified: bool = False
    verifier: str | None = None
    verification_timestamp: datetime | None = None

    # Metadata
    tags: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class HypothesisModel(SQLModel, table=True):
    """SQLModel for Hypothesis entity."""

    __tablename__ = "hypotheses"  # type: ignore[assignment]

    # Primary Key
    id: str = Field(primary_key=True)  # HypothesisId string value

    # Foreign Key
    session_id: str = Field(index=True)

    # Diagnosis (stored as JSON)
    diagnosis_data: dict[str, Any] = Field(sa_column=Column(JSON))

    # Bayesian
    prior_probability: float
    current_probability: float

    # Criteria (stored as JSON arrays)
    inclusion_criteria: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    exclusion_criteria: list[str] = Field(default_factory=list, sa_column=Column(JSON))

    # Evidence linking (stored as JSON arrays)
    likelihood_ratios: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    supporting_evidence_ids: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    contradicting_evidence_ids: list[str] = Field(default_factory=list, sa_column=Column(JSON))

    # Status
    status: str  # HypothesisStatus enum value

    # Audit trail (stored as JSON)
    bayesian_history: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))

    # Metadata
    clinical_rationale: str
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ThinkingStepModel(SQLModel, table=True):
    """SQLModel for ThinkingStep entity."""

    __tablename__ = "thinking_steps"  # type: ignore[assignment]

    # Primary Key
    id: str = Field(primary_key=True)

    # Foreign Key
    session_id: str = Field(index=True)

    # Content
    thinking_type: str  # ThinkingType enum value
    content: str
    internal_reasoning: str

    # Structured data (stored as JSON)
    alternatives: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    uncertainty_factors: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    assumptions_made: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    potential_biases: list[str] = Field(default_factory=list, sa_column=Column(JSON))

    # Confidence
    confidence: float

    # Relationships (stored as JSON arrays)
    related_evidence_ids: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    related_hypothesis_ids: list[str] = Field(default_factory=list, sa_column=Column(JSON))

    # Metadata
    structured_data: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Status
    is_root_cause: bool = False
    needs_further_analysis: bool = True

    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
