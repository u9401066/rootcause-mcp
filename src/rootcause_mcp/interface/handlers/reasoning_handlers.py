"""
Reasoning Chain Handlers.

Handles all reasoning chain-related MCP tool calls.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from rootcause_mcp.infrastructure.export_paths import build_export_path

if TYPE_CHECKING:
    from rootcause_mcp.application.server_state import ServerState


class ReasoningHandlers:
    """Handlers for reasoning chain tools."""

    def __init__(self, server_state: ServerState) -> None:
        """Initialize reasoning handlers with shared persisted state."""
        self._state = server_state

    async def handle(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Route reasoning tool calls to appropriate methods."""
        if tool_name == "rc_get_reasoning_chain":
            return await self.handle_get_reasoning_chain(arguments)
        elif tool_name == "rc_export_reasoning_chain":
            return await self.handle_export_reasoning_chain(arguments)
        else:
            raise ValueError(f"Unknown reasoning tool: {tool_name}")

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

        result = {
            "status": "success",
            "session_id": session_id,
            "total_steps": len(chain.steps),
            "steps": [step.model_dump(mode="json") for step in chain.steps],
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
            extension=export_format,
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
        elif export_format in ["mermaid", "markdown"]:
            # Simple text export for now
            content = f"# Reasoning Chain Export\n\nSession: {session_id}\nTotal Steps: {len(chain.steps)}\n\n"
            for i, step in enumerate(chain.steps, 1):
                content += f"## Step {i}: {step.step_type.value}\n\n"
                content += f"**Content**: {step.content}\n\n"
                content += f"**Rationale**: {step.rationale}\n\n"
                if step.confidence:
                    content += f"**Confidence**: {step.confidence:.0%}\n\n"
        else:
            return {
                "status": "error",
                "message": f"Unsupported export format: {export_format}",
            }

        # Write to file
        output_path.write_text(content, encoding="utf-8")

        return {
            "status": "success",
            "session_id": session_id,
            "format": export_format,
            "output_path": str(output_path),
            "total_steps": len(chain.steps),
        }
