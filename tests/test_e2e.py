"""
End-to-End test for complete clinical reasoning workflow.

Tests the full pipeline:
1. Add evidence
2. Propose hypotheses
3. Link evidence to hypotheses (Bayesian update)
4. Record thinking process
5. Generate CONTRACT report
"""

import pytest

from rootcause_mcp.interface.handlers import (
    ContractHandlers,
    DDHandlers,
    EvidenceHandlers,
    ReasoningHandlers,
    ThinkingHandlers,
)


@pytest.mark.asyncio
async def test_complete_clinical_reasoning_workflow():
    """Test complete end-to-end clinical reasoning workflow."""
    
    # Initialize shared state
    from rootcause_mcp.application.server_state import ServerState
    server_state = ServerState()
    
    # Initialize handlers with shared state
    thinking_handler = ThinkingHandlers()
    evidence_handler = EvidenceHandlers(server_state)
    dd_handler = DDHandlers(server_state)
    reasoning_handler = ReasoningHandlers()
    contract_handler = ContractHandlers(server_state)
    
    session_id = "e2e_test_session"
    
    # Step 1: Add evidence
    evd1 = await evidence_handler.handle("rc_add_evidence", {
        "session_id": session_id,
        "content": "08:30 BP 75/40 mmHg, HR 120 bpm",
        "evidence_type": "DOCUMENT",
        "source_document": "nursing_flowsheet.csv",
        "source_location": "Line 42",
        "clinical_strength": "STRONG",
        "source_reliability": "GRADE_A",
    })
    assert evd1["status"] == "success"
    assert "evidence_id" in evd1
    
    # Step 2: Record thinking process
    think1 = await thinking_handler.handle("rc_think_aloud", {
        "session_id": session_id,
        "thinking_type": "HYPOTHESIS_CONSIDERED",
        "content": "Considering cardiogenic shock",
        "internal_reasoning": "Post-CABG patient with hypotension and tachycardia",
        "confidence": 0.7,
        "alternatives": [
            {
                "alternative": "Septic shock",
                "reason_rejected": "No fever, WBC normal",
                "confidence_if_chosen": 0.3,
            }
        ],
    })
    assert think1["status"] == "success"
    
    # Step 3: Propose hypothesis
    hyp1 = await dd_handler.handle("rc_propose_hypothesis", {
        "session_id": session_id,
        "diagnosis": "Cardiogenic shock",
        "icd10_code": "R57.0",
        "prior_probability": 0.3,
        "clinical_reasoning": "Recent CABG, hypotension, on vasopressors",
        "differential_diagnoses_considered": [
            {
                "diagnosis": "Septic shock",
                "reason_rejected": "No fever, WBC normal",
                "likelihood_if_not_rejected": "low",
            }
        ],
        "evidence_supporting": [evd1["evidence_id"]],
        "uncertainty_factors": ["Troponin pending", "Echo not done yet"],
        "confidence_rationale": "Moderate confidence due to typical presentation but pending labs",
    })
    assert hyp1["status"] == "success"
    assert "hypothesis_id" in hyp1
    
    # Step 4: Link evidence to hypothesis (Bayesian update)
    link1 = await dd_handler.handle("rc_link_evidence_to_hypothesis", {
        "session_id": session_id,
        "evidence_id": evd1["evidence_id"],
        "hypothesis_id": hyp1["hypothesis_id"],
        "likelihood_ratio": 5.0,
        "supports": True,
        "rationale": "Hypotension strongly supports cardiogenic shock in post-CABG patient",
    })
    assert link1["status"] == "success"
    assert link1["posterior_probability"] > 0.3  # Prior was 0.3

    # Step 5: Get differential diagnosis
    ddx = await dd_handler.handle("rc_get_differential_diagnosis", {
        "session_id": session_id,
        "status_filter": "ACTIVE",
        "min_probability": 0.01,
    })
    assert ddx["status"] == "success"
    assert len(ddx["hypotheses"]) > 0
    
    # Step 6: Generate CONTRACT report
    report = await contract_handler.handle("rc_generate_contract_report", {
        "session_id": session_id,
        "format": "json",
        "finalize": True,
        "include_reasoning_chain": True,
        "include_evidence_graph": True,
        "include_quality_metrics": True,
    })
    assert report["status"] == "success"
    assert "output_path" in report


@pytest.mark.asyncio
async def test_persistence_layer():
    """Test persistence layer functionality."""
    from rootcause_mcp.infrastructure.persistence.evidence_repository import (
        SQLiteEvidenceRepository,
    )
    from rootcause_mcp.infrastructure.persistence.hypothesis_repository import (
        SQLiteHypothesisRepository,
    )
    from rootcause_mcp.infrastructure.persistence.thinking_chain_repository import (
        SQLiteThinkingChainRepository,
    )
    
    # Initialize repositories (None for in-memory)
    evidence_repo = SQLiteEvidenceRepository(None)
    hypothesis_repo = SQLiteHypothesisRepository(None)
    thinking_repo = SQLiteThinkingChainRepository(None)
    
    assert evidence_repo is not None
    assert hypothesis_repo is not None
    assert thinking_repo is not None


@pytest.mark.asyncio
async def test_contract_report_vo():
    """Test ContractReport value object."""
    from rootcause_mcp.domain.value_objects.contract_report import (
        ContractReport,
        EvidenceCoverageMetrics,
        ReasoningQualityMetrics,
    )
    
    # Create metrics
    evidence_metrics = EvidenceCoverageMetrics(
        total_evidence=10,
        verified_evidence=7,
        strong_evidence=5,
        moderate_evidence=3,
        weak_evidence=2,
    )
    
    reasoning_metrics = ReasoningQualityMetrics(
        total_steps=15,
        avg_confidence=0.75,
        hypothesis_coverage=0.8,
        evidence_coverage=0.9,
        decision_points=3,
        alternatives_considered=5,
        biases_identified=2,
        uncertainties_acknowledged=4,
    )
    
    # Create report
    report = ContractReport(
        report_id="RPT-001",
        session_id="test_session",
        generated_by="test_agent",
        evidence_metrics=evidence_metrics,
        reasoning_metrics=reasoning_metrics,
    )
    
    assert report.report_id == "RPT-001"
    assert not report.is_finalized
    
    # Finalize report
    report.finalize("test_reviewer")
    assert report.is_finalized
    assert report.content_hash is not None
    
    # Test FHIR export
    fhir = report.to_fhir()
    assert fhir["resourceType"] == "DiagnosticReport"
    assert fhir["status"] == "final"
