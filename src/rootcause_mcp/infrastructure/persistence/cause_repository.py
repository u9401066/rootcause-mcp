"""
SQLite Cause Repository Implementation.

Implements CauseRepository using SQLModel.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Session as DBSession, select

from rootcause_mcp.domain.entities.cause import Cause
from rootcause_mcp.domain.repositories.cause_repository import CauseRepository
from rootcause_mcp.domain.value_objects.identifiers import CauseId, SessionId
from rootcause_mcp.domain.value_objects.enums import FishboneCategoryType
from rootcause_mcp.domain.value_objects.scores import ConfidenceScore
from rootcause_mcp.infrastructure.persistence.models import CauseModel
from rootcause_mcp.infrastructure.persistence.database import Database


class SQLiteCauseRepository(CauseRepository):
    """
    SQLite implementation of CauseRepository.

    Uses SQLModel for ORM operations.
    """

    def __init__(self, database: Database) -> None:
        """
        Initialize repository with database connection.

        Args:
            database: Database instance for connection management
        """
        self._db = database

    def save(self, cause: Cause) -> None:
        """Save a cause (create or update)."""
        with self._db.get_session() as db_session:
            model = self._to_model(cause)

            existing = db_session.get(CauseModel, str(cause.id))
            if existing:
                for key, value in model.model_dump().items():
                    setattr(existing, key, value)
                existing.updated_at = datetime.now(timezone.utc)
            else:
                db_session.add(model)

            db_session.commit()

    def get(self, cause_id: CauseId) -> Cause | None:
        """Get a cause by ID."""
        return self.get_by_id(str(cause_id))

    def get_by_id(self, cause_id: str) -> Cause | None:
        """Get a cause by string ID."""
        with self._db.get_session() as db_session:
            model = db_session.get(CauseModel, cause_id)
            if model:
                return self._to_entity(model)
            return None

    def list_by_session(
        self,
        session_id: SessionId,
        category: FishboneCategoryType | None = None,
        verified_only: bool = False,
    ) -> list[Cause]:
        """List all causes for a session."""
        with self._db.get_session() as db_session:
            query = select(CauseModel).where(
                CauseModel.session_id == str(session_id)
            )

            if category:
                query = query.where(CauseModel.category == category.value)
            if verified_only:
                query = query.where(CauseModel.verified == True)  # noqa: E712

            results = db_session.exec(query).all()
            return [self._to_entity(model) for model in results]

    def list_by_parent(self, parent_id: CauseId) -> list[Cause]:
        """List all child causes of a parent."""
        with self._db.get_session() as db_session:
            query = select(CauseModel).where(
                CauseModel.parent_id == str(parent_id)
            )
            results = db_session.exec(query).all()
            return [self._to_entity(model) for model in results]

    def delete(self, cause_id: CauseId) -> bool:
        """Delete a cause and its children."""
        with self._db.get_session() as db_session:
            # First delete children recursively
            children = db_session.exec(
                select(CauseModel).where(CauseModel.parent_id == str(cause_id))
            ).all()
            for child in children:
                self.delete(CauseId.from_string(child.id))

            # Then delete the cause itself
            model = db_session.get(CauseModel, str(cause_id))
            if model:
                db_session.delete(model)
                db_session.commit()
                return True
            return False

    def delete_by_session(self, session_id: SessionId) -> int:
        """Delete all causes for a session."""
        with self._db.get_session() as db_session:
            query = select(CauseModel).where(
                CauseModel.session_id == str(session_id)
            )
            results = db_session.exec(query).all()
            count = len(results)

            for model in results:
                db_session.delete(model)

            db_session.commit()
            return count

    def count_by_session(
        self,
        session_id: SessionId,
        category: FishboneCategoryType | None = None,
    ) -> int:
        """Count causes for a session."""
        with self._db.get_session() as db_session:
            query = select(CauseModel).where(
                CauseModel.session_id == str(session_id)
            )

            if category:
                query = query.where(CauseModel.category == category.value)

            results = db_session.exec(query).all()
            return len(results)

    # === Mapping Methods ===

    def _to_model(self, entity: Cause) -> CauseModel:
        """Convert domain entity to database model."""
        return CauseModel(
            id=str(entity.id),
            session_id=str(entity.session_id),
            description=entity.description,
            category=entity.category.value,
            hfacs_code=entity.hfacs_code,
            hfacs_confidence=float(entity.hfacs_confidence) if entity.hfacs_confidence else None,
            evidence=entity.evidence,
            verified=entity.verified,
            confidence=float(entity.confidence) if entity.confidence else None,
            parent_id=str(entity.parent_id) if entity.parent_id else None,
            depth=entity.depth,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    def _to_entity(self, model: CauseModel) -> Cause:
        """Convert database model to domain entity."""
        return Cause(
            id=CauseId.from_string(model.id),
            session_id=SessionId.from_string(model.session_id),
            description=model.description,
            category=FishboneCategoryType(model.category),
            hfacs_code=model.hfacs_code,
            hfacs_confidence=ConfidenceScore(model.hfacs_confidence) if model.hfacs_confidence else None,
            evidence=model.evidence,
            verified=model.verified,
            confidence=ConfidenceScore(model.confidence) if model.confidence else None,
            parent_id=CauseId.from_string(model.parent_id) if model.parent_id else None,
            depth=model.depth,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
