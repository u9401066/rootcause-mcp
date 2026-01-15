"""
Database Configuration and Connection Management.

SQLite database setup using SQLModel.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from sqlmodel import SQLModel, Session, create_engine

if TYPE_CHECKING:
    from sqlalchemy import Engine


class Database:
    """
    Database connection manager.

    Handles SQLite database initialization and session management.
    """

    def __init__(self, db_path: str | Path | None = None) -> None:
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file.
                    If None, uses in-memory database.
                    If ":memory:", uses in-memory database.
        """
        if db_path is None or db_path == ":memory:":
            self.db_url = "sqlite:///:memory:"
        else:
            # Ensure path is absolute
            path = Path(db_path).resolve()
            # Create parent directories if needed
            path.parent.mkdir(parents=True, exist_ok=True)
            self.db_url = f"sqlite:///{path}"

        self._engine: Engine | None = None

    @property
    def engine(self) -> "Engine":
        """Get or create the database engine."""
        if self._engine is None:
            self._engine = create_engine(
                self.db_url,
                echo=False,  # Set to True for SQL debugging
                connect_args={"check_same_thread": False},  # Required for SQLite
            )
        return self._engine

    def create_tables(self) -> None:
        """Create all database tables."""
        # Import models to register them with SQLModel
        from rootcause_mcp.infrastructure.persistence import models  # noqa: F401

        SQLModel.metadata.create_all(self.engine)

    def drop_tables(self) -> None:
        """Drop all database tables."""
        SQLModel.metadata.drop_all(self.engine)

    def get_session(self) -> Session:
        """
        Get a new database session.

        Usage:
            with db.get_session() as session:
                # Use session
                session.add(entity)
                session.commit()
        """
        return Session(self.engine)

    def close(self) -> None:
        """Close the database connection."""
        if self._engine:
            self._engine.dispose()
            self._engine = None


# Global database instance (initialized lazily)
_db: Database | None = None


def get_database(db_path: str | Path | None = None) -> Database:
    """
    Get or create the global database instance.

    Args:
        db_path: Path to database file. Only used on first call.

    Returns:
        The global Database instance.
    """
    global _db
    if _db is None:
        _db = Database(db_path)
        _db.create_tables()
    return _db


def reset_database() -> None:
    """Reset the global database instance."""
    global _db
    if _db:
        _db.close()
        _db = None
