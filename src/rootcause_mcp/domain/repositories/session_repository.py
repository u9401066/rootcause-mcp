"""
Session Repository Interface.

Abstract repository for RCA Session persistence.
"""

from abc import ABC, abstractmethod

from rootcause_mcp.domain.entities.session import RCASession
from rootcause_mcp.domain.value_objects.identifiers import SessionId
from rootcause_mcp.domain.value_objects.enums import SessionStatus, CaseType


class SessionRepository(ABC):
    """
    Abstract repository for RCA Sessions.

    Implementations should be in the Infrastructure layer.
    """

    @abstractmethod
    def save(self, session: RCASession) -> None:
        """
        Save a session (create or update).

        Args:
            session: The RCASession to save
        """
        ...

    @abstractmethod
    def get(self, session_id: SessionId) -> RCASession | None:
        """
        Get a session by ID.

        Args:
            session_id: The session's unique identifier

        Returns:
            The RCASession if found, None otherwise
        """
        ...

    @abstractmethod
    def get_by_id(self, session_id: str) -> RCASession | None:
        """
        Get a session by string ID.

        Convenience method that accepts string ID.

        Args:
            session_id: The session ID as string

        Returns:
            The RCASession if found, None otherwise
        """
        ...

    @abstractmethod
    def list_all(
        self,
        status: SessionStatus | None = None,
        case_type: CaseType | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[RCASession]:
        """
        List all sessions with optional filters.

        Args:
            status: Filter by session status
            case_type: Filter by case type
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of matching RCASessions
        """
        ...

    @abstractmethod
    def delete(self, session_id: SessionId) -> bool:
        """
        Delete a session.

        Args:
            session_id: The session's unique identifier

        Returns:
            True if deleted, False if not found
        """
        ...

    @abstractmethod
    def count(
        self,
        status: SessionStatus | None = None,
        case_type: CaseType | None = None,
    ) -> int:
        """
        Count sessions with optional filters.

        Args:
            status: Filter by session status
            case_type: Filter by case type

        Returns:
            Number of matching sessions
        """
        ...

    @abstractmethod
    def exists(self, session_id: SessionId) -> bool:
        """
        Check if a session exists.

        Args:
            session_id: The session's unique identifier

        Returns:
            True if exists, False otherwise
        """
        ...
