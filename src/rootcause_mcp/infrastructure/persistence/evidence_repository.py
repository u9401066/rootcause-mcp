"""
Evidence Repository (SQLite with SQLModel).

Persists Evidence entities to SQLite database.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlmodel import select

from rootcause_mcp.domain.entities.evidence import (
    Evidence,
    EvidenceSource,
    EvidenceType,
)
from rootcause_mcp.domain.value_objects.clinical_temporal import ClinicalTemporal
from rootcause_mcp.domain.value_objects.evidence_quality import EvidenceQuality
from rootcause_mcp.domain.value_objects.identifiers import EvidenceId
from rootcause_mcp.infrastructure.persistence.models import EvidenceModel

if TYPE_CHECKING:
    from rootcause_mcp.infrastructure.persistence.database import Database


class SQLiteEvidenceRepository:
    """SQLite implementation of Evidence repository using SQLModel."""

    def __init__(self, db: Database) -> None:
        """Initialize repository with database connection."""
        self.db = db

    async def save(self, session_id: str, evidence: Evidence) -> None:
        """Save evidence to database."""
        source_data = evidence.source.model_dump(mode="json")
        # Preserve verification detail in the existing JSON column so alpha
        # databases retain it without requiring an in-place table alteration.
        source_data["_verification_method"] = evidence.verification_method
        source_data["_matched_lines"] = evidence.matched_lines
        # SQLite alpha compatibility: retain typed temporal semantics in the
        # existing JSON column. SQLite DateTime commonly drops offsets, so the
        # legacy column is only a convenience mirror for genuine instants.
        source_data["_clinical_temporal_v1"] = evidence.temporal.model_dump(mode="json")
        model = EvidenceModel(
            id=evidence.id.value,
            session_id=session_id,
            content=evidence.content,
            evidence_type=evidence.evidence_type.value,
            clinical_context=evidence.clinical_context,
            quality_data=evidence.quality.model_dump(mode="json"),
            source_data=source_data,
            event_timestamp=evidence.event_timestamp,
            supports_cause_ids=evidence.supports_cause_ids,
            supports_hypothesis_ids=evidence.supports_hypothesis_ids,
            contradicts_hypothesis_ids=evidence.contradicts_hypothesis_ids,
            verified=evidence.verified,
            verifier=evidence.verifier,
            verification_timestamp=evidence.verification_timestamp,
            tags=evidence.tags,
        )

        with self.db.get_session() as session:
            session.merge(model)
            session.commit()

    async def get_by_id(self, session_id: str, evidence_id: str) -> Evidence | None:
        """Get evidence by ID."""
        with self.db.get_session() as session:
            statement = select(EvidenceModel).where(
                EvidenceModel.id == evidence_id,
                EvidenceModel.session_id == session_id,
            )
            model = session.exec(statement).first()

            if not model:
                return None

            return self._to_entity(model)

    async def list_by_session(self, session_id: str) -> list[Evidence]:
        """List all evidence for a session."""
        with self.db.get_session() as session:
            statement = select(EvidenceModel).where(
                EvidenceModel.session_id == session_id
            )
            models = session.exec(statement).all()

            return [self._to_entity(m) for m in models]

    async def update(self, session_id: str, evidence: Evidence) -> None:
        """Update existing evidence."""
        await self.save(session_id, evidence)

    async def delete(self, session_id: str, evidence_id: str) -> None:
        """Delete evidence."""
        with self.db.get_session() as session:
            statement = select(EvidenceModel).where(
                EvidenceModel.id == evidence_id,
                EvidenceModel.session_id == session_id,
            )
            model = session.exec(statement).first()
            if model:
                session.delete(model)
                session.commit()

    def _to_entity(self, model: EvidenceModel) -> Evidence:
        """Convert EvidenceModel to Evidence entity."""
        source_data = dict(model.source_data)
        verification_method = source_data.pop("_verification_method", None)
        matched_lines = source_data.pop("_matched_lines", [])
        temporal_data = source_data.pop("_clinical_temporal_v1", None)
        if temporal_data is not None:
            temporal = ClinicalTemporal.model_validate(temporal_data)
        elif model.event_timestamp is None:
            temporal = ClinicalTemporal.unknown()
        elif (
            model.event_timestamp.tzinfo is not None
            and model.event_timestamp.utcoffset() is not None
        ):
            temporal = ClinicalTemporal.from_legacy_event_timestamp(
                model.event_timestamp
            )
        else:
            # An old SQLite row may have lost its offset. Preserve the literal
            # local value, but never promote it to a sortable instant.
            temporal = ClinicalTemporal.from_lost_local_timestamp(model.event_timestamp)
        return Evidence(
            id=EvidenceId(model.id),
            content=model.content,
            evidence_type=EvidenceType(model.evidence_type),
            clinical_context=model.clinical_context,
            quality=EvidenceQuality(**model.quality_data),
            source=EvidenceSource(**source_data),
            temporal=temporal,
            event_timestamp=temporal.source_aware_instant,
            supports_cause_ids=model.supports_cause_ids,
            supports_hypothesis_ids=model.supports_hypothesis_ids,
            contradicts_hypothesis_ids=model.contradicts_hypothesis_ids,
            verified=model.verified,
            verifier=model.verifier,
            verification_method=verification_method,
            matched_lines=matched_lines,
            verification_timestamp=model.verification_timestamp,
            tags=model.tags,
        )
