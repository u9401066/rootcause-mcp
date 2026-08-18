"""Fail-closed regressions for uncalibrated Bayesian compatibility values."""

from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import pytest

from rootcause_mcp.application.clinical_reasoning_orchestrator import (
    ClinicalReasoningOrchestrator,
)
from rootcause_mcp.application.server_state import ServerState
from rootcause_mcp.domain.entities.hypothesis import DiagnosticCertainty
from rootcause_mcp.domain.entities.reasoning_step import (
    ReasoningChain,
    ReasoningStep,
    ReasoningStepType,
)
from rootcause_mcp.domain.services.causation_validator import (
    CausationValidator,
    CauseEvent,
)
from rootcause_mcp.domain.services.final_report_conformance import (
    evaluate_final_report_conformance,
)
from rootcause_mcp.domain.services.gap_analyzer import ClinicalGapAnalyzer
from rootcause_mcp.domain.value_objects.contract_report import ContractReport
from rootcause_mcp.interface.contract_markdown import render_contract_report_markdown
from rootcause_mcp.interface.fhir import render_contract_report_fhir
from rootcause_mcp.interface.handlers.dd_handlers import DDHandlers
from rootcause_mcp.interface.mermaid import (
    build_evidence_graph,
    render_reasoning_chain_mermaid,
)


def _report_with_conflicting_numeric_order() -> ContractReport:
    hypotheses = []
    for hypothesis_id, diagnosis, probability, certainty in (
        ("HYP-ledger-first", "Ledger-first diagnosis", 0.01, "PROBABLE"),
        ("HYP-ledger-second", "Ledger-second diagnosis", 0.99, "POSSIBLE"),
    ):
        hypotheses.append(
            {
                "id": hypothesis_id,
                "diagnosis": {"display": diagnosis},
                "prior_probability": probability,
                "current_probability": probability,
                "status": "ACTIVE",
                "certainty": certainty,
                "mechanism_category": "OTHER",
                "diagnostic_role": "ETIOLOGIC",
                "reasoning_basis": "MECHANISM_INFERENCE",
                "clinical_rationale": "A source-linked mechanism remains under review.",
                "likelihood_ratios": [],
                "supporting_evidence_ids": [],
                "contradicting_evidence_ids": [],
                "uncertainty_factors": ["Calibration is not established"],
                "planned_tests": [],
            }
        )
    return ContractReport(
        report_id="RPT-uncalibrated-attack",
        session_id="uncalibrated-attack",
        generated_by="test-agent",
        leading_hypothesis_id="HYP-ledger-first",
        hypotheses=hypotheses,
        reasoning_chain=[
            {
                "id": "RS-placeholder",
                "sequence_number": 1,
                "step_type": "BAYESIAN_UPDATE",
                "content": "Updated a compatibility ledger value",
                "rationale": "Applied direct LR=1.0",
                "evidence_ids": [],
                "hypothesis_ids": ["HYP-ledger-first"],
                "cause_ids": [],
                "agent_id": "test-agent",
                "confidence": 0.99,
            }
        ],
    )


def _add_verified_calibration_source(
    orchestrator: ClinicalReasoningOrchestrator,
) -> str:
    evidence = orchestrator.add_evidence(
        content="Published direct likelihood-ratio calibration fixture.",
        evidence_type="LITERATURE",
        source_document="calibration-source.txt",
        source_location="line 1",
        raw_snippet="Published direct likelihood-ratio calibration fixture.",
        extraction_method="verbatim_quote",
        auto_verify=False,
    )
    orchestrator.evidence_store[evidence.id.value] = evidence.mark_verified(
        verifier="SYSTEM_PROVENANCE_VERIFIER",
        verification_method="EXACT_SNIPPET_MATCH",
        matched_lines=[1],
    )
    return evidence.id.value


