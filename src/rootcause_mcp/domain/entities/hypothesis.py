"""
Hypothesis Entity for Differential Diagnosis.

Implements a Bayesian compatibility ledger with:
- An uncalibrated numeric starting value
- Direct likelihood ratio (LR) updating
- An uncalibrated numeric compatibility result
- Inclusion/exclusion criteria tracking
"""

from __future__ import annotations

import math
import re
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Self
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator

from rootcause_mcp.domain.value_objects.clinical_concept import ClinicalConcept
from rootcause_mcp.domain.value_objects.identifiers import HypothesisId


class HypothesisStatus(str, Enum):
    """Hypothesis lifecycle status."""

    ACTIVE = "ACTIVE"  # Currently being considered
    CONFIRMED = "CONFIRMED"  # Confirmed as the actual diagnosis
    EXCLUDED = "EXCLUDED"  # Ruled out by evidence
    ON_HOLD = "ON_HOLD"  # Temporarily suspended (insufficient evidence)


class MechanismCategory(str, Enum):
    """Broad etiologic mechanism used to audit DDx breadth.

    The categories deliberately follow a VINDICATE-style axis instead of an
    organ-system axis.  ``UNKNOWN`` is an honest preliminary value and never
    counts toward the final mechanism-breadth gate.
    """

    VASCULAR = "VASCULAR"
    INFECTIOUS = "INFECTIOUS"
    INFLAMMATORY_IMMUNE = "INFLAMMATORY_IMMUNE"
    NEOPLASTIC = "NEOPLASTIC"
    DRUG_TOXIN_IATROGENIC = "DRUG_TOXIN_IATROGENIC"
    METABOLIC_ENDOCRINE = "METABOLIC_ENDOCRINE"
    TRAUMATIC_MECHANICAL = "TRAUMATIC_MECHANICAL"
    CONGENITAL_GENETIC = "CONGENITAL_GENETIC"
    DEGENERATIVE = "DEGENERATIVE"
    FUNCTIONAL_PHYSIOLOGIC = "FUNCTIONAL_PHYSIOLOGIC"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class DiagnosticRole(str, Enum):
    """Role played by a candidate within the clinical explanation."""

    ETIOLOGIC = "ETIOLOGIC"
    SYNDROMIC = "SYNDROMIC"
    COMPLICATION = "COMPLICATION"
    MIMIC = "MIMIC"
    UNKNOWN = "UNKNOWN"


class DiagnosticCertainty(str, Enum):
    """Human/agent-declared qualitative certainty, separate from probability."""

    UNKNOWN = "UNKNOWN"
    POSSIBLE = "POSSIBLE"
    PROBABLE = "PROBABLE"
    HIGH_CONFIDENCE = "HIGH_CONFIDENCE"
    CONFIRMED = "CONFIRMED"
    EXCLUDED = "EXCLUDED"


class DiagnosticReasoningBasis(str, Enum):
    """Epistemic origin of the candidate diagnosis.

    ``OBSERVED_DIAGNOSIS`` means the diagnosis itself is explicitly documented
    in a source; the associated source still belongs in the evidence ledger.
    ``MECHANISM_INFERENCE`` identifies a clinical inference from observations.
    It is not causal proof. ``UNKNOWN`` is retained instead of inventing a basis.
    """

    OBSERVED_DIAGNOSIS = "OBSERVED_DIAGNOSIS"
    MECHANISM_INFERENCE = "MECHANISM_INFERENCE"
    UNKNOWN = "UNKNOWN"


class DiagnosticTestStatus(str, Enum):
    """Machine-readable lifecycle for a hypothesis-specific diagnostic test."""

    PLANNED = "PLANNED"
    ORDERED = "ORDERED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class DiagnosticTestPurpose(str, Enum):
    """Declared relationship between a planned test and its target diagnosis."""

    DISCONFIRM = "DISCONFIRM"
    RULE_OUT = "RULE_OUT"
    CONFIRM = "CONFIRM"
    DISCRIMINATE = "DISCRIMINATE"


