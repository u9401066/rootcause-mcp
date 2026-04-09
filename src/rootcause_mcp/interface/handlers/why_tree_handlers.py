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

import json
import logging
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from mcp.types import TextContent

from rootcause_mcp.application.guided_response import format_guided_response
from rootcause_mcp.domain.entities.why_node import (
    CausalLink,
    TeachingCase,
    WhyChain,
    WhyNode,
)
from rootcause_mcp.domain.value_objects.enums import CausalLinkType, TeachingLevel
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
                status = "🎯" if node.is_root_cause else ("❓" if node.needs_further_analysis else "✅")

                lines.append(f"{prefix}{status} **Why {level}:** {node.question}")
                lines.append(f"{prefix}   → {node.answer}")

                if node.evidence:
                    lines.append(f"{prefix}   📋 Evidence: {', '.join(node.evidence)}")
                if node.is_root_cause:
                    lines.append(f"{prefix}   🎯 **ROOT CAUSE** (confidence: {node.confidence_level})")

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

    async def handle_add_causal_link(
        self, arguments: dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle rc_add_causal_link tool call."""
        if self._why_repo is None:
            return [TextContent(type="text", text="Error: WhyTreeRepository not initialized")]

        session_id_str = arguments["session_id"]
        session_id = SessionId.from_string(session_id_str)
        chain = self._why_repo.get_chain(session_id)

        if chain is None:
            return [TextContent(
                type="text",
                text=f"❌ **No Why Tree Found** for session `{session_id_str}`"
            )]

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
            return [TextContent(type="text", text=f"❌ **Invalid Causal Link**\n\n{exc}")]

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
            result = self._generate_why_tree_mermaid(chain)

        # Write to file for easy preview
        file_path = self._write_export_file(session_id_str, "why_tree", export_format, result)
        if file_path:
            result += f"\n\n---\n📁 **Saved to:** `{file_path}`\n💡 Open in VS Code to preview Mermaid diagram"

        return [TextContent(type="text", text=result)]

    async def handle_build_teaching_case(
        self, arguments: dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle rc_build_teaching_case tool call."""
        if self._why_repo is None:
            return [TextContent(type="text", text="Error: WhyTreeRepository not initialized")]

        session_id_str = arguments["session_id"]
        export_format = arguments.get("format", "markdown")
        learner_level = TeachingLevel(arguments.get("learner_level", "medical_student"))

        session_id = SessionId.from_string(session_id_str)
        chain = self._why_repo.get_chain(session_id)
        if chain is None:
            return [TextContent(
                type="text",
                text=f"❌ **No Why Tree Found** for session `{session_id_str}`"
            )]

        teaching_case = chain.build_teaching_case(learner_level)

        if export_format == "json":
            file_path = self._write_export_file(
                session_id_str,
                "teaching_case",
                export_format,
                json.dumps(teaching_case.to_dict(), indent=2, ensure_ascii=False),
            )
            result = json.dumps(
                {
                    "teaching_case": teaching_case.to_dict(),
                    "saved_to": file_path,
                },
                indent=2,
                ensure_ascii=False,
            )
        else:
            result = self._format_teaching_case_markdown(chain, teaching_case)
            file_path = self._write_export_file(
                session_id_str,
                "teaching_case",
                export_format,
                result,
            )
            if file_path:
                result += (
                    f"\n\n---\n📁 **Saved to:** `{file_path}`\n"
                    "💡 Open in VS Code to review or adapt for teaching sessions"
                )

        if self._progress is not None and export_format != "json":
            progress = self._progress.update_from_why_tree(session_id_str, chain)
            result = format_guided_response(result, progress, "rc_build_teaching_case")

        return [TextContent(type="text", text=result)]

    def _format_teaching_case_markdown(
        self,
        chain: WhyChain,
        teaching_case: TeachingCase,
    ) -> str:
        """Format a teaching case as Markdown."""
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
        lines.extend(f"- {objective}" for objective in teaching_case.learning_objectives)
        lines.extend(["", "## Teaching Flow"])
        lines.extend(f"- {step}" for step in teaching_case.teaching_flow)
        lines.extend(["", "## Clinical Pearls"])
        lines.extend(f"- {pearl}" for pearl in teaching_case.clinical_pearls)
        lines.extend(["", "## Common Pitfalls"])
        lines.extend(f"- {pitfall}" for pitfall in teaching_case.common_pitfalls)
        lines.extend(["", "## Discussion Questions"])
        lines.extend(f"- {question}" for question in teaching_case.discussion_questions)

        if teaching_case.feedback_loops:
            lines.extend(["", "## Feedback Loops"])
            lines.extend(f"- {loop}" for loop in teaching_case.feedback_loops)

        lines.extend(["", "## Reverse-Causality Prompts"])
        lines.extend(
            f"- {prompt}" for prompt in teaching_case.reverse_causality_prompts
        )
        return "\n".join(lines)

    def _generate_why_tree_mermaid(self, chain: WhyChain) -> str:
        """Generate an enhanced Why Tree diagram in Mermaid format.

        Creates a visually appealing tree structure with:
        - Problem statement at the top
        - Progressive deepening with color gradients
        - Root causes highlighted with special styling
        - Branch support if multiple analysis paths exist
        """
        # Escape quotes and limit text length
        def escape(text: str, max_len: int = 45) -> str:
            text = text.replace('"', "'").replace("\n", " ")
            return text[:max_len] + "..." if len(text) > max_len else text

        problem = escape(chain.initial_problem, 60)

        lines = [
            "```mermaid",
            "flowchart TB",
            "",
            "    %% === 5-WHY ANALYSIS TREE ===",
            "    %% Deeper levels show progression toward root cause",
            "",
            f'    PROBLEM["❓ {problem}"]:::problem',
            "",
        ]

        # Color classes for different depth levels
        level_classes = {
            1: "why1",
            2: "why2",
            3: "why3",
            4: "why4",
            5: "why5",
        }

        # Track nodes by level for better organization
        nodes_by_level: dict[int, list[WhyNode]] = {}
        for node in chain.nodes:
            nodes_by_level.setdefault(node.level, []).append(node)

        # Generate nodes level by level
        for level in sorted(nodes_by_level.keys()):
            lines.append(f"    %% --- Why Level {level} ---")
            nodes = nodes_by_level[level]

            for node in nodes:
                node_id = f"N{str(node.id)[-8:]}"
                parent_id = f"N{str(node.parent_id)[-8:]}" if node.parent_id else "PROBLEM"

                answer = escape(node.answer)
                level_class = level_classes.get(level, "why5")

                # Different node shapes based on status
                if node.is_root_cause:
                    # Root cause: stadium shape (rounded)
                    lines.append(f'    {node_id}(["🎯 ROOT: {answer}"]):::rootcause')
                elif node.needs_further_analysis:
                    # Needs analysis: rounded rectangle with question mark
                    lines.append(f'    {node_id}("❓ {answer}"):::{level_class}')
                else:
                    # Normal node: rectangle
                    lines.append(f'    {node_id}["{answer}"]:::{level_class}')

                # Connection with labeled arrow
                arrow_label = f"Why {level}"
                if node.evidence:
                    # Show first evidence item on arrow
                    ev_hint = escape(node.evidence[0], 20)
                    arrow_label = f"{arrow_label}<br/>📋 {ev_hint}"

                lines.append(f'    {parent_id} -->|"{arrow_label}"| {node_id}')
                lines.append("")

        if chain.causal_links:
            lines.append("    %% --- Cross Causal Links / Feedback Loops ---")
            for index, link in enumerate(chain.causal_links, start=1):
                source_ref = f"N{str(link.source_id)[-8:]}"
                target_ref = f"N{str(link.target_id)[-8:]}"
                label = f"{link.relationship.value}<br/>{int(link.strength * 100)}%"
                lines.append(f'    {source_ref} -. "{label}" .-> {target_ref}')
                if link.bidirectional:
                    lines.append(
                        f'    {target_ref} -. "feedback #{index}" .-> {source_ref}'
                    )
            lines.append("")

        # Add depth indicator
        lines.append(f"    %% Analysis Depth: {chain.depth}")
        lines.append(f"    %% Root Causes Found: {len(chain.root_causes)}")
        lines.append(f"    %% Feedback Loops: {len(chain.detect_feedback_loops())}")
        lines.append("")

        # Enhanced styling with gradient colors showing progression
        lines.extend([
            "    %% === STYLING ===",
            "    %% Colors progress from red (surface) to green (root)",
            "    classDef problem fill:#2196F3,stroke:#1565C0,stroke-width:3px,color:#fff,font-weight:bold",
            "    classDef why1 fill:#FF5722,stroke:#E64A19,stroke-width:2px,color:#fff",
            "    classDef why2 fill:#FF9800,stroke:#F57C00,stroke-width:2px,color:#fff",
            "    classDef why3 fill:#FFC107,stroke:#FFA000,stroke-width:2px,color:#000",
            "    classDef why4 fill:#8BC34A,stroke:#689F38,stroke-width:2px,color:#fff",
            "    classDef why5 fill:#4CAF50,stroke:#388E3C,stroke-width:2px,color:#fff",
            "    classDef rootcause fill:#9C27B0,stroke:#7B1FA2,stroke-width:4px,color:#fff,font-weight:bold",
            "```",
        ])

        return "\n".join(lines)