def test_hypothesis_reasoning_steps_do_not_store_probability_as_confidence() -> None:
    orchestrator = ClinicalReasoningOrchestrator("reasoning-confidence-attack")
    evidence = orchestrator.add_evidence("Atomic observation", auto_verify=False)
    hypothesis = orchestrator.propose_hypothesis(
        diagnosis="Example diagnosis",
        prior_probability=0.91,
        rationale="The phenotype remains compatible with this mechanism.",
    )
    orchestrator.link_evidence_to_hypothesis(
        evidence_id=evidence.id.value,
        hypothesis_id=hypothesis.id.value,
        likelihood_ratio=1.0,
        supports=None,
        rationale="Quantitatively unknown neutral relationship.",
        calibration_status="QUANTITATIVELY_UNKNOWN",
    )
    orchestrator.exclude_hypothesis(
        hypothesis.id.value,
        excluded_by="test-agent",
        reason="A later source-linked disposition excluded the candidate.",
    )

    hypothesis_steps = [
        step
        for step in orchestrator.reasoning_chain.steps
        if step.step_type
        in {
            ReasoningStepType.HYPOTHESIS_GENERATION,
            ReasoningStepType.BAYESIAN_UPDATE,
            ReasoningStepType.HYPOTHESIS_ELIMINATION,
        }
    ]
    assert hypothesis_steps
    assert all(step.confidence is None for step in hypothesis_steps)


def test_reports_preserve_ledger_order_and_hide_uncalibrated_percentages(
    tmp_path: Path,
) -> None:
    report = _report_with_conflicting_numeric_order()

    conclusions = report.ranked_conclusion_hypotheses()
    assert [item["id"] for item in conclusions] == [
        "HYP-ledger-first",
        "HYP-ledger-second",
    ]

    english = render_contract_report_markdown(report, detail_level="full")
    zh_tw = render_contract_report_markdown(
        report,
        detail_level="full",
        locale="zh-TW",
        audience="clinician",
    )
    assert english.index("Ledger-first diagnosis") < english.index(
        "Ledger-second diagnosis"
    )
    assert zh_tw.index("Ledger-first diagnosis") < zh_tw.index(
        "Ledger-second diagnosis"
    )
    for rendered in (english, zh_tw):
        assert "99%" not in rendered
        assert "1%" not in rendered
        assert "0.99" not in rendered
        assert "0.01" not in rendered

    template_root = tmp_path / "templates"
    template_root.mkdir()
    (template_root / "attack.md").write_text(
        "# Custom\n\n{{hypothesis_table}}\n\n{{reasoning_chain_diagram}}\n",
        encoding="utf-8",
    )
    custom = render_contract_report_markdown(
        report,
        detail_level="full",
        template_path="attack.md",
        template_root=template_root,
    )
    assert "99%" not in custom
    assert "1%" not in custom
    assert "0.99" not in custom
    assert "0.01" not in custom


def test_preliminary_output_does_not_infer_an_unselected_lead() -> None:
    payload = _report_with_conflicting_numeric_order().model_dump(mode="json")
    payload["leading_hypothesis_id"] = None
    report = ContractReport.model_validate(payload)

    assert report.ranked_conclusion_hypotheses() == []
    english = render_contract_report_markdown(report)
    zh_tw = render_contract_report_markdown(
        report,
        locale="zh-TW",
        audience="clinician",
    )
    fhir = render_contract_report_fhir(report)

    assert "No explicit leading diagnosis has been selected" in english
    assert "尚未透過 audited mutation 選定 explicit leading DDx" in zh_tw
    assert "No explicit leading diagnosis was selected" in fhir["conclusion"]
    assert fhir["conclusionCode"] == []