class DiagnosticTestResultDisposition(str, Enum):
    """Typed interpretation of a completed test relative to its hypothesis."""

    SUPPORTS_HYPOTHESIS = "SUPPORTS_HYPOTHESIS"
    REFUTES_HYPOTHESIS = "REFUTES_HYPOTHESIS"
    NEUTRAL = "NEUTRAL"
    INDETERMINATE = "INDETERMINATE"


class LikelihoodRatioCalibrationStatus(str, Enum):
    """Whether a direct LR has an identifiable quantitative calibration source."""

    SOURCE_CALIBRATED = "SOURCE_CALIBRATED"
    QUANTITATIVELY_UNKNOWN = "QUANTITATIVELY_UNKNOWN"


def is_calibration_evidence_ref(value: str | None) -> bool:
    """Require a cross-reference into the case evidence ledger.

    A citation-looking caller string is not evidence that a quantitative value
    was retrieved or applies to this population.  Admission therefore uses a
    stable ``EVD-*`` record; the runtime and final conformance evaluator inspect
    that record's type, verification state, exact snippet, hash, and location.
    """
    return re.fullmatch(r"EVD-[A-Za-z0-9_-]+", str(value or "").strip()) is not None


class PlannedDiagnosticTest(BaseModel):
    """Explicit test disposition used to challenge one diagnosis.

    The server binds ``target_hypothesis_id`` when the hypothesis is created.
    Free-text gaps, inclusion criteria, or exclusion criteria are deliberately
    not substitutes for this typed record.
    """

    test_id: str = Field(
        default_factory=lambda: f"TST-{uuid4().hex[:8]}",
        min_length=5,
        max_length=64,
        pattern=r"^TST-[A-Za-z0-9_-]+$",
    )
    name: str = Field(..., min_length=1, max_length=200)
    purpose: DiagnosticTestPurpose
    target_hypothesis_id: str = Field(
        ...,
        min_length=5,
        max_length=64,
        pattern=r"^HYP-[A-Za-z0-9_-]+$",
    )
    expected_supporting_result: str = Field(..., min_length=1, max_length=500)
    expected_refuting_result: str = Field(..., min_length=1, max_length=500)
    status: DiagnosticTestStatus = Field(default=DiagnosticTestStatus.PLANNED)
    result_evidence_id: str | None = Field(default=None, max_length=64)
    result_summary: str | None = Field(default=None, max_length=1000)
    result_disposition: DiagnosticTestResultDisposition | None = None

    @field_validator(
        "name",
        "expected_supporting_result",
        "expected_refuting_result",
    )
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        """Reject visually empty required fields after whitespace normalization."""
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("Diagnostic test fields cannot be blank")
        return normalized

    @model_validator(mode="after")
    def validate_result_metadata(self) -> Self:
        """Keep completed/cancelled dispositions explicit and auditable."""
        if self.status is DiagnosticTestStatus.COMPLETED and (
            not self.result_evidence_id
            or not self.result_summary
            or self.result_disposition is None
        ):
            raise ValueError(
                "COMPLETED diagnostic tests require result_evidence_id, "
                "result_summary, and typed result_disposition"
            )
        if self.status is DiagnosticTestStatus.CANCELLED and not self.result_summary:
            raise ValueError("CANCELLED diagnostic tests require result_summary")
        if (
            self.status is not DiagnosticTestStatus.COMPLETED
            and self.result_disposition is not None
        ):
            raise ValueError("result_disposition is only valid for COMPLETED tests")
        return self

    model_config = {"frozen": True, "extra": "forbid"}


