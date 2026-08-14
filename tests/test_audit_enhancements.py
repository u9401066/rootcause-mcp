"""
Comprehensive Tests for Core Architectural Enhancements:
1. SQLiteWhyTreeRepository persistent storage and rehydration.
2. ClinicalGapAnalyzer diagnostic contradiction & guideline gap detection.
3. CaseCheckpointService state snapshotting and restoration.
4. rc_detect_conflicts, rc_create_checkpoint, rc_restore_checkpoint, rc_list_checkpoints tool handlers.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from rootcause_mcp.application.clinical_reasoning_orchestrator import (
    ClinicalReasoningOrchestrator,
)
from rootcause_mcp.application.server_state import ServerState
from rootcause_mcp.domain.entities.why_node import CausalLink, WhyNode
from rootcause_mcp.domain.services.gap_analyzer import (
    ClinicalGapAnalyzer,
)
from rootcause_mcp.domain.value_objects.enums import CausalLinkType
from rootcause_mcp.domain.value_objects.identifiers import SessionId
from rootcause_mcp.infrastructure.persistence.database import Database
from rootcause_mcp.infrastructure.persistence.why_tree_repository import (
    SQLiteWhyTreeRepository,
)
from rootcause_mcp.interface.handlers.dd_handlers import DDHandlers
from rootcause_mcp.interface.handlers.evidence_handlers import EvidenceHandlers
from rootcause_mcp.interface.handlers.reasoning_handlers import ReasoningHandlers


def test_sqlite_why_tree_repository_persistence_and_rehydration(tmp_path: Path) -> None:
    """Why trees, nodes, and causal links should persist to SQLite and reload accurately."""
    db_file = tmp_path / "test_why_tree.db"
    db = Database(db_file)
    db.create_tables()

    repo = SQLiteWhyTreeRepository(db)
    session_id = SessionId("rc_sess_why_persist_01")

    # Create and populate why chain
    chain = repo.create_chain(session_id, initial_problem="Intraoperative Severe Shock")
    node1 = WhyNode.create_first_why(
        session_id=session_id,
        initial_problem="Intraoperative Severe Shock",
        answer="Dynamic LVOT gradient developed post-induction",
    )
    node2 = WhyNode.create_follow_up_why(
        session_id=session_id,
        parent=node1,
        answer="Epinephrine bolus was administered in hyperdynamic underfilled LV",
    )
    node2.mark_as_root_cause(confidence=0.95)

    chain.add_node(node1)
    chain.add_node(node2)
    chain.add_causal_link(
        CausalLink(
            source_id=node2.id,
            target_id=node1.id,
            relationship=CausalLinkType.ESCALATES,
            strength=0.90,
            note="Positive inotropy escalates dynamic obstruction",
        )
    )
    repo.save_chain(chain)

    # Reopen a fresh repository instance from the same SQLite DB file
    db_reopened = Database(db_file)
    reopened_repo = SQLiteWhyTreeRepository(db_reopened)

    loaded_chain = reopened_repo.get_chain(session_id)
    assert loaded_chain is not None
    assert loaded_chain.initial_problem == "Intraoperative Severe Shock"
    assert len(loaded_chain.nodes) == 2
    assert len(loaded_chain.causal_links) == 1
    assert loaded_chain.nodes[1].is_root_cause is True
    assert loaded_chain.nodes[1].confidence is not None
    assert loaded_chain.nodes[1].confidence.value == 0.95
    assert loaded_chain.causal_links[0].relationship == CausalLinkType.ESCALATES

    # Test get_node
    single_node = reopened_repo.get_node(node1.id)
    assert single_node is not None
    assert single_node.answer == "Dynamic LVOT gradient developed post-induction"

    # Test delete_chain
    assert reopened_repo.delete_chain(session_id) is True
    assert reopened_repo.get_chain(session_id) is None


def test_clinical_gap_analyzer_detects_contradictions_and_guideline_gaps() -> None:
    """ClinicalGapAnalyzer should surface diagnostic contradictions, paradoxical responses, and gaps."""
    orch = ClinicalReasoningOrchestrator("gap-test-session")

    # 1. Add paradoxical inotrope collapse evidence
    ev1 = orch.add_evidence(
        content="Patient blood pressure dropped further to 35/15 after Epinephrine 50mcg bolus (worsening with epi)",
        source_document="anesthesia.csv",
    )
    # 2. Add MTP transfusion evidence without potassium check
    orch.add_evidence(
        content="Massive transfusion protocol MTP cooler with Unit #7 PRBC transfused rapidly",
        source_document="trauma_log.txt",
    )
    # 3. Add high dose propofol evidence without lipid panel
    orch.add_evidence(
        content="Continuous high dose propofol infusion 60 ml/hr (8 mg/kg/hr) for >48h",
        source_document="icu_flowsheet.csv",
    )

    # Propose Hypovolemia as leading diagnosis (P=0.80) with conflicting evidence
    hyp1 = orch.propose_hypothesis(
        diagnosis="Isolated Hypovolemia",
        prior_probability=0.80,
        rationale="Low BP assumed to be hypovolemia",
    )
    orch.link_evidence_to_hypothesis(
        evidence_id=ev1.id.value,
        hypothesis_id=hyp1.id.value,
        likelihood_ratio=0.10,
        supports=False,
        rationale="Hypovolemia does not crash further with inotropes",
    )

    report = ClinicalGapAnalyzer.analyze(
        session_id="gap-test-session",
        evidence_store=orch.evidence_store,
        hypothesis_store=orch.hypothesis_store,
        thinking_chain=orch.thinking_chain,
        reasoning_chain=orch.reasoning_chain,
    )

    assert report.total_conflicts >= 3
    assert report.safety_invariants_met is False

    categories = [c.category for c in report.conflicts]
    assert "DIAGNOSTIC_CONTRADICTION" in categories
    assert "PARADOXICAL_RESPONSE" in categories
    assert "GUIDELINE_GAP" in categories

    # Verify specific alerts
    alert_text = " ".join(report.guideline_alerts)
    assert "MTP Safety Alert" in alert_text
    assert "PRIS Safety Alert" in alert_text


@pytest.mark.asyncio
async def test_case_checkpoint_service_and_handlers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Case checkpoints should create immutable JSON snapshots and restore them seamlessly."""
    monkeypatch.setenv("ROOTCAUSE_DATA_DIR", str(tmp_path))

    state = ServerState()
    ev_handler = EvidenceHandlers(state)
    dd_handler = DDHandlers(state)
    reason_handler = ReasoningHandlers(state)

    session_id = "checkpoint-test-sess"

    # 1. Build initial case state
    res_ev = await ev_handler.handle(
        "rc_add_evidence",
        {
            "session_id": session_id,
            "content": "08:18 CRASH BP 35/15",
            "source_document": "chart.txt",
        },
    )
    res_h = await dd_handler.handle(
        "rc_propose_hypothesis",
        {
            "session_id": session_id,
            "diagnosis": "Dynamic LVOT Obstruction (SAM)",
            "clinical_reasoning": "Paradoxical inotrope response",
            "prior_probability": 0.35,
        },
    )
    await dd_handler.handle(
        "rc_link_evidence_to_hypothesis",
        {
            "session_id": session_id,
            "hypothesis_id": res_h["hypothesis_id"],
            "evidence_id": res_ev["evidence_id"],
            "likelihood_ratio": 15.0,
            "supports": True,
        },
    )

    # 2. Create checkpoint
    cp_res = await reason_handler.handle(
        "rc_create_checkpoint",
        {
            "session_id": session_id,
            "tag": "after_tee_confirmation",
            "notes": "Snapshot before deciding on surgical cancelation",
        },
    )
    assert cp_res["status"] == "success"
    checkpoint_id = cp_res["checkpoint_id"]
    assert "after_tee_confirmation" in checkpoint_id
    assert cp_res["evidence_count"] == 1
    assert cp_res["hypothesis_count"] == 1
    assert "sha256:" in cp_res["content_hash"]

    # 3. List checkpoints
    list_res = await reason_handler.handle(
        "rc_list_checkpoints",
        {"session_id": session_id},
    )
    assert list_res["status"] == "success"
    assert list_res["total_checkpoints"] == 1
    assert list_res["checkpoints"][0]["checkpoint_id"] == checkpoint_id

    # 4. Mutate state (add conflicting hypothesis)
    await dd_handler.handle(
        "rc_propose_hypothesis",
        {
            "session_id": session_id,
            "diagnosis": "Alternative Diagnosis",
            "clinical_reasoning": "Test mutation",
        },
    )
    orch = await state.get_orchestrator(session_id)
    assert orch is not None
    assert len(orch.hypothesis_store) == 2

    # 5. Restore from checkpoint
    restore_res = await reason_handler.handle(
        "rc_restore_checkpoint",
        {
            "session_id": session_id,
            "checkpoint_id": checkpoint_id,
        },
    )
    assert restore_res["status"] == "success"
    assert restore_res["restored_hypothesis_count"] == 1
    assert restore_res["top_diagnosis"] == "Dynamic LVOT Obstruction (SAM)"

    # Verify orchestrator in state is restored
    restored_orch = await state.get_orchestrator(session_id)
    assert restored_orch is not None
    assert len(restored_orch.hypothesis_store) == 1
    assert (
        "Dynamic LVOT Obstruction (SAM)"
        in next(iter(restored_orch.hypothesis_store.values())).diagnosis.display
    )
