"""
Server State Management.

Centralized state for all handlers to share Orchestrator instances.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rootcause_mcp.application.clinical_reasoning_orchestrator import (
        ClinicalReasoningOrchestrator,
    )
    from rootcause_mcp.domain.repositories.medical_reasoning_repository import (
        EvidenceRepository,
        HypothesisRepository,
        ReasoningChainRepository,
        ThinkingChainRepository,
    )


class ServerState:
    """
    Shared state across all handlers.

    Ensures all handlers work with the same Orchestrator instance per session.
    """

    def __init__(
        self,
        *,
        evidence_repository: EvidenceRepository | None = None,
        hypothesis_repository: HypothesisRepository | None = None,
        thinking_repository: ThinkingChainRepository | None = None,
        reasoning_repository: ReasoningChainRepository | None = None,
    ) -> None:
        """Initialize shared state with optional persistence adapters."""
        self._orchestrators: dict[str, ClinicalReasoningOrchestrator] = {}
        self._evidence_repository = evidence_repository
        self._hypothesis_repository = hypothesis_repository
        self._thinking_repository = thinking_repository
        self._reasoning_repository = reasoning_repository

    async def get_or_create_orchestrator(
        self, session_id: str
    ) -> ClinicalReasoningOrchestrator:
        """
        Get or create Orchestrator for a session.

        Args:
            session_id: RCA session ID

        Returns:
            ClinicalReasoningOrchestrator instance
        """
        existing = self._orchestrators.get(session_id)
        if existing is not None:
            return existing
        created = await self._hydrate(session_id, create_if_empty=True)
        assert created is not None
        return created

    async def get_orchestrator(
        self, session_id: str
    ) -> ClinicalReasoningOrchestrator | None:
        """
        Get existing Orchestrator (does not create).

        Args:
            session_id: RCA session ID

        Returns:
            ClinicalReasoningOrchestrator or None if not found
        """
        existing = self._orchestrators.get(session_id)
        if existing is not None:
            return existing
        return await self._hydrate(session_id, create_if_empty=False)

    async def persist_orchestrator(self, session_id: str) -> None:
        """Persist every component of a session aggregate."""
        orchestrator = self._orchestrators.get(session_id)
        if orchestrator is None:
            raise KeyError(f"No orchestrator found for session {session_id}")

        if self._evidence_repository is not None:
            for evidence in orchestrator.evidence_store.values():
                await self._evidence_repository.save(session_id, evidence)
        if self._hypothesis_repository is not None:
            for hypothesis in orchestrator.hypothesis_store.values():
                await self._hypothesis_repository.save(session_id, hypothesis)
        if self._thinking_repository is not None:
            await self._thinking_repository.save(
                session_id,
                orchestrator.thinking_chain,
            )
        if self._reasoning_repository is not None:
            await self._reasoning_repository.save(
                session_id,
                orchestrator.reasoning_chain,
            )

    async def _hydrate(
        self,
        session_id: str,
        *,
        create_if_empty: bool,
    ) -> ClinicalReasoningOrchestrator | None:
        """Load an aggregate from repositories or create a new empty one."""
        from rootcause_mcp.application.clinical_reasoning_orchestrator import (
            ClinicalReasoningOrchestrator,
        )

        evidence = (
            await self._evidence_repository.list_by_session(session_id)
            if self._evidence_repository is not None
            else []
        )
        hypotheses = (
            await self._hypothesis_repository.list_by_session(session_id)
            if self._hypothesis_repository is not None
            else []
        )
        thinking_chain = (
            await self._thinking_repository.get_by_session(session_id)
            if self._thinking_repository is not None
            else None
        )
        reasoning_chain = (
            await self._reasoning_repository.get_by_session(session_id)
            if self._reasoning_repository is not None
            else None
        )
        if (
            not create_if_empty
            and not evidence
            and not hypotheses
            and thinking_chain is None
            and reasoning_chain is None
        ):
            return None

        orchestrator = ClinicalReasoningOrchestrator(session_id)
        orchestrator.restore(
            evidence=evidence,
            hypotheses=hypotheses,
            thinking_chain=thinking_chain,
            reasoning_chain=reasoning_chain,
        )
        self._orchestrators[session_id] = orchestrator
        return orchestrator

    def remove_orchestrator(self, session_id: str) -> None:
        """Remove Orchestrator for a session."""
        if session_id in self._orchestrators:
            del self._orchestrators[session_id]

    def list_sessions(self) -> list[str]:
        """List all active session IDs."""
        return list(self._orchestrators.keys())
