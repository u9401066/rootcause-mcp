"""Regression tests for generated Mermaid analysis artifacts."""

from rootcause_mcp.application.clinical_reasoning_orchestrator import (
    ClinicalReasoningOrchestrator,
)
from rootcause_mcp.domain.entities.fishbone import Fishbone, FishboneCause
from rootcause_mcp.domain.entities.reasoning_step import (
    ReasoningChain,
    ReasoningStep,
    ReasoningStepType,
)
from rootcause_mcp.domain.entities.why_node import CausalLink, WhyChain, WhyNode
from rootcause_mcp.domain.value_objects.enums import (
    CausalLinkType,
    FishboneCategoryType,
)
from rootcause_mcp.domain.value_objects.identifiers import CauseId, SessionId
from rootcause_mcp.interface.mermaid import (
    build_evidence_graph,
    build_timeline,
    escape_mermaid_label,
    render_fishbone_mermaid,
    render_reasoning_chain_mermaid,
    render_timeline_mermaid,
    render_timeline_table,
    render_why_tree_mermaid,
)


def test_mermaid_label_escapes_node_delimiters() -> None:
    malicious = 'Finding"]:::rootcause\nEVIL --> NODE)'

    escaped = escape_mermaid_label(malicious)

    assert '"]:::rootcause' not in escaped
    assert "&#93;:::rootcause" in escaped
    assert "NODE&#41;" in escaped
    assert "\n" not in escaped


def test_evidence_graph_tracks_contradictions_causes_and_safe_labels() -> None:
    orchestrator = ClinicalReasoningOrchestrator("graph-case")
    evidence = orchestrator.add_evidence(
        content='Troponin "normal" & ECG < threshold',
        source_document="lab & ECG.txt",
    )
    hypothesis = orchestrator.propose_hypothesis(
        diagnosis="Acute myocardial infarction",
        prior_probability=0.3,
        rationale="Chest pain requires exclusion of acute myocardial infarction.",
    )
    orchestrator.link_evidence_to_hypothesis(
        evidence_id=evidence.id.value,
        hypothesis_id=hypothesis.id.value,
        likelihood_ratio=5.0,
        supports=False,
        rationale="Normal serial tests argue against acute myocardial infarction.",
    )
    linked_evidence = orchestrator.evidence_store[evidence.id.value].link_to_cause(
        "c_monitoring_gap"
    )
    orchestrator.evidence_store[evidence.id.value] = linked_evidence

    graph = build_evidence_graph(
        orchestrator.evidence_store.values(),
        orchestrator.hypothesis_store.values(),
    )

    relationships = {edge["relationship"] for edge in graph["edges"]}
    assert relationships == {"contradicts", "supports_cause"}
    assert graph["mermaid"].startswith("```mermaid\nflowchart LR")
    assert "&quot;normal&quot; &amp; ECG &lt; threshold" in graph["mermaid"]
    assert 'N1 -. "contradicts" .-> N2' in graph["mermaid"]


def test_evidence_graph_omits_dangling_and_duplicate_edges() -> None:
    orchestrator = ClinicalReasoningOrchestrator("graph-integrity")
    evidence = orchestrator.add_evidence("Objective finding")
    hypothesis = orchestrator.propose_hypothesis(
        diagnosis="Pneumonia",
        rationale="Objective findings could support an infectious diagnosis.",
    )
    corrupt_evidence = evidence.model_copy(
        update={
            "supports_hypothesis_ids": [
                hypothesis.id.value,
                hypothesis.id.value,
                "HYP-missing",
            ]
        }
    )

    graph = build_evidence_graph([corrupt_evidence], [hypothesis])

    assert graph["edges"] == [
        {
            "source": evidence.id.value,
            "target": hypothesis.id.value,
            "relationship": "supports",
        }
    ]
    assert len(graph["warnings"]) == 1
    assert "HYP-missing" in graph["warnings"][0]


def test_fishbone_mermaid_has_spine_subcauses_and_safe_labels() -> None:
    session_id = SessionId.generate()
    fishbone = Fishbone.create(
        session_id=session_id,
        problem_statement='Dose "10x" & response < 5 minutes',
    )
    fishbone.add_cause_to_category(
        FishboneCategoryType.PROCESS,
        FishboneCause(
            cause_id=CauseId.generate(),
            category=FishboneCategoryType.PROCESS,
            description='No "independent" double check & alert',
            sub_causes=["Policy < current standard"],
            hfacs_code="OI-OP",
            verified=True,
        ),
    )

    diagram = render_fishbone_mermaid(fishbone)

    assert diagram.startswith("```mermaid\nflowchart LR")
    assert "S0 ==> S1" in diagram
    assert "S1 ==> S2" in diagram
    assert "S2 ==> HEAD" in diagram
    assert "PERS --> S0" in diagram
    assert "PROC --> S0" in diagram
    assert "PROC_C1_S1" in diagram
    assert "&quot;10x&quot; &amp; response &lt; 5 minutes" in diagram
    assert "No &quot;independent&quot; double check &amp; alert" in diagram


