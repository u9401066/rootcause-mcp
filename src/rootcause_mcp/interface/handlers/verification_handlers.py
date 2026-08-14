"""MCP adapter for causation-verification and diagram validation/rendering."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import TYPE_CHECKING, Any

from mcp.types import TextContent

from rootcause_mcp.application.guided_response import format_guided_response
from rootcause_mcp.domain.services.causation_validator import (
    CausationValidator,
    CausationVerificationResult,
    CauseEvent,
    VerificationLevel,
)
from rootcause_mcp.domain.value_objects.enums import VerificationResult
from rootcause_mcp.interface.mermaid import (
    build_timeline,
    validate_mermaid_syntax,
)

if TYPE_CHECKING:
    from rootcause_mcp.application.server_state import ServerState
    from rootcause_mcp.application.session_progress import SessionProgressTracker


class VerificationHandlers:
    """Expose causation validation and diagram verification through MCP interface layer."""

    def __init__(
        self,
        progress_tracker: SessionProgressTracker | None = None,
        validator: CausationValidator | None = None,
        server_state: ServerState | None = None,
    ) -> None:
        self._progress = progress_tracker
        self._validator = validator or CausationValidator()
        self._server_state = server_state

    async def handle(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Route verification and diagram tool calls."""
        if tool_name == "rc_verify_causation":
            return await self.handle_verify_causation(arguments)
        elif tool_name == "rc_validate_diagram":
            return await self.handle_validate_diagram(arguments)
        elif tool_name == "rc_render_timeline":
            return await self.handle_render_timeline(arguments)
        else:
            raise ValueError(f"Unknown verification/diagram tool: {tool_name}")

    async def handle_validate_diagram(
        self,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """Audit, validate, and auto-sanitize Mermaid diagram source."""
        source = arguments["mermaid_source"]
        diagram_type = arguments.get("diagram_type")
        auto_fix = arguments.get("auto_fix", True)

        result = validate_mermaid_syntax(
            source=source,
            diagram_type=diagram_type,
            auto_fix=auto_fix,
        )
        return {
            "status": "success" if result["is_valid"] else "warning",
            **result,
        }

    async def handle_render_timeline(
        self,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """Render a structured chronological event timeline with clinical pattern clustering."""
        session_id = arguments.get("session_id")
        custom_events = arguments.get("events")
        pattern = arguments.get("pattern", "auto")
        title = arguments.get("title")
        include_table = arguments.get("include_table", True)

        evidence_items = []
        if session_id and self._server_state is not None:
            orch = await self._server_state.get_orchestrator(session_id)
            if orch:
                evidence_items = list(orch.evidence_store.values())

        tl_res = build_timeline(
            evidence=evidence_items,
            pattern=pattern,
            custom_events=custom_events,
            title=title,
        )
        return {
            "status": "success",
            "pattern": tl_res["pattern"],
            "title": tl_res["title"],
            "total_events": len(tl_res["events"]),
            "events": tl_res["events"],
            "mermaid": tl_res["mermaid"],
            "table": tl_res["table"] if include_table else None,
        }

    async def handle_verify_causation(
        self,
        arguments: dict[str, Any],
    ) -> Sequence[TextContent]:
        """Validate a proposed cause/effect relationship conservatively."""
        session_id = arguments["session_id"]
        cause_data = arguments["cause"]
        effect_data = arguments["effect"]
        result = self._validator.validate(
            cause=self._to_event(cause_data),
            effect=self._to_event(effect_data),
            level=VerificationLevel(
                arguments.get("verification_level", VerificationLevel.STANDARD.value)
            ),
        )
        text = self._format_result(result)

        if self._progress is not None and result.overall_result in {
            VerificationResult.VERIFIED,
            VerificationResult.VERIFIED_WITH_CAVEATS,
        }:
            progress = self._progress.update_root_cause_verified(session_id)
            text = format_guided_response(text, progress, "rc_verify_causation")

        return [TextContent(type="text", text=text)]

    @staticmethod
    def _to_event(data: dict[str, Any]) -> CauseEvent:
        timestamp = data.get("timestamp")
        return CauseEvent(
            description=data["description"],
            timestamp=(
                datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                if timestamp
                else None
            ),
            evidence=data.get("evidence"),
        )

    @staticmethod
    def _format_result(result: CausationVerificationResult) -> str:
        lines = [
            "# Causation Verification Result",
            "",
            f"**Verification ID:** `{result.verification_id}`",
            f"**Cause:** {result.cause}",
            f"**Effect:** {result.effect}",
            f"**Level:** {result.verification_level.value}",
            f"**Overall Result:** {result.overall_result.value}",
            f"**Confidence:** {result.confidence.value:.0%}",
            "",
            "## Test Results",
        ]
        tests = result.tests
        if tests.temporality is not None:
            lines.extend(
                [
                    f"- **Temporality:** {tests.temporality.passed}",
                    f"  - {tests.temporality.conclusion}",
                ]
            )
        if tests.necessity is not None:
            lines.extend(
                [
                    f"- **Necessity:** {tests.necessity.passed}",
                    f"  - {tests.necessity.counterfactual_question}",
                    f"  - Assessment: {tests.necessity.counterfactual_answer}",
                    f"  - {tests.necessity.reasoning}",
                ]
            )
        if tests.mechanism is not None:
            lines.extend(
                [
                    f"- **Mechanism:** {tests.mechanism.passed}",
                    "  - Pathway: " + " -> ".join(tests.mechanism.causal_pathway),
                ]
            )
        if tests.sufficiency is not None:
            lines.extend(
                [
                    f"- **Sufficiency:** {tests.sufficiency.passed}",
                    f"  - {tests.sufficiency.conclusion}",
                ]
            )

        if result.caveats:
            lines.extend(["", "## Caveats", *[f"- {item}" for item in result.caveats]])
        if result.next_steps:
            lines.extend(
                ["", "## Next Steps", *[f"- {item}" for item in result.next_steps]]
            )
        return "\n".join(lines)