def test_mermaid_omits_hypothesis_probability_and_placeholder_confidence() -> None:
    orchestrator = ClinicalReasoningOrchestrator("mermaid-probability-attack")
    hypothesis = orchestrator.propose_hypothesis(
        diagnosis="Example diagnosis",
        prior_probability=0.99,
        rationale="The phenotype remains compatible with this mechanism.",
        certainty="POSSIBLE",
    )

    graph = build_evidence_graph([], [hypothesis])
    hypothesis_node = next(
        node for node in graph["nodes"] if node["type"] == "hypothesis"
    )
    assert "probability" not in hypothesis_node
    assert hypothesis_node["certainty"] == "POSSIBLE"
    assert "99%" not in graph["mermaid"]

    chain = ReasoningChain(
        session_id="mermaid-probability-attack",
        steps=[
            ReasoningStep(
                sequence_number=1,
                step_type=ReasoningStepType.HYPOTHESIS_GENERATION,
                content="Candidate generated",
                rationale="Mechanism review",
                hypothesis_ids=[hypothesis.id.value],
                agent_id="test-agent",
                confidence=0.99,
            )
        ],
    )
    diagram = render_reasoning_chain_mermaid(chain)
    assert "99%" not in diagram
    assert "Confidence:" not in diagram


def test_gap_analyzer_uses_qualitative_state_not_probability_threshold() -> None:
    orchestrator = ClinicalReasoningOrchestrator("gap-probability-attack")
    evidence = orchestrator.add_evidence("Verified finding refutes the candidate")
    hypothesis = orchestrator.propose_hypothesis(
        diagnosis="Example diagnosis",
        prior_probability=0.01,
        rationale="The mechanism remains under review despite refuting evidence.",
        certainty=DiagnosticCertainty.HIGH_CONFIDENCE,
    )
    orchestrator.hypothesis_store[hypothesis.id.value] = hypothesis.model_copy(
        update={"contradicting_evidence_ids": [evidence.id.value]}
    )

    def categories() -> list[str]:
        report = ClinicalGapAnalyzer.analyze(
            session_id=orchestrator.session_id,
            evidence_store=orchestrator.evidence_store,
            hypothesis_store=orchestrator.hypothesis_store,
        )
        return [conflict.category for conflict in report.conflicts]

    low_probability_categories = categories()
    linked = orchestrator.hypothesis_store[hypothesis.id.value]
    orchestrator.hypothesis_store[hypothesis.id.value] = linked.model_copy(
        update={"current_probability": 0.99}
    )
    high_probability_categories = categories()

    assert low_probability_categories == high_probability_categories
    assert "DIAGNOSTIC_CONTRADICTION" in low_probability_categories


@pytest.mark.parametrize(
    "observation",
    [
        "Massive transfusion protocol was initiated.",
        "Propofol infusion continued for 48 hours.",
    ],
)
def test_gap_analyzer_does_not_infer_monitoring_omission_from_missing_mention(
    observation: str,
) -> None:
    orchestrator = ClinicalReasoningOrchestrator("missing-mention-attack")
    orchestrator.add_evidence(observation)

    report = ClinicalGapAnalyzer.analyze(
        session_id=orchestrator.session_id,
        evidence_store=orchestrator.evidence_store,
        hypothesis_store=orchestrator.hypothesis_store,
    )

    assert all(conflict.category != "GUIDELINE_GAP" for conflict in report.conflicts)
    combined = " ".join(
        f"{conflict.title} {conflict.description} {conflict.actionable_remedy}"
        for conflict in report.conflicts
    )
    assert "omitted" not in combined.casefold()
    assert "without" not in combined.casefold()
    assert "order stat" not in combined.casefold()
    assert "unknown" in combined.casefold()


def test_gap_analyzer_requires_explicit_absence_for_monitoring_omission() -> None:
    orchestrator = ClinicalReasoningOrchestrator("explicit-absence-control")
    trigger = orchestrator.add_evidence("Massive transfusion protocol was initiated.")
    absence = orchestrator.add_evidence(
        "Potassium was not monitored during the transfusion."
    )

    report = ClinicalGapAnalyzer.analyze(
        session_id=orchestrator.session_id,
        evidence_store=orchestrator.evidence_store,
        hypothesis_store=orchestrator.hypothesis_store,
    )

    omission = next(
        conflict
        for conflict in report.conflicts
        if conflict.conflict_id == "GAP-MTP-ELECTROLYTE"
    )
    assert omission.category == "GUIDELINE_GAP"
    assert set(omission.conflicting_evidence_ids) == {
        trigger.id.value,
        absence.id.value,
    }
    assert "Retrospectively" in omission.actionable_remedy
    assert "Order STAT" not in omission.actionable_remedy


