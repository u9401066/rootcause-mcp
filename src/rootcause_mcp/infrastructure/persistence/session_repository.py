"""
SQLite Session Repository Implementation.

Implements SessionRepository using SQLModel.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlmodel import Session as DBSession, select

from rootcause_mcp.domain.entities.session import RCASession, StageRecord
from rootcause_mcp.domain.repositories.session_repository import SessionRepository
from rootcause_mcp.domain.value_objects.identifiers import SessionId
from rootcause_mcp.domain.value_objects.enums import (
    CaseType,
    SessionStatus,
    Stage,
    StageStatus,
)
from rootcause_mcp.infrastructure.persistence.models import SessionModel
from rootcause_mcp.infrastructure.persistence.database import Database


class SQLiteSessionRepository(SessionRepository):
    """
    SQLite implementation of SessionRepository.

    Uses SQLModel for ORM operations.
    """

    def __init__(self, database: Database) -> None:
        """
        Initialize repository with database connection.

        Args:
            database: Database instance for connection management
        """
        self._db = database

    def save(self, session: RCASession) -> None:
        """Save a session (create or update)."""
        with self._db.get_session() as db_session:
            # Convert domain entity to model
            model = self._to_model(session)

            # Check if exists
            existing = db_session.get(SessionModel, str(session.id))
            if existing:
                # Update existing
                for key, value in model.model_dump().items():
                    setattr(existing, key, value)
                existing.updated_at = datetime.now(timezone.utc)
            else:
                # Create new
                db_session.add(model)

            db_session.commit()

    def get(self, session_id: SessionId) -> RCASession | None:
        """Get a session by ID."""
        return self.get_by_id(str(session_id))

    def get_by_id(self, session_id: str) -> RCASession | None:
        """Get a session by string ID."""
        with self._db.get_session() as db_session:
            model = db_session.get(SessionModel, session_id)
            if model:
                return self._to_entity(model)
            return None

    def list_all(
        self,
        status: SessionStatus | None = None,
        case_type: CaseType | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[RCASession]:
        """List all sessions with optional filters."""
        with self._db.get_session() as db_session:
            query = select(SessionModel)

            if status:
                query = query.where(SessionModel.status == status.value)
            if case_type:
                query = query.where(SessionModel.case_type == case_type.value)

            query = query.offset(offset).limit(limit)
            query = query.order_by(SessionModel.updated_at.desc())  # type: ignore[attr-defined]

            results = db_session.exec(query).all()
            return [self._to_entity(model) for model in results]

    def delete(self, session_id: SessionId) -> bool:
        """Delete a session."""
        with self._db.get_session() as db_session:
            model = db_session.get(SessionModel, str(session_id))
            if model:
                db_session.delete(model)
                db_session.commit()
                return True
            return False

    def count(
        self,
        status: SessionStatus | None = None,
        case_type: CaseType | None = None,
    ) -> int:
        """Count sessions with optional filters."""
        with self._db.get_session() as db_session:
            query = select(SessionModel)

            if status:
                query = query.where(SessionModel.status == status.value)
            if case_type:
                query = query.where(SessionModel.case_type == case_type.value)

            results = db_session.exec(query).all()
            return len(results)

    def exists(self, session_id: SessionId) -> bool:
        """Check if a session exists."""
        with self._db.get_session() as db_session:
            model = db_session.get(SessionModel, str(session_id))
            return model is not None

    # === Mapping Methods ===

    def _to_model(self, entity: RCASession) -> SessionModel:
        """Convert domain entity to database model."""
        # Serialize stage records
        stage_data: dict[str, Any] = {}
        for stage, record in entity.stage_records.items():
            stage_data[stage.value] = {
                "status": record.status.value,
                "data": record.data,
                "started_at": record.started_at.isoformat() if record.started_at else None,
                "completed_at": record.completed_at.isoformat() if record.completed_at else None,
                "validation_errors": record.validation_errors,
                "validation_warnings": record.validation_warnings,
            }

        return SessionModel(
            id=str(entity.id),
            case_type=entity.case_type.value,
            case_title=entity.case_title,
            current_stage=entity.current_stage.value,
            status=entity.status.value,
            problem_statement=entity.problem_statement,
            initial_description=entity.initial_description,
            stage_data=stage_data,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            created_by=entity.created_by,
        )

    def _to_entity(self, model: SessionModel) -> RCASession:
        """Convert database model to domain entity."""
        # Deserialize stage records
        stage_records: dict[Stage, StageRecord] = {}
        for stage in Stage:
            stage_value = stage.value
            if stage_value in model.stage_data:
                data = model.stage_data[stage_value]
                record = StageRecord(
                    stage=stage,
                    status=StageStatus(data["status"]),
                    data=data.get("data", {}),
                    validation_errors=data.get("validation_errors", []),
                    validation_warnings=data.get("validation_warnings", []),
                )
                if data.get("started_at"):
                    record.started_at = datetime.fromisoformat(data["started_at"])
                if data.get("completed_at"):
                    record.completed_at = datetime.fromisoformat(data["completed_at"])
                stage_records[stage] = record
            else:
                stage_records[stage] = StageRecord(stage=stage)

        return RCASession(
            id=SessionId.from_string(model.id),
            case_type=CaseType(model.case_type),
            case_title=model.case_title,
            current_stage=Stage(model.current_stage),
            status=SessionStatus(model.status),
            problem_statement=model.problem_statement,
            initial_description=model.initial_description,
            stage_records=stage_records,
            created_at=model.created_at,
            updated_at=model.updated_at,
            created_by=model.created_by,
        )
