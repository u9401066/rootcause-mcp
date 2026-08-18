"""
Unified Facade Handlers for RootCause MCP (SDK 2.0).

Dispatches actions from the 8 condensed facade tools to the underlying domain handlers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from rootcause_mcp.interface.handlers.contract_handlers import ContractHandlers
    from rootcause_mcp.interface.handlers.dd_handlers import DDHandlers
    from rootcause_mcp.interface.handlers.evidence_handlers import EvidenceHandlers
    from rootcause_mcp.interface.handlers.fishbone_handlers import FishboneHandlers
    from rootcause_mcp.interface.handlers.hfacs_handlers import HFACSHandlers
    from rootcause_mcp.interface.handlers.reasoning_handlers import ReasoningHandlers
    from rootcause_mcp.interface.handlers.session_handlers import SessionHandlers
    from rootcause_mcp.interface.handlers.thinking_handlers import ThinkingHandlers
    from rootcause_mcp.interface.handlers.verification_handlers import (
        VerificationHandlers,
    )
    from rootcause_mcp.interface.handlers.why_tree_handlers import WhyTreeHandlers


class FacadeHandlers:
    """Consolidated facade dispatcher for 8 unified tools."""

    def __init__(
        self,
        evidence_handlers: EvidenceHandlers,
        dd_handlers: DDHandlers,
        thinking_handlers: ThinkingHandlers,
        reasoning_handlers: ReasoningHandlers,
        contract_handlers: ContractHandlers,
        verification_handlers: VerificationHandlers,
        session_handlers: SessionHandlers,
        fishbone_handlers: FishboneHandlers,
        why_tree_handlers: WhyTreeHandlers,
        hfacs_handlers: HFACSHandlers,
    ) -> None:
        self.evidence = evidence_handlers
        self.dd = dd_handlers
        self.thinking = thinking_handlers
        self.reasoning = reasoning_handlers
        self.contract = contract_handlers
        self.verification = verification_handlers
        self.session = session_handlers
        self.fishbone = fishbone_handlers
        self.why_tree = why_tree_handlers
        self.hfacs = hfacs_handlers

    async def handle_evidence(self, args: dict[str, Any]) -> Any:
        """Route rc_evidence actions: add, get, verify."""
        action = args.get("action", "add").lower()
        if action == "add":
            return await self.evidence.handle("rc_add_evidence", args)
        elif action == "get":
            return await self.evidence.handle("rc_get_evidence", args)
        elif action == "verify":
            return await self.evidence.handle("rc_verify_evidence", args)
        raise ValueError(f"Unknown rc_evidence action: {action}")

    async def handle_hypothesis(self, args: dict[str, Any]) -> Any:
        """Route rc_hypothesis actions: propose, link, rank, exclude."""
        action = args.get("action", "propose").lower()
        if action == "propose":
            return await self.dd.handle("rc_propose_hypothesis", args)
        elif action == "audit_breadth":
            return await self.dd.handle("rc_audit_differential_breadth", args)
        elif action in {"link", "evaluate"}:
            return await self.dd.handle("rc_link_evidence_to_hypothesis", args)
        elif action == "select_leading":
            return await self.dd.handle("rc_select_leading_hypothesis", args)
        elif action in {"rank", "list", "get"}:
            return await self.dd.handle("rc_get_differential_diagnosis", args)
        elif action == "exclude":
            return await self.dd.handle("rc_exclude_hypothesis", args)
        raise ValueError(f"Unknown rc_hypothesis action: {action}")

    async def handle_thinking(self, args: dict[str, Any]) -> Any:
        """Route rc_thinking actions: think, reflect, gap, challenge, get_chain."""
        action = args.get("action", "think").lower()
        if action == "think":
            return await self.thinking.handle("rc_think_aloud", args)
        elif action == "reflect":
            return await self.thinking.handle("rc_reflect", args)
        elif action in {"gap", "gaps"}:
            return await self.thinking.handle("rc_identify_gaps", args)
        elif action in {"challenge", "assumption"}:
            return await self.thinking.handle("rc_challenge_assumption", args)
        elif action in {"get_chain", "chain"}:
            return await self.thinking.handle("rc_get_thinking_chain", args)
        raise ValueError(f"Unknown rc_thinking action: {action}")

    async def handle_audit(self, args: dict[str, Any]) -> Any:
        """Route rc_audit actions: stage_guidance, detect_conflicts, verify_causation."""
        action = args.get("action", "stage_guidance").lower()
        if action in {"stage_guidance", "guidance", "stage", "audit"}:
            return await self.reasoning.handle("rc_audit_reasoning_state", args)
        elif action in {"detect_conflicts", "conflicts", "gaps"}:
            return await self.reasoning.handle("rc_detect_conflicts", args)
        elif action in {"verify_causation", "causation"}:
            return await self.verification.handle("rc_verify_causation", args)
        raise ValueError(f"Unknown rc_audit action: {action}")

    async def handle_report(self, args: dict[str, Any]) -> Any:
        """Route rc_report actions: generate, preview."""
        return await self.contract.handle("rc_generate_contract_report", args)

    async def handle_diagram(self, args: dict[str, Any]) -> Any:
        """Route rc_diagram actions: timeline, validate, reasoning_chain, evidence_graph."""
        action = args.get("action", "timeline").lower()
        if action == "timeline":
            return await self.verification.handle("rc_render_timeline", args)
        elif action in {"validate", "lint", "check"}:
            return await self.verification.handle("rc_validate_diagram", args)
        elif action == "reasoning_chain":
            return await self.reasoning.handle("rc_export_reasoning_chain", args)
        elif action == "evidence_graph":
            return await self.contract.handle(
                "rc_generate_contract_report",
                {**args, "format": "json", "include_evidence_graph": True},
            )
        raise ValueError(f"Unknown rc_diagram action: {action}")

    async def handle_checkpoint(self, args: dict[str, Any]) -> Any:
        """Route rc_checkpoint actions: create, list, restore."""
        action = args.get("action", "create").lower()
        if action in {"create", "save"}:
            return await self.reasoning.handle("rc_create_checkpoint", args)
        elif action in {"list", "get_all"}:
            return await self.reasoning.handle("rc_list_checkpoints", args)
        elif action in {"restore", "load"}:
            return await self.reasoning.handle("rc_restore_checkpoint", args)
        raise ValueError(f"Unknown rc_checkpoint action: {action}")

    async def handle_rca(self, args: dict[str, Any]) -> Any:
        """Route traditional RCA actions (Session, Fishbone, WhyTree, HFACS)."""
        action = args.get("action", "session_start").lower()
        if action.startswith("session_"):
            sub = action.replace("session_", "")
            if sub == "start":
                return await self.session.handle_start_session(args)
            elif sub == "get":
                return await self.session.handle_get_session(args)
            elif sub == "list":
                return await self.session.handle_list_sessions(args)
            elif sub == "archive":
                return await self.session.handle_archive_session(args)
            elif sub == "adjudicate_source":
                return await self.session.handle_adjudicate_source(args)
        elif action.startswith("fishbone_"):
            sub = action.replace("fishbone_", "")
            if sub == "init":
                return await self.fishbone.handle_init_fishbone(args)
            elif sub == "add_cause":
                return await self.fishbone.handle_add_cause(args)
            elif sub == "get":
                return await self.fishbone.handle_get_fishbone(args)
            elif sub == "export":
                return await self.fishbone.handle_export_fishbone(args)
        elif action.startswith("why_"):
            sub = action.replace("why_", "")
            if sub == "ask":
                return await self.why_tree.handle_ask_why(args)
            elif sub == "get":
                return await self.why_tree.handle_get_why_tree(args)
            elif sub == "link":
                return await self.why_tree.handle_add_causal_link(args)
            elif sub == "mark_root":
                return await self.why_tree.handle_mark_root_cause(args)
            elif sub == "export":
                return await self.why_tree.handle_export_why_tree(args)
            elif sub == "teach":
                return await self.why_tree.handle_build_teaching_case(args)
        elif action.startswith("hfacs_"):
            sub = action.replace("hfacs_", "")
            if sub == "suggest":
                return await self.hfacs.handle_suggest_hfacs(args)
            elif sub == "confirm":
                return await self.hfacs.handle_confirm_classification(args)
            elif sub == "framework":
                return await self.hfacs.handle_get_framework(args)
            elif sub == "rules":
                return await self.hfacs.handle_list_learned_rules(args)
        raise ValueError(f"Unknown rc_rca action: {action}")
