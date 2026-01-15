"""
Session Handler implementations.

Handles 4 Session management tools:
- rc_start_session
- rc_get_session
- rc_list_sessions
- rc_archive_session
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from mcp.types import TextContent

from rootcause_mcp.application.guided_response import format_guided_response
from rootcause_mcp.domain.entities.session import RCASession
from rootcause_mcp.domain.value_objects.enums import CaseType, SessionStatus

if TYPE_CHECKING:
    from rootcause_mcp.application.session_progress import SessionProgressTracker
    from rootcause_mcp.domain.repositories.session_repository import SessionRepository

logger = logging.getLogger(__name__)


class SessionHandlers:
    """Handler class for Session management tools."""

    def __init__(
        self,
        session_repository: SessionRepository | None = None,
        progress_tracker: SessionProgressTracker | None = None,
    ) -> None:
        """Initialize handlers with dependencies."""
        self._repo = session_repository
        self._progress = progress_tracker

    async def handle_start_session(
        self, arguments: dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle rc_start_session tool call."""
        if self._repo is None:
            return [TextContent(type="text", text="Error: SessionRepository not initialized")]

        case_type_str = arguments["case_type"]
        case_title = arguments["case_title"]
        initial_description = arguments.get("initial_description", "")

        try:
            case_type = CaseType(case_type_str)
        except ValueError:
            return [TextContent(
                type="text",
                text=f"Error: Invalid case_type '{case_type_str}'. "
                     f"Valid options: {[ct.value for ct in CaseType]}"
            )]

        session = RCASession.create(
            case_type=case_type,
            case_title=case_title,
            initial_description=initial_description,
        )

        self._repo.save(session)

        result = (
            "✅ **Session Created Successfully**\n\n"
            f"- **Session ID:** `{session.id}`\n"
            f"- **Case Type:** {case_type.value}\n"
            f"- **Title:** {case_title}\n"
            f"- **Current Stage:** {session.current_stage.value}\n\n"
            "**Next Steps:**\n"
            "1. Use `rc_init_fishbone` to create a Fishbone diagram\n"
            "2. Use `rc_suggest_hfacs` to get classification suggestions\n"
            "3. Use `rc_add_cause` to document causes"
        )

        # Add guided response with progress tracking
        if self._progress is not None:
            progress = self._progress.get_progress(str(session.id))
            result = format_guided_response(result, progress, "rc_start_session")

        return [TextContent(type="text", text=result)]

    async def handle_get_session(
        self, arguments: dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle rc_get_session tool call."""
        if self._repo is None:
            return [TextContent(type="text", text="Error: SessionRepository not initialized")]

        session_id = arguments["session_id"]
        session = self._repo.get_by_id(session_id)

        if session is None:
            return [TextContent(
                type="text",
                text=f"❌ **Session Not Found**\n\nNo session with ID: `{session_id}`"
            )]

        progress = session.get_progress()
        progress_lines = [f"  - {stage}: {status}" for stage, status in progress.items()]

        result = (
            f"# Session: {session.case_title}\n\n"
            f"- **Session ID:** `{session.id}`\n"
            f"- **Case Type:** {session.case_type.value}\n"
            f"- **Status:** {session.status.value}\n"
            f"- **Current Stage:** {session.current_stage.value}\n"
            f"- **Created:** {session.created_at.strftime('%Y-%m-%d %H:%M')}\n"
            f"- **Updated:** {session.updated_at.strftime('%Y-%m-%d %H:%M')}\n\n"
            "**Stage Progress:**\n" + "\n".join(progress_lines)
        )

        if session.problem_statement:
            result += f"\n\n**Problem Statement:**\n{session.problem_statement}"

        return [TextContent(type="text", text=result)]

    async def handle_list_sessions(
        self, arguments: dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle rc_list_sessions tool call."""
        if self._repo is None:
            return [TextContent(type="text", text="Error: SessionRepository not initialized")]

        status_str = arguments.get("status")
        case_type_str = arguments.get("case_type")
        limit = arguments.get("limit", 20)

        status = SessionStatus(status_str) if status_str else None
        case_type = CaseType(case_type_str) if case_type_str else None

        sessions = self._repo.list_all(
            status=status,
            case_type=case_type,
            limit=limit,
        )

        if not sessions:
            result = "📋 **No Sessions Found**\n\nNo sessions match the specified criteria."
            if status_str or case_type_str:
                result += f"\n\nFilters applied: status={status_str}, case_type={case_type_str}"
        else:
            lines = [f"# RCA Sessions ({len(sessions)} found)\n"]

            for s in sessions:
                status_emoji = {
                    SessionStatus.ACTIVE: "🟢",
                    SessionStatus.COMPLETED: "✅",
                    SessionStatus.ABANDONED: "🔴",
                    SessionStatus.ARCHIVED: "📦",
                }.get(s.status, "⚪")

                lines.append(
                    f"### {status_emoji} {s.case_title}\n"
                    f"- **ID:** `{s.id}`\n"
                    f"- **Type:** {s.case_type.value}\n"
                    f"- **Stage:** {s.current_stage.value}\n"
                    f"- **Updated:** {s.updated_at.strftime('%Y-%m-%d %H:%M')}\n"
                )

            result = "\n".join(lines)

        return [TextContent(type="text", text=result)]

    async def handle_archive_session(
        self, arguments: dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle rc_archive_session tool call."""
        if self._repo is None:
            return [TextContent(type="text", text="Error: SessionRepository not initialized")]

        session_id = arguments["session_id"]
        session = self._repo.get_by_id(session_id)

        if session is None:
            return [TextContent(
                type="text",
                text=f"❌ **Session Not Found**\n\nNo session with ID: `{session_id}`"
            )]

        session.archive()
        self._repo.save(session)

        result = (
            "📦 **Session Archived**\n\n"
            f"- **Session ID:** `{session.id}`\n"
            f"- **Title:** {session.case_title}\n"
            f"- **Status:** {session.status.value}\n\n"
            "The session has been archived and is now read-only."
        )

        return [TextContent(type="text", text=result)]
