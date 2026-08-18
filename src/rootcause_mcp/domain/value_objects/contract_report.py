"""Typed, content-hashed contract report for clinical reasoning."""

from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    field_validator,
    model_validator,
)

from rootcause_mcp.domain.services.final_report_conformance import (
    HARD_CONFORMANCE_CODES,
    evaluate_final_report_conformance,
    hard_failures,
)
from rootcause_mcp.domain.value_objects.report_sections import (
    CausationVerificationRecord,
    EvidenceGraphRecord,
    EvidenceRecord,
    FishboneRecord,
    GapAnalysisRecord,
    HFACSClassificationRecord,
    HypothesisRecord,
    RCASessionRecord,
    ReasoningStepRecord,
    ReportReadinessRecord,
    RootCauseRecord,
    SourceInventoryRecord,
    ThinkingStepRecord,
    TimelineRecord,
    WhyTreeRecord,
)

_HASH_PATTERN = r"^[0-9a-f]{64}$"
_FINAL_METADATA_FIELDS = (
    "approved_by",
    "finalized_at",
    "content_hash",
    "conformance_checks",
)
_CANONICAL_HASH_EXCLUDES = {"content_hash"}
_NORMALIZED_REPORT_FIELDS = (
    "report_id",
    "session_id",
    "report_version",
    "generated_at",
    "finalized_at",
    "hypotheses",
    "evidence",
    "source_inventory",
    "timeline",
    "reasoning_chain",
    "thinking_chain",
    "evidence_graph",
    "rca_session",
    "fishbone",
    "why_tree",
    "root_causes",
    "hfacs_classifications",
    "causation_verifications",
    "gap_analysis",
    "report_readiness",
    "evidence_metrics",
    "reasoning_metrics",
    "generated_by",
    "reviewed_by",
    "approved_by",
    "conformance_checks",
    "is_finalized",
    "content_hash",
)


class ConformanceStatus(StrEnum):
    """Machine-readable outcome for one deterministic report check."""

    # This is a conformance enum label, never an authentication secret.
    PASS = "PASS"  # nosec B105
    FAIL = "FAIL"
    WARN = "WARN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ConformanceSeverity(StrEnum):
    """Release impact of a conformance result."""

    HARD = "HARD"
    BLOCKER = "BLOCKER"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


class ConformanceCheck(BaseModel):
    """One deterministic, machine-readable conformance result."""

    code: str = Field(
        ...,
        min_length=1,
        pattern=r"^[A-Z][A-Z0-9_]*$",
        description="Stable check identifier",
    )
    status: ConformanceStatus
    severity: ConformanceSeverity
    message: str = Field(..., min_length=1)
    refs: list[str] = Field(
        default_factory=list,
        description="JSON Pointers or stable ledger IDs involved in the check",
    )
    details: dict[str, JsonValue] = Field(default_factory=dict)

    model_config = ConfigDict(frozen=True, extra="forbid")

    def model_post_init(self, _context: object) -> None:
        """Deep-freeze reference/detail containers despite Pydantic shallow freeze."""
        object.__setattr__(self, "refs", _freeze_value(self.refs))
        object.__setattr__(self, "details", _freeze_value(self.details))


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

    model_config = ConfigDict(frozen=True, extra="forbid")


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

    model_config = ConfigDict(frozen=True, extra="forbid")


