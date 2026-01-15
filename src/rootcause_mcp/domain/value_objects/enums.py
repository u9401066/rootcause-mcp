"""
Domain Enumerations.

Strongly-typed enums for domain concepts.
"""

from enum import Enum, auto


class Stage(str, Enum):
    """RCA Process Stages (6-stage model)."""

    GATHER = "GATHER"
    CONTEXTUALIZE = "CONTEXTUALIZE"
    ANALYZE = "ANALYZE"
    FISHBONE = "FISHBONE"
    VERIFY = "VERIFY"
    ACTION = "ACTION"

    @classmethod
    def first(cls) -> "Stage":
        """Return the first stage."""
        return cls.GATHER

    @classmethod
    def last(cls) -> "Stage":
        """Return the last stage."""
        return cls.ACTION

    def next(self) -> "Stage | None":
        """Return the next stage, or None if this is the last."""
        stages = list(Stage)
        idx = stages.index(self)
        if idx + 1 < len(stages):
            return stages[idx + 1]
        return None

    def previous(self) -> "Stage | None":
        """Return the previous stage, or None if this is the first."""
        stages = list(Stage)
        idx = stages.index(self)
        if idx > 0:
            return stages[idx - 1]
        return None

    def can_transition_to(self, target: "Stage") -> bool:
        """Check if transition to target stage is allowed."""
        stages = list(Stage)
        current_idx = stages.index(self)
        target_idx = stages.index(target)

        # Can only move forward by one step, or backward (rollback)
        return target_idx == current_idx + 1 or target_idx < current_idx


class CaseType(str, Enum):
    """RCA Case Types."""

    DEATH = "death"  # 死亡案例
    COMPLICATION = "complication"  # 併發症
    NEAR_MISS = "near_miss"  # Near Miss
    SAFETY = "safety"  # 病安事件
    STAFFING = "staffing"  # 人力問題


class SessionStatus(str, Enum):
    """Session Status."""

    ACTIVE = "active"  # 進行中
    COMPLETED = "completed"  # 已完成
    ABANDONED = "abandoned"  # 已放棄
    ARCHIVED = "archived"  # 已歸檔


class StageStatus(str, Enum):
    """Stage Status within a Session."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class FishboneCategoryType(str, Enum):
    """
    Fishbone 6M Categories (Clinical Version).

    Traditional 6M adapted for healthcare context.
    """

    PERSONNEL = "Personnel"  # 人員 (Man)
    EQUIPMENT = "Equipment"  # 設備 (Machine)
    MATERIAL = "Material"  # 物料 (Material)
    PROCESS = "Process"  # 流程 (Method)
    ENVIRONMENT = "Environment"  # 環境 (Mother Nature)
    MONITORING = "Monitoring"  # 監測 (Measurement)

    @classmethod
    def all_categories(cls) -> list["FishboneCategoryType"]:
        """Return all 6M categories."""
        return list(cls)


class VerificationResult(str, Enum):
    """Causation Verification Result."""

    VERIFIED = "VERIFIED"  # 因果關係已驗證
    VERIFIED_WITH_CAVEATS = "VERIFIED_WITH_CAVEATS"  # 有條件驗證
    REJECTED = "REJECTED"  # 因果關係被拒絕
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"  # 資料不足


class CausalStrength(str, Enum):
    """Causal Relationship Strength."""

    ROOT_CAUSE = "root_cause"  # 根本原因
    CONTRIBUTING_FACTOR = "contributing_factor"  # 貢獻因素
    CONTEXTUAL_FACTOR = "contextual_factor"  # 背景因素
    NOT_CAUSAL = "not_causal"  # 非因果


class Priority(str, Enum):
    """Action Item Priority."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ActionStatus(str, Enum):
    """Action Item Status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