def test_differential_listing_does_not_filter_or_sort_by_placeholder_probability() -> (
    None
):
    orchestrator = ClinicalReasoningOrchestrator("ddx-order-attack")
    first = orchestrator.propose_hypothesis(
        diagnosis="Ledger-first diagnosis",
        prior_probability=0.01,
        rationale="This candidate was recorded first in the working ledger.",
    )
    second = orchestrator.propose_hypothesis(
        diagnosis="Ledger-second diagnosis",
        prior_probability=0.99,
        rationale="This candidate was recorded second in the working ledger.",
    )

    listed = orchestrator.get_differential_diagnosis(min_probability=0.95)

    assert [item.id for item in listed] == [first.id, second.id]


def test_excluded_explicit_lead_does_not_fall_back_to_another_candidate() -> None:
    orchestrator = ClinicalReasoningOrchestrator("stale-leading-selection-attack")
    selected = orchestrator.propose_hypothesis(
        diagnosis="Explicit lead later excluded",
        prior_probability=0.99,
        rationale="This candidate will be excluded in the regression fixture.",
    )
    orchestrator.propose_hypothesis(
        diagnosis="Remaining active candidate",
        prior_probability=0.01,
        rationale="This candidate must not become leading implicitly.",
    )
    orchestrator.select_leading_hypothesis(
        selected.id.value,
        reason="The fixture first records an explicit auditable working selection.",
        changed_by="test-agent",
    )
    orchestrator.exclude_hypothesis(
        selected.id.value,
        excluded_by="test-agent",
        reason="A later source-linked review excludes the previously selected lead.",
    )

    guidance = orchestrator.get_guidance()
    assert guidance.checklist["leading_hypothesis_id"] == selected.id.value
    assert guidance.checklist["explicit_leading_hypothesis_selected"] is True
    assert guidance.checklist["leading_selection_eligible"] is False
    assert guidance.checklist["leading_diagnosis_challenged"] is False
    assert any(
        "No eligible explicit leading diagnosis" in item
        for item in guidance.missing_prerequisites
    )


