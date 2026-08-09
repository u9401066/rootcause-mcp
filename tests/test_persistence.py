"""
Test real persistence with SQLite.

Verifies that data survives across sessions.
"""

from pathlib import Path

import pytest

from rootcause_mcp.domain.entities.evidence import (
    Evidence,
    EvidenceSource,
    EvidenceType,
)
from rootcause_mcp.domain.value_objects.evidence_quality import (
    EvidenceQuality,
    EvidenceReliability,
    EvidenceStrength,
)
from rootcause_mcp.infrastructure.persistence.database import Database
from rootcause_mcp.infrastructure.persistence.evidence_repository import (
    SQLiteEvidenceRepository,
)


@pytest.mark.asyncio
async def test_evidence_persistence(tmp_path: Path) -> None:
    """Test that evidence persists across database sessions."""
    # Create temporary database
    db_path = tmp_path / "test.db"
    db = Database(db_path)
    db.create_tables()

    repo = SQLiteEvidenceRepository(db)

    # Create evidence
    evidence = Evidence(
        content="Test evidence for persistence",
        evidence_type=EvidenceType.DOCUMENT,
        clinical_context="Test context",
        quality=EvidenceQuality(
            strength=EvidenceStrength.STRONG,
            reliability=EvidenceReliability.GRADE_A,
        ),
        source=EvidenceSource(
            document_id="test.pdf",
            location="Page 1",
            collected_by="test_agent",
            source_system=None,
        ),
        event_timestamp=None,
        verified=False,
        verifier=None,
        verification_timestamp=None,
    )

    # Save evidence
    await repo.save("test_session", evidence)

    # Close database
    db.close()

    # Reopen database
    db2 = Database(db_path)
    repo2 = SQLiteEvidenceRepository(db2)

    # Retrieve evidence
    retrieved = await repo2.get_by_id("test_session", evidence.id.value)

    assert retrieved is not None
    assert retrieved.content == "Test evidence for persistence"
    assert retrieved.quality.strength == EvidenceStrength.STRONG

    # Cleanup
    db2.close()


@pytest.mark.asyncio
async def test_evidence_list_by_session(tmp_path: Path) -> None:
    """Test listing evidence by session."""
    db_path = tmp_path / "test.db"
    db = Database(db_path)
    db.create_tables()

    repo = SQLiteEvidenceRepository(db)

    # Add multiple evidence
    for i in range(3):
        evidence = Evidence(
            content=f"Evidence {i}",
            evidence_type=EvidenceType.DOCUMENT,
            clinical_context=None,
            quality=EvidenceQuality(
                strength=EvidenceStrength.MODERATE,
                reliability=EvidenceReliability.GRADE_B,
            ),
            source=EvidenceSource(
                document_id=f"doc{i}.pdf",
                location=None,
                collected_by="test",
                source_system=None,
            ),
            event_timestamp=None,
            verified=False,
            verifier=None,
            verification_timestamp=None,
        )
        await repo.save("test_session", evidence)

    # List all
    all_evidence = await repo.list_by_session("test_session")

    assert len(all_evidence) == 3
    assert all_evidence[0].content.startswith("Evidence")

    db.close()


@pytest.mark.asyncio
async def test_server_state_rehydrates_complete_reasoning_case(tmp_path: Path) -> None:
    """Evidence, hypotheses, thinking, and reasoning survive a restart."""
    from rootcause_mcp.application.server_state import ServerState
    from rootcause_mcp.domain.entities.thinking_step import ThinkingStep, ThinkingType
    from rootcause_mcp.infrastructure.persistence.hypothesis_repository import (
        SQLiteHypothesisRepository,
    )
    from rootcause_mcp.infrastructure.persistence.reasoning_chain_repository import (
        SQLiteReasoningChainRepository,
    )
    from rootcause_mcp.infrastructure.persistence.thinking_chain_repository import (
        SQLiteThinkingChainRepository,
    )

    database_path = tmp_path / "reasoning.db"
    database = Database(database_path)
    database.create_tables()
    state = ServerState(
        evidence_repository=SQLiteEvidenceRepository(database),
        hypothesis_repository=SQLiteHypothesisRepository(database),
        thinking_repository=SQLiteThinkingChainRepository(database),
        reasoning_repository=SQLiteReasoningChainRepository(database),
    )

    orchestrator = await state.get_or_create_orchestrator("case-001")
    evidence = orchestrator.add_evidence(
        content="Troponin I 2.5 ng/mL",
        evidence_type="LAB_RESULT",
        clinical_strength="STRONG",
        source_reliability="GRADE_A",
    )
    hypothesis = orchestrator.propose_hypothesis(
        diagnosis="Acute myocardial infarction",
        icd10_code="I21.9",
        prior_probability=0.3,
        rationale="Chest pain with elevated troponin supports acute MI.",
    )
    orchestrator.link_evidence_to_hypothesis(
        evidence_id=evidence.id.value,
        hypothesis_id=hypothesis.id.value,
        likelihood_ratio=5.0,
        rationale="Marked troponin elevation strongly supports myocardial injury.",
    )
    orchestrator.thinking_chain.add_step(
        ThinkingStep(
            thinking_type=ThinkingType.HYPOTHESIS_CONSIDERED,
            content="Acute MI is the leading diagnosis",
            internal_reasoning="The temporal pattern and biomarker result align with MI.",
            confidence=0.8,
        )
    )
    await state.persist_orchestrator("case-001")
    database.close()

    reopened_database = Database(database_path)
    reopened_database.create_tables()
    restored_state = ServerState(
        evidence_repository=SQLiteEvidenceRepository(reopened_database),
        hypothesis_repository=SQLiteHypothesisRepository(reopened_database),
        thinking_repository=SQLiteThinkingChainRepository(reopened_database),
        reasoning_repository=SQLiteReasoningChainRepository(reopened_database),
    )

    restored = await restored_state.get_orchestrator("case-001")
    assert restored is not None
    assert list(restored.evidence_store) == [evidence.id.value]
    assert list(restored.hypothesis_store) == [hypothesis.id.value]
    assert restored.hypothesis_store[hypothesis.id.value].current_probability > 0.3
    assert len(restored.reasoning_chain.steps) == 3
    assert len(restored.thinking_chain.steps) == 1
    reopened_database.close()
