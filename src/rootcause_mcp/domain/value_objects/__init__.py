"""
Value Objects - Immutable domain primitives.

Value Objects are defined by their attributes rather than identity.
Two Value Objects with the same attributes are considered equal.
"""

from rootcause_mcp.domain.value_objects.identifiers import SessionId, CauseId
from rootcause_mcp.domain.value_objects.scores import ConfidenceScore
from rootcause_mcp.domain.value_objects.hfacs import HFACSCode, HFACSLevel
from rootcause_mcp.domain.value_objects.enums import (
    Stage,
    CaseType,
    SessionStatus,
    StageStatus,
    FishboneCategoryType,
)

__all__ = [
    "SessionId",
    "CauseId",
    "ConfidenceScore",
    "HFACSCode",
    "HFACSLevel",
    "Stage",
    "CaseType",
    "SessionStatus",
    "StageStatus",
    "FishboneCategoryType",
]
