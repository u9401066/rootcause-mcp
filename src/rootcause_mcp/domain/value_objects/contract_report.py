"""Typed, content-hashed contract report for clinical reasoning."""

from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Collection, Mapping, Sequence
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal, Self

from jsonschema import Draft202012Validator, FormatChecker
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    ValidationInfo,
    field_serializer,
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
    DifferentialBreadthAuditRecord,
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
    SourceReviewLedgerRecord,
    ThinkingStepRecord,
    TimelineRecord,
    WhyTreeRecord,
)

_HASH_PATTERN = r"^[0-9a-f]{64}$"
_CLINICAL_TEMPORAL_FINAL_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "kind",
        "raw_value",
        "precision",
        "normalized_start",
        "normalized_end",
        "timezone_provenance",
    ],
    "properties": {
        "kind": {
            "type": "string",
            "enum": ["instant", "date", "range", "relative", "unknown"],
        },
        "raw_value": {"type": ["string", "null"]},
        "precision": {
            "type": "string",
            "enum": [
                "day",
                "minute",
                "second",
                "subsecond",
                "relative",
                "unknown",
            ],
        },
        "normalized_start": {"type": ["string", "null"]},
        "normalized_end": {"type": ["string", "null"]},
        "timezone_provenance": {
            "type": "string",
            "enum": [
                "source_explicit_offset",
                "not_applicable",
                "source_local_unknown",
                "unknown",
            ],
        },
    },
    "allOf": [
        {
            "if": {"properties": {"kind": {"const": "instant"}}},
            "then": {
                "properties": {
                    "raw_value": {"type": "string", "minLength": 1},
                    "precision": {"enum": ["minute", "second", "subsecond"]},
                    "normalized_start": {
                        "type": "string",
                        "format": "date-time",
                    },
                    "normalized_end": {
                        "type": "string",
                        "format": "date-time",
                    },
                    "timezone_provenance": {"const": "source_explicit_offset"},
                }
            },
        },
        {
            "if": {"properties": {"kind": {"const": "date"}}},
            "then": {
                "properties": {
                    "raw_value": {"type": "string", "format": "date"},
                    "precision": {"const": "day"},
                    "normalized_start": {"type": "string", "format": "date"},
                    "normalized_end": {"type": "string", "format": "date"},
                    "timezone_provenance": {"const": "not_applicable"},
                }
            },
        },
        {
            "if": {"properties": {"kind": {"const": "range"}}},
            "then": {
                "properties": {
                    "raw_value": {"type": "string", "minLength": 1},
                    "normalized_start": {"type": "string", "minLength": 1},
                    "normalized_end": {"type": "string", "minLength": 1},
                }
            },
        },
        {
            "if": {"properties": {"kind": {"const": "relative"}}},
            "then": {
                "properties": {
                    "raw_value": {"type": "string", "minLength": 1},
                    "precision": {"const": "relative"},
                    "normalized_start": {"type": "null"},
                    "normalized_end": {"type": "null"},
                    "timezone_provenance": {"const": "not_applicable"},
                }
            },
        },
        {
            "if": {"properties": {"kind": {"const": "unknown"}}},
            "then": {
                "properties": {
                    "precision": {"const": "unknown"},
                    "normalized_start": {"type": "null"},
                    "normalized_end": {"type": "null"},
                    "timezone_provenance": {
                        "enum": ["source_local_unknown", "unknown"]
                    },
                }
            },
        },
    ],
}
_FINAL_METADATA_FIELDS = (
    "approved_by",
    "finalized_at",
    "content_hash",
    "conformance_checks",
)
_FINAL_REQUIRED_FIELDS = (*_FINAL_METADATA_FIELDS, "leading_hypothesis_id")
_CANONICAL_HASH_EXCLUDES = {"content_hash"}
_CORE_FINAL_CHECK_CODES = frozenset(
    {
        "TYPED_REPORT_SCHEMA",
        "FINALIZATION_METADATA_COMPLETE",
        "CONTENT_HASH_RECOMPUTABLE",
    }
)
_NORMALIZED_REPORT_FIELDS = (
    "report_id",
    "session_id",
    "report_version",
    "generated_at",
    "finalized_at",
    "hypotheses",
    "leading_hypothesis_id",
    "differential_breadth_audits",
    "evidence",
    "source_inventory",
    "source_review_ledger",
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

    @field_serializer("refs", "details")
    def serialize_frozen_containers(self, value: object) -> object:
        """Expose ordinary JSON containers without weakening runtime immutability."""
        return _thaw_value(value)


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
    report_version: str = Field(default="2.0.0a2", description="Report format version")

    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    finalized_at: datetime | None = Field(default=None)

    hypotheses: list[HypothesisRecord] = Field(default_factory=list)
    leading_hypothesis_id: str | None = Field(
        default=None,
        description=(
            "Explicit working lead selected through the audited DDx mutation; "
            "never inferred from list order or an uncalibrated numeric value"
        ),
    )
    differential_breadth_audits: list[DifferentialBreadthAuditRecord] = Field(
        default_factory=list
    )
    evidence: list[EvidenceRecord] = Field(default_factory=list)
    source_inventory: list[SourceInventoryRecord] = Field(default_factory=list)
    source_review_ledger: list[SourceReviewLedgerRecord] = Field(default_factory=list)
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
                        "required": list(_FINAL_REQUIRED_FIELDS),
                        "properties": {
                            "leading_hypothesis_id": {
                                "type": "string",
                                "minLength": 1,
                            },
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
                                        "probability_semantics",
                                        "clinical_probability_established",
                                        "must_not_miss",
                                        "mechanism_category",
                                        "diagnostic_role",
                                        "certainty",
                                        "reasoning_basis",
                                        "uncertainty_factors",
                                        "supporting_evidence_ids",
                                        "contradicting_evidence_ids",
                                        "status",
                                        "clinical_rationale",
                                    ],
                                    "properties": {
                                        "probability_semantics": {
                                            "const": "UNCALIBRATED_COMPATIBILITY_ONLY"
                                        },
                                        "clinical_probability_established": {
                                            "const": False
                                        },
                                        "diagnosis": {
                                            "required": ["code", "display", "system"],
                                            "properties": {
                                                "code": {
                                                    "type": "string",
                                                    "minLength": 1,
                                                },
                                                "display": {
                                                    "type": "string",
                                                    "minLength": 1,
                                                },
                                                "system": {
                                                    "type": "string",
                                                    "minLength": 1,
                                                },
                                            },
                                        },
                                        "likelihood_ratios": {
                                            "items": {
                                                "required": [
                                                    "evidence_id",
                                                    "applied_likelihood_ratio",
                                                    "supports",
                                                    "rationale",
                                                    "calibration_status",
                                                    "calibration_source_ref",
                                                ],
                                                "properties": {
                                                    "applied_likelihood_ratio": {
                                                        "type": "number",
                                                        "exclusiveMinimum": 0,
                                                        "maximum": 100,
                                                    },
                                                    "calibration_status": {
                                                        "enum": [
                                                            "SOURCE_CALIBRATED",
                                                            "QUANTITATIVELY_UNKNOWN",
                                                        ]
                                                    },
                                                    "calibration_source_ref": {
                                                        "anyOf": [
                                                            {
                                                                "type": "string",
                                                                "minLength": 1,
                                                            },
                                                            {"type": "null"},
                                                        ]
                                                    },
                                                },
                                            }
                                        },
                                        "planned_tests": {
                                            "items": {
                                                "required": [
                                                    "test_id",
                                                    "name",
                                                    "purpose",
                                                    "target_hypothesis_id",
                                                    "expected_supporting_result",
                                                    "expected_refuting_result",
                                                    "status",
                                                ]
                                            }
                                        },
                                    },
                                },
                            },
                            "differential_breadth_audits": {
                                "minItems": 1,
                                "items": {
                                    "required": [
                                        "audit_id",
                                        "framework",
                                        "framework_rationale",
                                        "role",
                                        "cells",
                                        "stop_rationale",
                                        "recorded_by",
                                        "recorded_at",
                                    ],
                                    "properties": {
                                        "cells": {
                                            "minItems": 3,
                                            "items": {
                                                "required": [
                                                    "cell_id",
                                                    "status",
                                                    "hypothesis_ids",
                                                    "mechanism_categories",
                                                    "rationale",
                                                    "unknowns",
                                                    "planned_discriminators",
                                                ]
                                            },
                                        }
                                    },
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
                                        "temporal",
                                        "event_timestamp",
                                        "verified",
                                        "verifier",
                                        "verification_method",
                                    ],
                                    "properties": {
                                        "verified": {"const": True},
                                        "verifier": {
                                            "type": "string",
                                            "minLength": 1,
                                        },
                                        "verification_method": {
                                            "type": "string",
                                            "minLength": 1,
                                        },
                                        "temporal": _CLINICAL_TEMPORAL_FINAL_SCHEMA,
                                        "quality": {
                                            "required": ["strength", "reliability"],
                                            "properties": {
                                                "strength": {
                                                    "type": "string",
                                                    "minLength": 1,
                                                },
                                                "reliability": {
                                                    "type": "string",
                                                    "minLength": 1,
                                                },
                                            },
                                        },
                                        "source": {
                                            "required": [
                                                "document_id",
                                                "location",
                                                "raw_snippet",
                                                "content_hash",
                                                "extraction_method",
                                                "collected_by",
                                                "collection_timestamp",
                                            ],
                                            "properties": {
                                                "document_id": {
                                                    "type": "string",
                                                    "minLength": 1,
                                                },
                                                "location": {
                                                    "type": "string",
                                                    "minLength": 1,
                                                },
                                                "raw_snippet": {
                                                    "type": "string",
                                                    "minLength": 1,
                                                },
                                                "content_hash": {
                                                    "type": "string",
                                                    "pattern": _HASH_PATTERN,
                                                },
                                                "extraction_method": {
                                                    "type": "string",
                                                    "minLength": 1,
                                                },
                                                "collected_by": {
                                                    "type": "string",
                                                    "minLength": 1,
                                                },
                                            },
                                        },
                                    },
                                    "allOf": [
                                        {
                                            "if": {
                                                "properties": {
                                                    "temporal": {
                                                        "properties": {
                                                            "kind": {"const": "instant"}
                                                        }
                                                    }
                                                }
                                            },
                                            "then": {
                                                "properties": {
                                                    "event_timestamp": {
                                                        "type": "string",
                                                        "format": "date-time",
                                                    }
                                                }
                                            },
                                            "else": {
                                                "properties": {
                                                    "event_timestamp": {"type": "null"}
                                                }
                                            },
                                        }
                                    ],
                                },
                            },
                            "source_inventory": {
                                "minItems": 2,
                                "items": {
                                    "required": [
                                        "document",
                                        "source_uri",
                                        "sha256",
                                        "media_type",
                                        "source_kind",
                                        "de_identified",
                                        "evidence_count",
                                        "verified_count",
                                        "coverage_status",
                                        "independence_status",
                                        "source_group_id",
                                        "parent_document_id",
                                        "derivation_method",
                                        "source_review_adjudication_id",
                                        "source_reviewed_by",
                                        "source_reviewed_at",
                                        "source_review_reason",
                                    ],
                                    "properties": {
                                        "document": {
                                            "type": "string",
                                            "minLength": 1,
                                        },
                                        "sha256": {
                                            "type": "string",
                                            "pattern": _HASH_PATTERN,
                                        },
                                        "source_uri": {
                                            "type": "string",
                                            "minLength": 1,
                                        },
                                        "media_type": {
                                            "type": "string",
                                            "minLength": 1,
                                        },
                                        "source_kind": {
                                            "type": "string",
                                            "minLength": 1,
                                        },
                                        "de_identified": {"const": True},
                                        "evidence_count": {
                                            "type": "integer",
                                            "minimum": 0,
                                        },
                                        "verified_count": {
                                            "type": "integer",
                                            "minimum": 0,
                                        },
                                        "coverage_status": {"const": "reviewed"},
                                        "source_review_adjudication_id": {
                                            "type": "string",
                                            "minLength": 1,
                                        },
                                        "source_reviewed_by": {
                                            "type": "string",
                                            "minLength": 1,
                                        },
                                        "source_reviewed_at": {
                                            "type": "string",
                                            "format": "date-time",
                                        },
                                        "source_review_reason": {
                                            "type": "string",
                                            "minLength": 1,
                                        },
                                    },
                                },
                            },
                            "source_review_ledger": {
                                "type": "array",
                                "minItems": 2,
                                "items": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "required": [
                                        "adjudication_id",
                                        "manifest_digest",
                                        "document_id",
                                        "status",
                                        "de_identified",
                                        "independence_status",
                                        "source_group_id",
                                        "parent_document_id",
                                        "derivation_method",
                                        "reviewed_by",
                                        "reason",
                                        "reviewed_at",
                                    ],
                                    "properties": {
                                        "adjudication_id": {
                                            "type": "string",
                                            "pattern": "^SRV-[A-Za-z0-9._-]+$",
                                        },
                                        "manifest_digest": {
                                            "type": "string",
                                            "pattern": "^sha256:[0-9a-fA-F]{64}$",
                                        },
                                        "document_id": {
                                            "type": "string",
                                            "minLength": 1,
                                        },
                                        "status": {
                                            "enum": [
                                                "extracted",
                                                "reviewed",
                                                "failed",
                                            ]
                                        },
                                        "de_identified": {"type": ["boolean", "null"]},
                                        "independence_status": {
                                            "enum": [
                                                "unknown",
                                                "independent",
                                                "derived",
                                            ]
                                        },
                                        "source_group_id": {"type": ["string", "null"]},
                                        "parent_document_id": {
                                            "type": ["string", "null"]
                                        },
                                        "derivation_method": {
                                            "type": ["string", "null"]
                                        },
                                        "reviewed_by": {
                                            "type": "string",
                                            "minLength": 1,
                                        },
                                        "reason": {
                                            "type": "string",
                                            "minLength": 1,
                                        },
                                        "reviewed_at": {
                                            "type": "string",
                                            "format": "date-time",
                                        },
                                    },
                                },
                            },
                            "timeline": {
                                "type": "object",
                                "required": ["events"],
                                "properties": {
                                    "events": {
                                        "minItems": 1,
                                        "items": {
                                            "required": [
                                                "id",
                                                "time",
                                                "phase",
                                                "content",
                                                "source_document",
                                                "verified",
                                                "evidence_type",
                                                "temporal",
                                                "chronology_status",
                                            ],
                                            "properties": {
                                                "time": {
                                                    "type": "string",
                                                    "minLength": 1,
                                                },
                                                "source_document": {
                                                    "type": "string",
                                                    "minLength": 1,
                                                },
                                                "temporal": (
                                                    _CLINICAL_TEMPORAL_FINAL_SCHEMA
                                                ),
                                                "chronology_status": {
                                                    "type": "string",
                                                    "enum": [
                                                        "ORDERED_INSTANT",
                                                        "UNPOSITIONED",
                                                    ],
                                                },
                                            },
                                            "allOf": [
                                                {
                                                    "if": {
                                                        "properties": {
                                                            "temporal": {
                                                                "properties": {
                                                                    "kind": {
                                                                        "const": "instant"
                                                                    }
                                                                }
                                                            }
                                                        }
                                                    },
                                                    "then": {
                                                        "properties": {
                                                            "chronology_status": {
                                                                "const": "ORDERED_INSTANT"
                                                            }
                                                        }
                                                    },
                                                    "else": {
                                                        "properties": {
                                                            "chronology_status": {
                                                                "const": "UNPOSITIONED"
                                                            }
                                                        }
                                                    },
                                                }
                                            ],
                                        },
                                    }
                                },
                            },
                            "rca_session": {
                                "type": "object",
                                "required": [
                                    "source_manifest_digest",
                                    "source_document_count",
                                    "source_review_event_count",
                                ],
                                "properties": {
                                    "source_manifest_digest": {
                                        "type": "string",
                                        "pattern": "^sha256:[0-9a-fA-F]{64}$",
                                    },
                                    "source_document_count": {
                                        "type": "integer",
                                        "minimum": 1,
                                    },
                                    "source_review_event_count": {
                                        "type": "integer",
                                        "minimum": 1,
                                    },
                                },
                            },
                            "fishbone": {
                                "type": "object",
                                "required": [
                                    "fishbone_id",
                                    "problem_statement",
                                    "categories",
                                ],
                                "properties": {
                                    "categories": {
                                        "minItems": 1,
                                        "items": {
                                            "required": ["category", "causes"],
                                            "properties": {
                                                "category": {
                                                    "type": "string",
                                                    "minLength": 1,
                                                },
                                                "causes": {
                                                    "minItems": 1,
                                                    "items": {
                                                        "required": [
                                                            "cause_id",
                                                            "description",
                                                            "hfacs_code",
                                                            "hfacs_review_status",
                                                            "hfacs_reviewed_by",
                                                            "hfacs_reviewed_at",
                                                            "hfacs_review_reason",
                                                            "evidence",
                                                        ],
                                                        "properties": {
                                                            "cause_id": {
                                                                "type": "string",
                                                                "minLength": 1,
                                                            },
                                                            "description": {
                                                                "type": "string",
                                                                "minLength": 1,
                                                            },
                                                            "hfacs_review_status": {
                                                                "enum": [
                                                                    "CONFIRMED",
                                                                    "NOT_APPLICABLE",
                                                                ]
                                                            },
                                                            "hfacs_reviewed_by": {
                                                                "type": "string",
                                                                "minLength": 1,
                                                            },
                                                            "hfacs_reviewed_at": {
                                                                "type": "string",
                                                                "format": "date-time",
                                                            },
                                                            "hfacs_review_reason": {
                                                                "type": "string",
                                                                "minLength": 1,
                                                            },
                                                        },
                                                        "allOf": [
                                                            {
                                                                "if": {
                                                                    "properties": {
                                                                        "hfacs_review_status": {
                                                                            "const": "CONFIRMED"
                                                                        }
                                                                    }
                                                                },
                                                                "then": {
                                                                    "properties": {
                                                                        "hfacs_code": {
                                                                            "type": "string",
                                                                            "minLength": 1,
                                                                        }
                                                                    }
                                                                },
                                                                "else": {
                                                                    "properties": {
                                                                        "hfacs_code": {
                                                                            "type": "null"
                                                                        }
                                                                    }
                                                                },
                                                            }
                                                        ],
                                                    },
                                                },
                                            },
                                        },
                                    }
                                },
                            },
                            "why_tree": {"type": "object"},
                            "root_causes": {
                                # Cross-ledger conformance permits an empty
                                # admitted-root bucket only when every persisted
                                # Why root has a matching latest REJECTED audit.
                                "minItems": 0,
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
                                        "verification_level",
                                        "cause_event",
                                        "effect_event",
                                        "tests",
                                        "overall_result",
                                        "interpretation",
                                        "next_steps",
                                        "audit_scope",
                                        "clinical_causality_established",
                                    ],
                                    "properties": {
                                        "verification_level": {
                                            "enum": ["standard", "comprehensive"]
                                        },
                                        "cause_event": {
                                            "required": [
                                                "id",
                                                "description",
                                                "evidence",
                                            ],
                                            "properties": {
                                                "description": {
                                                    "type": "string",
                                                    "minLength": 1,
                                                },
                                                "evidence": {"minItems": 1},
                                            },
                                        },
                                        "effect_event": {
                                            "required": ["description", "evidence"],
                                            "properties": {
                                                "description": {
                                                    "type": "string",
                                                    "minLength": 1,
                                                },
                                                "evidence": {"minItems": 1},
                                            },
                                        },
                                        "tests": {
                                            "type": "object",
                                            "required": ["temporality"],
                                            "properties": {
                                                "temporality": {
                                                    "type": "object",
                                                    "required": [
                                                        "passed",
                                                        "conclusion",
                                                    ],
                                                },
                                                "necessity": {
                                                    "type": "object",
                                                    "required": [
                                                        "passed",
                                                        "counterfactual_question",
                                                        "counterfactual_answer",
                                                        "reasoning",
                                                    ],
                                                },
                                                "mechanism": {
                                                    "anyOf": [
                                                        {"type": "object"},
                                                        {"type": "null"},
                                                    ]
                                                },
                                                "sufficiency": {
                                                    "anyOf": [
                                                        {"type": "object"},
                                                        {"type": "null"},
                                                    ]
                                                },
                                            },
                                        },
                                        "interpretation": {
                                            "type": "string",
                                            "minLength": 1,
                                        },
                                        "next_steps": {
                                            "type": "array",
                                            "minItems": 1,
                                            "items": {
                                                "type": "string",
                                                "minLength": 1,
                                            },
                                        },
                                    },
                                    "allOf": [
                                        {
                                            "if": {
                                                "properties": {
                                                    "overall_result": {
                                                        "not": {"const": "REJECTED"}
                                                    }
                                                }
                                            },
                                            "then": {
                                                "properties": {
                                                    "tests": {"required": ["necessity"]}
                                                }
                                            },
                                        },
                                        {
                                            "if": {
                                                "properties": {
                                                    "verification_level": {
                                                        "const": "comprehensive"
                                                    },
                                                    "overall_result": {
                                                        "not": {"const": "REJECTED"}
                                                    },
                                                }
                                            },
                                            "then": {
                                                "properties": {
                                                    "tests": {
                                                        "required": [
                                                            "mechanism",
                                                            "sufficiency",
                                                        ],
                                                        "properties": {
                                                            "mechanism": {
                                                                "type": "object"
                                                            },
                                                            "sufficiency": {
                                                                "type": "object"
                                                            },
                                                        },
                                                    }
                                                }
                                            },
                                        },
                                    ],
                                },
                            },
                            "hfacs_classifications": {
                                "minItems": 1,
                                "items": {
                                    "required": [
                                        "cause_id",
                                        "cause",
                                        "category",
                                        "hfacs_code",
                                        "review_status",
                                        "reviewed_by",
                                        "reviewed_at",
                                        "review_reason",
                                        "evidence",
                                        "source",
                                    ],
                                    "properties": {
                                        "cause_id": {
                                            "type": "string",
                                            "minLength": 1,
                                        },
                                        "cause": {
                                            "type": "string",
                                            "minLength": 1,
                                        },
                                        "category": {
                                            "type": "string",
                                            "minLength": 1,
                                        },
                                        "review_status": {
                                            "enum": [
                                                "CONFIRMED",
                                                "NOT_APPLICABLE",
                                            ]
                                        },
                                        "reviewed_by": {
                                            "type": "string",
                                            "minLength": 1,
                                        },
                                        "reviewed_at": {
                                            "type": "string",
                                            "format": "date-time",
                                        },
                                        "review_reason": {
                                            "type": "string",
                                            "minLength": 1,
                                        },
                                        "source": {"const": "fishbone_cause"},
                                    },
                                    "allOf": [
                                        {
                                            "if": {
                                                "properties": {
                                                    "review_status": {
                                                        "const": "CONFIRMED"
                                                    }
                                                }
                                            },
                                            "then": {
                                                "properties": {
                                                    "hfacs_code": {
                                                        "type": "string",
                                                        "minLength": 1,
                                                    }
                                                }
                                            },
                                            "else": {
                                                "properties": {
                                                    "hfacs_code": {"type": "null"}
                                                }
                                            },
                                        }
                                    ],
                                },
                            },
                            "gap_analysis": {"type": "object"},
                            "report_readiness": {
                                "type": "object",
                                "required": [
                                    "session_id",
                                    "current_stage",
                                    "stage_display",
                                    "completeness_score",
                                    "checklist",
                                    "missing_prerequisites",
                                    "next_recommended_actions",
                                    "push_questions",
                                    "is_ready_for_report",
                                ],
                                "properties": {
                                    "session_id": {
                                        "type": "string",
                                        "minLength": 1,
                                    },
                                    "current_stage": {"const": "READY_FOR_SYNTHESIS"},
                                    "stage_display": {
                                        "type": "string",
                                        "minLength": 1,
                                    },
                                    "completeness_score": {
                                        "type": "number",
                                        "minimum": 0.9,
                                        "maximum": 1.0,
                                    },
                                    "checklist": {"type": "object"},
                                    "missing_prerequisites": {
                                        "type": "array",
                                        "maxItems": 0,
                                    },
                                    "next_recommended_actions": {
                                        "type": "array",
                                        "minItems": 1,
                                    },
                                    "push_questions": {
                                        "type": "array",
                                        "minItems": 1,
                                    },
                                    "is_ready_for_report": {"const": True},
                                },
                            },
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

    @field_serializer("*")
    def serialize_frozen_fields(self, value: object) -> object:
        """Serialize immutable Mapping/Sequence wrappers as ordinary JSON values."""
        return _thaw_value(value)

    @model_validator(mode="after")
    def validate_lifecycle_state(self, info: ValidationInfo) -> Self:
        """Validate conditional final metadata and freeze loaded snapshots."""
        if not self.is_finalized:
            if self.finalized_at is not None or self.content_hash is not None:
                raise ValueError(
                    "Preliminary reports cannot carry finalization time or hash"
                )
            if self.approved_by is not None:
                raise ValueError("Preliminary reports cannot carry approved_by")
            return self
        context = info.context if isinstance(info.context, Mapping) else {}
        authorized_reviewers = context.get("authorized_reviewers")
        if not isinstance(authorized_reviewers, Collection) or isinstance(
            authorized_reviewers, str | bytes | Mapping
        ):
            raise ValueError(
                "Loading a final report requires operator-controlled "
                "authorized_reviewers validation context"
            )
        self._assert_final_requirements(
            authorized_reviewers=[str(item) for item in authorized_reviewers]
        )
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
        authorized_reviewers: Collection[str] | None,
        finalized_at: datetime | None = None,
    ) -> None:
        """Authorize, hash, and recursively freeze one final snapshot."""
        if self.is_finalized:
            raise ValueError("Report already finalized")

        if not isinstance(finalized_by, str):
            raise ValueError("finalized_by must identify a reviewer")
        reviewer = finalized_by.strip()
        if not reviewer:
            raise ValueError("finalized_by must identify a reviewer")
        if authorized_reviewers is None:
            raise ValueError("authorized_reviewers cannot be None")
        authorized = {
            str(item).strip().casefold()
            for item in authorized_reviewers
            if str(item).strip()
        }
        if not authorized:
            raise ValueError("authorized_reviewers cannot be empty")
        if reviewer.casefold() not in authorized:
            raise ValueError("finalized_by is not in authorized_reviewers")
        timestamp = finalized_at or datetime.now(UTC)
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("finalized_at must include an explicit timezone")
        if self.generated_at.tzinfo is None or self.generated_at.utcoffset() is None:
            raise ValueError("generated_at must include an explicit timezone")
        if timestamp < self.generated_at:
            raise ValueError("finalized_at cannot precede generated_at")

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
            authorized_reviewers=authorized_reviewers,
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

        candidate = self.model_dump(mode="json", warnings=False)
        candidate.update(
            {
                "approved_by": reviewer,
                "reviewed_by": reviewed_by,
                "finalized_at": timestamp.isoformat(),
                "conformance_checks": [
                    check.model_dump(mode="json") for check in checks
                ],
                "is_finalized": True,
                # The integrity digest excludes itself.  A shape-valid sentinel
                # lets the final-only schema run before mutating this instance.
                "content_hash": "0" * 64,
            }
        )
        _validate_final_schema_payload(candidate)

        object.__setattr__(self, "approved_by", reviewer)
        object.__setattr__(self, "reviewed_by", reviewed_by)
        object.__setattr__(self, "finalized_at", timestamp)
        object.__setattr__(self, "conformance_checks", checks)
        object.__setattr__(self, "is_finalized", True)
        object.__setattr__(self, "content_hash", self.compute_content_hash())

        self._assert_final_requirements(authorized_reviewers=authorized_reviewers)
        self._freeze_snapshot()

    def canonical_content(self) -> str:
        """Return the stable JSON string used as content-hash input."""
        payload = self.model_dump(
            mode="json",
            exclude=_CANONICAL_HASH_EXCLUDES,
            warnings=False,
        )
        return json.dumps(
            payload,
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

    def to_final_snapshot(
        self,
        *,
        authorized_reviewers: Collection[str],
    ) -> FinalContractReport:
        """Return the final-only validation type for persistence boundaries."""
        if not self.is_finalized:
            raise ValueError("Preliminary reports do not have a final snapshot")
        return FinalContractReport.model_validate(
            self.model_dump(mode="json"),
            context={"authorized_reviewers": authorized_reviewers},
        )

    def ranked_conclusion_hypotheses(self) -> list[HypothesisRecord]:
        """Return the explicit lead first, followed by eligible ledger entries.

        No implicit lead is inferred from list order, qualitative certainty, or
        numeric compatibility state. Preliminary reports without an audited
        selection therefore have no conclusion hypotheses.
        """
        ineligible_statuses = {"EXCLUDED", "ON_HOLD", "RULED_OUT"}
        eligible = [
            hypothesis
            for hypothesis in self.hypotheses
            if str(hypothesis.get("status") or "").upper() not in ineligible_statuses
        ]
        if not self.leading_hypothesis_id:
            return []
        selected = next(
            (
                hypothesis
                for hypothesis in eligible
                if _stable_record_id(hypothesis.get("id")) == self.leading_hypothesis_id
            ),
            None,
        )
        if selected is None:
            return []
        return [selected, *(item for item in eligible if item is not selected)]

    def _assert_final_requirements(
        self,
        *,
        authorized_reviewers: Collection[str],
    ) -> None:
        """Raise when a purported final snapshot is incomplete or altered."""
        if not self.approved_by or not self.approved_by.strip():
            raise ValueError("Final reports require approved_by")
        if self.approved_by not in self.reviewed_by:
            raise ValueError("Final approved_by must also appear in reviewed_by")
        if self.finalized_at is None:
            raise ValueError("Final reports require finalized_at")
        if self.finalized_at.tzinfo is None or self.finalized_at.utcoffset() is None:
            raise ValueError("Final reports require a timezone-aware finalized_at")
        if self.generated_at.tzinfo is None or self.generated_at.utcoffset() is None:
            raise ValueError("Final reports require a timezone-aware generated_at")
        if self.finalized_at < self.generated_at:
            raise ValueError(
                "Final reports require finalized_at on or after generated_at"
            )
        if not self.content_hash:
            raise ValueError("Final reports require content_hash")
        if not self.conformance_checks:
            raise ValueError("Final reports require conformance_checks")
        _validate_final_schema_payload(self.model_dump(mode="json", warnings=False))
        supplied_core_checks = {
            check.code: check.model_dump(mode="json")
            for check in self.conformance_checks
            if check.code in _CORE_FINAL_CHECK_CODES
        }
        expected_core_checks = {
            check.code: check.model_dump(mode="json")
            for check in self._with_core_final_checks([])
            if check.code in _CORE_FINAL_CHECK_CODES
        }
        if supplied_core_checks != expected_core_checks:
            raise ValueError(
                "Final report lifecycle conformance checks are missing or altered"
            )
        recomputed_hard_checks = evaluate_final_report_conformance(
            self.model_dump(mode="json", warnings=False),
            approved_by=self.approved_by,
            authorized_reviewers=authorized_reviewers,
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
    leading_hypothesis_id: str = Field(..., min_length=1)
    finalized_at: datetime
    approved_by: str = Field(..., min_length=1)
    content_hash: str = Field(..., pattern=_HASH_PATTERN)
    conformance_checks: list[ConformanceCheck] = Field(..., min_length=1)

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_assignment=True,
    )


def _validate_final_schema_payload(payload: Mapping[str, Any]) -> None:
    """Validate a final candidate against the exact public Draft 2020-12 schema.

    Preliminary section records are intentionally forward-compatible and may be
    incomplete.  Finalization is the boundary where every stable nested field
    becomes mandatory; using the exported schema here prevents the runtime and
    the advertised MCP contract from disagreeing.
    """
    validator = Draft202012Validator(
        ContractReport.model_json_schema(),
        format_checker=FormatChecker(),
    )
    errors = sorted(
        validator.iter_errors(dict(payload)),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if not errors:
        return
    locations = []
    for error in errors[:12]:
        pointer = "#/" + "/".join(str(part) for part in error.absolute_path)
        locations.append(f"{pointer.rstrip('/') or '#/'}: {error.message}")
    if len(errors) > len(locations):
        locations.append(f"... and {len(errors) - len(locations)} more violation(s)")
    raise ValueError(
        "Cannot finalize; typed final report schema failed: " + "; ".join(locations)
    )


def _stable_record_id(value: object) -> str | None:
    """Normalize strong-ID dumps and plain strings without inventing an ID."""
    if isinstance(value, Mapping):
        value = value.get("value")
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


class _FrozenMapping(Mapping[object, object]):
    """Immutable mapping that is not vulnerable to unbound ``dict`` methods."""

    __slots__ = ("_items",)
    __hash__ = None  # type: ignore[assignment]
    _items: tuple[tuple[object, object], ...]

    def __init__(self, items: Sequence[tuple[object, object]]) -> None:
        object.__setattr__(self, "_items", tuple(items))

    def __getitem__(self, key: object) -> object:
        for candidate, value in self._items:
            if candidate == key:
                return value
        raise KeyError(key)

    @staticmethod
    def _blocked(*_args: object, **_kwargs: object) -> None:
        raise TypeError("Finalized ContractReport snapshots are immutable")

    __setitem__ = _blocked
    __delitem__ = _blocked
    clear = _blocked
    pop = _blocked
    popitem = _blocked
    setdefault = _blocked
    update = _blocked

    def __iter__(self):  # type: ignore[no-untyped-def]
        return (key for key, _value in self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __setattr__(self, _name: str, _value: object) -> None:
        raise TypeError("Finalized ContractReport snapshots are immutable")

    def __delattr__(self, _name: str) -> None:
        raise TypeError("Finalized ContractReport snapshots are immutable")

    def __repr__(self) -> str:
        return repr(dict(self._items))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Mapping) and dict(self.items()) == dict(other.items())


class _FrozenSequence(Sequence[object]):
    """Immutable sequence that is not vulnerable to unbound ``list`` methods."""

    __slots__ = ("_items",)
    __hash__ = None  # type: ignore[assignment]
    _items: tuple[object, ...]

    def __init__(self, items: Sequence[object]) -> None:
        object.__setattr__(self, "_items", tuple(items))

    def __getitem__(self, index):  # type: ignore[no-untyped-def]
        return self._items[index]

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

    def __len__(self) -> int:
        return len(self._items)

    def __setattr__(self, _name: str, _value: object) -> None:
        raise TypeError("Finalized ContractReport snapshots are immutable")

    def __delattr__(self, _name: str) -> None:
        raise TypeError("Finalized ContractReport snapshots are immutable")

    def __repr__(self) -> str:
        return repr(list(self._items))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Sequence) and list(self) == list(other)


def _freeze_value(value: object) -> object:
    """Recursively replace mutable containers with read-compatible wrappers."""
    if isinstance(value, _FrozenMapping | _FrozenSequence):
        return value
    if isinstance(value, Mapping):
        return _FrozenMapping(
            [(key, _freeze_value(item)) for key, item in value.items()]
        )
    if isinstance(value, list | tuple):
        return _FrozenSequence([_freeze_value(item) for item in value])
    if isinstance(value, set):
        return frozenset(_freeze_value(item) for item in value)
    return value


def _thaw_value(value: object) -> object:
    """Return serialization-only builtins for recursively frozen containers."""
    if isinstance(value, Mapping):
        return {key: _thaw_value(item) for key, item in value.items()}
    if isinstance(value, _FrozenSequence):
        return [_thaw_value(item) for item in value]
    return value
