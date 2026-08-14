"""
SQLite Why Tree Repository Implementation.

Persists WhyChains, WhyNodes, and CausalLinks to SQLite using SQLModel.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlmodel import select

from rootcause_mcp.domain.entities.why_node import CausalLink, WhyChain, WhyNode
from rootcause_mcp.domain.repositories.why_tree_repository import WhyTreeRepository
from rootcause_mcp.domain.value_objects.enums import CausalLinkType
from rootcause_mcp.domain.value_objects.identifiers import CauseId, SessionId
from rootcause_mcp.domain.value_objects.scores import ConfidenceScore
from rootcause_mcp.infrastructure.persistence.models import (
    CausalLinkModel,
    WhyChainModel,
    WhyNodeModel,
)

if TYPE_CHECKING:
    from rootcause_mcp.infrastructure.persistence.database import Database


class SQLiteWhyTreeRepository(WhyTreeRepository):
    """
    Persistent SQLite implementation of WhyTreeRepository using SQLModel.

    Ensures complete 5-Why analysis trees and causal links are preserved
    across server restarts.
    """

    def __init__(self, database: Database) -> None:
        """Initialize repository with database connection."""
        self.db = database

    def save_chain(self, chain: WhyChain) -> None:
        """Save or update a WhyChain and all its nodes and causal links."""
        session_id_str = str(chain.session_id)
        with self.db.get_session() as session:
            # 1. Save or update WhyChainModel
            chain_model = session.get(WhyChainModel, session_id_str)
            if chain_model is None:
                chain_model = WhyChainModel(
                    session_id=session_id_str,
                    initial_problem=chain.initial_problem,
                )
            else:
                chain_model.initial_problem = chain.initial_problem
            session.merge(chain_model)

            # 2. Save or update WhyNodeModels
            for node in chain.nodes:
                node_model = WhyNodeModel(
                    id=str(node.id),
                    session_id=session_id_str,
                    parent_id=str(node.parent_id) if node.parent_id else None,
                    question=node.question,
                    answer=node.answer,
                    level=node.level,
                    evidence=list(node.evidence),
                    confidence=node.confidence.value if node.confidence else None,
                    is_root_cause=node.is_root_cause,
                    needs_further_analysis=node.needs_further_analysis,
                    is_proximate=node.is_proximate,
                    created_at=node.created_at,
                    updated_at=node.updated_at,
                )
                session.merge(node_model)

            # 3. Save CausalLinkModels
            for link in chain.causal_links:
                link_id = f"LINK-{link.source_id}-{link.target_id}"
                link_model = CausalLinkModel(
                    id=link_id,
                    session_id=session_id_str,
                    source_id=str(link.source_id),
                    target_id=str(link.target_id),
                    relationship=link.relationship.value,
                    strength=link.strength,
                    evidence=list(link.evidence),
                    note=link.note,
                    bidirectional=link.bidirectional,
                )
                session.merge(link_model)

            session.commit()

    def get_chain(self, session_id: SessionId) -> WhyChain | None:
        """Get WhyChain with all nodes and causal links by session ID."""
        session_id_str = str(session_id)
        with self.db.get_session() as session:
            chain_model = session.get(WhyChainModel, session_id_str)
            if chain_model is None:
                return None

            # Load nodes
            node_statement = (
                select(WhyNodeModel)
                .where(WhyNodeModel.session_id == session_id_str)
                .order_by(WhyNodeModel.level, WhyNodeModel.created_at)  # type: ignore[arg-type]
            )
            node_models = session.exec(node_statement).all()
            nodes = [self._node_model_to_entity(nm) for nm in node_models]

            # Load links
            link_statement = select(CausalLinkModel).where(
                CausalLinkModel.session_id == session_id_str
            )
            link_models = session.exec(link_statement).all()
            links = [self._link_model_to_entity(lm) for lm in link_models]

            return WhyChain(
                session_id=session_id,
                initial_problem=chain_model.initial_problem,
                nodes=nodes,
                causal_links=links,
            )

    def add_node(self, session_id: SessionId, node: WhyNode) -> None:
        """Add a WhyNode to a session chain."""
        session_id_str = str(session_id)
        with self.db.get_session() as session:
            chain_model = session.get(WhyChainModel, session_id_str)
            if chain_model is None:
                chain_model = WhyChainModel(
                    session_id=session_id_str,
                    initial_problem="(問題待定義)",
                )
                session.merge(chain_model)

            node_model = WhyNodeModel(
                id=str(node.id),
                session_id=session_id_str,
                parent_id=str(node.parent_id) if node.parent_id else None,
                question=node.question,
                answer=node.answer,
                level=node.level,
                evidence=list(node.evidence),
                confidence=node.confidence.value if node.confidence else None,
                is_root_cause=node.is_root_cause,
                needs_further_analysis=node.needs_further_analysis,
                is_proximate=node.is_proximate,
                created_at=node.created_at,
                updated_at=node.updated_at,
            )
            session.merge(node_model)
            session.commit()

    def get_node(self, node_id: CauseId) -> WhyNode | None:
        """Get a specific WhyNode by ID."""
        with self.db.get_session() as session:
            node_model = session.get(WhyNodeModel, str(node_id))
            if node_model is None:
                return None
            return self._node_model_to_entity(node_model)

    def update_node(self, node: WhyNode) -> None:
        """Update an existing WhyNode."""
        with self.db.get_session() as session:
            node_model = session.get(WhyNodeModel, str(node.id))
            if node_model is not None:
                node_model.question = node.question
                node_model.answer = node.answer
                node_model.level = node.level
                node_model.evidence = list(node.evidence)
                node_model.confidence = (
                    node.confidence.value if node.confidence else None
                )
                node_model.is_root_cause = node.is_root_cause
                node_model.needs_further_analysis = node.needs_further_analysis
                node_model.is_proximate = node.is_proximate
                node_model.updated_at = node.updated_at
                session.merge(node_model)
                session.commit()

    def delete_chain(self, session_id: SessionId) -> bool:
        """Delete a WhyChain, its nodes, and causal links."""
        session_id_str = str(session_id)
        with self.db.get_session() as session:
            chain_model = session.get(WhyChainModel, session_id_str)
            if chain_model is None:
                return False

            session.delete(chain_model)
            # Delete associated nodes
            for nm in session.exec(
                select(WhyNodeModel).where(WhyNodeModel.session_id == session_id_str)
            ).all():
                session.delete(nm)
            # Delete associated links
            for lm in session.exec(
                select(CausalLinkModel).where(
                    CausalLinkModel.session_id == session_id_str
                )
            ).all():
                session.delete(lm)
            session.commit()
            return True

    def create_chain(self, session_id: SessionId, initial_problem: str) -> WhyChain:
        """Create a new WhyChain for a session."""
        chain = WhyChain(
            session_id=session_id,
            initial_problem=initial_problem,
            nodes=[],
        )
        self.save_chain(chain)
        return chain

    def get_all_chains(self) -> list[WhyChain]:
        """Get all WhyChains in the database."""
        with self.db.get_session() as session:
            chain_models = session.exec(select(WhyChainModel)).all()
            return [
                self.get_chain(SessionId(cm.session_id))  # type: ignore[misc]
                for cm in chain_models
                if self.get_chain(SessionId(cm.session_id)) is not None
            ]

    @staticmethod
    def _node_model_to_entity(model: WhyNodeModel) -> WhyNode:
        return WhyNode(
            id=CauseId(model.id),
            session_id=SessionId(model.session_id),
            question=model.question,
            answer=model.answer,
            level=model.level,
            parent_id=CauseId(model.parent_id) if model.parent_id else None,
            evidence=list(model.evidence or []),
            confidence=(
                ConfidenceScore(model.confidence)
                if model.confidence is not None
                else None
            ),
            is_root_cause=model.is_root_cause,
            needs_further_analysis=model.needs_further_analysis,
            is_proximate=model.is_proximate,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _link_model_to_entity(model: CausalLinkModel) -> CausalLink:
        return CausalLink(
            source_id=CauseId(model.source_id),
            target_id=CauseId(model.target_id),
            relationship=CausalLinkType(model.relationship),
            strength=model.strength,
            evidence=tuple(model.evidence or ()),
            note=model.note or "",
            bidirectional=model.bidirectional,
        )


class InMemoryWhyTreeRepository(WhyTreeRepository):
    """
    In-memory implementation of WhyTreeRepository for fast unit testing.
    """

    def __init__(self, database: Database | None = None) -> None:
        """Initialize in-memory storage."""
        self._database = database
        self._chains: dict[str, WhyChain] = {}
        self._nodes: dict[str, WhyNode] = {}

    def save_chain(self, chain: WhyChain) -> None:
        """Save or update a WhyChain."""
        session_key = str(chain.session_id)
        self._chains[session_key] = chain
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
            for node in chain.nodes:
                self._nodes.pop(str(node.id), None)
            del self._chains[session_key]
            return True
        return False

    def create_chain(self, session_id: SessionId, initial_problem: str) -> WhyChain:
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
