"""
Value Objects - Immutable domain primitives.

Value Objects are defined by their attributes rather than identity.
Two Value Objects with the same attributes are considered equal.
"""

from rootcause_mcp.domain.value_objects.case_manifest import (
    CaseInputManifest,
    SourceDocument,
    SourceReviewStatus,
)
from rootcause_mcp.domain.value_objects.enums import (
    CaseType,
    CausalLinkType,
    FishboneCategoryType,
    SessionStatus,
    Stage,
    StageStatus,
    TeachingLevel,
)
from rootcause_mcp.domain.value_objects.hfacs import HFACSCode, HFACSLevel
from rootcause_mcp.domain.value_objects.identifiers import CauseId, SessionId
from rootcause_mcp.domain.value_objects.scores import ConfidenceScore

__all__ = [
    "CaseInputManifest",
    "CaseType",
    "CausalLinkType",
    "CauseId",
    "ConfidenceScore",
    "FishboneCategoryType",
    "HFACSCode",
    "HFACSLevel",
    "SessionId",
    "SessionStatus",
    "SourceDocument",
    "SourceReviewStatus",
    "Stage",
    "StageStatus",
    "TeachingLevel",
]
