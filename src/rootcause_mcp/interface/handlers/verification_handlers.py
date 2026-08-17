"""MCP adapter for causation-verification and diagram validation/rendering."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from mcp.types import TextContent
from pydantic import TypeAdapter

from rootcause_mcp.application.guided_response import format_guided_response
from rootcause_mcp.domain.services.causation_validator import (
    CausationValidator,
    CausationVerificationResult,
    CauseEvent,
    VerificationLevel,
)
from rootcause_mcp.domain.value_objects.enums import Stage, VerificationResult
from rootcause_mcp.interface.mermaid import (
    build_timeline,
    validate_mermaid_syntax,
)
from rootcause_mcp.interface.temporal_validation import parse_offset_datetime

if TYPE_CHECKING:
    from rootcause_mcp.application.server_state import ServerState
    from rootcause_mcp.application.session_progress import SessionProgressTracker
    from rootcause_mcp.domain.repositories.session_repository import SessionRepository
    from rootcause_mcp.domain.repositories.why_tree_repository import WhyTreeRepository


_CAUSATION_RESULT_ADAPTER = TypeAdapter(CausationVerificationResult)


class VerificationHandlers:
    """Expose causation validation and diagram verification through MCP interface layer."""

    def __init__(
        self,
        progress_tracker: SessionProgressTracker | None = None,
        validator: CausationValidator | None = None,
        server_state: ServerState | None = None,
        session_repository: SessionRepository | None = None,
        why_tree_repository: WhyTreeRepository | None = None,
    ) -> None:
        self._progress = progress_tracker
        self._validator = validator or CausationValidator()
        self._server_state = server_state
        self._session_repository = session_repository
        self._why_tree_repository = why_tree_repository

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
        try:
            cause = self._to_event(cause_data, field_name="cause.timestamp")
            effect = self._to_event(effect_data, field_name="effect.timestamp")
        except ValueError as exc:
            return [TextContent(type="text", text=f"Error: {exc}")]
        lineage_error = await self._validate_audit_lineage(session_id, cause, effect)
        if lineage_error is not None:
            return [TextContent(type="text", text=f"Error: {lineage_error}")]
        result = self._validator.validate(
            cause=cause,
            effect=effect,
            level=VerificationLevel(
                arguments.get("verification_level", VerificationLevel.STANDARD.value)
            ),
        )
        self._persist_causation_result(session_id, cause, effect, result)
        text = self._format_result(result)

        if (
            self._progress is not None
            and result.overall_result is VerificationResult.VERIFIED
        ):
            progress = self._progress.update_causation_audit_passed(session_id)
            text = format_guided_response(text, progress, "rc_verify_causation")

        return [TextContent(type="text", text=text)]

    async def _validate_audit_lineage(  # noqa: PLR0911, PLR0912
        self,
        session_id: str,
        cause: CauseEvent,
        effect: CauseEvent,
    ) -> str | None:
        """Fail closed for durable root audits in the configured public runtime.

        Standalone, non-persisting validator use remains available for unit-level
        temporality checks. Once a session/Why repository is configured, however,
        the submitted cause must be the exact persisted Why root and every cause
        and effect evidence reference must resolve in the clinical ledger.
        """
        if self._session_repository is None and self._why_tree_repository is None:
            return None
        if self._session_repository is None or self._why_tree_repository is None:
            return (
                "Persisted causation audits require both session and Why repositories"
            )
        if self._server_state is None:
            return "Persisted causation audits require the clinical evidence ledger"

        session = self._session_repository.get_by_id(session_id)
        if session is None:
            return f"Session {session_id} was not found"

        from rootcause_mcp.domain.value_objects.identifiers import SessionId

        try:
            typed_session_id = SessionId.from_string(session_id)
        except ValueError as exc:
            return str(exc)
        why_tree = self._why_tree_repository.get_chain(typed_session_id)
        if why_tree is None:
            return "A persisted Why tree is required before auditing a root claim"
        if not cause.event_id:
            return "cause.id is required and must be the stable persisted Why root ID"

        root = next(
            (node for node in why_tree.root_causes if str(node.id) == cause.event_id),
            None,
        )
        if root is None:
            return f"cause.id {cause.event_id} is not a persisted Why root"
        if cause.description != root.answer:
            return "cause.description must exactly match the persisted Why root answer"

        submitted_cause_evidence = list(cause.evidence or [])
        if not submitted_cause_evidence:
            return "cause.evidence must contain the persisted Why root evidence IDs"
        if len(submitted_cause_evidence) != len(set(submitted_cause_evidence)):
            return "cause.evidence cannot contain duplicate evidence IDs"
        if set(submitted_cause_evidence) != set(root.evidence):
            return "cause.evidence must exactly match the persisted Why root evidence"

        submitted_effect_evidence = list(effect.evidence or [])
        if not submitted_effect_evidence:
            return "effect.evidence must contain at least one clinical evidence ID"
        if len(submitted_effect_evidence) != len(set(submitted_effect_evidence)):
            return "effect.evidence cannot contain duplicate evidence IDs"

        orchestrator = await self._server_state.get_orchestrator(session_id)
        if orchestrator is None:
            return "The clinical evidence ledger is unavailable for this session"
        known_evidence_ids = set(orchestrator.evidence_store)
        unknown = sorted(
            (set(submitted_cause_evidence) | set(submitted_effect_evidence))
            - known_evidence_ids
        )
        if unknown:
            return (
                f"Causation audit references unknown evidence IDs: {', '.join(unknown)}"
            )
        return None

    def _persist_causation_result(
        self,
        session_id: str,
        cause: CauseEvent,
        effect: CauseEvent,
        result: CausationVerificationResult,
    ) -> None:
        """Append a durable causation audit to the RCA session when available."""
        if self._session_repository is None:
            return
        session = self._session_repository.get_by_id(session_id)
        if session is None:
            return

        payload = _CAUSATION_RESULT_ADAPTER.dump_python(result, mode="json")
        payload["audit_scope"] = "CONSERVATIVE_CAUSATION_AUDIT"
        payload["clinical_causality_established"] = False
        payload["cause_event"] = self._serialize_event(cause)
        payload["effect_event"] = self._serialize_event(effect)
        existing = list(
            session.get_stage_data(Stage.VERIFY).get("causation_verifications", [])
        )
        existing.append(payload)
        session.update_stage_data(
            Stage.VERIFY,
            {"causation_verifications": existing},
        )
        self._session_repository.save(session)

    @staticmethod
    def _serialize_event(event: CauseEvent) -> dict[str, Any]:
        return {
            "id": event.event_id,
            "description": event.description,
            "timestamp": event.timestamp.isoformat() if event.timestamp else None,
            "evidence": list(event.evidence or []),
        }

    @staticmethod
    def _to_event(data: dict[str, Any], *, field_name: str) -> CauseEvent:
        timestamp = data.get("timestamp")
        return CauseEvent(
            description=data["description"],
            event_id=data.get("id"),
            timestamp=(
                parse_offset_datetime(timestamp, field_name=field_name)
                if timestamp is not None
                else None
            ),
            evidence=data.get("evidence"),
        )

    @staticmethod
    def _format_result(result: CausationVerificationResult) -> str:
        lines = [
            "# Conservative Causation Audit",
            "",
            (
                "This audit checks submitted obligations conservatively; it does "
                "not establish clinical causality."
            ),
            "",
            f"**Verification ID:** `{result.verification_id}`",
            f"**Cause:** {result.cause}",
            f"**Effect:** {result.effect}",
            f"**Level:** {result.verification_level.value}",
            f"**Audit Disposition:** {result.overall_result.value}",
            "**Clinical Causality Established:** No",
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
