"""SQLModel persistence for clinical reasoning chains."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlmodel import col, delete, select

from rootcause_mcp.domain.entities.reasoning_step import (
    ReasoningChain,
    ReasoningStep,
    ReasoningStepType,
)
from rootcause_mcp.domain.value_objects.identifiers import ReasoningStepId
from rootcause_mcp.infrastructure.persistence.models import ReasoningStepModel

if TYPE_CHECKING:
    from rootcause_mcp.infrastructure.persistence.database import Database


class SQLiteReasoningChainRepository:
    """Persist an ordered reasoning chain as individual SQLModel rows."""

    def __init__(self, db: Database) -> None:
        self.db = db

    async def save(self, session_id: str, chain: ReasoningChain) -> None:
        """Replace the persisted chain for a session atomically."""
        with self.db.get_session() as session:
            session.exec(
                delete(ReasoningStepModel).where(
                    col(ReasoningStepModel.session_id) == session_id
                )
            )
            for step in chain.steps:
                session.add(self._to_model(session_id, step))
            session.commit()

    async def get_by_session(self, session_id: str) -> ReasoningChain | None:
        """Load an ordered reasoning chain for a session."""
        with self.db.get_session() as session:
            statement = (
                select(ReasoningStepModel)
                .where(col(ReasoningStepModel.session_id) == session_id)
                .order_by(col(ReasoningStepModel.sequence_number))
            )
            models = session.exec(statement).all()
            if not models:
                return None
            return ReasoningChain(
                session_id=session_id,
                steps=[self._to_entity(model) for model in models],
                finalized_at=None,
            )

    async def delete(self, session_id: str) -> None:
        """Delete every reasoning step for a session."""
        with self.db.get_session() as session:
            session.exec(
                delete(ReasoningStepModel).where(
                    col(ReasoningStepModel.session_id) == session_id
                )
            )
            session.commit()

    @staticmethod
    def _to_model(session_id: str, step: ReasoningStep) -> ReasoningStepModel:
        return ReasoningStepModel(
            id=step.id.value,
            session_id=session_id,
            sequence_number=step.sequence_number,
            timestamp=step.timestamp,
            step_type=step.step_type.value,
            content=step.content,
            rationale=step.rationale,
            evidence_ids=step.evidence_ids,
            hypothesis_ids=step.hypothesis_ids,
            cause_ids=step.cause_ids,
            agent_id=step.agent_id,
            agent_model=step.agent_model,
            confidence=step.confidence,
            tokens_used=step.tokens_used,
            chain_of_thought=step.chain_of_thought,
        )

    @staticmethod
    def _to_entity(model: ReasoningStepModel) -> ReasoningStep:
        return ReasoningStep(
            id=ReasoningStepId(model.id),
            sequence_number=model.sequence_number,
            timestamp=model.timestamp,
            step_type=ReasoningStepType(model.step_type),
            content=model.content,
            rationale=model.rationale,
            evidence_ids=model.evidence_ids,
            hypothesis_ids=model.hypothesis_ids,
            cause_ids=model.cause_ids,
            agent_id=model.agent_id,
            agent_model=model.agent_model,
            confidence=model.confidence,
            tokens_used=model.tokens_used,
            chain_of_thought=model.chain_of_thought,
        )
