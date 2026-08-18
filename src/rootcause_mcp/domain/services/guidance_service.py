"""
Clinical Guidance Domain Service.

Evaluates clinical reasoning state and generates actionable guidance,
checklists, and next recommended actions for AI agents.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from rootcause_mcp.domain.entities.hypothesis import HypothesisStatus, MechanismCategory
from rootcause_mcp.domain.services.final_report_conformance import (
    diagnostic_certainty_is_supported,
    evaluate_differential_breadth_audits,
    evaluate_hypothesis_disposition,
    has_pending_discriminating_test,
    normalize_diagnosis,
)
from rootcause_mcp.domain.value_objects.reasoning_guidance import (
    ReasoningGuidance,
    ReasoningStage,
)

if TYPE_CHECKING:
    from rootcause_mcp.domain.entities.evidence import Evidence
    from rootcause_mcp.domain.entities.hypothesis import Hypothesis
    from rootcause_mcp.domain.entities.reasoning_step import ReasoningChain
    from rootcause_mcp.domain.entities.thinking_step import ThinkingChain


class ClinicalGuidanceService:
    """
    Evaluates clinical reasoning completion and provides deterministic guidance.

    Acts as the constraint harness that guides Flash/mini models through
    complete multi-loop reasoning without requiring LLM intelligence in the MCP.
    """

    @classmethod
    def evaluate(
        cls,
        session_id: str,
        evidence_store: dict[str, Evidence],
        hypothesis_store: dict[str, Hypothesis],
        thinking_chain: ThinkingChain,
        reasoning_chain: ReasoningChain,
        leading_hypothesis_id: str | None = None,
    ) -> ReasoningGuidance:
        """Evaluate current clinical reasoning state and build guidance."""
        case_evidence = {
            evidence_id: evidence
            for evidence_id, evidence in evidence_store.items()
            if evidence.evidence_type.value != "LITERATURE"
        }
        evidence_count = len(case_evidence)
        verified_evidence_count = sum(1 for e in case_evidence.values() if e.verified)
        evidence_with_sources = sum(
            1 for e in case_evidence.values() if e.source.document_id
        )

        (
            hypotheses_count,
            unique_hypotheses_count,
            duplicate_diagnoses,
            differential_is_unique,
            mechanism_categories,
            mechanism_breadth_met,
            readiness_hypothesis_count,
        ) = cls._evaluate_differential_shape(hypothesis_store)
        must_not_miss_count = sum(
            1 for hypothesis in hypothesis_store.values() if hypothesis.must_not_miss
        )
        active_hypotheses = [
            h for h in hypothesis_store.values() if h.status == HypothesisStatus.ACTIVE
        ]

        linked_evidence_ids: set[str] = set()
        for h in hypothesis_store.values():
            linked_evidence_ids.update(h.supporting_evidence_ids)
            linked_evidence_ids.update(h.contradicting_evidence_ids)
            linked_evidence_ids.update(
                relationship.evidence_id for relationship in h.likelihood_ratios
            )

        unlinked_evidence = [
            e.id.value
            for e in case_evidence.values()
            if e.id.value not in linked_evidence_ids
        ]

        evidence_payloads: dict[str, Mapping[str, Any]] = {
            evidence_id: evidence.model_dump(mode="json")
            for evidence_id, evidence in evidence_store.items()
        }
        disposition_by_id = {
            hypothesis.id.value: evaluate_hypothesis_disposition(
                hypothesis.model_dump(mode="json"),
                evidence_payloads,
            )
            for hypothesis in hypothesis_store.values()
        }
        breadth_audit_failures, breadth_audit_details = cls._evaluate_breadth_audit(
            thinking_chain,
            hypothesis_store,
        )
        breadth_audit_complete = not breadth_audit_failures
        active_disposition_failures = [
            hypothesis.id.value
            for hypothesis in active_hypotheses
            if not cls._active_disposition_complete(
                hypothesis, disposition_by_id[hypothesis.id.value]
            )
        ]
        certainty_failures = [
            hypothesis.id.value
            for hypothesis in hypothesis_store.values()
            if not diagnostic_certainty_is_supported(
                hypothesis.model_dump(mode="json"),
                evidence_payloads,
            )
        ]
        selected_hypothesis = hypothesis_store.get(leading_hypothesis_id or "")
        leading_hypothesis = (
            selected_hypothesis
            if selected_hypothesis is not None
            and selected_hypothesis.status
            not in {HypothesisStatus.EXCLUDED, HypothesisStatus.ON_HOLD}
            else None
        )
        leading_diagnosis_challenged = (
            leading_hypothesis is not None
            and cls._leading_or_must_not_miss_disposition_complete(
                disposition_by_id[leading_hypothesis.id.value]
            )
        )
        must_not_miss_disposition_failures = [
            hypothesis.id.value
            for hypothesis in hypothesis_store.values()
            if hypothesis.must_not_miss
            and not cls._leading_or_must_not_miss_disposition_complete(
                disposition_by_id[hypothesis.id.value]
            )
        ]
        differential_disposition_complete = (
            not active_disposition_failures
            and leading_diagnosis_challenged
            and must_not_miss_count > 0
            and not must_not_miss_disposition_failures
        )
        has_genuine_contradiction = any(
            disposition[1] for disposition in disposition_by_id.values()
        )

        uncertainty_factors = [
            factor
            for step in thinking_chain.steps
            for factor in step.uncertainty_factors
        ]
        bias_reports = thinking_chain.get_bias_report()
        reasoning_step_count = len(reasoning_chain.steps)

        completeness_score = cls._calculate_score(
            evidence_count=evidence_count,
            evidence_with_sources=evidence_with_sources,
            verified_evidence_count=verified_evidence_count,
            hypotheses_count=(
                readiness_hypothesis_count
                if mechanism_breadth_met and breadth_audit_complete
                else min(readiness_hypothesis_count, 2)
            ),
            unlinked_evidence_count=len(unlinked_evidence),
            has_disconfirming_check=differential_disposition_complete,
            has_uncertainties=bool(uncertainty_factors),
            has_biases=bool(bias_reports),
        )

        missing = cls._build_missing_prerequisites(
            evidence_count=evidence_count,
            evidence_with_sources=evidence_with_sources,
            verified_evidence_count=verified_evidence_count,
            hypotheses_count=readiness_hypothesis_count,
            must_not_miss_count=must_not_miss_count,
            unlinked_evidence=unlinked_evidence,
            has_disconfirming_check=differential_disposition_complete,
            has_uncertainties=bool(uncertainty_factors),
            has_biases=bool(bias_reports),
        )
        if duplicate_diagnoses:
            missing.insert(
                0,
                "Duplicate normalized differential diagnosis entries: "
                + ", ".join(duplicate_diagnoses),
            )
        if not mechanism_breadth_met:
            missing.insert(
                0,
                "Differential mechanism breadth needed: at least 2 non-UNKNOWN "
                "etiologic categories are required for final synthesis",
            )
        if breadth_audit_failures:
            missing.insert(
                0,
                "Systematic differential breadth audit is incomplete: "
                + ", ".join(breadth_audit_failures),
            )
        if active_disposition_failures:
            missing.append(
                "Active diagnoses missing clinical rationale, per-diagnosis "
                "uncertainty, or genuine evidence/typed discriminating test: "
                + ", ".join(active_disposition_failures)
            )
        if leading_hypothesis is None:
            missing.append(
                "No eligible explicit leading diagnosis has been selected; use the "
                "audited leading-hypothesis mutation before final synthesis"
            )
        if leading_hypothesis is not None and not leading_diagnosis_challenged:
            missing.append(
                "Leading diagnosis lacks genuine support plus contradiction or a "
                f"typed pending rule-out test: {leading_hypothesis.id.value}"
            )
        if must_not_miss_disposition_failures:
            missing.append(
                "Must-not-miss diagnoses lack genuine support plus contradiction or "
                "a typed pending rule-out test: "
                + ", ".join(must_not_miss_disposition_failures)
            )
        if certainty_failures:
            missing.append(
                "Diagnostic certainty labels lack genuine evidence/completed-test "
                "support or conflict with lifecycle status: "
                + ", ".join(certainty_failures)
            )

        stage, stage_display, next_actions, push_questions = (
            cls._determine_stage_and_actions(
                evidence_count=evidence_count,
                verified_evidence_count=verified_evidence_count,
                hypotheses_count=readiness_hypothesis_count,
                must_not_miss_count=must_not_miss_count,
                mechanism_breadth_met=mechanism_breadth_met,
                breadth_audit_complete=breadth_audit_complete,
                unlinked_evidence=unlinked_evidence,
                has_disconfirming_check=differential_disposition_complete,
                has_uncertainties=bool(uncertainty_factors),
                has_biases=bool(bias_reports),
            )
        )

        checklist = {
            "evidence_count": evidence_count,
            "verified_evidence_count": verified_evidence_count,
            "evidence_with_sources": evidence_with_sources,
            "hypotheses_count": hypotheses_count,
            "unique_hypotheses_count": unique_hypotheses_count,
            "duplicate_normalized_diagnoses": duplicate_diagnoses,
            "active_hypotheses_count": len(active_hypotheses),
            "min_hypotheses_met": differential_is_unique,
            "mechanism_categories": sorted(mechanism_categories),
            "mechanism_categories_count": len(mechanism_categories),
            "mechanism_breadth_met": mechanism_breadth_met,
            "differential_breadth_audit_complete": breadth_audit_complete,
            "differential_breadth_audit_details": breadth_audit_details,
            "must_not_miss_hypotheses_count": must_not_miss_count,
            "must_not_miss_reviewed": (
                must_not_miss_count > 0 and not must_not_miss_disposition_failures
            ),
            "unlinked_evidence_count": len(unlinked_evidence),
            "disconfirming_evidence_tested": differential_disposition_complete,
            "genuine_disconfirming_evidence_present": has_genuine_contradiction,
            "active_differential_disposition_complete": not active_disposition_failures,
            "diagnostic_certainty_supported": not certainty_failures,
            "leading_hypothesis_id": leading_hypothesis_id,
            "explicit_leading_hypothesis_selected": bool(leading_hypothesis_id),
            "leading_selection_eligible": leading_hypothesis is not None,
            "leading_diagnosis_challenged": leading_diagnosis_challenged,
            "must_not_miss_disposition_complete": (
                must_not_miss_count > 0 and not must_not_miss_disposition_failures
            ),
            "uncertainty_acknowledged": bool(uncertainty_factors),
            "bias_reviewed": bool(bias_reports),
            "reasoning_steps_recorded": reasoning_step_count,
        }

        is_ready = (
            evidence_count >= 2
            and verified_evidence_count == evidence_count
            and evidence_with_sources == evidence_count
            and differential_is_unique
            and mechanism_breadth_met
            and breadth_audit_complete
            and must_not_miss_count > 0
            and len(unlinked_evidence) == 0
            and differential_disposition_complete
            and not certainty_failures
            and bool(uncertainty_factors)
            and bool(bias_reports)
        )

        return ReasoningGuidance(
            session_id=session_id,
            current_stage=stage,
            stage_display=stage_display,
            completeness_score=completeness_score,
            checklist=checklist,
            missing_prerequisites=missing,
            next_recommended_actions=next_actions,
            push_questions=push_questions,
            is_ready_for_report=is_ready,
        )

    @staticmethod
    def _active_disposition_complete(
        hypothesis: Hypothesis,
        disposition: tuple[bool, bool, bool],
    ) -> bool:
        """Require auditable rationale/uncertainty plus evidence or a test plan."""
        has_support, has_contradiction, _ = disposition
        return (
            len(hypothesis.clinical_rationale.strip()) >= 10
            and any(item.strip() for item in hypothesis.uncertainty_factors)
            and (
                has_support
                or has_contradiction
                or has_pending_discriminating_test(hypothesis.model_dump(mode="json"))
            )
        )

    @staticmethod
    def _evaluate_differential_shape(
        hypothesis_store: Mapping[str, Hypothesis],
    ) -> tuple[int, int, list[str], bool, set[str], bool, int]:
        """Return normalized uniqueness and mechanism-breadth facts."""
        normalized = [
            normalize_diagnosis(hypothesis.model_dump(mode="json"))
            for hypothesis in hypothesis_store.values()
        ]
        unique_count = len(set(normalized))
        duplicates = sorted(
            {name for name in normalized if name and normalized.count(name) > 1}
        )
        hypothesis_count = len(hypothesis_store)
        is_unique = (
            hypothesis_count >= 3
            and unique_count >= 3
            and bool(normalized)
            and all(normalized)
            and not duplicates
        )
        mechanisms = {
            hypothesis.mechanism_category.value
            for hypothesis in hypothesis_store.values()
            if hypothesis.mechanism_category is not MechanismCategory.UNKNOWN
        }
        readiness_count = unique_count if not duplicates else min(unique_count, 2)
        return (
            hypothesis_count,
            unique_count,
            duplicates,
            is_unique,
            mechanisms,
            len(mechanisms) >= 2,
            readiness_count,
        )

    @staticmethod
    def _evaluate_breadth_audit(
        thinking_chain: ThinkingChain,
        hypothesis_store: Mapping[str, Hypothesis],
    ) -> tuple[list[str], dict[str, Any]]:
        """Project the latest persisted audits and run the shared final rules."""
        payloads_by_id: dict[str, Mapping[str, Any]] = {}
        for step in thinking_chain.steps:
            if step.structured_data.get("record_type") != (
                "DIFFERENTIAL_BREADTH_AUDIT"
            ):
                continue
            payload = step.structured_data.get("audit")
            if not isinstance(payload, Mapping):
                continue
            audit_id = str(payload.get("audit_id") or "").strip()
            if audit_id:
                payloads_by_id[audit_id] = payload
        return evaluate_differential_breadth_audits(
            list(payloads_by_id.values()),
            [
                hypothesis.model_dump(mode="json")
                for hypothesis in hypothesis_store.values()
            ],
        )

    @staticmethod
    def _leading_or_must_not_miss_disposition_complete(
        disposition: tuple[bool, bool, bool],
    ) -> bool:
        """Require support plus a genuine or typed prospective challenge."""
        has_support, has_contradiction, has_disconfirming_plan = disposition
        return has_support and (has_contradiction or has_disconfirming_plan)

    @staticmethod
    def _calculate_score(
        evidence_count: int,
        evidence_with_sources: int,
        verified_evidence_count: int,
        hypotheses_count: int,
        unlinked_evidence_count: int,
        has_disconfirming_check: bool,
        has_uncertainties: bool,
        has_biases: bool,
    ) -> float:
        ev_score = min(evidence_count / 3.0, 1.0) * 0.20
        if (
            evidence_count > 0
            and evidence_with_sources == evidence_count
            and verified_evidence_count == evidence_count
        ):
            ev_score += 0.05

        hyp_score = min(hypotheses_count / 3.0, 1.0) * 0.25

        unlinked_ratio = unlinked_evidence_count / max(evidence_count, 1)
        link_score = max(0.0, 1.0 - unlinked_ratio) * 0.15
        if has_disconfirming_check:
            link_score += 0.10

        meta_score = (0.15 if has_uncertainties else 0.0) + (
            0.10 if has_biases else 0.0
        )
        return round(min(1.0, ev_score + hyp_score + link_score + meta_score), 2)

    @staticmethod
    def _build_missing_prerequisites(
        evidence_count: int,
        evidence_with_sources: int,
        verified_evidence_count: int,
        hypotheses_count: int,
        must_not_miss_count: int,
        unlinked_evidence: list[str],
        has_disconfirming_check: bool,
        has_uncertainties: bool,
        has_biases: bool,
    ) -> list[str]:
        missing: list[str] = []
        if evidence_count < 2:
            missing.append(
                "At least 2 evidence findings registered from clinical records"
            )
        if evidence_with_sources < evidence_count:
            missing.append(
                f"{evidence_count - evidence_with_sources} evidence item(s) lack source document references"
            )
        if verified_evidence_count < evidence_count:
            missing.append(
                f"{evidence_count - verified_evidence_count} evidence item(s) lack verified source content"
            )
        if hypotheses_count < 3:
            missing.append(
                f"Differential expansion needed: currently {hypotheses_count}/3 recommended hypotheses"
            )
        if hypotheses_count >= 3 and must_not_miss_count == 0:
            missing.append(
                "No hypothesis is explicitly marked as a must-not-miss high-harm rule-out"
            )
        if unlinked_evidence:
            missing.append(
                f"{len(unlinked_evidence)} evidence item(s) not yet linked to any hypothesis"
            )
        if not has_disconfirming_check:
            missing.append(
                "One or more required diagnoses lack genuine LR<1 evidence or a "
                "typed pending DISCONFIRM/RULE_OUT test"
            )
        if not has_uncertainties:
            missing.append("No clinical uncertainty factors explicitly declared")
        if not has_biases:
            missing.append("No cognitive bias evaluation recorded")
        return missing

    @staticmethod
    def _determine_stage_and_actions(
        evidence_count: int,
        verified_evidence_count: int,
        hypotheses_count: int,
        must_not_miss_count: int,
        mechanism_breadth_met: bool,
        breadth_audit_complete: bool,
        unlinked_evidence: list[str],
        has_disconfirming_check: bool,
        has_uncertainties: bool,
        has_biases: bool,
    ) -> tuple[ReasoningStage, str, list[str], list[str]]:
        if (
            evidence_count < 2
            or verified_evidence_count < evidence_count
            or hypotheses_count == 0
        ):
            return (
                ReasoningStage.EVIDENCE_COLLECTION,
                "1. Evidence Collection & Grounding",
                [
                    "Call rc_add_evidence(content=..., source_document=..., raw_snippet=...) to extract key clinical findings",
                    "Call rc_propose_hypothesis(diagnosis=...) to create your initial working diagnosis",
                ],
                [
                    "What are the critical physiological vitals, lab outliers, or turning points in the raw data?",
                    "Are all evidence extractions verbatim-grounded in specific source records?",
                ],
            )

        if (
            hypotheses_count < 3
            or must_not_miss_count == 0
            or not mechanism_breadth_met
            or not breadth_audit_complete
        ):
            expansion_actions = [
                f"Propose {max(0, 3 - hypotheses_count)} more competing differential diagnosis hypothesis/hypotheses using rc_propose_hypothesis",
                "Mark at least one applicable high-risk diagnosis with must_not_miss=true",
            ]
            if not mechanism_breadth_met:
                expansion_actions.append(
                    "Classify and expand candidates until at least two plausible non-UNKNOWN mechanism_category values are represented"
                )
            if not breadth_audit_complete:
                expansion_actions.append(
                    "Call rc_audit_differential_breadth with a syndrome-appropriate complete PRIMARY framework audit and explicit stop_rationale"
                )
            return (
                ReasoningStage.DIFFERENTIAL_EXPANSION,
                "2. Differential Expansion (≥3 Hypotheses)",
                expansion_actions,
                [
                    "What competing diagnoses could explain these findings if your primary hypothesis is incorrect?",
                    "What rare or critical 'can't miss' emergencies must be actively ruled out?",
                ],
            )

        if unlinked_evidence or not has_disconfirming_check:
            return (
                ReasoningStage.BAYESIAN_EVALUATION,
                "3. Bayesian Hypothesis Testing & Rule-Out",
                [
                    f"Link unlinked evidence ({', '.join(unlinked_evidence[:3])}) to hypotheses using rc_link_evidence_to_hypothesis",
                    "Add genuine disconfirming evidence (supports=false and LR < 1.0) or a typed pending DISCONFIRM/RULE_OUT test for each required diagnosis",
                ],
                [
                    "What specific test result or physiological sign would definitively disprove your leading diagnosis?",
                    "Have you assigned likelihood ratios based on published clinical evidence or guidelines?",
                ],
            )

        if not has_uncertainties or not has_biases:
            return (
                ReasoningStage.COGNITIVE_AUDIT,
                "4. Metacognitive & Bias Audit",
                [
                    "Record clinical uncertainties and pending diagnostics with rc_think_aloud(uncertainty_factors=[...])",
                    "Audit cognitive biases (e.g., anchoring, confirmation bias, premature closure) with rc_reflect",
                ],
                [
                    "What data is missing, pending, or ambiguous? Are you anchoring on the first prominent finding?",
                    "Did initial impressions create an availability bias?",
                ],
            )

        return (
            ReasoningStage.READY_FOR_SYNTHESIS,
            "5. Ready for Auditable Report Synthesis",
            [
                "Call rc_generate_contract_report(format='markdown', detail_level='standard', finalize=True) to synthesize the case report",
                "Review the generated Evidence Graph and automated completeness checks in the report",
            ],
            [
                "Is the reasoning chain complete, verifiable, and defensible for an M&M conference or clinical audit?",
            ],
        )
