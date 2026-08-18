"""
Test real persistence with SQLite.

Verifies that data survives across sessions.
"""

import gc
import warnings
from pathlib import Path

import pytest

from rootcause_mcp.domain.entities.evidence import (
    Evidence,
    EvidenceSource,
    EvidenceType,
)
from rootcause_mcp.domain.entities.session import RCASession
from rootcause_mcp.domain.value_objects.case_manifest import (
    CaseInputManifest,
    SourceDocument,
)
from rootcause_mcp.domain.value_objects.enums import CaseType
from rootcause_mcp.domain.value_objects.evidence_quality import (
    EvidenceQuality,
    EvidenceReliability,
    EvidenceStrength,
)
from rootcause_mcp.infrastructure.persistence.database import Database
from rootcause_mcp.infrastructure.persistence.evidence_repository import (
    SQLiteEvidenceRepository,
)
from rootcause_mcp.infrastructure.persistence.session_repository import (
    SQLiteSessionRepository,
)


def test_database_close_prevents_sqlite_resource_warning(tmp_path: Path) -> None:
    """Explicit owner shutdown must close pooled SQLite connections."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", ResourceWarning)
        database = Database(tmp_path / "resource-owner.db")
        database.create_tables()
        database.close()
        del database
        gc.collect()

    resource_warnings = [
        warning for warning in caught if issubclass(warning.category, ResourceWarning)
    ]
    assert resource_warnings == []


def test_source_manifest_survives_session_restart(tmp_path: Path) -> None:
    database_path = tmp_path / "manifest.db"
    database = Database(database_path)
    database.create_tables()
    repository = SQLiteSessionRepository(database)
    session = RCASession.create(
        case_type=CaseType.COMPLICATION,
        case_title="Multi-source case",
    )
    manifest = CaseInputManifest(
        documents=(
            SourceDocument(
                document_id="chart-1",
                source_uri="records/chart-1.txt",
                sha256="c" * 64,
                media_type="text/plain",
                source_kind="progress_note",
            ),
            SourceDocument(
                document_id="device-1",
                source_uri="records/device-1.log",
                sha256="d" * 64,
                media_type="text/plain",
                source_kind="device_log",
            ),
        )
    )
    session.set_source_manifest(manifest)
    repository.save(session)
    session_id = str(session.id)
    database.close()

    reopened = Database(database_path)
    restored = SQLiteSessionRepository(reopened).get_by_id(session_id)

    assert restored is not None
    assert restored.get_source_manifest() == manifest
    reopened.close()


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
async def test_evidence_verification_metadata_survives_restart(tmp_path: Path) -> None:
    db_path = tmp_path / "verification.db"
    database = Database(db_path)
    database.create_tables()
    repository = SQLiteEvidenceRepository(database)
    evidence = Evidence(
        content="Verified chart finding",
        evidence_type=EvidenceType.DOCUMENT,
        quality=EvidenceQuality(
            strength=EvidenceStrength.STRONG,
            reliability=EvidenceReliability.GRADE_A,
        ),
        source=EvidenceSource(
            document_id="chart.txt",
            location="Line 7",
            raw_snippet="Verified chart finding",
            collected_by="test",
        ),
    ).mark_verified(
        verifier="SYSTEM_PROVENANCE_VERIFIER",
        verification_method="EXACT_SNIPPET_MATCH",
        matched_lines=[7],
        content_hash="sha256:abc",
    )
    await repository.save("verification-session", evidence)
    database.close()

    reopened = Database(db_path)
    restored = await SQLiteEvidenceRepository(reopened).get_by_id(
        "verification-session",
        evidence.id.value,
    )

    assert restored is not None
    assert restored.verification_method == "EXACT_SNIPPET_MATCH"
    assert restored.matched_lines == [7]
    assert restored.source.content_hash == "sha256:abc"
    reopened.close()


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
        must_not_miss=True,
        alternatives_considered=[
            {"diagnosis": "Pulmonary embolism", "reason_rejected": "No RV strain"}
        ],
        uncertainty_factors=["Serial ECG pending"],
        confidence_rationale="Clinical prevalence plus objective findings",
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
    restored_hypothesis = restored.hypothesis_store[hypothesis.id.value]
    assert restored_hypothesis.must_not_miss is True
    assert restored_hypothesis.uncertainty_factors == ["Serial ECG pending"]
    assert restored_hypothesis.confidence_rationale.startswith("Clinical prevalence")
    assert len(restored.reasoning_chain.steps) == 3
    assert len(restored.thinking_chain.steps) == 1
    reopened_database.close()
