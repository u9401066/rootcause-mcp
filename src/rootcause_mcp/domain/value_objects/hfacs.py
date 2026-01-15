"""
HFACS (Human Factors Analysis and Classification System) Value Objects.

HFACS-MES: Medical Event Specialization
Based on Shappell & Wiegmann (2000) adapted for healthcare.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Self


class HFACSLevel(str, Enum):
    """HFACS-MES Five-Level Hierarchy (based on Jalali et al. 2024)."""

    LEVEL_1 = "Level 1"  # Unsafe Acts (不安全行為)
    LEVEL_2 = "Level 2"  # Preconditions for Unsafe Acts (不安全行為前提)
    LEVEL_3 = "Level 3"  # Unsafe Supervision (不安全監督)
    LEVEL_4 = "Level 4"  # Organizational Influences (組織影響)
    LEVEL_5 = "Level 5"  # Extra-Organizational Issues (組織外部因素) - HFACS-MES 新增

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class HFACSCode:
    """
    HFACS-MES Code.

    Supports multiple formats:
    - XX-YY# (legacy): OI-RM1, UA-ER2
    - XX-YY (new): OF-RM, US-IS, EO-N
    - XX-YY-ZZZ (extended): PC-E-PE, PC-C-AMS
    """

    code: str
    level: HFACSLevel
    category: str
    subcategory: str
    description: str

    def __post_init__(self) -> None:
        if not self.code:
            raise ValueError("HFACS code cannot be empty")
        # Validate format: requires hyphen, minimum 3 chars (e.g., EO-N)
        if len(self.code) < 3 or "-" not in self.code:
            raise ValueError(f"Invalid HFACS code format: {self.code}")

    @classmethod
    def from_code(cls, code: str) -> Self:
        """
        Create HFACSCode from code string.

        Looks up the code in the standard HFACS-MES code table.
        """
        code_info = HFACS_CODE_TABLE.get(code)
        if not code_info:
            raise ValueError(f"Unknown HFACS code: {code}")
        level = code_info["level"]
        if not isinstance(level, HFACSLevel):
            raise TypeError(f"Invalid level type for code {code}")
        return cls(
            code=code,
            level=level,
            category=str(code_info["category"]),
            subcategory=str(code_info["subcategory"]),
            description=str(code_info["description"]),
        )

    def __str__(self) -> str:
        return self.code


# HFACS-MES Code Table (36 codes)
HFACS_CODE_TABLE: dict[str, dict[str, HFACSLevel | str]] = {
    # Level 4: Organizational Influences (組織影響)
    # Resource Management (資源管理)
    "OI-RM1": {
        "level": HFACSLevel.LEVEL_4,
        "category": "資源管理",
        "subcategory": "人力資源",
        "description": "人力資源不足",
    },
    "OI-RM2": {
        "level": HFACSLevel.LEVEL_4,
        "category": "資源管理",
        "subcategory": "財務資源",
        "description": "財務資源限制",
    },
    "OI-RM3": {
        "level": HFACSLevel.LEVEL_4,
        "category": "資源管理",
        "subcategory": "設備資源",
        "description": "設備資源不足",
    },
    # Organizational Climate (組織氛圍)
    "OI-OC1": {
        "level": HFACSLevel.LEVEL_4,
        "category": "組織氛圍",
        "subcategory": "組織結構",
        "description": "組織結構問題",
    },
    "OI-OC2": {
        "level": HFACSLevel.LEVEL_4,
        "category": "組織氛圍",
        "subcategory": "政策執行",
        "description": "政策執行落差",
    },
    "OI-OC3": {
        "level": HFACSLevel.LEVEL_4,
        "category": "組織氛圍",
        "subcategory": "組織文化",
        "description": "組織文化偏差",
    },
    # Organizational Process (組織流程)
    "OI-OP1": {
        "level": HFACSLevel.LEVEL_4,
        "category": "組織流程",
        "subcategory": "作業流程",
        "description": "作業流程設計缺陷",
    },
    "OI-OP2": {
        "level": HFACSLevel.LEVEL_4,
        "category": "組織流程",
        "subcategory": "程序文件",
        "description": "程序文件管理不當",
    },
    "OI-OP3": {
        "level": HFACSLevel.LEVEL_4,
        "category": "組織流程",
        "subcategory": "監督稽核",
        "description": "監督稽核機制不足",
    },
    # Level 3: Unsafe Supervision (不安全監督)
    # Inadequate Supervision (監督不足)
    "US-IS1": {
        "level": HFACSLevel.LEVEL_3,
        "category": "監督不足",
        "subcategory": "指導訓練",
        "description": "指導訓練不足",
    },
    "US-IS2": {
        "level": HFACSLevel.LEVEL_3,
        "category": "監督不足",
        "subcategory": "任務規劃",
        "description": "任務規劃不當",
    },
    "US-IS3": {
        "level": HFACSLevel.LEVEL_3,
        "category": "監督不足",
        "subcategory": "追蹤監控",
        "description": "追蹤監控缺失",
    },
    # Planned Inappropriate Operations (計畫不當)
    "US-PI1": {
        "level": HFACSLevel.LEVEL_3,
        "category": "計畫不當",
        "subcategory": "風險評估",
        "description": "風險評估不足",
    },
    "US-PI2": {
        "level": HFACSLevel.LEVEL_3,
        "category": "計畫不當",
        "subcategory": "工作安排",
        "description": "超時工作安排",
    },
    # Failed to Correct Problem (未糾正問題)
    "US-FC1": {
        "level": HFACSLevel.LEVEL_3,
        "category": "未糾正問題",
        "subcategory": "已知問題",
        "description": "已知問題未處理",
    },
    "US-FC2": {
        "level": HFACSLevel.LEVEL_3,
        "category": "未糾正問題",
        "subcategory": "違規行為",
        "description": "違規行為未糾正",
    },
    # Supervisory Violations (監督違規)
    "US-SV1": {
        "level": HFACSLevel.LEVEL_3,
        "category": "監督違規",
        "subcategory": "授權操作",
        "description": "授權不當操作",
    },
    "US-SV2": {
        "level": HFACSLevel.LEVEL_3,
        "category": "監督違規",
        "subcategory": "規定監督",
        "description": "未執行規定監督",
    },
    # Level 2: Preconditions for Unsafe Acts (不安全行為前提)
    # Environmental Factors (環境因素)
    "PC-EF1": {
        "level": HFACSLevel.LEVEL_2,
        "category": "環境因素",
        "subcategory": "物理環境",
        "description": "物理環境不良",
    },
    "PC-EF2": {
        "level": HFACSLevel.LEVEL_2,
        "category": "環境因素",
        "subcategory": "技術環境",
        "description": "技術環境問題",
    },
    "PC-EF3": {
        "level": HFACSLevel.LEVEL_2,
        "category": "環境因素",
        "subcategory": "工作環境",
        "description": "工作環境干擾",
    },
    # Condition of Operators (人員狀態)
    "PC-CO1": {
        "level": HFACSLevel.LEVEL_2,
        "category": "人員狀態",
        "subcategory": "生理狀態",
        "description": "生理狀態不佳",
    },
    "PC-CO2": {
        "level": HFACSLevel.LEVEL_2,
        "category": "人員狀態",
        "subcategory": "心理狀態",
        "description": "心理狀態問題",
    },
    "PC-CO3": {
        "level": HFACSLevel.LEVEL_2,
        "category": "人員狀態",
        "subcategory": "認知能力",
        "description": "認知能力受限",
    },
    # Personnel Factors (人員因素)
    "PC-PF1": {
        "level": HFACSLevel.LEVEL_2,
        "category": "人員因素",
        "subcategory": "溝通協調",
        "description": "溝通協調不良",
    },
    "PC-PF2": {
        "level": HFACSLevel.LEVEL_2,
        "category": "人員因素",
        "subcategory": "團隊合作",
        "description": "團隊合作問題",
    },
    "PC-PF3": {
        "level": HFACSLevel.LEVEL_2,
        "category": "人員因素",
        "subcategory": "適任性",
        "description": "適任性問題",
    },
    # Level 1: Unsafe Acts (不安全行為)
    # Errors (錯誤)
    "UA-ER1": {
        "level": HFACSLevel.LEVEL_1,
        "category": "錯誤",
        "subcategory": "決策錯誤",
        "description": "決策錯誤",
    },
    "UA-ER2": {
        "level": HFACSLevel.LEVEL_1,
        "category": "錯誤",
        "subcategory": "技能性錯誤",
        "description": "技能性錯誤",
    },
    "UA-ER3": {
        "level": HFACSLevel.LEVEL_1,
        "category": "錯誤",
        "subcategory": "感知性錯誤",
        "description": "感知性錯誤",
    },
    # Violations (違規)
    "UA-VL1": {
        "level": HFACSLevel.LEVEL_1,
        "category": "違規",
        "subcategory": "例行性違規",
        "description": "例行性違規",
    },
    "UA-VL2": {
        "level": HFACSLevel.LEVEL_1,
        "category": "違規",
        "subcategory": "例外性違規",
        "description": "例外性違規",
    },
}


def get_all_hfacs_codes() -> list[HFACSCode]:
    """Get all HFACS-MES codes."""
    return [HFACSCode.from_code(code) for code in HFACS_CODE_TABLE]


def get_codes_by_level(level: HFACSLevel) -> list[HFACSCode]:
    """Get all HFACS codes for a specific level."""
    return [
        HFACSCode.from_code(code)
        for code, info in HFACS_CODE_TABLE.items()
        if info["level"] == level
    ]


def is_valid_hfacs_code(code: str) -> bool:
    """Check if a code is a valid HFACS-MES code."""
    return code in HFACS_CODE_TABLE
