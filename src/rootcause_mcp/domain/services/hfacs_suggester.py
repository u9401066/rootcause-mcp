"""
HFACS Suggester Domain Service.

Suggests appropriate HFACS codes based on cause descriptions.
"""

from __future__ import annotations

from dataclasses import dataclass

from rootcause_mcp.domain.value_objects.enums import FishboneCategoryType
from rootcause_mcp.domain.value_objects.hfacs import (
    HFACSCode,
    HFACSLevel,
    HFACS_CODE_TABLE,
)
from rootcause_mcp.domain.value_objects.scores import ConfidenceScore


@dataclass
class HFACSSuggestion:
    """A suggested HFACS code with confidence score."""

    code: HFACSCode
    confidence: ConfidenceScore
    reason: str


# Keyword mappings for HFACS suggestion
# Maps keywords to HFACS codes with confidence scores
KEYWORD_MAPPINGS: dict[str, list[tuple[str, float, str]]] = {
    # Level 4: Organizational Influences
    "人力不足": [("OI-RM1", 0.9, "人力資源相關")],
    "人手不足": [("OI-RM1", 0.9, "人力資源相關")],
    "staffing": [("OI-RM1", 0.85, "人力資源相關")],
    "預算": [("OI-RM2", 0.8, "財務資源相關")],
    "經費": [("OI-RM2", 0.8, "財務資源相關")],
    "設備不足": [("OI-RM3", 0.9, "設備資源相關")],
    "儀器故障": [("OI-RM3", 0.85, "設備資源相關")],
    "SOP": [("OI-OP1", 0.8, "流程設計相關")],
    "流程": [("OI-OP1", 0.75, "流程設計相關")],
    "程序": [("OI-OP1", 0.75, "流程設計相關")],
    "文件管理": [("OI-OP2", 0.85, "程序文件相關")],
    "稽核": [("OI-OP3", 0.8, "監督稽核相關")],
    "組織文化": [("OI-OC3", 0.85, "組織文化相關")],
    # Level 3: Unsafe Supervision
    "訓練不足": [("US-IS1", 0.9, "指導訓練相關")],
    "教育訓練": [("US-IS1", 0.85, "指導訓練相關")],
    "新進人員": [("US-IS1", 0.8, "指導訓練相關")],
    "排班": [("US-IS2", 0.8, "任務規劃相關")],
    "任務分配": [("US-IS2", 0.8, "任務規劃相關")],
    "監督": [("US-IS3", 0.75, "追蹤監控相關")],
    "追蹤": [("US-IS3", 0.75, "追蹤監控相關")],
    "風險評估": [("US-PI1", 0.85, "風險評估相關")],
    "超時工作": [("US-PI2", 0.9, "超時工作相關")],
    "加班": [("US-PI2", 0.85, "超時工作相關")],
    "已知問題": [("US-FC1", 0.85, "已知問題未處理")],
    "違規未糾正": [("US-FC2", 0.85, "違規行為未糾正")],
    # Level 2: Preconditions
    "環境": [("PC-EF1", 0.7, "物理環境相關")],
    "噪音": [("PC-EF1", 0.8, "物理環境相關")],
    "光線": [("PC-EF1", 0.8, "物理環境相關")],
    "系統問題": [("PC-EF2", 0.8, "技術環境相關")],
    "軟體": [("PC-EF2", 0.8, "技術環境相關")],
    "干擾": [("PC-EF3", 0.8, "工作環境干擾")],
    "疲勞": [("PC-CO1", 0.9, "生理狀態相關")],
    "睡眠不足": [("PC-CO1", 0.9, "生理狀態相關")],
    "壓力": [("PC-CO2", 0.85, "心理狀態相關")],
    "焦慮": [("PC-CO2", 0.85, "心理狀態相關")],
    "注意力": [("PC-CO3", 0.8, "認知能力相關")],
    "分心": [("PC-CO3", 0.85, "認知能力相關")],
    "溝通": [("PC-PF1", 0.85, "溝通協調相關")],
    "交班": [("PC-PF1", 0.85, "溝通協調相關")],
    "團隊合作": [("PC-PF2", 0.85, "團隊合作相關")],
    "適任性": [("PC-PF3", 0.85, "適任性相關")],
    "資格": [("PC-PF3", 0.8, "適任性相關")],
    # Level 1: Unsafe Acts
    "判斷錯誤": [("UA-ER1", 0.9, "決策錯誤相關")],
    "決策": [("UA-ER1", 0.8, "決策錯誤相關")],
    "技術錯誤": [("UA-ER2", 0.85, "技能性錯誤相關")],
    "操作錯誤": [("UA-ER2", 0.85, "技能性錯誤相關")],
    "看錯": [("UA-ER3", 0.85, "感知性錯誤相關")],
    "誤認": [("UA-ER3", 0.85, "感知性錯誤相關")],
    "辨識錯誤": [("UA-ER3", 0.85, "感知性錯誤相關")],
    "違規": [("UA-VL1", 0.8, "違規相關")],
    "捷徑": [("UA-VL1", 0.75, "例行性違規相關")],
    "例外": [("UA-VL2", 0.75, "例外性違規相關")],
}

