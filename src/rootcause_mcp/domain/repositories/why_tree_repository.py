"""
Why Tree Repository Interface.

Abstract interface for WhyChain persistence.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from rootcause_mcp.domain.entities.why_node import WhyChain, WhyNode
from rootcause_mcp.domain.value_objects.identifiers import CauseId, SessionId


class WhyTreeRepository(ABC):
    """Abstract repository for WhyChain/WhyNode persistence."""

    @abstractmethod
    def save_chain(self, chain: WhyChain) -> None:
        """Save or update a WhyChain."""
        ...

    @abstractmethod
    def get_chain(self, session_id: SessionId) -> WhyChain | None:
        """Get WhyChain by session ID."""
        ...

    @abstractmethod
    def add_node(self, session_id: SessionId, node: WhyNode) -> None:
        """Add a WhyNode to a chain."""
        ...

    @abstractmethod
    def get_node(self, node_id: CauseId) -> WhyNode | None:
        """Get a specific WhyNode by ID."""
        ...

    @abstractmethod
    def update_node(self, node: WhyNode) -> None:
        """Update an existing WhyNode."""
        ...

    @abstractmethod
    def delete_chain(self, session_id: SessionId) -> bool:
        """Delete a WhyChain and all its nodes."""
        ...
