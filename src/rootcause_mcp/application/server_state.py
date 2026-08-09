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


class ServerState:
    """
    Shared state across all handlers.

    Ensures all handlers work with the same Orchestrator instance per session.
    """

    def __init__(self) -> None:
        """Initialize server state."""
        self._orchestrators: dict[str, ClinicalReasoningOrchestrator] = {}

    def get_or_create_orchestrator(self, session_id: str) -> ClinicalReasoningOrchestrator:
        """
        Get or create Orchestrator for a session.

        Args:
            session_id: RCA session ID

        Returns:
            ClinicalReasoningOrchestrator instance
        """
        if session_id not in self._orchestrators:
            from rootcause_mcp.application.clinical_reasoning_orchestrator import (
                ClinicalReasoningOrchestrator,
            )

            self._orchestrators[session_id] = ClinicalReasoningOrchestrator(session_id)

        return self._orchestrators[session_id]

    def get_orchestrator(self, session_id: str) -> ClinicalReasoningOrchestrator | None:
        """
        Get existing Orchestrator (does not create).

        Args:
            session_id: RCA session ID

        Returns:
            ClinicalReasoningOrchestrator or None if not found
        """
        return self._orchestrators.get(session_id)

    def remove_orchestrator(self, session_id: str) -> None:
        """Remove Orchestrator for a session."""
        if session_id in self._orchestrators:
            del self._orchestrators[session_id]

    def list_sessions(self) -> list[str]:
        """List all active session IDs."""
        return list(self._orchestrators.keys())
