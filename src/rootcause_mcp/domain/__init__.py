"""
Domain Layer - RootCause MCP

This layer contains the core business logic and domain models.
No external dependencies allowed (pure Python + Pydantic only).
"""

from rootcause_mcp.domain.entities import (
    RCASession,
    Cause,
    FishboneCategory,
    FishboneCause,
    WhyNode,
)
from rootcause_mcp.domain.value_objects import (
    SessionId,
    CauseId,
    ConfidenceScore,
    HFACSCode,
    HFACSLevel,
    Stage,
    CaseType,
    SessionStatus,
    StageStatus,
    FishboneCategoryType,
)
from rootcause_mcp.domain.repositories import (
    SessionRepository,
    CauseRepository,
    FishboneRepository,
)
from rootcause_mcp.domain.services import (
    HFACSSuggester,
    CausationValidator,
)

__all__ = [
    # Entities
    "RCASession",
    "Cause",
    "FishboneCategory",
    "FishboneCause",
    "WhyNode",
    # Value Objects
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
    # Repositories
    "SessionRepository",
    "CauseRepository",
    "FishboneRepository",
    # Services
    "HFACSSuggester",
    "CausationValidator",
]
