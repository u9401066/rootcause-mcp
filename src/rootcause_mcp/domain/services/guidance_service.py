"""
Clinical Guidance Domain Service.

Evaluates clinical reasoning state and generates actionable guidance,
checklists, and next recommended actions for AI agents.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from rootcause_mcp.domain.entities.hypothesis import HypothesisStatus
from rootcause_mcp.domain.services.final_report_conformance import (
    evaluate_hypothesis_disposition,
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
    ) -> ReasoningGuidance:
        """Evaluate current clinical reasoning state and build guidance."""
        evidence_count = len(evidence_store)
        verified_evidence_count = sum(1 for e in evidence_store.values() if e.verified)
        evidence_with_sources = sum(
            1 for e in evidence_store.values() if e.source.document_id
        )

        hypotheses_count = len(hypothesis_store)
        normalized_diagnoses = [
            normalize_diagnosis(hypothesis.model_dump(mode="json"))
            for hypothesis in hypothesis_store.values()
        ]
        unique_hypotheses_count = len(set(normalized_diagnoses))
        duplicate_diagnoses = sorted(
            {
                name
                for name in normalized_diagnoses
                if name and normalized_diagnoses.count(name) > 1
            }
        )
        differential_is_unique = (
            hypotheses_count >= 3
            and unique_hypotheses_count >= 3
            and bool(normalized_diagnoses)
            and all(normalized_diagnoses)
            and not duplicate_diagnoses
        )
        readiness_hypothesis_count = (
            unique_hypotheses_count
            if not duplicate_diagnoses
            else min(unique_hypotheses_count, 2)
        )
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

        unlinked_evidence = [
            e.id.value
            for e in evidence_store.values()
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
        active_disposition_failures = [
            hypothesis.id.value
            for hypothesis in active_hypotheses
            if not cls._active_disposition_complete(
                disposition_by_id[hypothesis.id.value]
            )
        ]
        eligible_hypotheses = [
            hypothesis
            for hypothesis in hypothesis_store.values()
            if hypothesis.status
            not in {HypothesisStatus.EXCLUDED, HypothesisStatus.ON_HOLD}
        ]
        leading_hypothesis = max(
            eligible_hypotheses,
            key=lambda hypothesis: hypothesis.current_probability,
            default=None,
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
            hypotheses_count=readiness_hypothesis_count,
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
        if active_disposition_failures:
            missing.append(
                "Active diagnoses missing genuine evidence plus contradiction or a "
                "typed pending rule-out test: " + ", ".join(active_disposition_failures)
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

        stage, stage_display, next_actions, push_questions = (
            cls._determine_stage_and_actions(
                evidence_count=evidence_count,
                verified_evidence_count=verified_evidence_count,
                hypotheses_count=readiness_hypothesis_count,
                must_not_miss_count=must_not_miss_count,
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
            "must_not_miss_hypotheses_count": must_not_miss_count,
            "must_not_miss_reviewed": (
                must_not_miss_count > 0 and not must_not_miss_disposition_failures
            ),
            "unlinked_evidence_count": len(unlinked_evidence),
            "disconfirming_evidence_tested": differential_disposition_complete,
            "genuine_disconfirming_evidence_present": has_genuine_contradiction,
            "active_differential_disposition_complete": not active_disposition_failures,
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
            and must_not_miss_count > 0
            and len(unlinked_evidence) == 0
            and differential_disposition_complete
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
        disposition: tuple[bool, bool, bool],
    ) -> bool:
        """Match the final gate for one active differential diagnosis."""
        has_support, has_contradiction, has_disconfirming_plan = disposition
        return (has_support or has_contradiction) and (
            has_contradiction or has_disconfirming_plan
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

        if hypotheses_count < 3 or must_not_miss_count == 0:
            return (
                ReasoningStage.DIFFERENTIAL_EXPANSION,
                "2. Differential Expansion (≥3 Hypotheses)",
                [
                    f"Propose {max(0, 3 - hypotheses_count)} more competing differential diagnosis hypothesis/hypotheses using rc_propose_hypothesis",
                    "Mark at least one applicable high-risk diagnosis with must_not_miss=true",
                ],
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