def test_why_tree_mermaid_merges_direct_cross_link() -> None:
    session_id = SessionId.generate()
    first = WhyNode.create_first_why(
        session_id=session_id,
        initial_problem="Delayed escalation",
        answer='Team missed "shock" & lactate < threshold',
    )
    second = WhyNode.create_follow_up_why(
        session_id=session_id,
        parent=first,
        answer="No escalation trigger",
    )
    second.mark_as_root_cause(0.8)
    link = CausalLink(
        source_id=first.id,
        target_id=second.id,
        relationship=CausalLinkType.CONTRIBUTES_TO,
        strength=0.7,
    )
    second_link = CausalLink(
        source_id=first.id,
        target_id=second.id,
        relationship=CausalLinkType.ESCALATES,
        strength=0.4,
    )
    chain = WhyChain(
        session_id=session_id,
        initial_problem="Delayed escalation",
        nodes=[first, second],
        causal_links=[link, second_link],
    )

    diagram = render_why_tree_mermaid(chain)

    assert diagram.startswith("```mermaid\nflowchart TB")
    assert 'N1 -->|"Why 2<br/>contributes_to 70%<br/>escalates 40%"| N2' in diagram
    assert 'N1 -. "contributes_to<br/>70%" .-> N2' not in diagram
    assert 'N1 -. "escalates<br/>40%" .-> N2' not in diagram
    assert "&quot;shock&quot; &amp; lactate &lt; threshold" in diagram


def test_reasoning_mermaid_handles_empty_chain_and_zero_confidence() -> None:
    chain = ReasoningChain(session_id="reasoning-graph")
    assert 'EMPTY["No reasoning steps recorded"]' in render_reasoning_chain_mermaid(
        chain
    )

    chain.add_step(
        ReasoningStep(
            sequence_number=1,
            step_type=ReasoningStepType.REFLECTION,
            content='Reconsider "anchor" & threshold < target',
            rationale="Conflicting evidence remains unresolved.",
            evidence_ids=["EVD-1"],
            hypothesis_ids=["HYP-1"],
            agent_id="test-agent",
            confidence=0.0,
        )
    )
    diagram = render_reasoning_chain_mermaid(chain)

    assert "Confidence: 0%" in diagram
    assert "&quot;anchor&quot; &amp; threshold &lt; target" in diagram
    assert 'E1["Evidence<br/>EVD-1"]' in diagram
    assert 'H1["Hypothesis<br/>HYP-1"]' in diagram


def test_timeline_mermaid_renders_phases_and_timestamps() -> None:
    orchestrator = ClinicalReasoningOrchestrator("timeline-case")
    orchestrator.add_evidence(
        content="08:00 Baseline BP 165/90, HR 85, Grade 2/6 murmur",
        source_document="preop.txt",
    )
    orchestrator.add_evidence(
        content="08:05 Induction with Propofol 80mg, Fentanyl 100mcg",
        source_document="anesthesia.csv",
    )
    orchestrator.add_evidence(
        content="08:18 CRASH BP 35/15, HR 160 following Epinephrine bolus",
        source_document="anesthesia.csv",
    )
    orchestrator.add_evidence(
        content="08:20 Emergency TEE shows Dagger-shaped Doppler >80mmHg",
        source_document="tee.txt",
    )

    tl_data = build_timeline(orchestrator.evidence_store.values())

    assert len(tl_data["events"]) == 4
    diagram = tl_data["mermaid"]
    assert diagram.startswith("```mermaid\ntimeline")
    assert "section 1. Baseline &amp; Pre-Op" in diagram
    assert "section 2. Induction &amp; Surgical Events" in diagram
    assert "section 3. Crisis Progression &amp; Deterioration" in diagram
    assert "section 4. Diagnostic Findings &amp; Rule-Outs" in diagram
    assert "08:00 : 08 -00 Baseline BP 165/90, HR 85, Grade 2/6 murmur" in diagram
    assert "08:18 : 08 -18 CRASH BP 35/15, HR 160 following Epinephrine bolus" in diagram

    table = tl_data["table"]
    assert "| `08:00` | **1. Baseline & Pre-Op** |" in table
    assert "| `08:20` | **4. Diagnostic Findings & Rule-Outs** |" in table


def test_timeline_mermaid_handles_empty_evidence() -> None:
    tl_data = build_timeline([])
    assert len(tl_data["events"]) == 0
    assert "No timeline events recorded" in tl_data["mermaid"]
    assert "No timeline events recorded" in tl_data["table"]
