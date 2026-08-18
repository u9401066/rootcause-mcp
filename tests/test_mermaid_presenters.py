"""Regression tests for generated Mermaid analysis artifacts."""

from datetime import UTC, datetime

import pytest

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
    render_why_tree_mermaid,
    validate_mermaid_syntax,
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
        likelihood_ratio=0.2,
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
    assert (
        "08:18 : 08 -18 CRASH BP 35/15, HR 160 following Epinephrine bolus" in diagram
    )

    table = tl_data["table"]
    assert "| `08:00` | **1. Baseline & Pre-Op** |" in table
    assert "| `08:20` | **4. Diagnostic Findings & Rule-Outs** |" in table


def test_timeline_mermaid_handles_empty_evidence() -> None:
    tl_data = build_timeline([])
    assert len(tl_data["events"]) == 0
    assert "No timeline events recorded" in tl_data["mermaid"]
    assert "No timeline events recorded" in tl_data["table"]


def test_timeline_uses_canonical_event_timestamp_for_cross_source_order() -> None:
    orchestrator = ClinicalReasoningOrchestrator("cross-source-time")
    later = orchestrator.add_evidence(
        content="Baseline label should not override the actual event time",
        source_document="late-note.txt",
        event_timestamp=datetime(2026, 8, 17, 8, 20, tzinfo=UTC),
    )
    earlier = orchestrator.add_evidence(
        content="Collapse label should not override the actual event time",
        source_document="early-device.log",
        event_timestamp=datetime(2026, 8, 17, 8, 5, tzinfo=UTC),
    )

    timeline = build_timeline(orchestrator.evidence_store.values())

    assert [event["id"] for event in timeline["events"]] == [
        earlier.id.value,
        later.id.value,
    ]


def test_validate_mermaid_syntax_auto_fix_and_diagnostics() -> None:
    """Mermaid syntax validator should detect issues and auto-fix formatting."""
    # Test 1: Flowchart with unclosed subgraph and unescaped quotes
    bad_flowchart = """
    subgraph Main Process
        A["Step 1: Administer "Drug A" now"] -> B["Step 2: Check vitals"]
    """
    res1 = validate_mermaid_syntax(
        bad_flowchart, diagram_type="flowchart", auto_fix=True
    )
    assert res1["is_valid"] is True
    assert res1["diagram_type"] == "flowchart"
    assert "&quot;Drug A&quot;" in res1["sanitized_mermaid"]
    assert "-->" in res1["sanitized_mermaid"]
    assert "end" in res1["sanitized_mermaid"]

    # Test 2: Timeline with extra colons in event description
    bad_timeline = """
    timeline
        title Patient Deterioration
        section Day 1
            08:00 : BP: 120/80, HR: 85 bpm
    """
    res2 = validate_mermaid_syntax(bad_timeline, auto_fix=True)
    assert res2["is_valid"] is True
    assert res2["diagram_type"] == "timeline"
    assert "BP - 120/80, HR - 85 bpm" in res2["sanitized_mermaid"]


def test_timeline_patterns_delayed_diagnosis_and_barrier_failure() -> None:
    """Timeline builder should classify events according to specific clinical patterns."""
    # Pattern 1: Delayed Diagnosis
    rad_events = [
        {"time": "2024/01/05", "content": "OPD visit, arranged chest CT scan"},
        {
            "time": "2024/01/07",
            "content": "CT completed, found 2.5cm mass in RUL (Critical Finding)",
        },
        {
            "time": "14:01",
            "content": "Report faxed to nursing station, placed on physician desk",
        },
        {"time": "44 days blank", "content": "Patient unaware, progression of cough"},
        {"time": "2024/02/20", "content": "Patient presented to ER with hemoptysis"},
    ]
    tl_diag = build_timeline(pattern="delayed_diagnosis", custom_events=rad_events)
    assert len(tl_diag["events"]) == 5
    phases = [ev["phase"] for ev in tl_diag["events"]]
    assert "1. Initial Contact & Testing Order" in phases
    assert "2. Diagnostic Test & Result Generation" in phases
    assert "3. Communication Gap & Missed Opportunity" in phases
    assert "5. Symptom Flare & Crisis Discovery" in phases

    # Pattern 2: Barrier Failure
    med_events = [
        {"time": "14:00", "content": "Order written: Hold Clexane for 24h"},
        {"time": "09:00", "content": "Pharmacy MAR: Order expired and not renewed"},
        {
            "time": "16:00",
            "content": "Nursing record: Patient bilateral calf pain and leg swelling",
        },
        {"time": "11:30", "content": "Chest tightness and sudden desaturation to 85%"},
    ]
    tl_barrier = build_timeline(pattern="barrier_failure", custom_events=med_events)
    assert len(tl_barrier["events"]) == 4
    b_phases = [ev["phase"] for ev in tl_barrier["events"]]
    assert "1. Prescribing & Ordering Phase" in b_phases
    assert "2. Dispensing & Pharmacy Barrier" in b_phases
    assert "3. Administration & Nursing Barrier" in b_phases


@pytest.mark.asyncio
async def test_verification_handlers_diagram_and_timeline_tools() -> None:
    """VerificationHandlers should execute rc_validate_diagram and rc_render_timeline."""
    from rootcause_mcp.application.server_state import ServerState
    from rootcause_mcp.interface.handlers.evidence_handlers import EvidenceHandlers
    from rootcause_mcp.interface.handlers.verification_handlers import (
        VerificationHandlers,
    )

    state = ServerState()
    ev_handler = EvidenceHandlers(state)
    v_handler = VerificationHandlers(server_state=state)

    session_id = "v-handler-test-01"
    await ev_handler.handle(
        "rc_add_evidence",
        {
            "session_id": session_id,
            "content": "08:00 Baseline BP 160/90",
            "source_document": "chart.txt",
        },
    )

    # Tool 1: rc_validate_diagram
    val_res = await v_handler.handle(
        "rc_validate_diagram",
        {
            "mermaid_source": 'A["Test "Epi" Crash"] -> B',
            "diagram_type": "flowchart",
            "auto_fix": True,
        },
    )
    assert val_res["status"] == "success"
    assert val_res["is_valid"] is True
    assert "&quot;Epi&quot;" in val_res["sanitized_mermaid"]
    assert "```mermaid" in val_res["preview_markdown"]

    # Tool 2: rc_render_timeline
    tl_res = await v_handler.handle(
        "rc_render_timeline",
        {
            "session_id": session_id,
            "pattern": "perioperative_sequence",
        },
    )
    assert tl_res["status"] == "success"
    assert tl_res["total_events"] >= 1
    assert "timeline" in tl_res["mermaid"]