class ContractReport(BaseModel):
    """Auditable report with typed sections and a deeply frozen final state.

    Preliminary instances intentionally permit absent sections. Final instances
    require reviewer identity, an aware timestamp, a recomputable canonical hash,
    and at least one typed conformance result. Finalization freezes both model
    attributes and all nested list/dict containers.
    """

    report_id: str = Field(..., min_length=1, description="Unique report ID")
    session_id: str = Field(..., min_length=1, description="RCA session ID")
    report_version: str = Field(default="2.0.0a1", description="Report format version")

    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    finalized_at: datetime | None = Field(default=None)

    hypotheses: list[HypothesisRecord] = Field(default_factory=list)
    evidence: list[EvidenceRecord] = Field(default_factory=list)
    source_inventory: list[SourceInventoryRecord] = Field(default_factory=list)
    timeline: TimelineRecord | None = Field(
        default=None,
        description="Canonical chronological events plus deterministic renderings",
    )
    reasoning_chain: list[ReasoningStepRecord] = Field(default_factory=list)
    thinking_chain: list[ThinkingStepRecord] = Field(default_factory=list)
    evidence_graph: EvidenceGraphRecord | None = None

    rca_session: RCASessionRecord | None = None
    fishbone: FishboneRecord | None = None
    why_tree: WhyTreeRecord | None = None
    root_causes: list[RootCauseRecord] = Field(default_factory=list)
    hfacs_classifications: list[HFACSClassificationRecord] = Field(default_factory=list)
    causation_verifications: list[CausationVerificationRecord] = Field(
        default_factory=list
    )
    gap_analysis: GapAnalysisRecord | None = None
    report_readiness: ReportReadinessRecord | None = None

    evidence_metrics: EvidenceCoverageMetrics | None = None
    reasoning_metrics: ReasoningQualityMetrics | None = None

    generated_by: str = Field(..., min_length=1, description="Report generator")
    reviewed_by: list[str] = Field(default_factory=list)
    approved_by: str | None = Field(default=None, min_length=1)
    conformance_checks: list[ConformanceCheck] = Field(default_factory=list)

    is_finalized: bool = Field(default=False)
    content_hash: str | None = Field(
        default=None,
        pattern=_HASH_PATTERN,
        description="Canonical lowercase SHA-256 content hash",
    )

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        json_schema_extra={
            "additionalProperties": False,
            "required": list(_NORMALIZED_REPORT_FIELDS),
            "allOf": [
                {
                    "if": {
                        "properties": {"is_finalized": {"const": True}},
                        "required": ["is_finalized"],
                    },
                    "then": {
                        "required": list(_FINAL_METADATA_FIELDS),
                        "properties": {
                            "approved_by": {"type": "string", "minLength": 1},
                            "finalized_at": {
                                "type": "string",
                                "format": "date-time",
                            },
                            "content_hash": {
                                "type": "string",
                                "pattern": _HASH_PATTERN,
                            },
                            "conformance_checks": {"minItems": 1},
                            "reviewed_by": {"minItems": 1},
                            "hypotheses": {
                                "minItems": 3,
                                "items": {
                                    "required": [
                                        "id",
                                        "diagnosis",
                                        "current_probability",
                                        "must_not_miss",
                                        "supporting_evidence_ids",
                                        "contradicting_evidence_ids",
                                        "status",
                                        "clinical_rationale",
                                    ]
                                },
                            },
                            "evidence": {
                                "minItems": 1,
                                "items": {
                                    "required": [
                                        "id",
                                        "content",
                                        "evidence_type",
                                        "quality",
                                        "source",
                                        "verified",
                                    ]
                                },
                            },
                            "source_inventory": {
                                "minItems": 2,
                                "items": {
                                    "required": [
                                        "document",
                                        "sha256",
                                        "evidence_count",
                                        "verified_count",
                                        "coverage_status",
                                    ]
                                },
                            },
                            "timeline": {
                                "type": "object",
                                "required": ["events"],
                                "properties": {"events": {"minItems": 1}},
                            },
                            "rca_session": {"type": "object"},
                            "fishbone": {"type": "object"},
                            "why_tree": {"type": "object"},
                            "root_causes": {
                                "minItems": 1,
                                "items": {
                                    "required": [
                                        "id",
                                        "answer",
                                        "evidence",
                                        "causation_verification_id",
                                        "causation_result",
                                        "disposition",
                                    ]
                                },
                            },
                            "causation_verifications": {
                                "minItems": 1,
                                "items": {
                                    "required": [
                                        "verification_id",
                                        "cause_event",
                                        "effect_event",
                                        "overall_result",
                                        "audit_scope",
                                        "clinical_causality_established",
                                    ]
                                },
                            },
                            "gap_analysis": {"type": "object"},
                            "report_readiness": {"type": "object"},
                        },
                    },
                }
            ],
        },
    )

    @field_validator("hypotheses", "evidence", "reasoning_chain", mode="before")
    @classmethod
    def coerce_legacy_identifier_objects(cls, value: object) -> object:
        """Normalize pre-contract ``{"value": "ID"}`` wrappers to strings."""
        if not isinstance(value, list | tuple):
            return value
        normalized: list[object] = []
        for item in value:
            if not isinstance(item, dict):
                normalized.append(item)
                continue
            record = dict(item)
            identifier = record.get("id")
            if isinstance(identifier, dict) and isinstance(
                identifier.get("value"), str
            ):
                record["id"] = identifier["value"]
            normalized.append(record)
        return normalized

    @model_validator(mode="after")
    def validate_lifecycle_state(self) -> Self:
        """Validate conditional final metadata and freeze loaded snapshots."""
        if not self.is_finalized:
            if self.finalized_at is not None or self.content_hash is not None:
                raise ValueError(
                    "Preliminary reports cannot carry finalization time or hash"
                )
            if self.approved_by is not None:
                raise ValueError("Preliminary reports cannot carry approved_by")
            return self
        self._assert_final_requirements()
        self._freeze_snapshot()
        return self

    def __setattr__(self, name: str, value: object) -> None:
        """Reject attribute mutation after finalization."""
        if getattr(self, "is_finalized", False):
            raise TypeError("Finalized ContractReport snapshots are immutable")
        super().__setattr__(name, value)

    def __delattr__(self, name: str) -> None:
        """Reject attribute deletion after finalization."""
        if getattr(self, "is_finalized", False):
            raise TypeError("Finalized ContractReport snapshots are immutable")
        super().__delattr__(name)

    def model_copy(
        self,
        *,
        update: Mapping[str, Any] | None = None,
        deep: bool = False,
    ) -> Self:
        """Disallow Pydantic's non-validating update path for final snapshots."""
        if self.is_finalized:
            if update:
                raise TypeError("Finalized ContractReport snapshots are immutable")
            return self
        return super().model_copy(update=update, deep=deep)

    def finalize(
        self,
        finalized_by: str,
        *,
        finalized_at: datetime | None = None,
    ) -> None:
        """Attach final metadata, compute the canonical hash, and freeze in place."""
        if self.is_finalized:
            raise ValueError("Report already finalized")

        reviewer = finalized_by.strip()
        if not reviewer:
            raise ValueError("finalized_by must identify a reviewer")
        timestamp = finalized_at or datetime.now(UTC)
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("finalized_at must include an explicit timezone")

        caller_blocking_failures = [
            check.code
            for check in self.conformance_checks
            if check.code not in HARD_CONFORMANCE_CODES
            if check.status is ConformanceStatus.FAIL
            and check.severity
            in {
                ConformanceSeverity.HARD,
                ConformanceSeverity.BLOCKER,
                ConformanceSeverity.ERROR,
            }
        ]
        if caller_blocking_failures:
            raise ValueError(
                "Cannot finalize with failed conformance checks: "
                + ", ".join(sorted(caller_blocking_failures))
            )

        recomputed_hard_checks = evaluate_final_report_conformance(
            self.model_dump(mode="json"),
            approved_by=reviewer,
            authorized_reviewers=None,
        )
        recomputed_failures = hard_failures(recomputed_hard_checks)
        if recomputed_failures:
            raise ValueError(
                "Cannot finalize; deterministic conformance failed: "
                + ", ".join(sorted(str(check["code"]) for check in recomputed_failures))
            )

        reviewed_by = list(self.reviewed_by)
        if reviewer not in reviewed_by:
            reviewed_by.append(reviewer)
        caller_non_hard_checks = [
            check
            for check in self.conformance_checks
            if check.code not in HARD_CONFORMANCE_CODES
        ]
        checks = self._with_core_final_checks(
            [
                *caller_non_hard_checks,
                *(
                    ConformanceCheck.model_validate(check)
                    for check in recomputed_hard_checks
                ),
            ]
        )

        object.__setattr__(self, "approved_by", reviewer)
        object.__setattr__(self, "reviewed_by", reviewed_by)
        object.__setattr__(self, "finalized_at", timestamp)
        object.__setattr__(self, "conformance_checks", checks)
        object.__setattr__(self, "is_finalized", True)
        object.__setattr__(self, "content_hash", self.compute_content_hash())

        self._assert_final_requirements()
        self._freeze_snapshot()

    def canonical_content(self) -> str:
        """Return the stable JSON string used as content-hash input."""
        payload = self.model_dump(
            mode="json",
            exclude=_CANONICAL_HASH_EXCLUDES,
            warnings=False,
        )
        canonical_payload = _without_derived_presentations(payload)
        return json.dumps(
            canonical_payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )

    def compute_content_hash(self) -> str:
        """Recompute the lowercase SHA-256 digest of canonical report content."""
        return hashlib.sha256(self.canonical_content().encode("utf-8")).hexdigest()

    def verify_content_hash(self) -> bool:
        """Return whether stored final integrity metadata is recomputable."""
        if not self.is_finalized or self.content_hash is None:
            return False
        return hmac.compare_digest(self.content_hash, self.compute_content_hash())

    def to_final_snapshot(self) -> FinalContractReport:
        """Return the final-only validation type for persistence boundaries."""
        if not self.is_finalized:
            raise ValueError("Preliminary reports do not have a final snapshot")
        return FinalContractReport.model_validate(self.model_dump(mode="json"))

    def ranked_conclusion_hypotheses(self) -> list[HypothesisRecord]:
        """Return active hypotheses eligible for report/FHIR conclusions."""
        ineligible_statuses = {"EXCLUDED", "ON_HOLD", "RULED_OUT"}
        eligible = [
            hypothesis
            for hypothesis in self.hypotheses
            if str(hypothesis.get("status") or "").upper() not in ineligible_statuses
        ]
        return sorted(eligible, key=_hypothesis_probability, reverse=True)

    def _assert_final_requirements(self) -> None:
        """Raise when a purported final snapshot is incomplete or altered."""
        if not self.approved_by or not self.approved_by.strip():
            raise ValueError("Final reports require approved_by")
        if self.approved_by not in self.reviewed_by:
            raise ValueError("Final approved_by must also appear in reviewed_by")
        if self.finalized_at is None:
            raise ValueError("Final reports require finalized_at")
        if self.finalized_at.tzinfo is None or self.finalized_at.utcoffset() is None:
            raise ValueError("Final reports require a timezone-aware finalized_at")
        if not self.content_hash:
            raise ValueError("Final reports require content_hash")
        if not self.conformance_checks:
            raise ValueError("Final reports require conformance_checks")
        recomputed_hard_checks = evaluate_final_report_conformance(
            self.model_dump(mode="json", warnings=False),
            approved_by=self.approved_by,
            authorized_reviewers=None,
        )
        recomputed_by_code = {
            str(check["code"]): ConformanceCheck.model_validate(check).model_dump(
                mode="json"
            )
            for check in recomputed_hard_checks
        }
        supplied_hard_checks = [
            check
            for check in self.conformance_checks
            if check.code in HARD_CONFORMANCE_CODES
        ]
        supplied_by_code = {
            check.code: check.model_dump(mode="json") for check in supplied_hard_checks
        }
        if (
            len(supplied_hard_checks) != len(HARD_CONFORMANCE_CODES)
            or set(supplied_by_code) != HARD_CONFORMANCE_CODES
            or any(
                supplied_by_code[code] != recomputed_by_code[code]
                for code in HARD_CONFORMANCE_CODES
            )
        ):
            raise ValueError(
                "Final report hard conformance checks do not match deterministic evaluation"
            )
        recomputed_failures = hard_failures(recomputed_hard_checks)
        if recomputed_failures:
            raise ValueError(
                "Final report has failed deterministic conformance checks: "
                + ", ".join(sorted(str(check["code"]) for check in recomputed_failures))
            )
        if not self.verify_content_hash():
            raise ValueError(
                "Final report content_hash does not match canonical content"
            )

    @staticmethod
    def _with_core_final_checks(
        checks: list[ConformanceCheck],
    ) -> list[ConformanceCheck]:
        """Upsert deterministic checks owned by the report lifecycle."""
        by_code = {check.code: check for check in checks}
        by_code.update(
            {
                "TYPED_REPORT_SCHEMA": ConformanceCheck(
                    code="TYPED_REPORT_SCHEMA",
                    status=ConformanceStatus.PASS,
                    severity=ConformanceSeverity.HARD,
                    message="All supplied report sections passed nested type validation.",
                    refs=["#/"],
                ),
                "FINALIZATION_METADATA_COMPLETE": ConformanceCheck(
                    code="FINALIZATION_METADATA_COMPLETE",
                    status=ConformanceStatus.PASS,
                    severity=ConformanceSeverity.HARD,
                    message=(
                        "Reviewer identity and timezone-aware finalization time are "
                        "present."
                    ),
                    refs=["#/approved_by", "#/finalized_at"],
                ),
                "CONTENT_HASH_RECOMPUTABLE": ConformanceCheck(
                    code="CONTENT_HASH_RECOMPUTABLE",
                    status=ConformanceStatus.PASS,
                    severity=ConformanceSeverity.HARD,
                    message=(
                        "Canonical report content has a recomputable SHA-256 digest."
                    ),
                    refs=["#/content_hash"],
                ),
            }
        )
        return [by_code[code] for code in sorted(by_code)]

    def _freeze_snapshot(self) -> None:
        """Recursively freeze every mutable report field."""
        for field_name in type(self).model_fields:
            value = getattr(self, field_name)
            object.__setattr__(self, field_name, _freeze_value(value))


