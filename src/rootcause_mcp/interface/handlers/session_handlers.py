"""
Session Handler implementations.

Handles 5 Session management tools:
- rc_start_session
- rc_adjudicate_source
- rc_get_session
- rc_list_sessions
- rc_archive_session
"""

from __future__ import annotations

import logging
import os
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from mcp.types import TextContent
from pydantic import ValidationError

from rootcause_mcp.application.guided_response import format_guided_response
from rootcause_mcp.domain.entities.session import RCASession
from rootcause_mcp.domain.value_objects.case_manifest import (
    CaseInputManifest,
    SourceIndependenceStatus,
    SourceReviewAdjudication,
    SourceReviewStatus,
)
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
            return [
                TextContent(
                    type="text", text="Error: SessionRepository not initialized"
                )
            ]

        case_type_str = arguments["case_type"]
        case_title = arguments["case_title"]
        initial_description = arguments.get("initial_description", "")

        try:
            case_type = CaseType(case_type_str)
        except ValueError:
            return [
                TextContent(
                    type="text",
                    text=f"Error: Invalid case_type '{case_type_str}'. "
                    f"Valid options: {[ct.value for ct in CaseType]}",
                )
            ]

        source_manifest: CaseInputManifest | None = None
        if raw_manifest := arguments.get("source_manifest"):
            try:
                source_manifest = CaseInputManifest.model_validate(raw_manifest)
            except ValidationError:
                return [
                    TextContent(
                        type="text",
                        text=(
                            "Error: Invalid source_manifest. Each document requires a "
                            "unique document_id, source_uri, whole-file sha256, media_type, "
                            "and source_kind."
                        ),
                    )
                ]

        session = RCASession.create(
            case_type=case_type,
            case_title=case_title,
            initial_description=initial_description,
        )
        if source_manifest is not None:
            session.set_source_manifest(source_manifest)

        self._repo.save(session)

        source_summary = (
            f"- **Registered Sources:** {len(source_manifest.documents)}\n"
            f"- **Source Manifest Digest:** `{source_manifest.digest}`\n\n"
            if source_manifest is not None
            else "- **Registered Sources:** 0 (source coverage is unknown)\n\n"
        )
        result = (
            "✅ **Session Created Successfully**\n\n"
            f"- **Session ID:** `{session.id}`\n"
            f"- **Case Type:** {case_type.value}\n"
            f"- **Title:** {case_title}\n"
            f"- **Current Stage:** {session.current_stage.value}\n\n"
            + source_summary
            + "**Next Steps:**\n"
            "1. Use `rc_init_fishbone` to create a Fishbone diagram\n"
            "2. Use `rc_suggest_hfacs` to get classification suggestions\n"
            "3. Use `rc_add_cause` to document causes"
        )

        # Add guided response with progress tracking
        if self._progress is not None:
            progress = self._progress.get_progress(str(session.id))
            result = format_guided_response(result, progress, "rc_start_session")

        return [TextContent(type="text", text=result)]

    async def handle_adjudicate_source(
        self, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Append an authorized review transition without changing manifest identity."""
        if self._repo is None:
            return {
                "status": "error",
                "message": "SessionRepository not initialized",
            }
        session_id = str(arguments.get("session_id") or "")
        session = self._repo.get_by_id(session_id)
        if session is None:
            return {
                "status": "not_found",
                "message": f"No session with ID: {session_id}",
            }
        reviewer = str(arguments.get("reviewed_by") or "").strip()
        authorized_reviewers = {
            item.strip()
            for item in os.environ.get("ROOTCAUSE_AUTHORIZED_REVIEWERS", "").split(",")
            if item.strip()
        }
        if not reviewer or reviewer not in authorized_reviewers:
            return {
                "status": "error",
                "message": (
                    "reviewed_by must be a named member of "
                    "ROOTCAUSE_AUTHORIZED_REVIEWERS"
                ),
            }
        manifest = session.get_source_manifest()
        if manifest is None:
            return {
                "status": "error",
                "message": "Source adjudication requires a pinned source manifest",
            }
        try:
            adjudication = SourceReviewAdjudication(
                adjudication_id=f"SRV-{uuid4().hex}",
                manifest_digest=manifest.digest,
                document_id=arguments["document_id"],
                status=SourceReviewStatus(arguments["source_status"]),
                de_identified=arguments.get("de_identified"),
                independence_status=SourceIndependenceStatus(
                    arguments.get("independence_status", "unknown")
                ),
                source_group_id=arguments.get("source_group_id"),
                parent_document_id=arguments.get("parent_document_id"),
                derivation_method=arguments.get("derivation_method"),
                reviewed_by=reviewer,
                reason=arguments["reason"],
                reviewed_at=datetime.now(UTC),
            )
            session.record_source_review(adjudication)
        except (KeyError, ValueError, ValidationError) as exc:
            return {"status": "error", "message": str(exc)}
        self._repo.save(session)
        return {
            "status": "success",
            "session_id": session_id,
            "manifest_digest": manifest.digest,
            "source_review": adjudication.model_dump(mode="json"),
            "append_only": True,
        }

    async def handle_get_session(
        self, arguments: dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle rc_get_session tool call."""
        if self._repo is None:
            return [
                TextContent(
                    type="text", text="Error: SessionRepository not initialized"
                )
            ]

        session_id = arguments["session_id"]
        session = self._repo.get_by_id(session_id)

        if session is None:
            return [
                TextContent(
                    type="text",
                    text=f"❌ **Session Not Found**\n\nNo session with ID: `{session_id}`",
                )
            ]

        progress = session.get_progress()
        progress_lines = [
            f"  - {stage}: {status}" for stage, status in progress.items()
        ]

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

        source_manifest = session.get_source_manifest()
        if source_manifest is not None:
            latest_reviews = session.get_latest_source_reviews()
            effective_statuses = [
                latest_reviews.get(document.document_id, document).status.value
                for document in source_manifest.documents
            ]
            result += (
                "\n\n**Source Manifest:**\n"
                f"- Documents: {len(source_manifest.documents)}\n"
                f"- Digest: `{source_manifest.digest}`\n"
                f"- Effective statuses: {', '.join(effective_statuses)}\n"
                f"- Append-only review events: {len(session.get_source_review_ledger())}"
            )

        return [TextContent(type="text", text=result)]

    async def handle_list_sessions(
        self, arguments: dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle rc_list_sessions tool call."""
        if self._repo is None:
            return [
                TextContent(
                    type="text", text="Error: SessionRepository not initialized"
                )
            ]

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
            result = (
                "📋 **No Sessions Found**\n\nNo sessions match the specified criteria."
            )
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
            return [
                TextContent(
                    type="text", text="Error: SessionRepository not initialized"
                )
            ]

        session_id = arguments["session_id"]
        session = self._repo.get_by_id(session_id)

        if session is None:
            return [
                TextContent(
                    type="text",
                    text=f"❌ **Session Not Found**\n\nNo session with ID: `{session_id}`",
                )
            ]

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