def test_swapping_numeric_values_cannot_change_hard_leading_gate() -> None:
    def hypothesis(
        hypothesis_id: str,
        probability: float,
        *,
        has_rule_out: bool,
    ) -> dict[str, object]:
        return {
            "id": hypothesis_id,
            "diagnosis": {"display": hypothesis_id},
            "prior_probability": probability,
            "current_probability": probability,
            "status": "ACTIVE",
            "certainty": "POSSIBLE",
            "likelihood_ratios": [
                {
                    "evidence_id": "EVD-support",
                    "applied_likelihood_ratio": 2.0,
                    "supports": True,
                    "rationale": "Direct supporting relationship",
                    "calibration_status": "SOURCE_CALIBRATED",
                    "calibration_source_ref": "EVD-calibration",
                }
            ],
            "supporting_evidence_ids": ["EVD-support"],
            "contradicting_evidence_ids": [],
            "planned_tests": (
                [
                    {
                        "test_id": f"TST-{hypothesis_id[-1]}",
                        "name": "Adequate rule-out test",
                        "purpose": "RULE_OUT",
                        "target_hypothesis_id": hypothesis_id,
                        "expected_supporting_result": "Predefined positive result",
                        "expected_refuting_result": "Adequate negative result",
                        "status": "PLANNED",
                    }
                ]
                if has_rule_out
                else []
            ),
        }

    payload: dict[str, object] = {
        "leading_hypothesis_id": "HYP-1",
        "hypotheses": [
            hypothesis("HYP-2", 0.99, has_rule_out=False),
            hypothesis("HYP-1", 0.01, has_rule_out=True),
        ],
        "evidence": [
            {
                "id": "EVD-support",
                "verified": True,
                "supports_hypothesis_ids": ["HYP-1", "HYP-2"],
            },
            {
                "id": "EVD-calibration",
                "evidence_type": "LITERATURE",
                "verified": True,
                "verifier": "qualified-reviewer",
                "verification_method": "EXACT_SNIPPET_MATCH",
                "source": {
                    "document_id": "calibration-source",
                    "location": "line 1",
                    "raw_snippet": "Published direct LR calibration.",
                    "extraction_method": "verbatim_quote",
                    "content_hash": "a" * 64,
                },
            },
        ],
    }

    def leading_check(report_payload: dict[str, object]) -> dict[str, object]:
        return next(
            check
            for check in evaluate_final_report_conformance(report_payload)
            if check["code"] == "LEADING_DIAGNOSIS_CHALLENGED"
        )

    before = leading_check(payload)
    swapped = deepcopy(payload)
    swapped_hypotheses = swapped["hypotheses"]
    assert isinstance(swapped_hypotheses, list)
    swapped_hypotheses[0]["current_probability"] = 0.01
    swapped_hypotheses[1]["current_probability"] = 0.99
    after = leading_check(swapped)

    assert before == after
    assert before["status"] == "PASS"
    assert before["refs"] == ["HYP-1"]

    missing_selection = deepcopy(payload)
    missing_selection["leading_hypothesis_id"] = None
    missing_check = leading_check(missing_selection)
    assert missing_check["status"] == "FAIL"
    assert missing_check["refs"] == ["#/leading_hypothesis_id"]

    ineligible_selection = deepcopy(payload)
    ineligible_selection["leading_hypothesis_id"] = "HYP-2"
    ineligible_hypotheses = ineligible_selection["hypotheses"]
    assert isinstance(ineligible_hypotheses, list)
    ineligible_hypotheses[0]["status"] = "EXCLUDED"
    ineligible_check = leading_check(ineligible_selection)
    assert ineligible_check["status"] == "FAIL"
    assert ineligible_check["refs"] == ["HYP-2"]


def test_swapping_numeric_values_cannot_change_guidance_or_fhir_lead() -> None:
    orchestrator = ClinicalReasoningOrchestrator("leading-invariance-attack")
    evidence = orchestrator.add_evidence(
        "Source-linked supporting observation",
        evidence_type="OBSERVATION",
        source_document="case-record.txt",
        source_location="line 1",
        raw_snippet="Source-linked supporting observation",
        extraction_method="verbatim_quote",
        auto_verify=False,
    )
    orchestrator.evidence_store[evidence.id.value] = evidence.mark_verified(
        verifier="SYSTEM_PROVENANCE_VERIFIER",
        verification_method="EXACT_SNIPPET_MATCH",
        matched_lines=[1],
    )
    calibration_source_id = _add_verified_calibration_source(orchestrator)
    first = orchestrator.propose_hypothesis(
        diagnosis="Ledger-first diagnosis",
        prior_probability=0.01,
        rationale="This candidate is the explicitly maintained working lead.",
        planned_tests=[
            {
                "name": "Adequate rule-out test",
                "purpose": "RULE_OUT",
                "expected_supporting_result": "Predefined positive result",
                "expected_refuting_result": "Adequate negative result",
                "status": "PLANNED",
            }
        ],
    )
    second = orchestrator.propose_hypothesis(
        diagnosis="Ledger-second diagnosis",
        prior_probability=0.99,
        rationale="This candidate remains second in the working ledger.",
    )
    for candidate in (first, second):
        orchestrator.link_evidence_to_hypothesis(
            evidence_id=evidence.id.value,
            hypothesis_id=candidate.id.value,
            likelihood_ratio=2.0,
            supports=True,
            rationale="Direct supporting relationship for the regression fixture.",
            calibration_status="SOURCE_CALIBRATED",
            calibration_source_ref=calibration_source_id,
        )
    orchestrator.select_leading_hypothesis(
        first.id.value,
        reason="The planned rule-out test makes this the auditable working lead.",
        changed_by="test-agent",
    )

    before_guidance = orchestrator.get_guidance()
    report = _report_with_conflicting_numeric_order()
    before_fhir = render_contract_report_fhir(report)

    for hypothesis_id, probability in ((first.id.value, 0.99), (second.id.value, 0.01)):
        candidate = orchestrator.hypothesis_store[hypothesis_id]
        orchestrator.hypothesis_store[hypothesis_id] = candidate.model_copy(
            update={"current_probability": probability}
        )
    before_payload = report.model_dump(mode="json")
    before_payload["hypotheses"][0]["current_probability"] = 0.99
    before_payload["hypotheses"][1]["current_probability"] = 0.01
    swapped_report = ContractReport.model_validate(before_payload)

    after_guidance = orchestrator.get_guidance()
    after_fhir = render_contract_report_fhir(swapped_report)

    assert (
        before_guidance.checklist["leading_diagnosis_challenged"]
        == (after_guidance.checklist["leading_diagnosis_challenged"])
    )
    assert before_fhir["conclusion"] == after_fhir["conclusion"]
    assert before_fhir["conclusionCode"] == after_fhir["conclusionCode"]
    assert "Ledger-first diagnosis" in before_fhir["conclusion"]
    extensions = {item["url"]: item for item in before_fhir["extension"]}
    assert (
        extensions[
            "urn:rootcause-mcp:StructureDefinition/diagnostic-ordering-semantics"
        ]["valueCode"]
        == "EXPLICIT_LEAD_THEN_WORKING_LEDGER_ORDER"
    )
    assert (
        extensions[
            "urn:rootcause-mcp:StructureDefinition/clinical-probability-established"
        ]["valueBoolean"]
        is False
    )