class PreliminaryContractReport(ContractReport):
    """Explicit preliminary type for callers that need lifecycle discrimination."""

    is_finalized: Literal[False] = False
    finalized_at: None = None
    approved_by: None = None
    content_hash: None = None


class FinalContractReport(ContractReport):
    """Final-only persistence boundary with statically required metadata."""

    is_finalized: Literal[True]
    finalized_at: datetime
    approved_by: str = Field(..., min_length=1)
    content_hash: str = Field(..., pattern=_HASH_PATTERN)
    conformance_checks: list[ConformanceCheck] = Field(..., min_length=1)

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_assignment=True,
    )


class _FrozenDict(dict[object, object]):
    """Dictionary that preserves read compatibility and rejects mutation."""

    @staticmethod
    def _blocked(*_args: object, **_kwargs: object) -> None:
        raise TypeError("Finalized ContractReport snapshots are immutable")

    __setitem__ = _blocked
    __delitem__ = _blocked
    clear = _blocked
    pop = _blocked
    popitem = _blocked  # type: ignore[assignment]
    setdefault = _blocked
    update = _blocked
    __ior__ = _blocked  # type: ignore[assignment]


class _FrozenList(list[object]):
    """List that preserves read compatibility and rejects mutation."""

    @staticmethod
    def _blocked(*_args: object, **_kwargs: object) -> None:
        raise TypeError("Finalized ContractReport snapshots are immutable")

    __setitem__ = _blocked
    __delitem__ = _blocked
    append = _blocked
    clear = _blocked
    extend = _blocked
    insert = _blocked
    pop = _blocked
    remove = _blocked
    reverse = _blocked
    sort = _blocked
    __iadd__ = _blocked  # type: ignore[assignment]
    __imul__ = _blocked  # type: ignore[assignment]


