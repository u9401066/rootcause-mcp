"""
SQLite Fishbone Repository Implementation.

Implements FishboneRepository using SQLModel.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlmodel import Session as DBSession, select

from rootcause_mcp.domain.entities.fishbone import (
    Fishbone,
    FishboneCategory,
    FishboneCause,
)
from rootcause_mcp.domain.repositories.fishbone_repository import FishboneRepository
from rootcause_mcp.domain.value_objects.identifiers import (
    FishboneId,
    SessionId,
    CauseId,
)
from rootcause_mcp.domain.value_objects.enums import FishboneCategoryType
from rootcause_mcp.domain.value_objects.scores import ConfidenceScore
from rootcause_mcp.infrastructure.persistence.models import FishboneModel
from rootcause_mcp.infrastructure.persistence.database import Database


class SQLiteFishboneRepository(FishboneRepository):
    """
    SQLite implementation of FishboneRepository.

    Uses SQLModel for ORM operations.
    """

    def __init__(self, database: Database) -> None:
        """
        Initialize repository with database connection.

        Args:
            database: Database instance for connection management
        """
        self._db = database

    def save(self, fishbone: Fishbone) -> None:
        """Save a fishbone diagram (create or update)."""
        with self._db.get_session() as db_session:
            model = self._to_model(fishbone)

            existing = db_session.get(FishboneModel, str(fishbone.id))
            if existing:
                for key, value in model.model_dump().items():
                    setattr(existing, key, value)
                existing.updated_at = datetime.now(timezone.utc)
            else:
                db_session.add(model)

            db_session.commit()

    def get(self, fishbone_id: FishboneId) -> Fishbone | None:
        """Get a fishbone by ID."""
        with self._db.get_session() as db_session:
            model = db_session.get(FishboneModel, str(fishbone_id))
            if model:
                return self._to_entity(model)
            return None

    def get_by_session(self, session_id: SessionId) -> Fishbone | None:
        """Get the fishbone diagram for a session."""
        with self._db.get_session() as db_session:
            query = select(FishboneModel).where(
                FishboneModel.session_id == str(session_id)
            )
            model = db_session.exec(query).first()
            if model:
                return self._to_entity(model)
            return None

    def delete(self, fishbone_id: FishboneId) -> bool:
        """Delete a fishbone diagram."""
        with self._db.get_session() as db_session:
            model = db_session.get(FishboneModel, str(fishbone_id))
            if model:
                db_session.delete(model)
                db_session.commit()
                return True
            return False

    def delete_by_session(self, session_id: SessionId) -> bool:
        """Delete the fishbone diagram for a session."""
        with self._db.get_session() as db_session:
            query = select(FishboneModel).where(
                FishboneModel.session_id == str(session_id)
            )
            model = db_session.exec(query).first()
            if model:
                db_session.delete(model)
                db_session.commit()
                return True
            return False

    # === Mapping Methods ===

    def _to_model(self, entity: Fishbone) -> FishboneModel:
        """Convert domain entity to database model."""
        # Serialize categories to JSON
        categories_data: dict[str, Any] = {}
        for cat_type, category in entity.categories.items():
            causes_list: list[dict[str, Any]] = []
            for cause in category.causes:
                causes_list.append({
                    "cause_id": str(cause.cause_id),
                    "description": cause.description,
                    "sub_causes": cause.sub_causes,
                    "hfacs_code": cause.hfacs_code,
                    "hfacs_confidence": float(cause.hfacs_confidence) if cause.hfacs_confidence else None,
                    "evidence": cause.evidence,
                    "confidence": float(cause.confidence) if cause.confidence else None,
                    "verified": cause.verified,
                    "depth": cause.depth,
                })
            categories_data[cat_type.value] = causes_list

        return FishboneModel(
            id=str(entity.id),
            session_id=str(entity.session_id),
            problem_statement=entity.problem_statement,
            categories_data=categories_data,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    def _to_entity(self, model: FishboneModel) -> Fishbone:
        """Convert database model to domain entity."""
        # Deserialize categories from JSON
        categories: dict[FishboneCategoryType, FishboneCategory] = {}

        for cat_type in FishboneCategoryType:
            category = FishboneCategory(category=cat_type)

            if cat_type.value in model.categories_data:
                for cause_data in model.categories_data[cat_type.value]:
                    cause = FishboneCause(
                        cause_id=CauseId.from_string(cause_data["cause_id"]),
                        category=cat_type,
                        description=cause_data["description"],
                        sub_causes=cause_data.get("sub_causes", []),
                        hfacs_code=cause_data.get("hfacs_code"),
                        hfacs_confidence=(
                            ConfidenceScore(cause_data["hfacs_confidence"])
                            if cause_data.get("hfacs_confidence")
                            else None
                        ),
                        evidence=cause_data.get("evidence", []),
                        confidence=(
                            ConfidenceScore(cause_data["confidence"])
                            if cause_data.get("confidence")
                            else None
                        ),
                        verified=cause_data.get("verified", False),
                        depth=cause_data.get("depth", 1),
                    )
                    category.add_cause(cause)

            categories[cat_type] = category

        return Fishbone(
            id=FishboneId.from_string(model.id),
            session_id=SessionId.from_string(model.session_id),
            problem_statement=model.problem_statement,
            categories=categories,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
