"""
Clinical Guidance Domain Service.

Evaluates clinical reasoning state and generates actionable guidance,
checklists, and next recommended actions for AI agents.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rootcause_mcp.domain.entities.hypothesis import HypothesisStatus
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
        active_hypotheses = [
            h for h in hypothesis_store.values() if h.status == HypothesisStatus.ACTIVE
        ]

        linked_evidence_ids: set[str] = set()
        for h in hypothesis_store.values():
            linked_evidence_ids.update(h.supporting_evidence_ids)
            linked_evidence_ids.update(h.contradicting_evidence_ids)

        unlinked_evidence = [
            e.id.value for e in evidence_store.values() if e.id.value not in linked_evidence_ids
        ]

        has_disconfirming_check = (
            any(bool(h.contradicting_evidence_ids) for h in hypothesis_store.values())
            or any(h.status == HypothesisStatus.EXCLUDED for h in hypothesis_store.values())
            or any(
                lr.lr_negative is not None
                for h in hypothesis_store.values()
                for lr in h.likelihood_ratios
            )
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
            hypotheses_count=hypotheses_count,
            unlinked_evidence_count=len(unlinked_evidence),
            has_disconfirming_check=has_disconfirming_check,
            has_uncertainties=bool(uncertainty_factors),
            has_biases=bool(bias_reports),
        )

        missing = cls._build_missing_prerequisites(
            evidence_count=evidence_count,
            evidence_with_sources=evidence_with_sources,
            hypotheses_count=hypotheses_count,
            unlinked_evidence=unlinked_evidence,
            has_disconfirming_check=has_disconfirming_check,
            has_uncertainties=bool(uncertainty_factors),
            has_biases=bool(bias_reports),
        )

        stage, stage_display, next_actions, push_questions = cls._determine_stage_and_actions(
            evidence_count=evidence_count,
            hypotheses_count=hypotheses_count,
            unlinked_evidence=unlinked_evidence,
            has_disconfirming_check=has_disconfirming_check,
            has_uncertainties=bool(uncertainty_factors),
            has_biases=bool(bias_reports),
        )

        checklist = {
            "evidence_count": evidence_count,
            "verified_evidence_count": verified_evidence_count,
            "evidence_with_sources": evidence_with_sources,
            "hypotheses_count": hypotheses_count,
            "active_hypotheses_count": len(active_hypotheses),
            "min_hypotheses_met": hypotheses_count >= 3,
            "unlinked_evidence_count": len(unlinked_evidence),
            "disconfirming_evidence_tested": has_disconfirming_check,
            "uncertainty_acknowledged": bool(uncertainty_factors),
            "bias_reviewed": bool(bias_reports),
            "reasoning_steps_recorded": reasoning_step_count,
        }

        is_ready = (
            evidence_count >= 2
            and hypotheses_count >= 2
            and len(unlinked_evidence) == 0
            and bool(uncertainty_factors)
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
    def _calculate_score(
        evidence_count: int,
        evidence_with_sources: int,
        hypotheses_count: int,
        unlinked_evidence_count: int,
        has_disconfirming_check: bool,
        has_uncertainties: bool,
        has_biases: bool,
    ) -> float:
        ev_score = min(evidence_count / 3.0, 1.0) * 0.20
        if evidence_count > 0 and evidence_with_sources == evidence_count:
            ev_score += 0.05

        hyp_score = min(hypotheses_count / 3.0, 1.0) * 0.25

        unlinked_ratio = unlinked_evidence_count / max(evidence_count, 1)
        link_score = max(0.0, 1.0 - unlinked_ratio) * 0.15
        if has_disconfirming_check:
            link_score += 0.10

        meta_score = (0.15 if has_uncertainties else 0.0) + (0.10 if has_biases else 0.0)
        return round(min(1.0, ev_score + hyp_score + link_score + meta_score), 2)

    @staticmethod
    def _build_missing_prerequisites(
        evidence_count: int,
        evidence_with_sources: int,
        hypotheses_count: int,
        unlinked_evidence: list[str],
        has_disconfirming_check: bool,
        has_uncertainties: bool,
        has_biases: bool,
    ) -> list[str]:
        missing: list[str] = []
        if evidence_count < 2:
            missing.append("At least 2 evidence findings registered from clinical records")
        if evidence_with_sources < evidence_count:
            missing.append(f"{evidence_count - evidence_with_sources} evidence item(s) lack source document references")
        if hypotheses_count < 3:
            missing.append(f"Differential expansion needed: currently {hypotheses_count}/3 recommended hypotheses")
        if unlinked_evidence:
            missing.append(f"{len(unlinked_evidence)} evidence item(s) not yet linked to any hypothesis")
        if not has_disconfirming_check:
            missing.append("No disconfirming tests or rule-out criteria evaluated")
        if not has_uncertainties:
            missing.append("No clinical uncertainty factors explicitly declared")
        if not has_biases:
            missing.append("No cognitive bias evaluation recorded")
        return missing

    @staticmethod
    def _determine_stage_and_actions(
        evidence_count: int,
        hypotheses_count: int,
        unlinked_evidence: list[str],
        has_disconfirming_check: bool,
        has_uncertainties: bool,
        has_biases: bool,
    ) -> tuple[ReasoningStage, str, list[str], list[str]]:
        if evidence_count < 2 or hypotheses_count == 0:
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

        if hypotheses_count < 3:
            return (
                ReasoningStage.DIFFERENTIAL_EXPANSION,
                "2. Differential Expansion (≥3 Hypotheses)",
                [
                    f"Propose {3 - hypotheses_count} more competing differential diagnosis hypothesis/hypotheses using rc_propose_hypothesis",
                    "Include high-risk 'cannot-miss' alternative diagnoses (e.g., Pulmonary Embolism, Aortic Dissection, Sepsis)",
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
                    "Actively test disconfirming evidence (LR < 1.0 or exclusion criteria) to avoid confirmation bias",
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