def _freeze_value(value: object) -> object:
    """Recursively replace mutable containers with read-compatible wrappers."""
    if isinstance(value, _FrozenDict | _FrozenList):
        return value
    if isinstance(value, dict):
        frozen_dict = _FrozenDict()
        for key, item in value.items():
            dict.__setitem__(frozen_dict, key, _freeze_value(item))
        return frozen_dict
    if isinstance(value, list):
        frozen_list = _FrozenList()
        for item in value:
            list.append(frozen_list, _freeze_value(item))
        return frozen_list
    if isinstance(value, tuple):
        return tuple(_freeze_value(item) for item in value)
    if isinstance(value, set):
        return frozenset(_freeze_value(item) for item in value)
    return value


def _without_derived_presentations(value: object) -> object:
    """Remove only known render derivatives, never same-named semantic extras."""
    if not isinstance(value, dict):
        return value
    payload = dict(value)
    for section_name, derived_keys in (
        ("timeline", ("mermaid", "table")),
        ("evidence_graph", ("mermaid",)),
    ):
        section = payload.get(section_name)
        if not isinstance(section, dict):
            continue
        section_without_rendering = dict(section)
        for key in derived_keys:
            section_without_rendering.pop(key, None)
        payload[section_name] = section_without_rendering
    return payload


def _hypothesis_probability(hypothesis: HypothesisRecord) -> float:
    """Return a safe sort key for persisted hypothesis payloads."""
    try:
        return float(hypothesis.get("current_probability", 0.0))
    except (TypeError, ValueError):
        return 0.0
