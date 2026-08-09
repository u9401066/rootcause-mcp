"""
CONTRACT Report Handlers.

Handles CONTRACT-level report generation.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from rootcause_mcp.domain.value_objects.contract_report import (
    ContractReport,
    EvidenceCoverageMetrics,
    ReasoningQualityMetrics,
)
from rootcause_mcp.infrastructure.export_paths import build_export_path

if TYPE_CHECKING:
    from rootcause_mcp.application.server_state import ServerState


class ContractHandlers:
    """Handlers for CONTRACT report tools (uses real data from Orchestrator)."""

    def __init__(self, server_state: ServerState) -> None:
        """
        Initialize contract handlers with shared server state.

        Args:
            server_state: ServerState instance for accessing Orchestrators
        """
        self._state = server_state

    async def handle(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Route contract tool calls to appropriate methods."""
        if tool_name == "rc_generate_contract_report":
            return await self.handle_generate_contract_report(arguments)
        else:
            raise ValueError(f"Unknown contract tool: {tool_name}")

    async def handle_generate_contract_report(
        self, args: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle rc_generate_contract_report tool call (uses real data)."""
        session_id = args["session_id"]
        report_format = args.get("format", "json")
        finalize = args.get("finalize", False)

        # Get orchestrator with real data
        orch = await self._state.get_orchestrator(session_id)
        if not orch:
            return {
                "status": "not_found",
                "message": f"No data found for session {session_id}",
            }

        # Calculate evidence metrics
        all_evidence = list(orch.evidence_store.values())
        verified_count = sum(1 for e in all_evidence if e.verified)
        strong_count = sum(
            1 for e in all_evidence if e.quality.strength.value == "STRONG"
        )
        moderate_count = sum(
            1 for e in all_evidence if e.quality.strength.value == "MODERATE"
        )
        weak_count = sum(
            1 for e in all_evidence if e.quality.strength.value in ["WEAK", "ANECDOTAL"]
        )

        evidence_metrics = EvidenceCoverageMetrics(
            total_evidence=len(all_evidence),
            verified_evidence=verified_count,
            strong_evidence=strong_count,
            moderate_evidence=moderate_count,
            weak_evidence=weak_count,
        )

        # Calculate reasoning metrics
        chain_metrics = orch.reasoning_chain.get_quality_metrics()
        thinking_chain = orch.thinking_chain
        reasoning_metrics = ReasoningQualityMetrics(
            total_steps=chain_metrics["total_steps"],
            avg_confidence=chain_metrics["avg_confidence"],
            hypothesis_coverage=chain_metrics["hypothesis_coverage"],
            evidence_coverage=chain_metrics["evidence_coverage"],
            decision_points=len(thinking_chain.get_decision_points()),
            alternatives_considered=sum(
                len(step.alternatives) for step in thinking_chain.steps
            ),
            biases_identified=len(thinking_chain.get_bias_report()),
            uncertainties_acknowledged=sum(
                len(step.uncertainty_factors) for step in thinking_chain.steps
            ),
        )

        # Create contract report
        report = ContractReport(
            report_id=f"RPT-{session_id[:8]}",
            session_id=session_id,
            generated_by="agent",
            hypotheses=[
                h.model_dump(mode="json") for h in orch.hypothesis_store.values()
            ],
            evidence=[e.model_dump(mode="json") for e in orch.evidence_store.values()],
            reasoning_chain=[
                s.model_dump(mode="json") for s in orch.reasoning_chain.steps
            ],
            thinking_chain=[
                step.model_dump(mode="json") for step in thinking_chain.steps
            ],
            evidence_metrics=evidence_metrics,
            reasoning_metrics=reasoning_metrics,
            finalized_at=None,
            content_hash=None,
        )

        # Finalize if requested
        if finalize:
            report.finalize(finalized_by="system")

        output_path = build_export_path(
            session_id=session_id,
            artifact="contract_report",
            extension=report_format,
        )

        # Export based on format
        if report_format == "fhir":
            content = json.dumps(report.to_fhir(), indent=2)
        else:
            content = json.dumps(report.model_dump(mode="json"), indent=2)

        output_path.write_text(content, encoding="utf-8")

        return {
            "status": "success",
            "session_id": session_id,
            "report_id": report.report_id,
            "format": report_format,
            "finalized": report.is_finalized,
            "output_path": str(output_path),
            "total_hypotheses": len(report.hypotheses),
            "total_evidence": len(report.evidence),
            "reasoning_steps": len(report.reasoning_chain),
            "evidence_metrics": evidence_metrics.model_dump(mode="json"),
            "reasoning_metrics": reasoning_metrics.model_dump(mode="json"),
        }
