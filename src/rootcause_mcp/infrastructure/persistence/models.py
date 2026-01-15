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

    # Status
    is_root_cause: bool = False
    needs_further_analysis: bool = True

    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
