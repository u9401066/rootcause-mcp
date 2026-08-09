"""
ThinkingChain Repository (SQLite).

Persists ThinkingChain entities to SQLite database.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlmodel import col, delete, select

from rootcause_mcp.domain.entities.thinking_step import (
    AlternativeConsidered,
    ThinkingChain,
    ThinkingStep,
    ThinkingType,
)
from rootcause_mcp.infrastructure.persistence.models import ThinkingStepModel

if TYPE_CHECKING:
    from rootcause_mcp.infrastructure.persistence.database import Database


class SQLiteThinkingChainRepository:
    """SQLModel implementation of the thinking-chain repository."""

    def __init__(self, db: Database) -> None:
        """Initialize repository with database connection."""
        self.db = db

    async def save(self, session_id: str, chain: ThinkingChain) -> None:
        """Save thinking chain to database."""
        with self.db.get_session() as session:
            session.exec(
                delete(ThinkingStepModel).where(
                    col(ThinkingStepModel.session_id) == session_id
                )
            )
            for step in chain.steps:
                session.add(self._to_model(session_id, step))
            session.commit()

    async def get_by_session(self, session_id: str) -> ThinkingChain | None:
        """Get thinking chain by session ID."""
        with self.db.get_session() as session:
            statement = (
                select(ThinkingStepModel)
                .where(col(ThinkingStepModel.session_id) == session_id)
                .order_by(col(ThinkingStepModel.timestamp))
            )
            models = session.exec(statement).all()
            if not models:
                return None
            return ThinkingChain(
                session_id=session_id,
                steps=[self._to_entity(model) for model in models],
            )

    async def add_step(self, session_id: str, step: ThinkingStep) -> None:
        """Add a thinking step to the chain."""
        chain = await self.get_by_session(session_id)
        if not chain:
            chain = ThinkingChain(session_id=session_id)
        chain.add_step(step)
        await self.save(session_id, chain)

    async def delete(self, session_id: str) -> None:
        """Delete thinking chain."""
        with self.db.get_session() as session:
            session.exec(
                delete(ThinkingStepModel).where(
                    col(ThinkingStepModel.session_id) == session_id
                )
            )
            session.commit()

    @staticmethod
    def _to_model(session_id: str, step: ThinkingStep) -> ThinkingStepModel:
        """Convert a domain step into a persistence model."""
        return ThinkingStepModel(
            id=step.id,
            session_id=session_id,
            thinking_type=step.thinking_type.value,
            content=step.content,
            internal_reasoning=step.internal_reasoning,
            alternatives=[item.model_dump(mode="json") for item in step.alternatives],
            uncertainty_factors=step.uncertainty_factors,
            assumptions_made=step.assumptions_made,
            potential_biases=step.potential_biases,
            confidence=step.confidence,
            related_evidence_ids=step.related_evidence_ids,
            related_hypothesis_ids=step.related_hypothesis_ids,
            structured_data=step.structured_data,
            timestamp=step.timestamp,
        )

    @staticmethod
    def _to_entity(model: ThinkingStepModel) -> ThinkingStep:
        """Convert a persistence model into a domain step."""
        return ThinkingStep(
            id=model.id,
            timestamp=model.timestamp,
            thinking_type=ThinkingType(model.thinking_type),
            content=model.content,
            internal_reasoning=model.internal_reasoning,
            alternatives=[
                AlternativeConsidered.model_validate(item)
                for item in model.alternatives
            ],
            confidence=model.confidence,
            uncertainty_factors=model.uncertainty_factors,
            related_evidence_ids=model.related_evidence_ids,
            related_hypothesis_ids=model.related_hypothesis_ids,
            assumptions_made=model.assumptions_made,
            potential_biases=model.potential_biases,
            structured_data=model.structured_data,
        )
