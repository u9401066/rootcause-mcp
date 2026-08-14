"""
Why Tree Handler implementations.

Handles Why Tree (5-Why Analysis) tools:
- rc_ask_why
- rc_get_why_tree
- rc_mark_root_cause
- rc_export_why_tree
- rc_add_causal_link
- rc_build_teaching_case
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from mcp.types import TextContent

from rootcause_mcp.application.guided_response import format_guided_response
from rootcause_mcp.domain.entities.why_node import CausalLink, WhyChain, WhyNode
from rootcause_mcp.domain.value_objects.enums import CausalLinkType
from rootcause_mcp.domain.value_objects.identifiers import CauseId, SessionId
from rootcause_mcp.interface.handlers.why_tree_artifact_handlers import (
    WhyTreeArtifactHandlers,
)
from rootcause_mcp.interface.handlers.why_tree_guidance import get_cause_type_by_level

if TYPE_CHECKING:
    from rootcause_mcp.application.session_progress import SessionProgressTracker
    from rootcause_mcp.domain.repositories.session_repository import SessionRepository
    from rootcause_mcp.domain.repositories.why_tree_repository import WhyTreeRepository


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
        self._artifacts = WhyTreeArtifactHandlers(
            why_tree_repository,
            progress_tracker,
        )

    async def handle_ask_why(self, arguments: dict[str, Any]) -> Sequence[TextContent]:
        """Handle rc_ask_why tool call - the core reasoning tool."""
        if self._why_repo is None or self._session_repo is None:
            return [
                TextContent(type="text", text="Error: Repositories not initialized")
            ]

        session_id_str = arguments["session_id"]
        answer = arguments["answer"]
        parent_node_id = arguments.get("parent_node_id")
        evidence = arguments.get("evidence", [])
        initial_problem = arguments.get("initial_problem")

        session_id = SessionId.from_string(session_id_str)

        session = self._session_repo.get_by_id(session_id_str)
        if session is None:
            return [
                TextContent(
                    type="text",
                    text=f"❌ **Session Not Found**\n\nNo session with ID: `{session_id_str}`",
                )
            ]

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
                leaves = [
                    n
                    for n in chain.nodes
                    if n.needs_further_analysis and not n.is_root_cause
                ]
                parent = (
                    leaves[-1] if leaves else (chain.nodes[-1] if chain.nodes else None)
                )

            if parent is None:
                return [
                    TextContent(
                        type="text",
                        text="❌ **No parent node found.** The chain may be complete or corrupted.",
                    )
                ]

            if not parent.can_ask_why:
                return [
                    TextContent(
                        type="text",
                        text=(
                            f"⚠️ **Cannot add more Why**\n\n"
                            f"Node `{parent.id}` is at level {parent.level} "
                            f"and {'is marked as root cause' if parent.is_root_cause else 'is at max depth (5)'}.\n"
                            f"Consider using `rc_mark_root_cause` to identify root causes."
                        ),
                    )
                ]

            node = WhyNode.create_follow_up_why(
                session_id=session_id,
                parent=parent,
                answer=answer,
            )
            for ev in evidence:
                node.add_evidence(ev)

            self._why_repo.add_node(session_id, node)

            # Determine cause type based on level
            cause_type_info = get_cause_type_by_level(node.level)

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
            return [
                TextContent(
                    type="text", text="Error: WhyTreeRepository not initialized"
                )
            ]

        session_id_str = arguments["session_id"]
        session_id = SessionId.from_string(session_id_str)

        chain = self._why_repo.get_chain(session_id)
        if chain is None:
            return [
                TextContent(
                    type="text",
                    text=(
                        f"❌ **No Why Tree Found**\n\n"
                        f"No 5-Why analysis for session `{session_id_str}`.\n"
                        "Use `rc_ask_why` to start one."
                    ),
                )
            ]

        lines = [
            "# 5-Why Analysis Tree\n",
            f"**Initial Problem:** {chain.initial_problem}\n",
            f"**Depth:** {chain.depth}/5\n",
            f"**Complete:** {'✅ Yes' if chain.is_complete else '❌ No'}\n",
        ]

        if chain.root_causes:
            lines.append(f"**Root Causes Identified:** {len(chain.root_causes)}\n")

        if chain.causal_links:
            lines.append(f"**Cross Links:** {len(chain.causal_links)}\n")

        feedback_loops = chain.detect_feedback_loops()
        if feedback_loops:
            lines.append(f"**Feedback Loops:** {len(feedback_loops)}\n")

        lines.append("\n## Analysis Chain\n")

        by_level: dict[int, list[WhyNode]] = {}
        for node in chain.nodes:
            by_level.setdefault(node.level, []).append(node)

        for level in sorted(by_level.keys()):
            nodes = by_level[level]
            for node in nodes:
                prefix = "  " * (level - 1)
                status = (
                    "🎯"
                    if node.is_root_cause
                    else ("❓" if node.needs_further_analysis else "✅")
                )

                lines.append(f"{prefix}{status} **Why {level}:** {node.question}")
                lines.append(f"{prefix}   → {node.answer}")

                if node.evidence:
                    lines.append(f"{prefix}   📋 Evidence: {', '.join(node.evidence)}")
                if node.is_root_cause:
                    lines.append(
                        f"{prefix}   🎯 **ROOT CAUSE** (confidence: {node.confidence_level})"
                    )

                lines.append(f"{prefix}   (ID: `{node.id}`)\n")

        if chain.causal_links:
            lines.append("## Bidirectional / Cross Causality\n")
            for link in chain.causal_links:
                direction = "↔" if link.bidirectional else "→"
                source = chain.get_node(link.source_id)
                target = chain.get_node(link.target_id)
                if source and target:
                    lines.append(
                        f"- {source.answer} {direction} {target.answer} "
                        f"({link.relationship.value}, strength={link.strength:.0%})"
                    )

        if feedback_loops:
            lines.append("\n## Feedback Loops\n")
            for loop in feedback_loops:
                lines.append(f"- {loop.summary}")

        return [TextContent(type="text", text="\n".join(lines))]

    async def handle_mark_root_cause(
        self, arguments: dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle rc_mark_root_cause tool call."""
        if self._why_repo is None:
            return [
                TextContent(
                    type="text", text="Error: WhyTreeRepository not initialized"
                )
            ]

        session_id_str = arguments["session_id"]
        node_id_str = arguments["node_id"]
        confidence = arguments.get("confidence", 0.8)

        session_id = SessionId.from_string(session_id_str)
        node_id = CauseId.from_string(node_id_str)

        chain = self._why_repo.get_chain(session_id)
        if chain is None:
            return [
                TextContent(
                    type="text",
                    text=f"❌ **No Why Tree Found** for session `{session_id_str}`",
                )
            ]

        node = chain.get_node(node_id)
        if node is None:
            return [
                TextContent(
                    type="text",
                    text=f"❌ **Node Not Found**\n\nNo node with ID: `{node_id_str}`",
                )
            ]

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

    async def handle_add_causal_link(
        self, arguments: dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle rc_add_causal_link tool call."""
        if self._why_repo is None:
            return [
                TextContent(
                    type="text", text="Error: WhyTreeRepository not initialized"
                )
            ]

        session_id_str = arguments["session_id"]
        session_id = SessionId.from_string(session_id_str)
        chain = self._why_repo.get_chain(session_id)

        if chain is None:
            return [
                TextContent(
                    type="text",
                    text=f"❌ **No Why Tree Found** for session `{session_id_str}`",
                )
            ]

        source_node_id = CauseId.from_string(arguments["source_node_id"])
        target_node_id = CauseId.from_string(arguments["target_node_id"])
        relationship = CausalLinkType(arguments.get("relationship", "feedback"))
        strength = float(arguments.get("strength", 0.5))
        bidirectional = bool(arguments.get("bidirectional", False))
        note = arguments.get("note", "")
        evidence = tuple(arguments.get("evidence", []))

        try:
            link = CausalLink(
                source_id=source_node_id,
                target_id=target_node_id,
                relationship=relationship,
                strength=strength,
                evidence=evidence,
                note=note,
                bidirectional=bidirectional,
            )
            chain.add_causal_link(link)
            self._why_repo.save_chain(chain)
        except ValueError as exc:
            return [
                TextContent(type="text", text=f"❌ **Invalid Causal Link**\n\n{exc}")
            ]

        source_node = chain.get_node(source_node_id)
        target_node = chain.get_node(target_node_id)
        feedback_loops = chain.detect_feedback_loops()

        result = (
            "🔁 **Causal Link Added**\n\n"
            f"**Source:** {source_node.answer if source_node else source_node_id}\n"
            f"**Target:** {target_node.answer if target_node else target_node_id}\n"
            f"**Relationship:** {relationship.value}\n"
            f"**Strength:** {strength:.0%}\n"
            f"**Direction:** {'bidirectional' if bidirectional else 'directed'}\n"
        )
        if note:
            result += f"**Note:** {note}\n"
        if evidence:
            result += f"**Evidence:** {', '.join(evidence)}\n"

        result += (
            "\n---\n"
            f"**Cross Links in Chain:** {len(chain.causal_links)}\n"
            f"**Feedback Loops Detected:** {len(feedback_loops)}"
        )

        if feedback_loops:
            result += f"\n**Latest Loop:** {feedback_loops[-1].summary}"

        if self._progress is not None:
            progress = self._progress.update_from_why_tree(session_id_str, chain)
            result = format_guided_response(result, progress, "rc_add_causal_link")

        return [TextContent(type="text", text=result)]

    async def handle_export_why_tree(
        self, arguments: dict[str, Any]
    ) -> Sequence[TextContent]:
        """Delegate Why Tree artifact generation."""
        return await self._artifacts.handle_export_why_tree(arguments)

    async def handle_build_teaching_case(
        self, arguments: dict[str, Any]
    ) -> Sequence[TextContent]:
        """Delegate teaching-case artifact generation."""
        return await self._artifacts.handle_build_teaching_case(arguments)