# 6M to HFACS Level Mapping
CATEGORY_LEVEL_MAPPING: dict[FishboneCategoryType, list[HFACSLevel]] = {
    FishboneCategoryType.PERSONNEL: [HFACSLevel.LEVEL_1, HFACSLevel.LEVEL_2],
    FishboneCategoryType.EQUIPMENT: [HFACSLevel.LEVEL_4],  # OI-RM3
    FishboneCategoryType.MATERIAL: [HFACSLevel.LEVEL_4],  # OI-RM
    FishboneCategoryType.PROCESS: [HFACSLevel.LEVEL_4, HFACSLevel.LEVEL_3],  # OI-OP, US
    FishboneCategoryType.ENVIRONMENT: [HFACSLevel.LEVEL_2, HFACSLevel.LEVEL_4],  # PC-EF, OI-RM
    FishboneCategoryType.MONITORING: [HFACSLevel.LEVEL_3, HFACSLevel.LEVEL_4],  # US, OI-OP
}


class HFACSSuggester:
    """
    Domain service for suggesting HFACS codes.

    Uses keyword matching and 6M category context to suggest
    appropriate HFACS codes for cause descriptions.
    """

    def suggest(
        self,
        description: str,
        category: FishboneCategoryType | None = None,
        max_suggestions: int = 3,
    ) -> list[HFACSSuggestion]:
        """
        Suggest HFACS codes for a cause description.

        Args:
            description: The cause description text
            category: Optional 6M category for context
            max_suggestions: Maximum number of suggestions to return

        Returns:
            List of HFACSSuggestions sorted by confidence
        """
        suggestions: list[HFACSSuggestion] = []
        description_lower = description.lower()

        # Find keyword matches
        for keyword, mappings in KEYWORD_MAPPINGS.items():
            if keyword.lower() in description_lower:
                for code_str, confidence, reason in mappings:
                    code = HFACSCode.from_code(code_str)

                    # Boost confidence if category matches expected level
                    adjusted_confidence = confidence
                    if category:
                        expected_levels = CATEGORY_LEVEL_MAPPING.get(category, [])
                        if code.level in expected_levels:
                            adjusted_confidence = min(1.0, confidence + 0.1)

                    suggestions.append(
                        HFACSSuggestion(
                            code=code,
                            confidence=ConfidenceScore(adjusted_confidence),
                            reason=reason,
                        )
                    )

        # Sort by confidence and deduplicate
        suggestions.sort(key=lambda s: float(s.confidence), reverse=True)

        # Remove duplicates (keep highest confidence)
        seen_codes: set[str] = set()
        unique_suggestions: list[HFACSSuggestion] = []
        for suggestion in suggestions:
            if suggestion.code.code not in seen_codes:
                seen_codes.add(suggestion.code.code)
                unique_suggestions.append(suggestion)

        return unique_suggestions[:max_suggestions]

    def suggest_by_category(
        self,
        category: FishboneCategoryType,
    ) -> list[HFACSSuggestion]:
        """
        Suggest HFACS codes based only on 6M category.

        Returns typical HFACS codes for a given Fishbone category.
        """
        suggestions: list[HFACSSuggestion] = []
        expected_levels = CATEGORY_LEVEL_MAPPING.get(category, [])

        for code_str, info in HFACS_CODE_TABLE.items():
            if info["level"] in expected_levels:
                code = HFACSCode.from_code(code_str)
                suggestions.append(
                    HFACSSuggestion(
                        code=code,
                        confidence=ConfidenceScore(0.5),  # Base confidence
                        reason=f"基於 {category.value} 分類建議",
                    )
                )

        return suggestions[:5]

    def get_guiding_questions(
        self,
        level: HFACSLevel,
    ) -> list[str]:
        """
        Get guiding questions to help identify causes at a specific HFACS level.
        """
        questions: dict[HFACSLevel, list[str]] = {
            HFACSLevel.LEVEL_4: [
                "組織的資源配置是否足夠？（人力、設備、預算）",
                "是否存在組織文化或政策問題？",
                "相關的 SOP 或流程是否完善？",
            ],
            HFACSLevel.LEVEL_3: [
                "主管是否提供足夠的指導和訓練？",
                "任務的規劃和分配是否適當？",
                "是否有已知問題未被處理？",
            ],
            HFACSLevel.LEVEL_2: [
                "工作環境（物理、技術）是否適當？",
                "人員當時的身心狀態如何？",
                "團隊溝通和協調是否良好？",
            ],
            HFACSLevel.LEVEL_1: [
                "是否有決策或判斷上的錯誤？",
                "是否有技術或操作上的錯誤？",
                "是否有違規或捷徑行為？",
            ],
        }
        return questions.get(level, [])