@pytest.mark.asyncio
async def test_ddx_machine_responses_label_numeric_compatibility_and_do_not_filter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ROOTCAUSE_DATA_DIR", str(tmp_path))
    state = ServerState()
    handler = DDHandlers(state)
    session_id = "machine-semantics-attack"

    first = await handler.handle_propose_hypothesis(
        {
            "session_id": session_id,
            "diagnosis": "Ledger-first diagnosis",
            "prior_probability": 0.01,
            "clinical_reasoning": "The candidate remains mechanistically plausible.",
        }
    )
    second = await handler.handle_propose_hypothesis(
        {
            "session_id": session_id,
            "diagnosis": "Ledger-second diagnosis",
            "prior_probability": 0.99,
            "clinical_reasoning": "The candidate remains mechanistically plausible.",
        }
    )
    for result in (first, second):
        assert result["probability_semantics"] == ("UNCALIBRATED_COMPATIBILITY_ONLY")
        assert result["clinical_probability_established"] is False

    listed = await handler.handle_get_differential_diagnosis(
        {"session_id": session_id, "min_probability": 0.95}
    )
    assert [item["id"]["value"] for item in listed["hypotheses"]] == [
        first["hypothesis_id"],
        second["hypothesis_id"],
    ]
    assert listed["ordering_semantics"] == "WORKING_LEDGER_ORDER"
    assert listed["leading_hypothesis_id"] is None
    assert all(not item["is_explicit_leading"] for item in listed["hypotheses"])
    assert all(
        item["probability_semantics"] == "UNCALIBRATED_COMPATIBILITY_ONLY"
        and item["clinical_probability_established"] is False
        for item in listed["hypotheses"]
    )

    selected = await handler.handle_select_leading_hypothesis(
        {
            "session_id": session_id,
            "hypothesis_id": second["hypothesis_id"],
            "reason": "This is an explicit audited selection independent of numerics.",
            "changed_by": "test-agent",
        }
    )
    assert selected["status"] == "success"
    listed_after_selection = await handler.handle_get_differential_diagnosis(
        {"session_id": session_id, "min_probability": 0.999}
    )
    assert listed_after_selection["leading_hypothesis_id"] == second["hypothesis_id"]
    assert [item["id"]["value"] for item in listed_after_selection["hypotheses"]] == [
        first["hypothesis_id"],
        second["hypothesis_id"],
    ]
    assert [
        item["id"]["value"]
        for item in listed_after_selection["hypotheses"]
        if item["is_explicit_leading"]
    ] == [second["hypothesis_id"]]
    assert listed["probability_semantics"] == "UNCALIBRATED_COMPATIBILITY_ONLY"
    assert listed["clinical_probability_established"] is False


