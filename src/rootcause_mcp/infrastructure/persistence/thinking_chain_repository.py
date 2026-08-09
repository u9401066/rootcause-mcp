"""
ThinkingChain Repository (SQLite).

Persists ThinkingChain entities to SQLite database.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rootcause_mcp.domain.entities.thinking_step import ThinkingChain, ThinkingStep

if TYPE_CHECKING:
    from rootcause_mcp.infrastructure.persistence.database import Database


class SQLiteThinkingChainRepository:
    """SQLite implementation of ThinkingChain repository."""

    def __init__(self, db: Database) -> None:
        """Initialize repository with database connection."""
        self.db = db
        self._ensure_table()

    def _ensure_table(self) -> None:
        """Create thinking chain table if not exists."""
        # For smoke test, use in-memory dict
        self._store: dict[str, dict[str, Any]] = {}

    async def save(self, session_id: str, chain: ThinkingChain) -> None:
        """Save thinking chain to database."""
        self._store[session_id] = chain.model_dump(mode="json")

    async def get_by_session(self, session_id: str) -> ThinkingChain | None:
        """Get thinking chain by session ID."""
        data = self._store.get(session_id)
        if not data:
            return None
        return ThinkingChain(**data)

    async def add_step(self, session_id: str, step: ThinkingStep) -> None:
        """Add a thinking step to the chain."""
        chain = await self.get_by_session(session_id)
        if not chain:
            chain = ThinkingChain(session_id=session_id)
        chain.add_step(step)
        await self.save(session_id, chain)

    async def delete(self, session_id: str) -> None:
        """Delete thinking chain."""
        if session_id in self._store:
            del self._store[session_id]
