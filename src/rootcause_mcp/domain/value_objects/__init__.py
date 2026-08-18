"""
Value Objects - Immutable domain primitives.

Value Objects are defined by their attributes rather than identity.
Two Value Objects with the same attributes are considered equal.
"""

from rootcause_mcp.domain.value_objects.case_manifest import (
    CaseInputManifest,
    SourceDocument,
    SourceIndependenceStatus,
    SourceReviewAdjudication,
    SourceReviewStatus,
)
from rootcause_mcp.domain.value_objects.clinical_temporal import (
    ClinicalTemporal,
    ClinicalTemporalKind,
    ClinicalTemporalPrecision,
    TimezoneProvenance,
)
from rootcause_mcp.domain.value_objects.differential_breadth import (
    BreadthCellStatus,
    DifferentialBreadthAudit,
    DifferentialBreadthFramework,
)
from rootcause_mcp.domain.value_objects.enums import (
    CaseType,
    CausalLinkType,
    FishboneCategoryType,
    HFACSReviewStatus,
    SessionStatus,
    Stage,
    StageStatus,
    TeachingLevel,
)
from rootcause_mcp.domain.value_objects.hfacs import HFACSCode, HFACSLevel
from rootcause_mcp.domain.value_objects.identifiers import CauseId, SessionId
from rootcause_mcp.domain.value_objects.leading_hypothesis import (
    LeadingHypothesisSelection,
)
from rootcause_mcp.domain.value_objects.scores import ConfidenceScore

__all__ = [
    "BreadthCellStatus",
    "CaseInputManifest",
    "CaseType",
    "CausalLinkType",
    "CauseId",
    "ClinicalTemporal",
    "ClinicalTemporalKind",
    "ClinicalTemporalPrecision",
    "ConfidenceScore",
    "DifferentialBreadthAudit",
    "DifferentialBreadthFramework",
    "FishboneCategoryType",
    "HFACSCode",
    "HFACSLevel",
    "HFACSReviewStatus",
    "LeadingHypothesisSelection",
    "SessionId",
    "SessionStatus",
    "SourceDocument",
    "SourceIndependenceStatus",
    "SourceReviewAdjudication",
    "SourceReviewStatus",
    "Stage",
    "StageStatus",
    "TeachingLevel",
    "TimezoneProvenance",
]