class HypothesisStatusChange(BaseModel):
    """Auditable transition between hypothesis lifecycle states."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    previous_status: HypothesisStatus
    new_status: HypothesisStatus
    changed_by: str = Field(..., min_length=1)
    reason: str = Field(..., min_length=1)

    model_config = {"frozen": True}


class LikelihoodRatio(BaseModel):
    """
    Likelihood ratio for evidence given hypothesis.

    LR+ = P(Evidence | Hypothesis True) / P(Evidence | Hypothesis False)
    LR- = P(No Evidence | Hypothesis True) / P(No Evidence | Hypothesis False)
    """

    evidence_id: str = Field(..., description="Evidence ID")
    lr_positive: float | None = Field(
        None, gt=0, description="LR+ for a validated diagnostic test, when supplied"
    )
    lr_negative: float | None = Field(None, gt=0, description="LR- (evidence absent)")
    applied_likelihood_ratio: float | None = Field(
        None,
        gt=0,
        le=100,
        description="The LR actually applied to the Bayesian update",
    )
    supports: bool | None = Field(
        None,
        description="Whether the observed evidence supports or contradicts the hypothesis",
    )
    rationale: str = Field(..., description="Why this LR value?")
    calibration_status: LikelihoodRatioCalibrationStatus
    calibration_source_ref: str | None = Field(default=None, max_length=500)

    @field_validator("lr_positive", "lr_negative")
    @classmethod
    def validate_lr_range(cls, v: float | None) -> float | None:
        """Validate LR is in reasonable range."""
        if v is not None and (v < 0.01 or v > 100):
            raise ValueError(f"LR {v} outside reasonable range [0.01, 100]")
        return v

    @field_validator("rationale")
    @classmethod
    def validate_rationale(cls, value: str) -> str:
        """Every quantitative relationship needs an explicit rationale."""
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("Likelihood ratio rationale cannot be blank")
        return normalized

    @model_validator(mode="after")
    def validate_calibration(self) -> Self:
        """Block invented non-neutral LRs and unverifiable calibration claims."""
        if self.calibration_status is (
            LikelihoodRatioCalibrationStatus.SOURCE_CALIBRATED
        ):
            if not is_calibration_evidence_ref(self.calibration_source_ref):
                raise ValueError(
                    "SOURCE_CALIBRATED requires calibration_source_ref to be an "
                    "EVD-* literature/calibration record in the case evidence ledger"
                )
        elif self.applied_likelihood_ratio is not None and not math.isclose(
            self.applied_likelihood_ratio, 1.0
        ):
            raise ValueError("QUANTITATIVELY_UNKNOWN requires likelihood_ratio=1.0")
        applied = self.applied_likelihood_ratio
        if applied is not None:
            if math.isclose(applied, 1.0):
                if self.supports is not None:
                    raise ValueError(
                        "likelihood_ratio=1.0 is neutral and requires supports=null"
                    )
            elif applied > 1.0 and self.supports is not True:
                raise ValueError("likelihood_ratio>1 requires supports=true")
            elif applied < 1.0 and self.supports is not False:
                raise ValueError("likelihood_ratio<1 requires supports=false")
        return self

    model_config = {"frozen": True, "allow_inf_nan": False}


class BayesianUpdate(BaseModel):
    """Record of a single uncalibrated compatibility update."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    evidence_id: str = Field(..., description="Evidence used for update")
    prior_probability: float = Field(
        ...,
        ge=0,
        le=1,
        description=(
            "Uncalibrated compatibility value before the direct LR update; not "
            "clinical probability, rank, or certainty"
        ),
    )
    likelihood_ratio: float = Field(..., gt=0, description="LR applied")
    posterior_probability: float = Field(
        ...,
        ge=0,
        le=1,
        description=(
            "Uncalibrated compatibility value after the direct LR update; not "
            "clinical probability, rank, or certainty"
        ),
    )
    updated_by: str = Field(..., description="Who performed this update")

    model_config = {"frozen": True}


