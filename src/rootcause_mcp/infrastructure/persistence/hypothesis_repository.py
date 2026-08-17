"""
Hypothesis Repository (SQLite).

Persists Hypothesis entities to SQLite database.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlmodel import select

from rootcause_mcp.domain.entities.hypothesis import (
    BayesianUpdate,
    Hypothesis,
    HypothesisStatus,
    HypothesisStatusChange,
    LikelihoodRatio,
    PlannedDiagnosticTest,
)
from rootcause_mcp.domain.value_objects.clinical_concept import ClinicalConcept
from rootcause_mcp.domain.value_objects.identifiers import HypothesisId
from rootcause_mcp.infrastructure.persistence.models import HypothesisModel

if TYPE_CHECKING:
    from rootcause_mcp.infrastructure.persistence.database import Database


class SQLiteHypothesisRepository:
    """SQLModel implementation of the hypothesis repository."""

    def __init__(self, db: Database) -> None:
        """Initialize repository with database connection."""
        self.db = db

    async def save(self, session_id: str, hypothesis: Hypothesis) -> None:
        """Save hypothesis to database."""
        diagnosis_data = hypothesis.diagnosis.model_dump(mode="json")
        diagnosis_data["_hypothesis_context"] = {
            "must_not_miss": hypothesis.must_not_miss,
            "alternatives_considered": hypothesis.alternatives_considered,
            "uncertainty_factors": hypothesis.uncertainty_factors,
            "confidence_rationale": hypothesis.confidence_rationale,
            "planned_tests": [
                item.model_dump(mode="json") for item in hypothesis.planned_tests
            ],
        }
        model = HypothesisModel(
            id=hypothesis.id.value,
            session_id=session_id,
            diagnosis_data=diagnosis_data,
            prior_probability=hypothesis.prior_probability,
            current_probability=hypothesis.current_probability,
            inclusion_criteria=hypothesis.inclusion_criteria,
            exclusion_criteria=hypothesis.exclusion_criteria,
            likelihood_ratios=[
                item.model_dump(mode="json") for item in hypothesis.likelihood_ratios
            ],
            supporting_evidence_ids=hypothesis.supporting_evidence_ids,
            contradicting_evidence_ids=hypothesis.contradicting_evidence_ids,
            status=hypothesis.status.value,
            status_history=[
                item.model_dump(mode="json") for item in hypothesis.status_history
            ],
            bayesian_history=[
                item.model_dump(mode="json") for item in hypothesis.bayesian_history
            ],
            clinical_rationale=hypothesis.clinical_rationale,
            created_by=hypothesis.created_by,
            created_at=hypothesis.created_at,
        )
        with self.db.get_session() as session:
            session.merge(model)
            session.commit()

    async def get_by_id(self, session_id: str, hypothesis_id: str) -> Hypothesis | None:
        """Get hypothesis by ID."""
        with self.db.get_session() as session:
            statement = select(HypothesisModel).where(
                HypothesisModel.id == hypothesis_id,
                HypothesisModel.session_id == session_id,
            )
            model = session.exec(statement).first()
            return self._to_entity(model) if model else None

    async def list_by_session(self, session_id: str) -> list[Hypothesis]:
        """List all hypotheses for a session."""
        with self.db.get_session() as session:
            statement = select(HypothesisModel).where(
                HypothesisModel.session_id == session_id
            )
            return [self._to_entity(model) for model in session.exec(statement).all()]

    async def update(self, session_id: str, hypothesis: Hypothesis) -> None:
        """Update existing hypothesis."""
        await self.save(session_id, hypothesis)

    async def delete(self, session_id: str, hypothesis_id: str) -> None:
        """Delete hypothesis."""
        with self.db.get_session() as session:
            statement = select(HypothesisModel).where(
                HypothesisModel.id == hypothesis_id,
                HypothesisModel.session_id == session_id,
            )
            model = session.exec(statement).first()
            if model:
                session.delete(model)
                session.commit()

    @staticmethod
    def _to_entity(model: HypothesisModel) -> Hypothesis:
        """Convert a persistence model into a domain entity."""
        context = model.diagnosis_data.get("_hypothesis_context", {})
        return Hypothesis(
            id=HypothesisId(model.id),
            diagnosis=ClinicalConcept.model_validate(model.diagnosis_data),
            prior_probability=model.prior_probability,
            current_probability=model.current_probability,
            inclusion_criteria=model.inclusion_criteria,
            exclusion_criteria=model.exclusion_criteria,
            must_not_miss=bool(context.get("must_not_miss", False)),
            alternatives_considered=list(context.get("alternatives_considered", [])),
            uncertainty_factors=list(context.get("uncertainty_factors", [])),
            confidence_rationale=str(context.get("confidence_rationale", "")),
            planned_tests=[
                PlannedDiagnosticTest.model_validate(item)
                for item in context.get("planned_tests", [])
            ],
            likelihood_ratios=[
                LikelihoodRatio.model_validate(item) for item in model.likelihood_ratios
            ],
            supporting_evidence_ids=model.supporting_evidence_ids,
            contradicting_evidence_ids=model.contradicting_evidence_ids,
            status=HypothesisStatus(model.status),
            status_history=[
                HypothesisStatusChange.model_validate(item)
                for item in model.status_history
            ],
            created_at=model.created_at,
            created_by=model.created_by,
            bayesian_history=[
                BayesianUpdate.model_validate(item) for item in model.bayesian_history
            ],
            clinical_rationale=model.clinical_rationale,
        )
