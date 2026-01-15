"""
SQLite Why Tree Repository Implementation.

Implements WhyTreeRepository using in-memory storage with SQLModel models.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rootcause_mcp.domain.entities.why_node import WhyChain, WhyNode
from rootcause_mcp.domain.repositories.why_tree_repository import WhyTreeRepository
from rootcause_mcp.domain.value_objects.identifiers import CauseId, SessionId
from rootcause_mcp.domain.value_objects.scores import ConfidenceScore

if TYPE_CHECKING:
    from rootcause_mcp.infrastructure.persistence.database import Database


class InMemoryWhyTreeRepository(WhyTreeRepository):
    """
    In-memory implementation of WhyTreeRepository.

    Stores WhyChains in memory, associated with sessions.
    For production, this could be replaced with SQLite persistence.
    """

    def __init__(self, database: "Database | None" = None) -> None:
        """Initialize the repository."""
        self._database = database
        self._chains: dict[str, WhyChain] = {}  # session_id -> WhyChain
        self._nodes: dict[str, WhyNode] = {}  # node_id -> WhyNode

    def save_chain(self, chain: WhyChain) -> None:
        """Save or update a WhyChain."""
        session_key = str(chain.session_id)
        self._chains[session_key] = chain
        # Index all nodes
        for node in chain.nodes:
            self._nodes[str(node.id)] = node

    def get_chain(self, session_id: SessionId) -> WhyChain | None:
        """Get WhyChain by session ID."""
        return self._chains.get(str(session_id))

    def add_node(self, session_id: SessionId, node: WhyNode) -> None:
        """Add a WhyNode to a chain."""
        chain = self.get_chain(session_id)
        if chain:
            chain.add_node(node)
            self._nodes[str(node.id)] = node
        else:
            # Create new chain
            chain = WhyChain(
                session_id=session_id,
                initial_problem="(問題待定義)",
                nodes=[node],
            )
            self._chains[str(session_id)] = chain
            self._nodes[str(node.id)] = node

    def get_node(self, node_id: CauseId) -> WhyNode | None:
        """Get a specific WhyNode by ID."""
        return self._nodes.get(str(node_id))

    def update_node(self, node: WhyNode) -> None:
        """Update an existing WhyNode."""
        self._nodes[str(node.id)] = node
        # Also update in chain
        chain = self._chains.get(str(node.session_id))
        if chain:
            for i, existing in enumerate(chain.nodes):
                if str(existing.id) == str(node.id):
                    chain.nodes[i] = node
                    break

    def delete_chain(self, session_id: SessionId) -> bool:
        """Delete a WhyChain and all its nodes."""
        session_key = str(session_id)
        chain = self._chains.get(session_key)
        if chain:
            # Remove all nodes
            for node in chain.nodes:
                self._nodes.pop(str(node.id), None)
            del self._chains[session_key]
            return True
        return False

    def create_chain(
        self, session_id: SessionId, initial_problem: str
    ) -> WhyChain:
        """Create a new WhyChain for a session."""
        chain = WhyChain(
            session_id=session_id,
            initial_problem=initial_problem,
            nodes=[],
        )
        self._chains[str(session_id)] = chain
        return chain

    def get_all_chains(self) -> list[WhyChain]:
        """Get all WhyChains."""
        return list(self._chains.values())
