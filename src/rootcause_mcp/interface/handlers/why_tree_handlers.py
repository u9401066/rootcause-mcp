"""
Why Tree Handler implementations.

Handles 4 Why Tree (5-Why Analysis) tools:
- rc_ask_why
- rc_get_why_tree
- rc_mark_root_cause
- rc_export_why_tree
"""

from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from mcp.types import TextContent

from rootcause_mcp.application.guided_response import format_guided_response
from rootcause_mcp.domain.entities.why_node import WhyChain, WhyNode
from rootcause_mcp.domain.value_objects.identifiers import CauseId, SessionId

if TYPE_CHECKING:
    from rootcause_mcp.application.session_progress import SessionProgressTracker
    from rootcause_mcp.domain.repositories.session_repository import SessionRepository
    from rootcause_mcp.domain.repositories.why_tree_repository import WhyTreeRepository

logger = logging.getLogger(__name__)


class WhyTreeHandlers:
    """Handler class for Why Tree tools."""

    # Export directory relative to project root
    EXPORT_DIR = Path("data/exports")

    # Cause type mapping by Why Tree depth
    CAUSE_TYPE_BY_LEVEL = {
        1: {
            "type": "Proximate",
            "chinese": "近端原因",
            "emoji": "🔴",
            "hfacs_hint": "通常對應 HFACS Level 1 (Unsafe Acts) 或 Level 2 (Preconditions)",
        },
        2: {
            "type": "Proximate/Intermediate",
            "chinese": "近端/中間原因",
            "emoji": "🟠",
            "hfacs_hint": "通常對應 HFACS Level 2 (Preconditions) 或 Level 3 (Supervision)",
        },
        3: {
            "type": "Intermediate",
            "chinese": "中間原因",
            "emoji": "🟡",
            "hfacs_hint": "通常對應 HFACS Level 3 (Unsafe Supervision)",
        },
        4: {
            "type": "Intermediate/Ultimate",
            "chinese": "中間/遠端原因",
            "emoji": "🟢",
            "hfacs_hint": "通常對應 HFACS Level 3-4 (Supervision/Organizational)",
        },
        5: {
            "type": "Ultimate",
            "chinese": "遠端/根本原因",
            "emoji": "💚",
            "hfacs_hint": "通常對應 HFACS Level 4 (Organizational Influences)",
        },
    }

    def __init__(
        self,
        why_tree_repository: WhyTreeRepository | None = None,
        session_repository: SessionRepository | None = None,
        progress_tracker: SessionProgressTracker | None = None,
    ) -> None:
        """Initialize handlers with dependencies."""
        self._why_repo = why_tree_repository
        self._session_repo = session_repository
        self._progress = progress_tracker

    def _write_export_file(
        self, session_id: str, export_type: str, export_format: str, content: str
    ) -> str | None:
        """Write export content to file and return path."""
        try:
            # Create session-specific export directory
            export_dir = self.EXPORT_DIR / session_id
            export_dir.mkdir(parents=True, exist_ok=True)

            # Determine file extension
            ext = "md" if export_format in ("mermaid", "markdown") else "json"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{export_type}_{timestamp}.{ext}"
            file_path = export_dir / filename

            # Add header for markdown files
            if ext == "md":
                header = f"# {export_type.replace('_', ' ').title()} Export\n\n"
                header += f"**Session:** `{session_id}`\n"
                header += f"**Exported:** {datetime.now().isoformat()}\n\n"
                content = header + content

            file_path.write_text(content, encoding="utf-8")
            logger.info(f"Exported {export_type} to {file_path}")
            return str(file_path)
        except Exception as e:
            logger.warning(f"Failed to write export file: {e}")
            return None

    def _get_cause_type_by_level(self, level: int) -> dict[str, str]:
        """Get cause type information based on Why Tree depth."""
        return self.CAUSE_TYPE_BY_LEVEL.get(level, {
            "type": "Unknown",
            "chinese": "未知",
            "emoji": "⚪",
            "hfacs_hint": "無對應資訊",
        })

    async def handle_ask_why(
        self, arguments: dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle rc_ask_why tool call - the core reasoning tool."""
        if self._why_repo is None or self._session_repo is None:
            return [TextContent(type="text", text="Error: Repositories not initialized")]

        session_id_str = arguments["session_id"]
        answer = arguments["answer"]
        parent_node_id = arguments.get("parent_node_id")
        evidence = arguments.get("evidence", [])
        initial_problem = arguments.get("initial_problem")

        session_id = SessionId.from_string(session_id_str)

        session = self._session_repo.get_by_id(session_id_str)
        if session is None:
            return [TextContent(
                type="text",
                text=f"❌ **Session Not Found**\n\nNo session with ID: `{session_id_str}`"
            )]

        chain = self._why_repo.get_chain(session_id)

        if chain is None:
            if not initial_problem:
                initial_problem = session.problem_statement or "問題待定義"

            # Create new WhyChain and save it
            chain = WhyChain(
                session_id=session_id,
                initial_problem=initial_problem,
                nodes=[],
            )
            self._why_repo.save_chain(chain)

            node = WhyNode.create_first_why(
                session_id=session_id,
                initial_problem=initial_problem,
                answer=answer,
            )
            for ev in evidence:
                node.add_evidence(ev)

            self._why_repo.add_node(session_id, node)

            result = (
                "✅ **5-Why Analysis Started**\n\n"
                f"**Initial Problem:** {initial_problem}\n\n"
                f"**Why 1:** {node.question}\n"
                f"**Answer:** {answer}\n"
            )
            if evidence:
                result += f"**Evidence:** {', '.join(evidence)}\n"

            result += (
                f"\n---\n"
                f"**Node ID:** `{node.id}`\n"
                f"**Next Step:** Call `rc_ask_why` again to go deeper.\n"
                f"- Ask: \"Why did '{answer}' happen?\""
            )

        else:
            if parent_node_id:
                parent = self._why_repo.get_node(CauseId.from_string(parent_node_id))
            else:
                leaves = [n for n in chain.nodes if n.needs_further_analysis and not n.is_root_cause]
                parent = leaves[-1] if leaves else (chain.nodes[-1] if chain.nodes else None)

            if parent is None:
                return [TextContent(
                    type="text",
                    text="❌ **No parent node found.** The chain may be complete or corrupted."
                )]

            if not parent.can_ask_why:
                return [TextContent(
                    type="text",
                    text=(
                        f"⚠️ **Cannot add more Why**\n\n"
                        f"Node `{parent.id}` is at level {parent.level} "
                        f"and {'is marked as root cause' if parent.is_root_cause else 'is at max depth (5)'}.\n"
                        f"Consider using `rc_mark_root_cause` to identify root causes."
                    )
                )]

            node = WhyNode.create_follow_up_why(
                session_id=session_id,
                parent=parent,
                answer=answer,
            )
            for ev in evidence:
                node.add_evidence(ev)

            self._why_repo.add_node(session_id, node)

            # Determine cause type based on level
            cause_type_info = self._get_cause_type_by_level(node.level)

            result = (
                f"✅ **Why {node.level} Added**\n\n"
                f"**Question:** {node.question}\n"
                f"**Answer:** {answer}\n"
            )
            if evidence:
                result += f"**Evidence:** {', '.join(evidence)}\n"

            result += f"\n**Node ID:** `{node.id}`\n"
            result += f"**Cause Type:** {cause_type_info['emoji']} {cause_type_info['type']} ({cause_type_info['chinese']})\n"
            result += f"**HFACS Guidance:** {cause_type_info['hfacs_hint']}\n"
            result += "**Cause Type:** 🔴 Proximate (近端原因)\n"

            if node.is_final_why:
                result += (
                    "\n⚠️ **Reached Level 5 (Final Why)**\n"
                    "Consider if this is the root cause, or if you need to branch earlier."
                )
            else:
                result += (
                    f"\n**Next Step:** Continue asking 'Why?' or mark as root cause.\n"
                    f"- Next question would be: \"Why did '{answer}' happen?\""
                )

        # Add chain status
        chain = self._why_repo.get_chain(session_id)
        if chain:
            result += (
                f"\n---\n"
                f"**Chain Status:**\n"
                f"- Depth: {chain.depth}/5\n"
                f"- Total nodes: {len(chain.nodes)}\n"
                f"- Root causes identified: {len(chain.root_causes)}\n"
                f"- Complete: {'✅ Yes' if chain.is_complete else '❌ No'}"
            )

            # Update progress and add guided response
            if self._progress is not None:
                progress = self._progress.update_from_why_tree(session_id_str, chain)
                result = format_guided_response(result, progress, "rc_ask_why")

        return [TextContent(type="text", text=result)]

    async def handle_get_why_tree(
        self, arguments: dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle rc_get_why_tree tool call."""
        if self._why_repo is None:
            return [TextContent(type="text", text="Error: WhyTreeRepository not initialized")]

        session_id_str = arguments["session_id"]
        session_id = SessionId.from_string(session_id_str)

        chain = self._why_repo.get_chain(session_id)
        if chain is None:
            return [TextContent(
                type="text",
                text=(
                    f"❌ **No Why Tree Found**\n\n"
                    f"No 5-Why analysis for session `{session_id_str}`.\n"
                    "Use `rc_ask_why` to start one."
                )
            )]

        lines = [
            "# 5-Why Analysis Tree\n",
            f"**Initial Problem:** {chain.initial_problem}\n",
            f"**Depth:** {chain.depth}/5\n",
            f"**Complete:** {'✅ Yes' if chain.is_complete else '❌ No'}\n",
        ]

        if chain.root_causes:
            lines.append(f"**Root Causes Identified:** {len(chain.root_causes)}\n")

        lines.append("\n## Analysis Chain\n")

        by_level: dict[int, list[WhyNode]] = {}
        for node in chain.nodes:
            by_level.setdefault(node.level, []).append(node)

        for level in sorted(by_level.keys()):
            nodes = by_level[level]
            for node in nodes:
                prefix = "  " * (level - 1)
                status = "🎯" if node.is_root_cause else ("❓" if node.needs_further_analysis else "✅")

                lines.append(f"{prefix}{status} **Why {level}:** {node.question}")
                lines.append(f"{prefix}   → {node.answer}")

                if node.evidence:
                    lines.append(f"{prefix}   📋 Evidence: {', '.join(node.evidence)}")
                if node.is_root_cause:
                    lines.append(f"{prefix}   🎯 **ROOT CAUSE** (confidence: {node.confidence_level})")

                lines.append(f"{prefix}   (ID: `{node.id}`)\n")

        return [TextContent(type="text", text="\n".join(lines))]

    async def handle_mark_root_cause(
        self, arguments: dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle rc_mark_root_cause tool call."""
        if self._why_repo is None:
            return [TextContent(type="text", text="Error: WhyTreeRepository not initialized")]

        session_id_str = arguments["session_id"]
        node_id_str = arguments["node_id"]
        confidence = arguments.get("confidence", 0.8)

        session_id = SessionId.from_string(session_id_str)
        node_id = CauseId.from_string(node_id_str)

        chain = self._why_repo.get_chain(session_id)
        if chain is None:
            return [TextContent(
                type="text",
                text=f"❌ **No Why Tree Found** for session `{session_id_str}`"
            )]

        node = chain.get_node(node_id)
        if node is None:
            return [TextContent(
                type="text",
                text=f"❌ **Node Not Found**\n\nNo node with ID: `{node_id_str}`"
            )]

        node.mark_as_root_cause(confidence)
        self._why_repo.update_node(node)

        result = (
            "🎯 **Root Cause Identified**\n\n"
            f"**Node:** `{node.id}`\n"
            f"**Level:** Why {node.level}\n"
            f"**Question:** {node.question}\n"
            f"**Answer (Root Cause):** {node.answer}\n"
            f"**Confidence:** {confidence:.0%}\n"
        )

        if node.evidence:
            result += f"**Evidence:** {', '.join(node.evidence)}\n"

        result += "\n---\n**Chain Status:** "
        if chain.is_complete:
            result += "✅ Complete (all branches have root causes)"
        else:
            remaining = len(chain.needs_analysis)
            result += f"❌ Incomplete ({remaining} node(s) need further analysis)"

        result += (
            "\n\n**Next Steps:**\n"
            "1. Use `rc_suggest_hfacs` to classify this root cause\n"
            "2. Add to Fishbone with `rc_add_cause`\n"
            "3. Use `rc_verify_causation` to validate causal relationship"
        )

        # Update progress and add guided response
        if self._progress is not None:
            # Refresh chain to get updated root cause count
            chain = self._why_repo.get_chain(session_id)
            progress = self._progress.update_from_why_tree(session_id_str, chain)
            result = format_guided_response(result, progress, "rc_mark_root_cause")

        return [TextContent(type="text", text=result)]

    async def handle_export_why_tree(
        self, arguments: dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle rc_export_why_tree tool call."""
        if self._why_repo is None:
            return [TextContent(type="text", text="Error: WhyTreeRepository not initialized")]

        session_id_str = arguments["session_id"]
        export_format = arguments.get("format", "mermaid")

        session_id = SessionId.from_string(session_id_str)
        chain = self._why_repo.get_chain(session_id)

        if chain is None:
            return [TextContent(
                type="text",
                text=f"❌ **No Why Tree Found** for session `{session_id_str}`"
            )]

        if export_format == "json":
            result = json.dumps(chain.to_dict(), indent=2, ensure_ascii=False)

        elif export_format == "markdown":
            lines = [
                f"# 5-Why Analysis: {chain.initial_problem}\n",
                f"**Depth:** {chain.depth} | **Complete:** {'Yes' if chain.is_complete else 'No'}\n",
            ]

            for node in chain.nodes:
                indent = "  " * (node.level - 1)
                rc_marker = " 🎯 **ROOT CAUSE**" if node.is_root_cause else ""
                lines.append(f"\n{indent}**Why {node.level}:** {node.question}")
                lines.append(f"{indent}→ {node.answer}{rc_marker}")
                if node.evidence:
                    lines.append(f"{indent}  Evidence: {', '.join(node.evidence)}")

            if chain.root_causes:
                lines.append("\n## Root Causes Summary")
                for rc in chain.root_causes:
                    lines.append(f"- {rc.answer}")

            result = "\n".join(lines)

        else:  # mermaid
            lines = [
                "```mermaid",
                "flowchart TD",
                f'    PROBLEM["{chain.initial_problem}"]',
            ]

            for node in chain.nodes:
                node_id = f"N{str(node.id)[-8:]}"
                parent_id = f"N{str(node.parent_id)[-8:]}" if node.parent_id else "PROBLEM"

                answer = node.answer[:40] + "..." if len(node.answer) > 40 else node.answer

                if node.is_root_cause:
                    lines.append(f'    {node_id}[["🎯 {answer}"]]')
                else:
                    lines.append(f'    {node_id}["{answer}"]')

                lines.append(f'    {parent_id} -->|Why {node.level}| {node_id}')

            lines.append("```")
            result = "\n".join(lines)

        # Write to file for easy preview
        file_path = self._write_export_file(session_id_str, "why_tree", export_format, result)
        if file_path:
            result += f"\n\n---\n📁 **Saved to:** `{file_path}`\n💡 Open in VS Code to preview Mermaid diagram"

        return [TextContent(type="text", text=result)]
