"""
Reasoning Chain, Gap Analysis & Checkpoint Handlers.

Handles all reasoning chain, conflict detection, and checkpoint MCP tool calls.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from rootcause_mcp.application.checkpoint_service import CaseCheckpointService
from rootcause_mcp.domain.services.gap_analyzer import ClinicalGapAnalyzer
from rootcause_mcp.infrastructure.export_paths import build_export_path
from rootcause_mcp.interface.mermaid import render_reasoning_chain_mermaid

if TYPE_CHECKING:
    from rootcause_mcp.application.server_state import ServerState


class ReasoningHandlers:
    """Handlers for reasoning chain, conflict detection, and checkpoint tools."""

    def __init__(self, server_state: ServerState) -> None:
        """Initialize reasoning handlers with shared persisted state."""
        self._state = server_state
        self._checkpoint_service = CaseCheckpointService(server_state)

    async def handle(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Route reasoning tool calls to appropriate methods."""
        dispatchers = {
            "rc_get_reasoning_chain": self.handle_get_reasoning_chain,
            "rc_export_reasoning_chain": self.handle_export_reasoning_chain,
            "rc_audit_reasoning_state": self.handle_audit_reasoning_state,
            "rc_detect_conflicts": self.handle_detect_conflicts,
            "rc_create_checkpoint": self.handle_create_checkpoint,
            "rc_restore_checkpoint": self.handle_restore_checkpoint,
            "rc_list_checkpoints": self.handle_list_checkpoints,
        }
        handler = dispatchers.get(tool_name)
        if handler is None:
            raise ValueError(f"Unknown reasoning tool: {tool_name}")
        return await handler(arguments)

    async def handle_detect_conflicts(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle rc_detect_conflicts tool call for diagnostic contradictions and guideline gaps."""
        session_id = args["session_id"]
        orch = await self._state.get_orchestrator(session_id)
        if orch is None:
            return {
                "status": "not_found",
                "message": f"No clinical session found for {session_id}",
                "session_id": session_id,
            }

        report = ClinicalGapAnalyzer.analyze(
            session_id=session_id,
            evidence_store=orch.evidence_store,
            hypothesis_store=orch.hypothesis_store,
            thinking_chain=orch.thinking_chain,
            reasoning_chain=orch.reasoning_chain,
        )
        return {
            "status": "success",
            **report.to_dict(),
        }

    async def handle_create_checkpoint(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle rc_create_checkpoint tool call."""
        session_id = args["session_id"]
        tag = args.get("tag")
        created_by = args.get("created_by", "agent")
        notes = args.get("notes", "")
        return await self._checkpoint_service.create_checkpoint(
            session_id=session_id,
            tag=tag,
            created_by=created_by,
            notes=notes,
        )

    async def handle_restore_checkpoint(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle rc_restore_checkpoint tool call."""
        session_id = args["session_id"]
        checkpoint_id = args.get("checkpoint_id")
        checkpoint_file = args.get("checkpoint_file")
        return await self._checkpoint_service.restore_checkpoint(
            session_id=session_id,
            checkpoint_id=checkpoint_id,
            checkpoint_file=checkpoint_file,
        )

    async def handle_list_checkpoints(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle rc_list_checkpoints tool call."""
        session_id = args["session_id"]
        return await self._checkpoint_service.list_checkpoints(session_id=session_id)

    async def handle_audit_reasoning_state(
        self, args: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle rc_audit_reasoning_state tool call for multi-loop guidance."""
        session_id = args["session_id"]

        orchestrator = await self._state.get_orchestrator(session_id)
        if orchestrator is None:
            return {
                "status": "not_found",
                "message": f"No clinical session found for {session_id}",
                "session_id": session_id,
            }

        guidance = orchestrator.get_guidance()
        gap_report = ClinicalGapAnalyzer.analyze(
            session_id=session_id,
            evidence_store=orchestrator.evidence_store,
            hypothesis_store=orchestrator.hypothesis_store,
            thinking_chain=orchestrator.thinking_chain,
            reasoning_chain=orchestrator.reasoning_chain,
        )

        return {
            "status": "success",
            "session_id": session_id,
            "stage": guidance.current_stage.value,
            "stage_display": guidance.stage_display,
            "completeness_score": guidance.completeness_score,
            "is_ready_for_report": guidance.is_ready_for_report,
            "missing_prerequisites": guidance.missing_prerequisites,
            "next_recommended_actions": guidance.next_recommended_actions,
            "push_questions": guidance.push_questions,
            "checklist": guidance.checklist,
            "conflicts_detected": gap_report.total_conflicts,
            "critical_conflicts": gap_report.critical_count,
            "guideline_alerts": gap_report.guideline_alerts,
        }

    async def handle_get_reasoning_chain(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle rc_get_reasoning_chain tool call."""
        session_id = args["session_id"]

        orchestrator = await self._state.get_orchestrator(session_id)
        if orchestrator is None or not orchestrator.reasoning_chain.steps:
            return {
                "status": "not_found",
                "message": f"No reasoning chain found for session {session_id}",
                "session_id": session_id,
                "total_steps": 0,
                "steps": [],
            }

        chain = orchestrator.reasoning_chain
        guidance = orchestrator.get_guidance()

        result = {
            "status": "success",
            "session_id": session_id,
            "total_steps": len(chain.steps),
            "steps": [step.model_dump(mode="json") for step in chain.steps],
            "guidance": guidance.model_dump(mode="json"),
        }

        # Optional: include metrics
        if args.get("include_metrics", True):
            result["quality_metrics"] = chain.get_quality_metrics()

        return result

    async def handle_export_reasoning_chain(
        self, args: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle rc_export_reasoning_chain tool call."""
        session_id = args["session_id"]
        export_format = args.get("format", "json")

        if export_format not in {"json", "mermaid", "markdown"}:
            return {
                "status": "error",
                "message": f"Unsupported export format: {export_format}",
            }

        orchestrator = await self._state.get_orchestrator(session_id)
        if orchestrator is None or not orchestrator.reasoning_chain.steps:
            return {
                "status": "not_found",
                "message": f"No reasoning chain found for session {session_id}",
            }

        chain = orchestrator.reasoning_chain

        output_path = build_export_path(
            session_id=session_id,
            artifact="reasoning_chain",
            extension="json" if export_format == "json" else "md",
            requested_path=args.get("output_path"),
        )

        # Export based on format
        if export_format == "json":
            content = json.dumps(
                {
                    "session_id": session_id,
                    "total_steps": len(chain.steps),
                    "steps": [step.model_dump(mode="json") for step in chain.steps],
                    "quality_metrics": chain.get_quality_metrics(),
                },
                indent=2,
            )
        elif export_format == "mermaid":
            content = render_reasoning_chain_mermaid(chain)
        else:
            content = f"# Reasoning Chain Export\n\nSession: {session_id}\nTotal Steps: {len(chain.steps)}\n\n"
            for i, step in enumerate(chain.steps, 1):
                content += f"## Step {i}: {step.step_type.value}\n\n"
                content += f"**Content**: {step.content}\n\n"
                content += f"**Rationale**: {step.rationale}\n\n"
                if step.confidence is not None:
                    content += f"**Confidence**: {step.confidence:.0%}\n\n"

        # Write to file
        output_path.write_text(content, encoding="utf-8")

        return {
            "status": "success",
            "session_id": session_id,
            "format": export_format,
            "output_path": str(output_path),
            "total_steps": len(chain.steps),
        }
