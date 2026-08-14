"""Why Tree artifact export and teaching-case handlers."""

from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from datetime import datetime
from typing import TYPE_CHECKING, Any

from mcp.types import TextContent

from rootcause_mcp.application.guided_response import format_guided_response
from rootcause_mcp.domain.entities.why_node import TeachingCase, WhyChain
from rootcause_mcp.domain.value_objects.enums import TeachingLevel
from rootcause_mcp.domain.value_objects.identifiers import SessionId
from rootcause_mcp.infrastructure.export_paths import build_export_path
from rootcause_mcp.interface.mermaid import render_why_tree_mermaid

if TYPE_CHECKING:
    from rootcause_mcp.application.session_progress import SessionProgressTracker
    from rootcause_mcp.domain.repositories.why_tree_repository import WhyTreeRepository

logger = logging.getLogger(__name__)


class WhyTreeArtifactHandlers:
    """Generate persisted Why Tree and teaching artifacts."""

    def __init__(
        self,
        why_tree_repository: WhyTreeRepository | None,
        progress_tracker: SessionProgressTracker | None,
    ) -> None:
        self._why_repo = why_tree_repository
        self._progress = progress_tracker

    async def handle_export_why_tree(
        self, arguments: dict[str, Any]
    ) -> Sequence[TextContent]:
        """Export a Why Tree as JSON, Markdown, or Mermaid."""
        chain, error = self._get_chain(arguments["session_id"])
        if error is not None:
            return [error]
        assert chain is not None

        export_format = arguments.get("format", "mermaid")
        if export_format == "json":
            result = json.dumps(chain.to_dict(), indent=2, ensure_ascii=False)
        elif export_format == "markdown":
            result = _format_why_tree_markdown(chain)
        elif export_format == "mermaid":
            result = render_why_tree_mermaid(chain)
        else:
            return [
                TextContent(
                    type="text", text=f"Error: Unsupported format {export_format}"
                )
            ]

        file_path = self._write_export_file(
            arguments["session_id"], "why_tree", export_format, result
        )
        if file_path:
            result += (
                f"\n\n---\n📁 **Saved to:** `{file_path}`\n"
                "💡 Open in VS Code to preview the artifact"
            )
        return [TextContent(type="text", text=result)]

    async def handle_build_teaching_case(
        self, arguments: dict[str, Any]
    ) -> Sequence[TextContent]:
        """Build a teaching-case artifact from the Why Tree."""
        session_id = arguments["session_id"]
        chain, error = self._get_chain(session_id)
        if error is not None:
            return [error]
        assert chain is not None

        export_format = arguments.get("format", "markdown")
        learner_level = TeachingLevel(arguments.get("learner_level", "medical_student"))
        teaching_case = chain.build_teaching_case(learner_level)

        if export_format == "json":
            artifact = json.dumps(teaching_case.to_dict(), indent=2, ensure_ascii=False)
            file_path = self._write_export_file(
                session_id, "teaching_case", export_format, artifact
            )
            result = json.dumps(
                {"teaching_case": teaching_case.to_dict(), "saved_to": file_path},
                indent=2,
                ensure_ascii=False,
            )
        elif export_format == "markdown":
            result = _format_teaching_case_markdown(chain, teaching_case)
            file_path = self._write_export_file(
                session_id, "teaching_case", export_format, result
            )
            if file_path:
                result += (
                    f"\n\n---\n📁 **Saved to:** `{file_path}`\n"
                    "💡 Open in VS Code to review or adapt for teaching sessions"
                )
        else:
            return [
                TextContent(
                    type="text", text=f"Error: Unsupported format {export_format}"
                )
            ]

        if self._progress is not None and export_format != "json":
            progress = self._progress.update_from_why_tree(session_id, chain)
            result = format_guided_response(result, progress, "rc_build_teaching_case")
        return [TextContent(type="text", text=result)]

    def _get_chain(self, session_id: str) -> tuple[WhyChain | None, TextContent | None]:
        if self._why_repo is None:
            return None, TextContent(
                type="text", text="Error: WhyTreeRepository not initialized"
            )
        chain = self._why_repo.get_chain(SessionId.from_string(session_id))
        if chain is None:
            return None, TextContent(
                type="text",
                text=f"❌ **No Why Tree Found** for session `{session_id}`",
            )
        return chain, None

    def _write_export_file(
        self, session_id: str, export_type: str, export_format: str, content: str
    ) -> str | None:
        try:
            extension = "md" if export_format in {"mermaid", "markdown"} else "json"
            file_path = build_export_path(
                session_id=session_id,
                artifact=export_type,
                extension=extension,
            )
            if extension == "md":
                content = (
                    f"# {export_type.title()} Export\n\n"
                    f"**Session:** `{session_id}`\n"
                    f"**Exported:** {datetime.now().isoformat()}\n\n{content}"
                )
            file_path.write_text(content, encoding="utf-8")
            return str(file_path)
        except (OSError, ValueError) as exc:
            logger.warning("Failed to write export file: %s", exc)
            return None


def _format_why_tree_markdown(chain: WhyChain) -> str:
    lines = [
        f"# 5-Why Analysis: {chain.initial_problem}\n",
        f"**Depth:** {chain.depth} | **Complete:** {'Yes' if chain.is_complete else 'No'}\n",
    ]
    for node in chain.nodes:
        indent = "  " * (node.level - 1)
        root_marker = " 🎯 **ROOT CAUSE**" if node.is_root_cause else ""
        lines.append(f"\n{indent}**Why {node.level}:** {node.question}")
        lines.append(f"{indent}→ {node.answer}{root_marker}")
        if node.evidence:
            lines.append(f"{indent}  Evidence: {', '.join(node.evidence)}")
    if chain.root_causes:
        lines.append("\n## Root Causes Summary")
        lines.extend(f"- {root.answer}" for root in chain.root_causes)
    return "\n".join(lines)


def _format_teaching_case_markdown(
    chain: WhyChain,
    teaching_case: TeachingCase,
) -> str:
    lines = [
        f"# Teaching Case: {chain.initial_problem}",
        "",
        f"**Learner Level:** `{teaching_case.learner_level.value}`",
        "",
        "## Case Summary",
        teaching_case.case_summary,
        "",
        "## Learning Objectives",
    ]
    sections = (
        ("", teaching_case.learning_objectives),
        ("## Teaching Flow", teaching_case.teaching_flow),
        ("## Clinical Pearls", teaching_case.clinical_pearls),
        ("## Common Pitfalls", teaching_case.common_pitfalls),
        ("## Discussion Questions", teaching_case.discussion_questions),
    )
    for heading, items in sections:
        if heading:
            lines.extend(["", heading])
        lines.extend(f"- {item}" for item in items)
    if teaching_case.feedback_loops:
        lines.extend(["", "## Feedback Loops"])
        lines.extend(f"- {loop}" for loop in teaching_case.feedback_loops)
    lines.extend(["", "## Reverse Causality Prompts"])
    lines.extend(f"- {prompt}" for prompt in teaching_case.reverse_causality_prompts)
    return "\n".join(lines)
