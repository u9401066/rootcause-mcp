"""
Test real persistence with SQLite.

Verifies that data survives across sessions.
"""

import pytest
from pathlib import Path

from rootcause_mcp.infrastructure.persistence.database import Database
from rootcause_mcp.infrastructure.persistence.evidence_repository import (
    SQLiteEvidenceRepository,
)
from rootcause_mcp.domain.entities.evidence import Evidence, EvidenceSource, EvidenceType
from rootcause_mcp.domain.value_objects.evidence_quality import (
    EvidenceQuality,
    EvidenceReliability,
    EvidenceStrength,
)


@pytest.mark.asyncio
async def test_evidence_persistence(tmp_path: Path):
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
async def test_evidence_list_by_session(tmp_path: Path):
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
