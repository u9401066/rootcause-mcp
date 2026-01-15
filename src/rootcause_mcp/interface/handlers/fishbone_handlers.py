"""
Fishbone Handler implementations.

Handles 4 Fishbone diagram tools:
- rc_init_fishbone
- rc_add_cause
- rc_get_fishbone
- rc_export_fishbone
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any, Sequence

from mcp.types import TextContent

from rootcause_mcp.domain.entities.fishbone import Fishbone, FishboneCause
from rootcause_mcp.domain.value_objects.enums import FishboneCategoryType
from rootcause_mcp.domain.value_objects.identifiers import CauseId, SessionId

if TYPE_CHECKING:
    from rootcause_mcp.domain.repositories.fishbone_repository import FishboneRepository
    from rootcause_mcp.domain.repositories.session_repository import SessionRepository
    from rootcause_mcp.application.session_progress import SessionProgressTracker

logger = logging.getLogger(__name__)


class FishboneHandlers:
    """Handler class for Fishbone diagram tools."""

    def __init__(
        self,
        fishbone_repository: FishboneRepository | None = None,
        session_repository: SessionRepository | None = None,
        progress_tracker: SessionProgressTracker | None = None,
    ) -> None:
        """Initialize handlers with dependencies."""
        self._fishbone_repo = fishbone_repository
        self._session_repo = session_repository
        self._progress = progress_tracker

    async def handle_init_fishbone(
        self, arguments: dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle rc_init_fishbone tool call."""
        if self._session_repo is None or self._fishbone_repo is None:
            return [TextContent(type="text", text="Error: Repositories not initialized")]

        session_id = arguments["session_id"]
        problem_statement = arguments["problem_statement"]

        session = self._session_repo.get_by_id(session_id)
        if session is None:
            return [TextContent(
                type="text",
                text=f"❌ **Session Not Found**\n\nNo session with ID: `{session_id}`"
            )]

        existing = self._fishbone_repo.get_by_session(SessionId.from_string(session_id))
        if existing:
            return [TextContent(
                type="text",
                text=(
                    f"⚠️ **Fishbone Already Exists**\n\n"
                    f"Session `{session_id}` already has a Fishbone diagram.\n"
                    f"Use `rc_get_fishbone` to view it or `rc_add_cause` to add causes."
                )
            )]

        fishbone = Fishbone.create(
            session_id=SessionId.from_string(session_id),
            problem_statement=problem_statement,
        )

        session.set_problem(problem_statement)

        self._fishbone_repo.save(fishbone)
        self._session_repo.save(session)

        categories = [cat.value for cat in FishboneCategoryType]

        result = (
            "✅ **Fishbone Diagram Initialized**\n\n"
            f"- **Session:** `{session_id}`\n"
            f"- **Problem (Fish Head):** {problem_statement}\n\n"
            "**6M Categories Ready:**\n"
            + "\n".join(f"- {cat}" for cat in categories) +
            "\n\n**Next Steps:**\n"
            "Use `rc_add_cause` to add causes to each category."
        )

        return [TextContent(type="text", text=result)]

    async def handle_add_cause(
        self, arguments: dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle rc_add_cause tool call."""
        if self._fishbone_repo is None:
            return [TextContent(type="text", text="Error: FishboneRepository not initialized")]

        session_id = arguments["session_id"]
        category_str = arguments["category"]
        description = arguments["description"]
        sub_causes = arguments.get("sub_causes", [])
        hfacs_code = arguments.get("hfacs_code")
        evidence = arguments.get("evidence", [])

        fishbone = self._fishbone_repo.get_by_session(SessionId.from_string(session_id))
        if fishbone is None:
            return [TextContent(
                type="text",
                text=(
                    f"❌ **Fishbone Not Found**\n\n"
                    f"No Fishbone for session `{session_id}`.\n"
                    "Use `rc_init_fishbone` first."
                )
            )]

        try:
            category = FishboneCategoryType(category_str)
        except ValueError:
            return [TextContent(
                type="text",
                text=(
                    f"Error: Invalid category '{category_str}'. "
                    f"Valid options: {[cat.value for cat in FishboneCategoryType]}"
                )
            )]

        cause = FishboneCause(
            cause_id=CauseId.generate(),
            category=category,
            description=description,
            sub_causes=sub_causes,
            hfacs_code=hfacs_code,
            evidence=evidence,
        )

        fishbone.add_cause_to_category(category, cause)
        self._fishbone_repo.save(fishbone)

        result = (
            "✅ **Cause Added**\n\n"
            f"- **Category:** {category.value}\n"
            f"- **Description:** {description}\n"
        )

        if sub_causes:
            result += f"- **Sub-causes:** {', '.join(sub_causes)}\n"
        if hfacs_code:
            result += f"- **HFACS Code:** {hfacs_code}\n"
        if evidence:
            result += f"- **Evidence:** {', '.join(evidence)}\n"

        result += (
            f"\n**Fishbone Status:**\n"
            f"- Total causes: {fishbone.total_cause_count}\n"
            f"- Categories covered: {len(fishbone.populated_categories)}/6 "
            f"({fishbone.coverage_ratio:.0%})"
        )

        return [TextContent(type="text", text=result)]

    async def handle_get_fishbone(
        self, arguments: dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle rc_get_fishbone tool call."""
        if self._fishbone_repo is None:
            return [TextContent(type="text", text="Error: FishboneRepository not initialized")]

        session_id = arguments["session_id"]

        fishbone = self._fishbone_repo.get_by_session(SessionId.from_string(session_id))
        if fishbone is None:
            return [TextContent(
                type="text",
                text=(
                    f"❌ **Fishbone Not Found**\n\n"
                    f"No Fishbone for session `{session_id}`.\n"
                    "Use `rc_init_fishbone` to create one."
                )
            )]

        lines = [
            f"# Fishbone Diagram\n",
            f"**Problem:** {fishbone.problem_statement}\n",
            f"**Total Causes:** {fishbone.total_cause_count}\n",
            f"**Coverage:** {fishbone.coverage_ratio:.0%}\n",
        ]

        for cat_type in FishboneCategoryType:
            category = fishbone.get_category(cat_type)
            if category.has_causes:
                lines.append(f"\n## {cat_type.value} ({category.cause_count} causes)")
                for cause in category.causes:
                    lines.append(f"\n### {cause.description}")
                    if cause.hfacs_code:
                        lines.append(f"- **HFACS:** {cause.hfacs_code}")
                    if cause.sub_causes:
                        lines.append(f"- **Sub-causes:** {', '.join(cause.sub_causes)}")
                    if cause.evidence:
                        lines.append(f"- **Evidence:** {', '.join(cause.evidence)}")
            else:
                lines.append(f"\n## {cat_type.value} (empty)")

        return [TextContent(type="text", text="\n".join(lines))]

    async def handle_export_fishbone(
        self, arguments: dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle rc_export_fishbone tool call."""
        if self._fishbone_repo is None:
            return [TextContent(type="text", text="Error: FishboneRepository not initialized")]

        session_id = arguments["session_id"]
        export_format = arguments.get("format", "mermaid")

        fishbone = self._fishbone_repo.get_by_session(SessionId.from_string(session_id))
        if fishbone is None:
            return [TextContent(
                type="text",
                text=(
                    f"❌ **Fishbone Not Found**\n\n"
                    f"No Fishbone for session `{session_id}`."
                )
            )]

        if export_format == "json":
            result = json.dumps(fishbone.to_dict(), indent=2, ensure_ascii=False)

        elif export_format == "markdown":
            lines = [
                f"# Fishbone Analysis: {fishbone.problem_statement}\n",
            ]
            for cat_type in FishboneCategoryType:
                category = fishbone.get_category(cat_type)
                lines.append(f"\n## {cat_type.value}")
                if category.has_causes:
                    for cause in category.causes:
                        lines.append(f"- {cause.description}")
                        if cause.hfacs_code:
                            lines.append(f"  - HFACS: {cause.hfacs_code}")
                        for sub in cause.sub_causes:
                            lines.append(f"  - {sub}")
                else:
                    lines.append("- (No causes identified)")
            result = "\n".join(lines)

        else:  # mermaid
            lines = [
                "```mermaid",
                "flowchart LR",
                f'    PROBLEM["{fishbone.problem_statement}"]',
            ]

            for cat_type in FishboneCategoryType:
                category = fishbone.get_category(cat_type)
                cat_id = cat_type.value.upper()
                lines.append(f'    {cat_id}["{cat_type.value}"] --> PROBLEM')

                for i, cause in enumerate(category.causes):
                    cause_id = f"{cat_id}_{i}"
                    desc = cause.description[:30] + "..." if len(cause.description) > 30 else cause.description
                    lines.append(f'    {cause_id}["{desc}"] --> {cat_id}')

            lines.append("```")
            result = "\n".join(lines)

        return [TextContent(type="text", text=result)]
