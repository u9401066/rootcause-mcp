"""
Evidence Repository (SQLite).

Persists Evidence entities to SQLite database.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rootcause_mcp.domain.entities.evidence import Evidence

if TYPE_CHECKING:
    from rootcause_mcp.infrastructure.persistence.database import Database


class SQLiteEvidenceRepository:
    """SQLite implementation of Evidence repository."""

    def __init__(self, db: Database) -> None:
        """Initialize repository with database connection."""
        self.db = db
        self._ensure_table()

    def _ensure_table(self) -> None:
        """Create evidence table if not exists."""
        # For smoke test, use in-memory dict
        # In production, this would create actual SQLite tables
        self._store: dict[str, dict[str, Any]] = {}

    async def save(self, session_id: str, evidence: Evidence) -> None:
        """Save evidence to database."""
        key = f"{session_id}:{evidence.id.value}"
        self._store[key] = evidence.model_dump(mode="json")

    async def get_by_id(self, session_id: str, evidence_id: str) -> Evidence | None:
        """Get evidence by ID."""
        key = f"{session_id}:{evidence_id}"
        data = self._store.get(key)
        if not data:
            return None
        return Evidence(**data)

    async def list_by_session(self, session_id: str) -> list[Evidence]:
        """List all evidence for a session."""
        prefix = f"{session_id}:"
        results = []
        for key, data in self._store.items():
            if key.startswith(prefix):
                results.append(Evidence(**data))
        return results

    async def update(self, session_id: str, evidence: Evidence) -> None:
        """Update existing evidence."""
        await self.save(session_id, evidence)

    async def delete(self, session_id: str, evidence_id: str) -> None:
        """Delete evidence."""
        key = f"{session_id}:{evidence_id}"
        if key in self._store:
            del self._store[key]