def test_compact_text_never_echoes_numeric_posterior() -> None:
    from rootcause_mcp.server_v2 import _compact_structured_text

    compact = _compact_structured_text(
        {
            "status": "success",
            "posterior_probability": 0.99,
            "probability_semantics": "UNCALIBRATED_COMPATIBILITY_ONLY",
            "clinical_probability_established": False,
        }
    )

    assert "0.99" not in compact
    assert "posterior_probability" not in compact
    assert "UNCALIBRATED_COMPATIBILITY_ONLY" in compact
    assert '"clinical_probability_established":false' in compact


def test_full_reports_hide_legacy_reasoning_root_causation_and_hfacs_percentages() -> (
    None
):
    report = _report_with_conflicting_numeric_order()
    report.reasoning_chain[0]["confidence"] = 0.91
    report.thinking_chain = [
        {
            "thinking_type": "BIAS_IDENTIFIED",
            "content": "Anchoring was reviewed.",
            "internal_reasoning": "A competing mechanism remains open.",
            "confidence": 0.82,
        }
    ]
    report.root_causes = [
        {
            "id": "cause-1",
            "answer": "Proposed process contributor",
            "confidence": 0.73,
            "evidence": [],
            "causation_result": "INSUFFICIENT_DATA",
            "disposition": "PROPOSED",
        }
    ]
    report.causation_verifications = [
        {
            "verification_id": "ver-1",
            "cause_event": {"id": "cause-1", "description": "Cause"},
            "effect_event": {"description": "Effect"},
            "overall_result": "INSUFFICIENT_DATA",
            "audit_scope": "CONSERVATIVE_CAUSATION_AUDIT",
            "clinical_causality_established": False,
            "confidence": {"value": 0.64},
        }
    ]
    report.hfacs_classifications = [
        {
            "cause": "Proposed process contributor",
            "hfacs_code": "UA.DM",
            "confidence": 0.88,
            "source": "keyword_rule",
        }
    ]

    rendered = (
        render_contract_report_markdown(report, detail_level="full"),
        render_contract_report_markdown(
            report,
            detail_level="full",
            locale="zh-TW",
            audience="clinician",
        ),
    )
    for output in rendered:
        for fabricated in ("91%", "82%", "73%", "64%", "88%"):
            assert fabricated not in output
        assert "classic hallmark" not in output

    fhir = render_contract_report_fhir(report)
    for extension in fhir["extension"]:
        if extension["url"].endswith(
            ("/root-cause", "/causation-verification", "/hfacs-classification")
        ):
            nested_urls = {item["url"] for item in extension["extension"]}
            assert "confidence" not in nested_urls
            assert "confidenceSemantics" in nested_urls


def test_causation_audit_does_not_fabricate_numeric_confidence() -> None:
    result = CausationValidator().validate(
        CauseEvent(
            description="Later event proposed as cause",
            timestamp=datetime(2026, 8, 18, 10, 5, tzinfo=UTC),
        ),
        CauseEvent(
            description="Earlier effect",
            timestamp=datetime(2026, 8, 18, 10, 0, tzinfo=UTC),
        ),
    )

    assert result.confidence is None
    assert result.tests.necessity is None


def test_thinking_tool_schemas_do_not_require_or_default_confidence() -> None:
    from rootcause_mcp.interface.tools import get_all_tools

    tools = {
        tool.name: tool
        for profile in ("all", "condensed")
        for tool in get_all_tools(profile)
        if tool.name in {"rc_think_aloud", "rc_thinking"}
    }
    assert set(tools) == {"rc_think_aloud", "rc_thinking"}
    for tool in tools.values():
        confidence = tool.input_schema["properties"]["confidence"]
        assert "default" not in confidence
        assert "confidence" not in tool.input_schema.get("required", [])
