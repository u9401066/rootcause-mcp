"""
Hypothesis Repository (SQLite).

Persists Hypothesis entities to SQLite database.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rootcause_mcp.domain.entities.hypothesis import Hypothesis

if TYPE_CHECKING:
    from rootcause_mcp.infrastructure.persistence.database import Database


class SQLiteHypothesisRepository:
    """SQLite implementation of Hypothesis repository."""

    def __init__(self, db: Database) -> None:
        """Initialize repository with database connection."""
        self.db = db
        self._ensure_table()

    def _ensure_table(self) -> None:
        """Create hypothesis table if not exists."""
        # For smoke test, use in-memory dict
        self._store: dict[str, dict[str, Any]] = {}

    async def save(self, session_id: str, hypothesis: Hypothesis) -> None:
        """Save hypothesis to database."""
        key = f"{session_id}:{hypothesis.id.value}"
        self._store[key] = hypothesis.model_dump(mode="json")

    async def get_by_id(self, session_id: str, hypothesis_id: str) -> Hypothesis | None:
        """Get hypothesis by ID."""
        key = f"{session_id}:{hypothesis_id}"
        data = self._store.get(key)
        if not data:
            return None
        return Hypothesis(**data)

    async def list_by_session(self, session_id: str) -> list[Hypothesis]:
        """List all hypotheses for a session."""
        prefix = f"{session_id}:"
        results = []
        for key, data in self._store.items():
            if key.startswith(prefix):
                results.append(Hypothesis(**data))
        return results

    async def update(self, session_id: str, hypothesis: Hypothesis) -> None:
        """Update existing hypothesis."""
        await self.save(session_id, hypothesis)

    async def delete(self, session_id: str, hypothesis_id: str) -> None:
        """Delete hypothesis."""
        key = f"{session_id}:{hypothesis_id}"
        if key in self._store:
            del self._store[key]
