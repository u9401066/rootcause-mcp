"""
Thinking/Reasoning Transparency Handlers.

Handles all thinking-related MCP tool calls.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rootcause_mcp.domain.entities.thinking_step import (
    AlternativeConsidered,
    ThinkingStep,
    ThinkingType,
)

if TYPE_CHECKING:
    from rootcause_mcp.application.server_state import ServerState


class ThinkingHandlers:
    """Handlers for thinking/reasoning transparency tools."""

    def __init__(self, server_state: ServerState) -> None:
        """Initialize thinking handlers with shared persisted state."""
        self._state = server_state

    async def handle(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Route thinking tool calls to appropriate methods."""
        if tool_name == "rc_think_aloud":
            return await self.handle_think_aloud(arguments)
        elif tool_name == "rc_reflect":
            return await self.handle_reflect(arguments)
        elif tool_name == "rc_identify_gaps":
            return await self.handle_identify_gaps(arguments)
        elif tool_name == "rc_challenge_assumption":
            return await self.handle_challenge_assumption(arguments)
        elif tool_name == "rc_get_thinking_chain":
            return await self.handle_get_thinking_chain(arguments)
        else:
            raise ValueError(f"Unknown thinking tool: {tool_name}")

    async def handle_think_aloud(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle rc_think_aloud tool call."""
        session_id = args["session_id"]

        orchestrator = await self._state.get_or_create_orchestrator(session_id)
        chain = orchestrator.thinking_chain

        # Parse alternatives
        alternatives = []
        if args.get("alternatives"):
            for alt in args["alternatives"]:
                alternatives.append(
                    AlternativeConsidered(
                        alternative=alt["alternative"],
                        reason_rejected=alt["reason_rejected"],
                        confidence_if_chosen=alt.get("confidence_if_chosen"),
                    )
                )

        # Create thinking step
        step = ThinkingStep(
            thinking_type=ThinkingType(args["thinking_type"]),
            content=args["content"],
            internal_reasoning=args["internal_reasoning"],
            alternatives=alternatives,
            confidence=args["confidence"],
            uncertainty_factors=args.get("uncertainty_factors", []),
            related_evidence_ids=args.get("related_evidence_ids", []),
            related_hypothesis_ids=args.get("related_hypothesis_ids", []),
            assumptions_made=args.get("assumptions_made", []),
            potential_biases=args.get("potential_biases", []),
        )

        chain.add_step(step)
        await self._state.persist_orchestrator(session_id)
        guidance = orchestrator.get_guidance()

        return {
            "status": "success",
            "thinking_step_id": step.id,
            "session_id": session_id,
            "total_thinking_steps": len(chain.steps),
            "guidance": guidance.model_dump(mode="json"),
        }

    async def handle_reflect(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle rc_reflect tool call."""
        session_id = args["session_id"]

        orchestrator = await self._state.get_or_create_orchestrator(session_id)
        chain = orchestrator.thinking_chain

        # Create reflection step (special type of thinking step)
        step = ThinkingStep(
            thinking_type=ThinkingType.UNCERTAINTY_ACKNOWLEDGED,  # Use as proxy for reflection
            content=args["reflection_content"],
            internal_reasoning=f"Meta-cognitive reflection: {args['reflection_content']}",
            confidence=0.8,  # Reflections are usually high confidence
            uncertainty_factors=args.get("identified_gaps", []),
            assumptions_made=[],
            potential_biases=args.get("identified_biases", []),
        )

        chain.add_step(step)
        await self._state.persist_orchestrator(session_id)
        guidance = orchestrator.get_guidance()

        return {
            "status": "success",
            "reflection_id": step.id,
            "session_id": session_id,
            "identified_gaps": args.get("identified_gaps", []),
            "identified_biases": args.get("identified_biases", []),
            "guidance": guidance.model_dump(mode="json"),
        }

    async def handle_identify_gaps(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle rc_identify_gaps tool call."""
        session_id = args["session_id"]

        orchestrator = await self._state.get_or_create_orchestrator(session_id)
        chain = orchestrator.thinking_chain

        # Create gap identification step
        step = ThinkingStep(
            thinking_type=ThinkingType.EVIDENCE_GAP_IDENTIFIED,
            content=args["gap_description"],
            internal_reasoning=f"Gap type: {args['gap_type']}. Impact: {args.get('impact_on_diagnosis', 'Unknown')}",
            confidence=0.9,  # Gap identification is usually high confidence
            uncertainty_factors=[args["gap_description"]],
        )

        chain.add_step(step)
        await self._state.persist_orchestrator(session_id)
        guidance = orchestrator.get_guidance()

        return {
            "status": "success",
            "gap_id": step.id,
            "session_id": session_id,
            "gap_type": args["gap_type"],
            "suggested_actions": args.get("suggested_actions", []),
            "guidance": guidance.model_dump(mode="json"),
        }

    async def handle_challenge_assumption(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle rc_challenge_assumption tool call."""
        session_id = args["session_id"]

        orchestrator = await self._state.get_or_create_orchestrator(session_id)
        chain = orchestrator.thinking_chain

        # Create assumption challenge step
        step = ThinkingStep(
            thinking_type=ThinkingType.ASSUMPTION_QUESTIONED,
            content=f"Challenging assumption: {args['assumption']}",
            internal_reasoning=args["challenge_reasoning"],
            confidence=0.7,  # Challenges are usually moderate confidence
            assumptions_made=[args["assumption"]],
        )

        chain.add_step(step)
        await self._state.persist_orchestrator(session_id)
        guidance = orchestrator.get_guidance()

        return {
            "status": "success",
            "challenge_id": step.id,
            "session_id": session_id,
            "assumption_challenged": args["assumption"],
            "alternative_scenario": args.get("alternative_scenario"),
            "guidance": guidance.model_dump(mode="json"),
        }

    async def handle_get_thinking_chain(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle rc_get_thinking_chain tool call."""
        session_id = args["session_id"]

        orchestrator = await self._state.get_orchestrator(session_id)
        if orchestrator is None or not orchestrator.thinking_chain.steps:
            return {
                "status": "not_found",
                "message": f"No thinking chain found for session {session_id}",
                "session_id": session_id,
                "total_steps": 0,
                "steps": [],
            }

        chain = orchestrator.thinking_chain

        # Build response
        result = {
            "status": "success",
            "session_id": session_id,
            "total_steps": len(chain.steps),
            "steps": [step.model_dump(mode="json") for step in chain.steps],
        }

        # Optional: include analysis
        if args.get("include_alternatives", True):
            result["decision_points"] = len(chain.get_decision_points())
            result["rejected_hypotheses"] = chain.get_rejected_hypotheses()

        if args.get("include_uncertainties", True):
            result["uncertainty_map"] = chain.get_uncertainty_map()

        if args.get("include_biases", True):
            result["potential_biases"] = chain.get_bias_report()

        return result
