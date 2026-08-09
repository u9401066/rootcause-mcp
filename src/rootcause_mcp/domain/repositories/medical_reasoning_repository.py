"""Repository contracts for the medical reasoning aggregate."""

from __future__ import annotations

from typing import Protocol

from rootcause_mcp.domain.entities.evidence import Evidence
from rootcause_mcp.domain.entities.hypothesis import Hypothesis
from rootcause_mcp.domain.entities.reasoning_step import ReasoningChain
from rootcause_mcp.domain.entities.thinking_step import ThinkingChain


class EvidenceRepository(Protocol):
    async def save(self, session_id: str, evidence: Evidence) -> None: ...

    async def get_by_id(self, session_id: str, evidence_id: str) -> Evidence | None: ...

    async def list_by_session(self, session_id: str) -> list[Evidence]: ...


class HypothesisRepository(Protocol):
    async def save(self, session_id: str, hypothesis: Hypothesis) -> None: ...

    async def get_by_id(
        self, session_id: str, hypothesis_id: str
    ) -> Hypothesis | None: ...

    async def list_by_session(self, session_id: str) -> list[Hypothesis]: ...


class ThinkingChainRepository(Protocol):
    async def save(self, session_id: str, chain: ThinkingChain) -> None: ...

    async def get_by_session(self, session_id: str) -> ThinkingChain | None: ...


class ReasoningChainRepository(Protocol):
    async def save(self, session_id: str, chain: ReasoningChain) -> None: ...

    async def get_by_session(self, session_id: str) -> ReasoningChain | None: ...
