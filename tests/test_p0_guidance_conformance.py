"""P0 readiness probes aligned with deterministic final-report DDx gates."""

from __future__ import annotations

from rootcause_mcp.application.clinical_reasoning_orchestrator import (
    ClinicalReasoningOrchestrator,
)
from rootcause_mcp.domain.entities.thinking_step import ThinkingStep, ThinkingType


def _planned_rule_out(name: str) -> dict[str, str]:
    return {
        "name": f"Definitive test for {name}",
        "purpose": "RULE_OUT",
        "expected_supporting_result": f"Predefined positive pattern for {name}",
        "expected_refuting_result": f"Adequate negative pattern refuting {name}",
        "status": "PLANNED",
    }


def _guidance_case(
    diagnoses: tuple[str, str, str],
    *,
    include_plans: bool = True,
    neutral_leading_support: bool = False,
    exclude_third: bool = False,
) -> ClinicalReasoningOrchestrator:
    orchestrator = ClinicalReasoningOrchestrator("p0-guidance")
    evidence = [
        orchestrator.add_evidence(
            content="Documented acute hypotension",
            source_document="SRC-1",
            auto_verify=False,
        ),
        orchestrator.add_evidence(
            content="Adequate negative diagnostic study",
            source_document="SRC-2",
            auto_verify=False,
        ),
    ]
    for item in evidence:
        orchestrator.evidence_store[item.id.value] = item.mark_verified(
            verifier="SYSTEM_PROVENANCE_VERIFIER",
            verification_method="EXACT_SNIPPET_MATCH",
        )

    hypotheses = [
        orchestrator.propose_hypothesis(
            diagnosis=diagnosis,
            prior_probability=prior,
            rationale=f"Auditable rationale for {diagnosis}.",
            must_not_miss=index == 1,
            planned_tests=[_planned_rule_out(diagnosis)] if include_plans else [],
        )
        for index, (diagnosis, prior) in enumerate(
            zip(diagnoses, (0.5, 0.3, 0.2), strict=True)
        )
    ]
    for index, hypothesis in enumerate(hypotheses):
        orchestrator.link_evidence_to_hypothesis(
            evidence_id=evidence[0].id.value,
            hypothesis_id=hypothesis.id.value,
            likelihood_ratio=1.0 if index == 0 and neutral_leading_support else 2.0,
            supports=True,
            rationale="Explicit observed-evidence relationship.",
        )
    orchestrator.link_evidence_to_hypothesis(
        evidence_id=evidence[1].id.value,
        hypothesis_id=hypotheses[2].id.value,
        likelihood_ratio=0.2,
        supports=False,
        rationale="Adequate negative study genuinely refutes the third diagnosis.",
    )
    if exclude_third:
        orchestrator.exclude_hypothesis(
            hypotheses[2].id.value,
            excluded_by="reviewer",
            reason="Evidence-based exclusion retained for audit history.",
        )
    orchestrator.thinking_chain.add_step(
        ThinkingStep(
            thinking_type=ThinkingType.UNCERTAINTY_ACKNOWLEDGED,
            content="Confirm all competing diagnoses before synthesis.",
            internal_reasoning="Prospective challenges remain explicit.",
            confidence=0.8,
            uncertainty_factors=["Definitive studies pending"],
            potential_biases=["Anchoring"],
        )
    )
    return orchestrator


def test_guidance_accepts_unique_ddx_with_per_diagnosis_typed_challenges() -> None:
    guidance = _guidance_case(
        ("Pulmonary embolism", "Cardiogenic shock", "Septic shock")
    ).get_guidance()

    assert guidance.is_ready_for_report is True
    assert guidance.checklist["unique_hypotheses_count"] == 3
    assert guidance.checklist["active_differential_disposition_complete"] is True
    assert guidance.checklist["leading_diagnosis_challenged"] is True
    assert guidance.checklist["must_not_miss_disposition_complete"] is True


def test_guidance_rejects_normalized_duplicate_diagnoses() -> None:
    guidance = _guidance_case(
        ("Pulmonary embolism", " pulmonary-embolism ", "Septic shock")
    ).get_guidance()

    assert guidance.is_ready_for_report is False
    assert guidance.checklist["unique_hypotheses_count"] == 2
    assert guidance.checklist["min_hypotheses_met"] is False
    assert guidance.checklist["duplicate_normalized_diagnoses"] == [
        "pulmonary embolism"
    ]


def test_excluded_or_global_contradiction_cannot_cover_unchallenged_diagnoses() -> None:
    guidance = _guidance_case(
        ("Pulmonary embolism", "Cardiogenic shock", "Septic shock"),
        include_plans=False,
        exclude_third=True,
    ).get_guidance()

    assert guidance.checklist["genuine_disconfirming_evidence_present"] is True
    assert guidance.checklist["active_differential_disposition_complete"] is False
    assert guidance.checklist["leading_diagnosis_challenged"] is False
    assert guidance.checklist["must_not_miss_disposition_complete"] is False
    assert guidance.is_ready_for_report is False


def test_neutral_lr_does_not_count_as_leading_support() -> None:
    guidance = _guidance_case(
        ("Pulmonary embolism", "Cardiogenic shock", "Septic shock"),
        neutral_leading_support=True,
    ).get_guidance()

    assert guidance.checklist["leading_diagnosis_challenged"] is False
    assert guidance.is_ready_for_report is False


def test_fully_resolved_differential_does_not_require_an_active_entry() -> None:
    orchestrator = _guidance_case(
        ("Pulmonary embolism", "Cardiogenic shock", "Septic shock")
    )
    hypotheses = list(orchestrator.hypothesis_store.values())
    orchestrator.hypothesis_store[hypotheses[0].id.value] = hypotheses[
        0
    ].mark_confirmed(
        confirmed_by="reviewer",
        reason="Diagnostic obligations satisfied.",
    )
    for hypothesis in hypotheses[1:]:
        orchestrator.exclude_hypothesis(
            hypothesis.id.value,
            excluded_by="reviewer",
            reason="Evidence-based resolved disposition.",
        )

    guidance = orchestrator.get_guidance()

    assert guidance.checklist["active_hypotheses_count"] == 0
    assert guidance.checklist["active_differential_disposition_complete"] is True
    assert guidance.is_ready_for_report is True
