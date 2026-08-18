"""
CONTRACT Report Handlers.

Handles CONTRACT-level report generation.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from rootcause_mcp.domain.services.final_report_conformance import (
    evaluate_final_report_conformance,
    hard_failures,
)
from rootcause_mcp.domain.services.gap_analyzer import ClinicalGapAnalyzer
from rootcause_mcp.domain.value_objects.contract_report import (
    ConformanceCheck,
    ContractReport,
    EvidenceCoverageMetrics,
    ReasoningQualityMetrics,
)
from rootcause_mcp.domain.value_objects.identifiers import SessionId
from rootcause_mcp.infrastructure.export_paths import (
    build_export_path,
    write_export_text,
)
from rootcause_mcp.interface.contract_markdown import render_contract_report_markdown
from rootcause_mcp.interface.fhir import render_contract_report_fhir
from rootcause_mcp.interface.mermaid import build_evidence_graph, build_timeline

if TYPE_CHECKING:
    from rootcause_mcp.application.server_state import ServerState
    from rootcause_mcp.domain.entities.fishbone import Fishbone
    from rootcause_mcp.domain.entities.session import RCASession
    from rootcause_mcp.domain.entities.why_node import WhyChain
    from rootcause_mcp.domain.repositories.fishbone_repository import (
        FishboneRepository,
    )
    from rootcause_mcp.domain.repositories.session_repository import SessionRepository
    from rootcause_mcp.domain.repositories.why_tree_repository import WhyTreeRepository
    from rootcause_mcp.domain.value_objects.case_manifest import CaseInputManifest


class ContractHandlers:
    """Handlers for CONTRACT report tools (uses real data from Orchestrator)."""

    def __init__(
        self,
        server_state: ServerState,
        *,
        session_repository: SessionRepository | None = None,
        fishbone_repository: FishboneRepository | None = None,
        why_tree_repository: WhyTreeRepository | None = None,
        template_root: str | Path | None = None,
    ) -> None:
        """
        Initialize contract handlers with shared server state.

        Args:
            server_state: ServerState instance for accessing Orchestrators
            session_repository: Optional legacy RCA session repository
            fishbone_repository: Optional persisted Fishbone repository
            why_tree_repository: Optional persisted 5-Why repository
            template_root: Optional allowlisted Markdown template directory
        """
        self._state = server_state
        self._session_repo = session_repository
        self._fishbone_repo = fishbone_repository
        self._why_tree_repo = why_tree_repository
        self._template_root = Path(template_root) if template_root is not None else None

    async def handle(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Route contract tool calls to appropriate methods."""
        if tool_name == "rc_generate_contract_report":
            return await self.handle_generate_contract_report(arguments)
        else:
            raise ValueError(f"Unknown contract tool: {tool_name}")

    async def handle_generate_contract_report(  # noqa: PLR0911, PLR0912, PLR0915
        self,
        args: dict[str, Any],
        *,
        persist_export: bool = True,
    ) -> dict[str, Any]:
        """Handle rc_generate_contract_report tool call (uses real data).

        ``persist_export`` is an internal integration control. Public tool calls
        retain the default export behavior, while read-only MCP resources can
        render the same unified report without writing an export artifact.
        """
        session_id = args["session_id"]
        report_format = args.get("format", "json")
        locale = args.get("locale", "en")
        audience = args.get("audience", "general")
        finalize = args.get("finalize", False)
        approved_by = args.get("approved_by")
        include_reasoning_chain = args.get("include_reasoning_chain", True)
        include_thinking_chain = args.get("include_thinking_chain", True)
        include_evidence_graph = args.get("include_evidence_graph", True)
        include_quality_metrics = args.get("include_quality_metrics", True)

        detail_level = args.get("detail_level", "standard")

        if report_format not in {"json", "fhir", "markdown"}:
            return {
                "status": "error",
                "message": f"Unsupported report format: {report_format}",
            }
        if detail_level not in {"brief", "standard", "full"}:
            return {
                "status": "error",
                "message": f"Unsupported detail level: {detail_level}",
            }
        if locale not in {"en", "zh-TW"}:
            return {
                "status": "error",
                "message": f"Unsupported report locale: {locale}",
            }
        if audience not in {"general", "clinician"}:
            return {
                "status": "error",
                "message": f"Unsupported report audience: {audience}",
            }

        rca_session = (
            self._session_repo.get_by_id(session_id)
            if self._session_repo is not None
            else None
        )

        # Get orchestrator with real data. A persisted RCA-only session is also
        # reportable even when no medical-reasoning records have been added yet.
        orch = await self._state.get_orchestrator(session_id)
        if not orch and rca_session is None:
            return {
                "status": "not_found",
                "message": f"No data found for session {session_id}",
            }

        # Calculate evidence metrics
        all_evidence = list(orch.evidence_store.values()) if orch else []
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
        chain_metrics = (
            orch.reasoning_chain.get_quality_metrics()
            if orch
            else {
                "total_steps": 0,
                "avg_confidence": None,
                "hypothesis_coverage": 0.0,
                "evidence_coverage": 0.0,
            }
        )
        thinking_steps = list(orch.thinking_chain.steps) if orch else []
        reasoning_steps = list(orch.reasoning_chain.steps) if orch else []
        reasoning_metrics = ReasoningQualityMetrics(
            total_steps=chain_metrics["total_steps"],
            avg_confidence=chain_metrics["avg_confidence"],
            hypothesis_coverage=chain_metrics["hypothesis_coverage"],
            evidence_coverage=chain_metrics["evidence_coverage"],
            decision_points=(
                len(orch.thinking_chain.get_decision_points()) if orch else 0
            ),
            alternatives_considered=sum(
                len(step.alternatives) for step in thinking_steps
            ),
            biases_identified=(
                len(orch.thinking_chain.get_bias_report()) if orch else 0
            ),
            uncertainties_acknowledged=sum(
                len(step.uncertainty_factors) for step in thinking_steps
            ),
        )

        working_hypotheses = list(orch.hypothesis_store.values() if orch else [])
        fishbone, why_tree = self._load_rca_artifacts(session_id)
        fishbone_payload = fishbone.to_dict() if fishbone else None
        source_manifest = (
            rca_session.get_source_manifest() if rca_session is not None else None
        )
        causation_verifications = self._extract_causation_verifications(rca_session)
        root_causes = self._serialize_root_causes(
            why_tree,
            causation_verifications,
        )
        source_inventory = self._build_source_inventory(
            all_evidence,
            source_manifest,
            (
                rca_session.get_latest_source_reviews()
                if rca_session is not None
                else None
            ),
        )
        source_review_ledger = (
            [
                event.model_dump(mode="json")
                for event in rca_session.get_source_review_ledger()
            ]
            if rca_session is not None
            else []
        )
        gap_analysis = (
            ClinicalGapAnalyzer.analyze(
                session_id=session_id,
                evidence_store=orch.evidence_store,
                hypothesis_store=orch.hypothesis_store,
                thinking_chain=orch.thinking_chain,
                reasoning_chain=orch.reasoning_chain,
            ).to_dict()
            if orch
            else None
        )
        report_readiness = orch.get_guidance().model_dump(mode="json") if orch else None
        hypothesis_payloads = [
            self._serialize_hypothesis(hypothesis) for hypothesis in working_hypotheses
        ]
        evidence_payloads = [self._serialize_evidence(item) for item in all_evidence]
        evidence_by_id = {item.id.value: item for item in all_evidence}
        reasoning_payloads = [
            self._serialize_reasoning_step(step, evidence_by_id)
            for step in reasoning_steps
        ]
        thinking_payloads = [
            {
                **step.model_dump(mode="json"),
                "confidence_semantics": "UNCALIBRATED_LEGACY_NOT_PRESENTED",
            }
            for step in thinking_steps
        ]
        breadth_audit_payloads = (
            [
                audit.model_dump(mode="json")
                for audit in orch.get_differential_breadth_audits()
            ]
            if orch
            else []
        )
        report_fields: dict[str, Any] = {
            "report_id": f"RPT-{session_id}",
            "session_id": session_id,
            "generated_by": "agent",
            "leading_hypothesis_id": (
                orch.get_leading_hypothesis_id() if orch else None
            ),
            "hypotheses": hypothesis_payloads,
            "differential_breadth_audits": breadth_audit_payloads,
            "evidence": evidence_payloads,
            "source_inventory": source_inventory,
            "source_review_ledger": source_review_ledger,
            "timeline": build_timeline(all_evidence),
            "reasoning_chain": (reasoning_payloads if include_reasoning_chain else []),
            "thinking_chain": thinking_payloads if include_thinking_chain else [],
            "evidence_graph": (
                build_evidence_graph(all_evidence, working_hypotheses)
                if include_evidence_graph
                else None
            ),
            "rca_session": self._serialize_rca_session(rca_session),
            "fishbone": fishbone_payload,
            "why_tree": why_tree.to_dict() if why_tree else None,
            "root_causes": root_causes,
            "hfacs_classifications": self._extract_hfacs_classifications(fishbone),
            "causation_verifications": causation_verifications,
            "gap_analysis": gap_analysis,
            "report_readiness": report_readiness,
            "evidence_metrics": (
                evidence_metrics.model_dump(mode="json")
                if include_quality_metrics
                else None
            ),
            "reasoning_metrics": (
                reasoning_metrics.model_dump(mode="json")
                if include_quality_metrics
                else None
            ),
            "finalized_at": None,
            "content_hash": None,
        }
        authorized_reviewers = {
            item.strip()
            for item in os.environ.get("ROOTCAUSE_AUTHORIZED_REVIEWERS", "").split(",")
            if item.strip()
        }
        conformance_checks = evaluate_final_report_conformance(
            report_fields,
            approved_by=approved_by if isinstance(approved_by, str) else None,
            authorized_reviewers=authorized_reviewers,
        )
        blockers = hard_failures(conformance_checks)
        if finalize and blockers:
            return {
                "status": "error",
                "message": "Report finalization blocked by safety requirements",
                "session_id": session_id,
                "finalized": False,
                "blockers": blockers,
                "conformance_checks": conformance_checks,
                "preliminary_available": True,
            }

        # Create the typed report only after deterministic conformance evaluation.
        try:
            typed_conformance_checks = [
                ConformanceCheck.model_validate(item) for item in conformance_checks
            ]
            report = ContractReport(
                **report_fields,
                conformance_checks=typed_conformance_checks,
            )
        except ValidationError as exc:
            schema_failure = {
                "code": "TYPED_REPORT_SCHEMA",
                "status": "FAIL",
                "severity": "HARD",
                "message": "Nested report content failed typed schema validation.",
                "refs": sorted(
                    {
                        "#/" + "/".join(str(part) for part in error["loc"])
                        for error in exc.errors()
                    }
                ),
            }
            return {
                "status": "error",
                "message": schema_failure["message"],
                "session_id": session_id,
                "finalized": False,
                "blockers": [schema_failure],
                "conformance_checks": [*conformance_checks, schema_failure],
                "preliminary_available": False,
            }

        # Finalize if requested
        if finalize:
            assert isinstance(approved_by, str)
            try:
                report.finalize(
                    finalized_by=approved_by.strip(),
                    authorized_reviewers=authorized_reviewers,
                )
            except ValueError as exc:
                lifecycle_failure = {
                    "code": (
                        "TYPED_REPORT_SCHEMA"
                        if "typed final report schema" in str(exc)
                        else "FINALIZATION_LIFECYCLE"
                    ),
                    "status": "FAIL",
                    "severity": "HARD",
                    "message": str(exc),
                    "refs": ["#/"],
                }
                return {
                    "status": "error",
                    "message": "Report finalization blocked by final snapshot validation",
                    "session_id": session_id,
                    "finalized": False,
                    "blockers": [lifecycle_failure],
                    "conformance_checks": [
                        *conformance_checks,
                        lifecycle_failure,
                    ],
                    "preliminary_available": True,
                }

        # Export based on format
        template_file = args.get("template_file") or args.get("template_path")
        if report_format == "fhir":
            content = json.dumps(render_contract_report_fhir(report), indent=2)
        elif report_format == "markdown":
            try:
                content = render_contract_report_markdown(
                    report,
                    detail_level,
                    template_path=template_file,
                    template_root=self._template_root,
                    locale=locale,
                    audience=audience,
                )
            except ValueError as exc:
                return {"status": "error", "message": str(exc)}
        else:
            report_payload = report.model_dump(mode="json")
            if not include_evidence_graph:
                report_payload.pop("evidence_graph", None)
            if not include_quality_metrics:
                report_payload.pop("evidence_metrics", None)
                report_payload.pop("reasoning_metrics", None)
            content = json.dumps(report_payload, indent=2)

        output_path: Path | None = None
        if persist_export:
            output_path = build_export_path(
                session_id=session_id,
                artifact="contract_report",
                extension="md" if report_format == "markdown" else "json",
            )
            write_export_text(output_path, content)
        artifact_bytes = content.encode("utf-8")
        artifact_sha256 = f"sha256:{hashlib.sha256(artifact_bytes).hexdigest()}"

        response = {
            "status": "success",
            "session_id": session_id,
            "report_id": report.report_id,
            "format": report_format,
            "detail_level": detail_level,
            "locale": locale,
            "audience": audience,
            "finalized": report.is_finalized,
            "content": content,
            "artifact_bytes": len(artifact_bytes),
            "artifact_sha256": artifact_sha256,
            "generation_mode": "deterministic",
            "llm_tokens_used": 0,
            "total_hypotheses": len(report.hypotheses),
            "conclusion_hypotheses": len(report.ranked_conclusion_hypotheses()),
            "total_evidence": len(report.evidence),
            "timeline_events": len((report.timeline or {}).get("events", [])),
            "reasoning_steps": len(report.reasoning_chain),
            "source_documents": len(report.source_inventory),
            "root_causes": len(report.root_causes),
            "hfacs_classifications": len(report.hfacs_classifications),
            "causation_verifications": len(report.causation_verifications),
            "conflicts": (
                int(report.gap_analysis.get("total_conflicts", 0))
                if report.gap_analysis
                else 0
            ),
            "conformance_checks": [
                check.model_dump(mode="json") for check in report.conformance_checks
            ],
        }
        if output_path is not None:
            response["output_path"] = str(output_path)
        if include_quality_metrics:
            response["evidence_metrics"] = evidence_metrics.model_dump(mode="json")
            response["reasoning_metrics"] = reasoning_metrics.model_dump(mode="json")
        if include_evidence_graph and report.evidence_graph is not None:
            response["evidence_graph_nodes"] = len(report.evidence_graph["nodes"])
            response["evidence_graph_edges"] = len(report.evidence_graph["edges"])
        return response

    @staticmethod
    def _serialize_hypothesis(hypothesis: Any) -> dict[str, Any]:
        """Normalize strong IDs while retaining the complete typed DDx payload."""
        payload: dict[str, Any] = hypothesis.model_dump(mode="json")
        payload["id"] = hypothesis.id.value
        payload["probability_semantics"] = "UNCALIBRATED_COMPATIBILITY_ONLY"
        payload["clinical_probability_established"] = False
        return payload

    @staticmethod
    def _serialize_evidence(evidence: Any) -> dict[str, Any]:
        """Normalize an evidence ID to the stable public string form."""
        payload: dict[str, Any] = evidence.model_dump(mode="json")
        payload["id"] = evidence.id.value
        source = payload.get("source")
        if isinstance(source, dict) and source.get("content_hash") is not None:
            source["content_hash"] = (
                str(source["content_hash"]).removeprefix("sha256:").lower()
            )
        return payload

    @staticmethod
    def _serialize_reasoning_step(
        step: Any,
        evidence_by_id: dict[str, Any],
    ) -> dict[str, Any]:
        """Normalize IDs and expose current evidence provenance in the snapshot.

        Evidence is commonly verified after its ingestion reasoning step is
        created.  The historical rationale therefore must not masquerade as the
        current provenance state in a generated report.
        """
        payload: dict[str, Any] = step.model_dump(mode="json")
        payload["id"] = step.id.value
        states = []
        for evidence_id in payload.get("evidence_ids", []):
            evidence = evidence_by_id.get(str(evidence_id))
            if evidence is None:
                continue
            states.append(
                {
                    "evidence_id": str(evidence_id),
                    "verified": bool(evidence.verified),
                    "verification_method": evidence.verification_method,
                }
            )
        payload["evidence_verification_states"] = states
        payload["confidence_semantics"] = "UNCALIBRATED_LEGACY_NOT_PRESENTED"
        rationale = str(payload.get("rationale", ""))
        if states and ", Verified:" in rationale:
            payload["rationale"] = rationale.split(", Verified:", 1)[0]
        return payload

    def _load_rca_artifacts(
        self, session_id: str
    ) -> tuple[Fishbone | None, WhyChain | None]:
        """Load optional RCA artifacts without weakening SessionId validation."""
        try:
            typed_session_id = SessionId.from_string(session_id)
        except ValueError:
            return None, None

        fishbone = (
            self._fishbone_repo.get_by_session(typed_session_id)
            if self._fishbone_repo is not None
            else None
        )
        why_tree = (
            self._why_tree_repo.get_chain(typed_session_id)
            if self._why_tree_repo is not None
            else None
        )
        return fishbone, why_tree

    @staticmethod
    def _build_source_inventory(
        evidence: list[Any],
        manifest: CaseInputManifest | None = None,
        latest_reviews: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Merge the declared input manifest with registered evidence coverage.

        When no manifest is pinned, this deliberately reports only documents
        visible through evidence provenance and labels that limitation. A
        manifest makes zero-evidence documents visible and supplies their
        host-declared processing status.
        """
        inventory: dict[str, dict[str, Any]] = {}
        if manifest is not None:
            for document in manifest.documents:
                metadata = document.model_dump(mode="json")
                document_id = metadata.pop("document_id")
                coverage_status = metadata.pop("status")
                review = (latest_reviews or {}).get(document_id)
                if review is not None:
                    coverage_status = review.status.value
                    metadata.update(
                        {
                            "de_identified": review.de_identified,
                            "independence_status": review.independence_status.value,
                            "source_group_id": review.source_group_id,
                            "parent_document_id": review.parent_document_id,
                            "derivation_method": review.derivation_method,
                            "source_review_adjudication_id": review.adjudication_id,
                            "source_reviewed_by": review.reviewed_by,
                            "source_reviewed_at": review.reviewed_at.isoformat(),
                            "source_review_reason": review.reason,
                        }
                    )
                inventory[document.document_id] = {
                    "document": document_id,
                    **metadata,
                    "evidence_count": 0,
                    "verified_count": 0,
                    "coverage_status": coverage_status,
                }

        for item in evidence:
            document = item.source.document_id
            key = document or "__UNSPECIFIED__"
            entry = inventory.setdefault(
                key,
                {
                    "document": document,
                    "evidence_count": 0,
                    "verified_count": 0,
                    "coverage_status": (
                        "registered_evidence_only"
                        if manifest is None
                        else "not_in_manifest"
                    ),
                    "source_uri": None,
                    "sha256": None,
                    "media_type": None,
                    "source_kind": None,
                    "revision": None,
                    "captured_at": None,
                    "parser_name": None,
                    "parser_version": None,
                    "de_identified": None,
                    "independence_status": "unknown",
                    "source_group_id": None,
                    "parent_document_id": None,
                    "derivation_method": None,
                },
            )
            entry["evidence_count"] += 1
            entry["verified_count"] += int(item.verified)
        return sorted(
            inventory.values(),
            key=lambda entry: str(entry["document"] or ""),
        )

    @staticmethod
    def _serialize_rca_session(session: RCASession | None) -> dict[str, Any] | None:
        if session is None:
            return None
        source_manifest = session.get_source_manifest()
        return {
            "session_id": str(session.id),
            "case_type": session.case_type.value,
            "case_title": session.case_title,
            "status": session.status.value,
            "current_stage": session.current_stage.value,
            "problem_statement": session.problem_statement,
            "initial_description": session.initial_description,
            "progress": session.get_progress(),
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "created_by": session.created_by,
            "source_manifest_digest": (
                source_manifest.digest if source_manifest is not None else None
            ),
            "source_document_count": (
                len(source_manifest.documents) if source_manifest is not None else 0
            ),
            "source_review_event_count": len(session.get_source_review_ledger()),
        }

    @staticmethod
    def _serialize_root_causes(
        why_tree: WhyChain | None,
        causation_verifications: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if why_tree is None:
            return []
        verification_by_cause_id = {
            str(item.get("cause_event", {}).get("id")): item
            for item in causation_verifications
            if isinstance(item.get("cause_event"), dict)
            and item.get("cause_event", {}).get("id")
        }
        root_records: list[dict[str, Any]] = []
        for node in why_tree.root_causes:
            verification = verification_by_cause_id.get(str(node.id), {})
            causation_result = str(verification.get("overall_result") or "").upper()
            if causation_result == "REJECTED":
                continue
            disposition = (
                "AUDIT_OBLIGATIONS_PASSED"
                if causation_result in {"VERIFIED", "VERIFIED_WITH_CAVEATS"}
                else "PROPOSED"
            )
            root_records.append(
                {
                    "id": str(node.id),
                    "answer": node.answer,
                    "question": node.question,
                    "level": node.level,
                    "parent_id": str(node.parent_id) if node.parent_id else None,
                    "evidence": list(node.evidence),
                    "confidence": node.confidence.value if node.confidence else None,
                    "confidence_semantics": "UNCALIBRATED_LEGACY_NOT_PRESENTED",
                    "causation_verification_id": verification.get("verification_id"),
                    "causation_result": verification.get("overall_result"),
                    "disposition": disposition,
                }
            )
        return root_records

    @staticmethod
    def _extract_causation_verifications(
        session: RCASession | None,
    ) -> list[dict[str, Any]]:
        if session is None:
            return []
        from rootcause_mcp.domain.value_objects.enums import Stage

        raw_items = session.get_stage_data(Stage.VERIFY).get(
            "causation_verifications", []
        )
        normalized: list[dict[str, Any]] = []
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            normalized_item = {
                **item,
                "confidence_semantics": "UNCALIBRATED_LEGACY_NOT_PRESENTED",
            }
            # Confidence is optional for conservative INSUFFICIENT_DATA audits.
            # Preserve the typed contract by omitting the optional key rather than
            # serializing an invalid null value.
            if normalized_item.get("confidence") is None:
                normalized_item.pop("confidence", None)
            normalized.append(normalized_item)
        return normalized

    @staticmethod
    def _extract_hfacs_classifications(
        fishbone: Fishbone | None,
    ) -> list[dict[str, Any]]:
        if fishbone is None:
            return []
        classifications: list[dict[str, Any]] = []
        for cause in fishbone.get_all_causes():
            classifications.append(
                {
                    "cause_id": str(cause.cause_id),
                    "cause": cause.description,
                    "category": cause.category.value,
                    "hfacs_code": cause.hfacs_code,
                    "review_status": cause.hfacs_review_status.value,
                    "reviewed_by": cause.hfacs_reviewed_by,
                    "reviewed_at": (
                        cause.hfacs_reviewed_at.isoformat()
                        if cause.hfacs_reviewed_at
                        else None
                    ),
                    "review_reason": cause.hfacs_review_reason,
                    "confidence": (
                        cause.hfacs_confidence.value if cause.hfacs_confidence else None
                    ),
                    "confidence_semantics": "HEURISTIC_RULE_MATCH_NOT_CALIBRATED",
                    "evidence": list(cause.evidence),
                    "verified": cause.verified,
                    "source": "fishbone_cause",
                }
            )
        return classifications
