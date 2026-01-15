"""
Cause Repository Interface.

Abstract repository for Cause persistence.
"""

from abc import ABC, abstractmethod

from rootcause_mcp.domain.entities.cause import Cause
from rootcause_mcp.domain.value_objects.identifiers import CauseId, SessionId
from rootcause_mcp.domain.value_objects.enums import FishboneCategoryType


class CauseRepository(ABC):
    """
    Abstract repository for Causes.

    Implementations should be in the Infrastructure layer.
    """

    @abstractmethod
    def save(self, cause: Cause) -> None:
        """
        Save a cause (create or update).

        Args:
            cause: The Cause to save
        """
        ...

    @abstractmethod
    def get(self, cause_id: CauseId) -> Cause | None:
        """
        Get a cause by ID.

        Args:
            cause_id: The cause's unique identifier

        Returns:
            The Cause if found, None otherwise
        """
        ...

    @abstractmethod
    def get_by_id(self, cause_id: str) -> Cause | None:
        """
        Get a cause by string ID.

        Args:
            cause_id: The cause ID as string

        Returns:
            The Cause if found, None otherwise
        """
        ...

    @abstractmethod
    def list_by_session(
        self,
        session_id: SessionId,
        category: FishboneCategoryType | None = None,
        verified_only: bool = False,
    ) -> list[Cause]:
        """
        List all causes for a session.

        Args:
            session_id: The session's unique identifier
            category: Optional filter by 6M category
            verified_only: Only return verified causes

        Returns:
            List of matching Causes
        """
        ...

    @abstractmethod
    def list_by_parent(self, parent_id: CauseId) -> list[Cause]:
        """
        List all child causes of a parent.

        Args:
            parent_id: The parent cause's ID

        Returns:
            List of child Causes
        """
        ...

    @abstractmethod
    def delete(self, cause_id: CauseId) -> bool:
        """
        Delete a cause.

        Also deletes all child causes.

        Args:
            cause_id: The cause's unique identifier

        Returns:
            True if deleted, False if not found
        """
        ...

    @abstractmethod
    def delete_by_session(self, session_id: SessionId) -> int:
        """
        Delete all causes for a session.

        Args:
            session_id: The session's unique identifier

        Returns:
            Number of causes deleted
        """
        ...

    @abstractmethod
    def count_by_session(
        self,
        session_id: SessionId,
        category: FishboneCategoryType | None = None,
    ) -> int:
        """
        Count causes for a session.

        Args:
            session_id: The session's unique identifier
            category: Optional filter by 6M category

        Returns:
            Number of matching causes
        """
        ...
