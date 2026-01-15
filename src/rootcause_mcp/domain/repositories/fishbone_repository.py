"""
Fishbone Repository Interface.

Abstract repository for Fishbone diagram persistence.
"""

from abc import ABC, abstractmethod

from rootcause_mcp.domain.entities.fishbone import Fishbone
from rootcause_mcp.domain.value_objects.identifiers import FishboneId, SessionId


class FishboneRepository(ABC):
    """
    Abstract repository for Fishbone diagrams.

    Implementations should be in the Infrastructure layer.
    """

    @abstractmethod
    def save(self, fishbone: Fishbone) -> None:
        """
        Save a fishbone diagram (create or update).

        Args:
            fishbone: The Fishbone to save
        """
        ...

    @abstractmethod
    def get(self, fishbone_id: FishboneId) -> Fishbone | None:
        """
        Get a fishbone by ID.

        Args:
            fishbone_id: The fishbone's unique identifier

        Returns:
            The Fishbone if found, None otherwise
        """
        ...

    @abstractmethod
    def get_by_session(self, session_id: SessionId) -> Fishbone | None:
        """
        Get the fishbone diagram for a session.

        Each session should have at most one fishbone.

        Args:
            session_id: The session's unique identifier

        Returns:
            The Fishbone if found, None otherwise
        """
        ...

    @abstractmethod
    def delete(self, fishbone_id: FishboneId) -> bool:
        """
        Delete a fishbone diagram.

        Args:
            fishbone_id: The fishbone's unique identifier

        Returns:
            True if deleted, False if not found
        """
        ...

    @abstractmethod
    def delete_by_session(self, session_id: SessionId) -> bool:
        """
        Delete the fishbone diagram for a session.

        Args:
            session_id: The session's unique identifier

        Returns:
            True if deleted, False if not found
        """
        ...
