"""
Contract Report Value Object.

Immutable, auditable report for clinical reasoning.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class EvidenceCoverageMetrics(BaseModel):
    """Evidence coverage quality metrics."""

    total_evidence: int = Field(..., ge=0)
    verified_evidence: int = Field(..., ge=0)
    strong_evidence: int = Field(..., ge=0)
    moderate_evidence: int = Field(..., ge=0)
    weak_evidence: int = Field(..., ge=0)

    @property
    def verification_rate(self) -> float:
        """Calculate verification rate."""
        if self.total_evidence == 0:
            return 0.0
        return self.verified_evidence / self.total_evidence

    @property
    def strength_distribution(self) -> dict[str, float]:
        """Calculate strength distribution."""
        total = self.total_evidence
        if total == 0:
            return {"strong": 0.0, "moderate": 0.0, "weak": 0.0}
        return {
            "strong": self.strong_evidence / total,
            "moderate": self.moderate_evidence / total,
            "weak": self.weak_evidence / total,
        }

    model_config = {"frozen": True}


class ReasoningQualityMetrics(BaseModel):
    """Reasoning quality metrics."""

    total_steps: int = Field(..., ge=0)
    avg_confidence: float | None = Field(None, ge=0, le=1)
    hypothesis_coverage: float = Field(..., ge=0, le=1)
    evidence_coverage: float = Field(..., ge=0, le=1)
    decision_points: int = Field(..., ge=0)
    alternatives_considered: int = Field(..., ge=0)
    biases_identified: int = Field(..., ge=0)
    uncertainties_acknowledged: int = Field(..., ge=0)

    model_config = {"frozen": True}


class ContractReport(BaseModel):
    """
    CONTRACT-level auditable report.

    Immutable after finalization.
    """

    # Identity
    report_id: str = Field(..., description="Unique report ID")
    session_id: str = Field(..., description="RCA session ID")
    report_version: str = Field(default="2.0.0a1", description="Report format version")

    # Timestamps
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    finalized_at: datetime | None = Field(None)

    # Content
    hypotheses: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    reasoning_chain: list[dict[str, Any]] = Field(default_factory=list)
    thinking_chain: list[dict[str, Any]] = Field(default_factory=list)

    # Quality metrics
    evidence_metrics: EvidenceCoverageMetrics | None = None
    reasoning_metrics: ReasoningQualityMetrics | None = None

    # Audit
    generated_by: str = Field(..., description="Agent that generated this report")
    reviewed_by: list[str] = Field(default_factory=list)
    approved_by: str | None = None

    # Immutability
    is_finalized: bool = Field(default=False)
    content_hash: str | None = Field(None, description="SHA-256 hash of content")

    def finalize(self, finalized_by: str) -> None:
        """
        Finalize report (make immutable).

        Args:
            finalized_by: Who finalized this report

        Raises:
            ValueError: If already finalized
        """
        if self.is_finalized:
            raise ValueError("Report already finalized")

        import hashlib
        import json

        # Calculate content hash
        content = json.dumps(
            {
                "hypotheses": self.hypotheses,
                "evidence": self.evidence,
                "reasoning_chain": self.reasoning_chain,
                "thinking_chain": self.thinking_chain,
            },
            sort_keys=True,
        )
        self.content_hash = hashlib.sha256(content.encode()).hexdigest()

        # Mark as finalized
        self.is_finalized = True
        self.finalized_at = datetime.now(UTC)
        self.approved_by = finalized_by

    def to_fhir(self) -> dict[str, Any]:
        """
        Export to FHIR-compatible format.

        Returns:
            FHIR DiagnosticReport resource
        """
        return {
            "resourceType": "DiagnosticReport",
            "id": self.report_id,
            "status": "final" if self.is_finalized else "preliminary",
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "11502-2",
                        "display": "Pathology report",
                    }
                ],
                "text": "Clinical Reasoning Report",
            },
            "effectiveDateTime": self.generated_at.isoformat(),
            "issued": self.finalized_at.isoformat() if self.finalized_at else None,
            "performer": [{"display": self.generated_by}],
            "conclusion": f"Differential diagnosis with {len(self.hypotheses)} hypotheses",
            "conclusionCode": [
                {
                    "coding": [
                        {
                            "system": "http://hl7.org/fhir/sid/icd-10",
                            "code": h.get("diagnosis", {}).get("code", "unknown"),
                            "display": h.get("diagnosis", {}).get("display", "Unknown"),
                        }
                    ]
                }
                for h in self.hypotheses[:3]  # Top 3 hypotheses
            ],
        }

    model_config = {"frozen": False}  # Mutable until finalized
