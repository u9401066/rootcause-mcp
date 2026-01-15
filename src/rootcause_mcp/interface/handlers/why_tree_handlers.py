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
from typing import TYPE_CHECKING, Any, Sequence

from mcp.types import TextContent

from rootcause_mcp.domain.entities.why_node import WhyChain, WhyNode
from rootcause_mcp.domain.value_objects.identifiers import CauseId, SessionId

if TYPE_CHECKING:
    from rootcause_mcp.domain.repositories.session_repository import SessionRepository
    from rootcause_mcp.domain.repositories.why_tree_repository import WhyTreeRepository
    from rootcause_mcp.application.session_progress import SessionProgressTracker

logger = logging.getLogger(__name__)


class WhyTreeHandlers:
    """Handler class for Why Tree tools."""

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

            result = (
                f"✅ **Why {node.level} Added**\n\n"
                f"**Question:** {node.question}\n"
                f"**Answer:** {answer}\n"
            )
            if evidence:
                result += f"**Evidence:** {', '.join(evidence)}\n"

            result += f"\n**Node ID:** `{node.id}`\n"

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
            f"# 5-Why Analysis Tree\n",
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

        result += f"\n---\n**Chain Status:** "
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

        return [TextContent(type="text", text=result)]