class Hypothesis(BaseModel):
    """
    Differential Diagnosis Hypothesis with Bayesian updating.

    Examples:
        >>> hyp = Hypothesis(
        ...     diagnosis=ClinicalConcept(
        ...         code="I21.9",
        ...         display="Acute MI",
        ...         system=CodingSystem.ICD_10
        ...     ),
        ...     prior_probability=0.15,
        ...     inclusion_criteria=["Chest pain", "Elevated troponin"],
        ...     exclusion_criteria=["Normal ECG", "Age < 30"]
        ... )
        >>>
        >>> # Apply evidence with LR+ = 5.0
        >>> hyp_updated = hyp.bayesian_update(
        ...     evidence_id="EVD-001",
        ...     likelihood_ratio=5.0,
        ...     updated_by="DR_SMITH"
        ... )
    """

    # Identity
    id: HypothesisId = Field(
        default_factory=lambda: HypothesisId(f"HYP-{uuid4().hex[:8]}")
    )

    # Diagnosis
    diagnosis: ClinicalConcept = Field(..., description="Clinical diagnosis concept")

    # Bayesian reasoning
    prior_probability: float = Field(
        ...,
        ge=0,
        le=1,
        description=(
            "Uncalibrated Bayesian compatibility baseline; not clinical probability, "
            "rank, or certainty"
        ),
    )
    current_probability: float = Field(
        ...,
        ge=0,
        le=1,
        description=(
            "Current uncalibrated compatibility value; not clinical probability, "
            "rank, or certainty"
        ),
    )

    # Criteria
    inclusion_criteria: list[str] = Field(
        default_factory=list, description="Criteria that support this diagnosis"
    )
    exclusion_criteria: list[str] = Field(
        default_factory=list, description="Criteria that rule out this diagnosis"
    )
    must_not_miss: bool = Field(
        default=False,
        description="Whether this is an explicitly reviewed high-harm rule-out",
    )
    mechanism_category: MechanismCategory = Field(
        default=MechanismCategory.UNKNOWN,
        description=(
            "Broad etiologic mechanism used to demonstrate differential breadth; "
            "UNKNOWN is allowed for preliminary work but does not satisfy breadth"
        ),
    )
    diagnostic_role: DiagnosticRole = Field(
        default=DiagnosticRole.UNKNOWN,
        description="Whether the candidate is etiologic, syndromic, a complication, or a mimic",
    )
    certainty: DiagnosticCertainty = Field(
        default=DiagnosticCertainty.UNKNOWN,
        description=(
            "Qualitative certainty label; independent of the numeric Bayesian "
            "placeholder/probability"
        ),
    )
    reasoning_basis: DiagnosticReasoningBasis = Field(
        default=DiagnosticReasoningBasis.UNKNOWN,
        description=(
            "Whether the diagnosis was explicitly observed/documented, inferred "
            "through a mechanism, or remains unknown"
        ),
    )
    alternatives_considered: list[dict[str, Any]] = Field(
        default_factory=list,
        description=(
            "Deprecated context-only alternative notes; plausible diagnoses belong "
            "in their own hypothesis records and the typed breadth audit"
        ),
    )
    uncertainty_factors: list[str] = Field(
        default_factory=list,
        description="Known diagnostic uncertainty retained with the hypothesis",
    )
    confidence_rationale: str = Field(
        default="",
        description=(
            "Why the candidate is considered and the calibration/source limitations "
            "of any numeric starting value"
        ),
    )
    planned_tests: list[PlannedDiagnosticTest] = Field(
        default_factory=list,
        description=(
            "Typed diagnostic tests planned or ordered to support or refute this "
            "specific hypothesis"
        ),
    )

    # Evidence linking
    likelihood_ratios: list[LikelihoodRatio] = Field(
        default_factory=list, description="LR for each evidence"
    )
    supporting_evidence_ids: list[str] = Field(
        default_factory=list, description="Evidence IDs supporting this hypothesis"
    )
    contradicting_evidence_ids: list[str] = Field(
        default_factory=list, description="Evidence IDs contradicting this hypothesis"
    )

    # Audit trail
    status: HypothesisStatus = Field(default=HypothesisStatus.ACTIVE)
    status_history: list[HypothesisStatusChange] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    created_by: str = Field(..., description="Who proposed this hypothesis")

    bayesian_history: list[BayesianUpdate] = Field(
        default_factory=list, description="History of Bayesian updates"
    )

    # Reasoning
    clinical_rationale: str = Field(
        ..., min_length=10, description="Why is this hypothesis being considered?"
    )

    @model_validator(mode="after")
    def validate_current_matches_prior_on_creation(self) -> Self:
        """Ensure current_probability matches prior on initial creation."""
        if (
            not self.bayesian_history
            and abs(self.current_probability - self.prior_probability) > 0.001
        ):
            raise ValueError(
                f"Initial current_probability ({self.current_probability}) must equal "
                f"prior_probability ({self.prior_probability}) when no Bayesian "
                "history exists"
            )
        if any(
            test.target_hypothesis_id != self.id.value for test in self.planned_tests
        ):
            raise ValueError(
                "Every planned diagnostic test must target its containing hypothesis"
            )
        test_ids = [test.test_id for test in self.planned_tests]
        if len(test_ids) != len(set(test_ids)):
            raise ValueError("Diagnostic test IDs must be unique within a hypothesis")
        return self

    def bayesian_update(
        self,
        evidence_id: str,
        likelihood_ratio: float,
        updated_by: str,
        supports: bool | None = None,
    ) -> Self:
        """
        Perform Bayesian update with new evidence.

        Args:
            evidence_id: ID of evidence
            likelihood_ratio: The likelihood ratio to apply directly. Supporting
                evidence normally uses LR > 1 and contradicting evidence LR < 1.
            updated_by: Who performed this update
            supports: Relationship label used for the evidence audit trail

        Returns:
            New Hypothesis instance with updated probability

        Mathematical formula:
            Posterior Odds = Prior Odds × LR
            Posterior P = Posterior Odds / (1 + Posterior Odds)
        """
        if not math.isfinite(likelihood_ratio) or not 0 < likelihood_ratio <= 100:
            raise ValueError("Applied likelihood ratio must be finite and in (0, 100]")
        if supports is True and likelihood_ratio <= 1.0:
            raise ValueError(
                "Supporting evidence requires an applied likelihood ratio > 1.0"
            )
        if supports is False and likelihood_ratio >= 1.0:
            raise ValueError(
                "Contradicting evidence requires an applied likelihood ratio < 1.0"
            )
        if supports is None and not math.isclose(likelihood_ratio, 1.0):
            raise ValueError("Only likelihood_ratio=1.0 may use a neutral direction")

        # ``likelihood_ratio`` is already the applied LR.  Older code inverted a
        # contradicting LR here even though the MCP contract supplies LR- (< 1),
        # causing refuting evidence to increase the posterior probability.
        lr = likelihood_ratio
        if self.current_probability <= 0.0:
            posterior_prob = 0.0
        elif self.current_probability >= 1.0:
            posterior_prob = 1.0
        else:
            prior_odds = self.current_probability / (1 - self.current_probability)
            posterior_odds = prior_odds * lr
            posterior_prob = posterior_odds / (1 + posterior_odds)

        # Create update record
        update = BayesianUpdate(
            evidence_id=evidence_id,
            prior_probability=self.current_probability,
            likelihood_ratio=lr,
            posterior_probability=posterior_prob,
            updated_by=updated_by,
        )

        # Update evidence lists
        if supports is True:
            updated_supporting = [*self.supporting_evidence_ids, evidence_id]
            updated_contradicting = self.contradicting_evidence_ids
        elif supports is False:
            updated_supporting = self.supporting_evidence_ids
            updated_contradicting = [*self.contradicting_evidence_ids, evidence_id]
        else:
            updated_supporting = self.supporting_evidence_ids
            updated_contradicting = self.contradicting_evidence_ids

        # Return new instance
        return self.model_copy(
            update={
                "current_probability": posterior_prob,
                "bayesian_history": [*self.bayesian_history, update],
                "supporting_evidence_ids": updated_supporting,
                "contradicting_evidence_ids": updated_contradicting,
            }
        )

    def add_likelihood_ratio(
        self,
        evidence_id: str,
        lr_positive: float | None,
        lr_negative: float | None,
        rationale: str,
        calibration_status: LikelihoodRatioCalibrationStatus,
        calibration_source_ref: str | None,
        applied_likelihood_ratio: float | None = None,
        supports: bool | None = None,
    ) -> Self:
        """
        Add likelihood ratio for a piece of evidence.

        Args:
            evidence_id: Evidence ID
            lr_positive: LR when evidence is present
            lr_negative: LR when evidence is absent (optional)
            rationale: Clinical justification for this LR
            applied_likelihood_ratio: LR actually used for this observation
            supports: Direction of the observed evidence relationship

        Returns:
            New Hypothesis instance with added LR
        """
        lr = LikelihoodRatio(
            evidence_id=evidence_id,
            lr_positive=lr_positive,
            lr_negative=lr_negative,
            rationale=rationale,
            calibration_status=calibration_status,
            calibration_source_ref=calibration_source_ref,
            applied_likelihood_ratio=applied_likelihood_ratio,
            supports=supports,
        )

        return self.model_copy(
            update={"likelihood_ratios": [*self.likelihood_ratios, lr]}
        )

    def mark_confirmed(
        self,
        confirmed_by: str,
        reason: str = "Diagnostic criteria satisfied",
    ) -> Self:
        """Mark hypothesis as confirmed."""
        return self._transition_to(HypothesisStatus.CONFIRMED, confirmed_by, reason)

    def mark_excluded(self, excluded_by: str, reason: str) -> Self:
        """Mark hypothesis as excluded."""
        return self._transition_to(HypothesisStatus.EXCLUDED, excluded_by, reason)

    def mark_on_hold(self, held_by: str, reason: str) -> Self:
        """Put hypothesis on hold pending more information."""
        return self._transition_to(HypothesisStatus.ON_HOLD, held_by, reason)

    def _transition_to(
        self,
        new_status: HypothesisStatus,
        changed_by: str,
        reason: str,
    ) -> Self:
        change = HypothesisStatusChange(
            previous_status=self.status,
            new_status=new_status,
            changed_by=changed_by,
            reason=reason,
        )
        certainty_update: DiagnosticCertainty | None = None
        if new_status is HypothesisStatus.CONFIRMED:
            certainty_update = DiagnosticCertainty.CONFIRMED
        elif new_status is HypothesisStatus.EXCLUDED:
            certainty_update = DiagnosticCertainty.EXCLUDED
        updates: dict[str, Any] = {
            "status": new_status,
            "status_history": [*self.status_history, change],
        }
        if certainty_update is not None:
            updates["certainty"] = certainty_update
        return self.model_copy(update=updates)

    def get_confidence_interval(
        self, confidence_level: float = 0.95
    ) -> tuple[float, float]:
        """
        Calculate confidence interval for current probability.

        Args:
            confidence_level: Confidence level (default 95%)

        Returns:
            (lower_bound, upper_bound)

        Note:
            This is a simplified approximation. For rigorous CI,
            use Beta distribution based on number of updates.
        """
        n_updates = len(self.bayesian_history)

        if n_updates == 0:
            # No updates yet, wide interval
            return (0.0, 1.0)

        # Approximate standard error (decreases with more updates)
        # This is a heuristic, not a rigorous statistical CI
        se = 1.0 / math.sqrt(n_updates + 1)
        z_score = 1.96 if confidence_level == 0.95 else 2.576  # 95% or 99%

        lower = max(0.0, self.current_probability - z_score * se)
        upper = min(1.0, self.current_probability + z_score * se)

        return (lower, upper)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return self.model_dump(mode="json", exclude_none=True)

    model_config = {"frozen": False}  # Mutable entity


# Convenience constructors
class CardiologyHypotheses:
    """Pre-configured cardiology differential diagnoses."""

    @staticmethod
    def acute_mi(prior: float = 0.15, created_by: str = "system") -> Hypothesis:
        """Acute myocardial infarction hypothesis."""
        from rootcause_mcp.domain.value_objects.clinical_concept import (
            ClinicalConcept,
            CodingSystem,
        )

        return Hypothesis(
            diagnosis=ClinicalConcept(
                code="I21.9",
                display="Acute myocardial infarction, unspecified",
                system=CodingSystem.ICD_10,
                version=None,
            ),
            prior_probability=prior,
            current_probability=prior,
            inclusion_criteria=[
                "Chest pain or angina equivalent",
                "Elevated cardiac biomarkers (troponin)",
                "ECG changes (ST elevation, depression, or Q waves)",
            ],
            exclusion_criteria=[
                "Normal serial troponins",
                "Alternative diagnosis explains symptoms",
            ],
            created_by=created_by,
            clinical_rationale="Acute myocardial infarction should be considered in patients with chest pain and cardiac risk factors.",
        )
