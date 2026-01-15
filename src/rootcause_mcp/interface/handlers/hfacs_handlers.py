"""
HFACS Handler implementations.

Handles 6 HFACS-related tools:
- rc_suggest_hfacs
- rc_confirm_classification
- rc_get_hfacs_framework
- rc_list_learned_rules
- rc_reload_rules
- rc_get_6m_hfacs_mapping (NEW)
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from mcp.types import TextContent

if TYPE_CHECKING:
    from rootcause_mcp.domain.services.hfacs_suggester import HFACSSuggester
    from rootcause_mcp.domain.services.learned_rules_service import LearnedRulesService

logger = logging.getLogger(__name__)


class HFACSHandlers:
    """Handler class for HFACS-related tools."""

    # HFACS-MES Framework structure
    FRAMEWORK = {
        "EF": {
            "name": "External Factors",
            "description": "Factors outside the organization's direct control",
            "categories": {
                "EF-RE": "Regulatory Environment",
                "EF-OS": "Other (External factors)",
            },
        },
        "OI": {
            "name": "Organizational Influences",
            "description": "Management and organizational-level factors",
            "categories": {
                "OI-RM": "Resource Management",
                "OI-OC": "Organizational Climate",
                "OI-OP": "Organizational Process",
            },
        },
        "US": {
            "name": "Unsafe Supervision",
            "description": "Supervisory actions or inactions contributing to error",
            "categories": {
                "US-IS": "Inadequate Supervision",
                "US-PIO": "Planned Inappropriate Operations",
                "US-FCP": "Failed to Correct Problem",
                "US-SV": "Supervisory Violation",
            },
        },
        "PC": {
            "name": "Preconditions for Unsafe Acts",
            "description": "Conditions that enable or facilitate unsafe acts",
            "subcategories": {
                "PC-E": {
                    "name": "Environmental Factors",
                    "codes": {
                        "PC-E-PE": "Physical Environment",
                        "PC-E-TE": "Technological Environment",
                    },
                },
                "PC-C": {
                    "name": "Condition of Operators",
                    "codes": {
                        "PC-C-AMS": "Adverse Mental States",
                        "PC-C-APS": "Adverse Physiological States",
                        "PC-C-PML": "Physical/Mental Limitations",
                    },
                },
                "PC-P": {
                    "name": "Personnel Factors",
                    "codes": {
                        "PC-P-CRM": "Communication, Resources, and Management",
                        "PC-P-PRF": "Personal Readiness and Fitness",
                    },
                },
            },
        },
        "UA": {
            "name": "Unsafe Acts",
            "description": "Direct actions or inactions leading to the event",
            "subcategories": {
                "UA-E": {
                    "name": "Errors",
                    "codes": {
                        "UA-E-SB": "Skill-Based Errors",
                        "UA-E-DM": "Decision Errors",
                        "UA-E-PM": "Perceptual Errors",
                    },
                },
                "UA-V": {
                    "name": "Violations",
                    "codes": {
                        "UA-V-R": "Routine Violations",
                        "UA-V-E": "Exceptional Violations",
                    },
                },
            },
        },
    }

    # 6M to HFACS Mapping (表圖樹 cross-reference)
    MAPPING_6M_HFACS = {
        "Personnel": {
            "hfacs_levels": ["Level 1 (Unsafe Acts)", "Level 2 (Preconditions)"],
            "hfacs_codes": ["UA-*", "PC-C-*", "PC-P-*"],
            "description": "人員因素對應 HFACS 不安全行為 (Level 1) 和前置條件 (Level 2)",
            "cause_type": "proximate",  # 近端原因
            "why_tree_depth": {"typical": "1-2", "max": 3},
            "example_mappings": [
                {"cause": "護理師因疲勞未及時發現異常", "6m": "Personnel", "hfacs": "PC-C-APS"},
                {"cause": "醫師計算藥物劑量錯誤", "6m": "Personnel", "hfacs": "UA-E-SB"},
                {"cause": "交班時漏傳重要資訊", "6m": "Personnel", "hfacs": "PC-P-CRM"},
            ],
        },
        "Equipment": {
            "hfacs_levels": ["Level 4 (Organizational)", "Level 2 (Preconditions)"],
            "hfacs_codes": ["OI-RM", "PC-E-TE"],
            "description": "設備因素對應組織資源管理 (Level 4) 或技術環境 (Level 2)",
            "cause_type": "intermediate",  # 中間原因
            "why_tree_depth": {"typical": "2-3", "max": 4},
            "example_mappings": [
                {"cause": "監測儀器故障未及時維修", "6m": "Equipment", "hfacs": "OI-RM"},
                {"cause": "軟體介面設計不良導致誤操作", "6m": "Equipment", "hfacs": "PC-E-TE"},
            ],
        },
        "Material": {
            "hfacs_levels": ["Level 4 (Organizational)"],
            "hfacs_codes": ["OI-RM", "OI-OP"],
            "description": "物料因素對應組織資源管理和流程規劃 (Level 4)",
            "cause_type": "intermediate",
            "why_tree_depth": {"typical": "2-4", "max": 4},
            "example_mappings": [
                {"cause": "藥品標籤相似易混淆", "6m": "Material", "hfacs": "OI-OP"},
                {"cause": "關鍵耗材庫存不足", "6m": "Material", "hfacs": "OI-RM"},
            ],
        },
        "Process": {
            "hfacs_levels": ["Level 3 (Supervision)", "Level 4 (Organizational)"],
            "hfacs_codes": ["US-*", "OI-OP"],
            "description": "流程因素對應督導失效 (Level 3) 和組織流程 (Level 4)",
            "cause_type": "ultimate",  # 遠端/根本原因
            "why_tree_depth": {"typical": "3-5", "max": 5},
            "example_mappings": [
                {"cause": "查核流程有漏洞", "6m": "Process", "hfacs": "OI-OP"},
                {"cause": "主管未落實督導", "6m": "Process", "hfacs": "US-IS"},
                {"cause": "SOP 過時未更新", "6m": "Process", "hfacs": "OI-OP"},
            ],
        },
        "Environment": {
            "hfacs_levels": ["Level 2 (Preconditions)", "Level 4 (Organizational)"],
            "hfacs_codes": ["PC-E-PE", "OI-OC"],
            "description": "環境因素涵蓋物理環境 (Level 2) 和組織文化 (Level 4)",
            "cause_type": "mixed",
            "why_tree_depth": {"typical": "2-4", "max": 5},
            "example_mappings": [
                {"cause": "照明不足影響判讀", "6m": "Environment", "hfacs": "PC-E-PE"},
                {"cause": "噪音干擾溝通", "6m": "Environment", "hfacs": "PC-E-PE"},
                {"cause": "安全文化薄弱不敢提出疑慮", "6m": "Environment", "hfacs": "OI-OC"},
            ],
        },
        "Monitoring": {
            "hfacs_levels": ["Level 3 (Supervision)", "Level 4 (Organizational)"],
            "hfacs_codes": ["US-IS", "US-FCP", "OI-OP"],
            "description": "監控因素對應督導不足 (Level 3) 和組織流程 (Level 4)",
            "cause_type": "ultimate",
            "why_tree_depth": {"typical": "3-5", "max": 5},
            "example_mappings": [
                {"cause": "缺乏異常警示機制", "6m": "Monitoring", "hfacs": "OI-OP"},
                {"cause": "主管未追蹤改善進度", "6m": "Monitoring", "hfacs": "US-FCP"},
                {"cause": "稽核機制形同虛設", "6m": "Monitoring", "hfacs": "US-IS"},
            ],
        },
    }

    def __init__(
        self,
        hfacs_suggester: HFACSSuggester | None = None,
        learned_rules_service: LearnedRulesService | None = None,
    ) -> None:
        """Initialize handlers with dependencies."""
        self._suggester = hfacs_suggester
        self._learned_rules = learned_rules_service

    async def handle_suggest_hfacs(
        self, arguments: dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle rc_suggest_hfacs tool call."""
        if self._suggester is None:
            return [TextContent(type="text", text="Error: HFACSSuggester not initialized")]

        description = arguments["description"]
        max_suggestions = arguments.get("max_suggestions", 3)

        suggestions = self._suggester.suggest(
            description=description,
            max_suggestions=max_suggestions,
        )

        if not suggestions:
            result = (
                f"No HFACS classifications suggested for: '{description}'\n\n"
                "Consider:\n"
                "1. Provide more context about the event\n"
                "2. Check if the description relates to human factors or system issues"
            )
        else:
            lines = [f"**HFACS Suggestions for:** '{description}'\n"]

            for i, suggestion in enumerate(suggestions, 1):
                code = suggestion.code.code
                name = suggestion.code.description
                confidence = float(suggestion.confidence)
                source = suggestion.source

                lines.append(f"\n### {i}. {code} - {name}")
                lines.append(f"- **Confidence:** {confidence:.0%}")
                lines.append(f"- **Source:** {source}")
                lines.append(f"- **Reason:** {suggestion.reason}")

            lines.append("\n---")
            lines.append("Use `rc_confirm_classification` to confirm the correct classification.")

            result = "\n".join(lines)

        return [TextContent(type="text", text=result)]

    async def handle_confirm_classification(
        self, arguments: dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle rc_confirm_classification tool call."""
        if self._learned_rules is None:
            return [TextContent(type="text", text="Error: LearnedRulesService not initialized")]

        description = arguments["description"]
        hfacs_code = arguments["hfacs_code"]
        reason = arguments["reason"]
        session_id = arguments.get("session_id")
        confidence = arguments.get("confidence", 0.8)

        success = self._learned_rules.confirm_classification(
            description=description,
            hfacs_code=hfacs_code,
            reason=reason,
            session_id=session_id,
            confidence=confidence,
        )

        if success:
            result = (
                f"✅ **Classification Confirmed**\n\n"
                f"- **Description:** {description}\n"
                f"- **HFACS Code:** {hfacs_code}\n"
                f"- **Reason:** {reason}\n"
                f"- **Confidence:** {confidence:.0%}\n\n"
                f"This rule has been saved and will be used for future suggestions."
            )
        else:
            result = (
                "❌ **Failed to save classification**\n\n"
                "Please check the logs for details."
            )

        return [TextContent(type="text", text=result)]

    async def handle_get_framework(
        self, arguments: dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle rc_get_hfacs_framework tool call."""
        level_filter = arguments.get("level")

        if level_filter and level_filter in self.FRAMEWORK:
            result_data = {level_filter: self.FRAMEWORK[level_filter]}
        else:
            result_data = self.FRAMEWORK

        # Format as readable text
        lines = ["# HFACS-MES Framework\n"]

        for level_code, level_data in result_data.items():
            lines.append(f"## {level_code} - {level_data['name']}")
            lines.append(f"*{level_data['description']}*\n")

            if "categories" in level_data:
                for cat_code, cat_name in level_data["categories"].items():
                    lines.append(f"- **{cat_code}**: {cat_name}")

            if "subcategories" in level_data:
                for sub_code, sub_data in level_data["subcategories"].items():
                    lines.append(f"\n### {sub_code} - {sub_data['name']}")
                    for code, name in sub_data["codes"].items():
                        lines.append(f"- **{code}**: {name}")

            lines.append("")

        return [TextContent(type="text", text="\n".join(lines))]

    async def handle_list_learned_rules(
        self, arguments: dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle rc_list_learned_rules tool call."""
        if self._learned_rules is None:
            return [TextContent(type="text", text="Error: LearnedRulesService not initialized")]

        hfacs_code_filter = arguments.get("hfacs_code")
        min_confidence = arguments.get("min_confidence", 0.0)

        all_rules = self._learned_rules.get_learned_rules()

        rules = []
        for rule in all_rules:
            if hfacs_code_filter and rule.get("code") != hfacs_code_filter:
                continue
            if rule.get("confidence", 0) < min_confidence:
                continue
            rules.append(rule)

        if not rules:
            result = "No learned rules found."
            if hfacs_code_filter:
                result += f" (filtered by code: {hfacs_code_filter})"
        else:
            lines = [f"# Learned Classification Rules ({len(rules)} found)\n"]

            for rule in rules:
                lines.append(f"## {rule.get('code', 'N/A')}")
                lines.append(f"- **Keyword:** {rule.get('keyword', 'N/A')}")
                lines.append(f"- **Source Type:** {rule.get('source_type', 'N/A')}")
                lines.append(f"- **Confidence:** {rule.get('confidence', 0):.0%}")
                lines.append(f"- **Reason:** {rule.get('reason', 'N/A')}")
                lines.append(f"- **Confirmed At:** {rule.get('confirmed_at', 'N/A')}")
                lines.append(f"- **Hit Count:** {rule.get('hit_count', 0)}")
                lines.append("")

            result = "\n".join(lines)

        return [TextContent(type="text", text=result)]

    async def handle_reload_rules(self) -> Sequence[TextContent]:
        """Handle rc_reload_rules tool call."""
        if self._suggester is None:
            return [TextContent(type="text", text="Error: HFACSSuggester not initialized")]

        self._suggester.reload_rules()
        summary = self._suggester.get_loaded_rules_summary()

        result = (
            "✅ **Rules Reloaded Successfully**\n\n"
            f"- **Base rules:** {summary.get('base_count', 0)}\n"
            f"- **Domain rules:** {summary.get('domain_count', 0)}\n"
            f"- **Learned rules:** {summary.get('learned_count', 0)}\n"
            f"- **Total rules:** {summary.get('total_count', 0)}"
        )

        return [TextContent(type="text", text=result)]

    async def handle_get_6m_hfacs_mapping(
        self, arguments: dict[str, Any]
    ) -> Sequence[TextContent]:
        """Handle rc_get_6m_hfacs_mapping tool call.
        
        Returns the mapping between 6M Fishbone categories and HFACS codes,
        including Why Tree depth guidance for comprehensive analysis.
        """
        category_filter = arguments.get("category")

        if category_filter and category_filter in self.MAPPING_6M_HFACS:
            mapping_data = {category_filter: self.MAPPING_6M_HFACS[category_filter]}
        else:
            mapping_data = self.MAPPING_6M_HFACS

        lines = [
            "# 6M-HFACS 對照表 (表圖樹 Cross-Reference)\n",
            "此對照表幫助 Agent 理解：",
            "1. **魚骨圖 (6M)** → **HFACS 表** 的對應關係",
            "2. **Why Tree 深度** 建議：近端原因 vs 遠端原因",
            "3. **Proximate vs Ultimate Cause** 概念\n",
            "---\n",
            "## 因果層級概念\n",
            "| 類型 | Why Tree 深度 | HFACS Level | 說明 |",
            "|------|--------------|-------------|------|",
            "| **Proximate (近端)** | 1-2 | Level 1-2 | 直接導致事件的行為/條件 |",
            "| **Intermediate (中間)** | 2-4 | Level 2-3 | 促成近端原因的因素 |",
            "| **Ultimate (遠端)** | 3-5 | Level 3-4 | 組織/系統層面的根本原因 |",
            "",
        ]

        cause_type_emoji_map = {
            "proximate": "🔴",
            "intermediate": "🟡",
            "ultimate": "🟢",
            "mixed": "🔵",
        }

        for category, data in mapping_data.items():
            # Cast to dict for type safety
            data_dict = dict(data) if not isinstance(data, dict) else data

            cause_type = str(data_dict.get("cause_type", "unknown"))
            cause_type_emoji = cause_type_emoji_map.get(cause_type, "⚪")

            hfacs_levels = data_dict.get("hfacs_levels", [])
            hfacs_codes = data_dict.get("hfacs_codes", [])
            description = str(data_dict.get("description", ""))

            lines.append(f"\n## {cause_type_emoji} {category}\n")
            lines.append(f"**{description}**\n")
            lines.append(f"- **HFACS Levels:** {', '.join(str(x) for x in hfacs_levels)}")
            lines.append(f"- **HFACS Codes:** {', '.join(str(x) for x in hfacs_codes)}")
            lines.append(f"- **Cause Type:** {cause_type.title()}")

            depth_info = data_dict.get("why_tree_depth", {})
            if isinstance(depth_info, dict):
                lines.append(f"- **Why Tree Depth:** 通常 {depth_info.get('typical', 'N/A')}, 最深 {depth_info.get('max', 'N/A')}")

            example_mappings = data_dict.get("example_mappings", [])
            if example_mappings:
                lines.append("\n**範例對照：**")
                for ex in example_mappings:
                    if isinstance(ex, dict):
                        lines.append(f"- 「{ex.get('cause', '')}」 → **{ex.get('hfacs', '')}**")

        lines.append("\n---\n")
        lines.append("## 使用建議\n")
        lines.append("1. **起點 (Proximate):** 從 Personnel 類別開始，通常是 Why 1-2")
        lines.append("2. **深入 (Intermediate):** Equipment/Material/Environment 是 Why 2-4")
        lines.append("3. **終點 (Ultimate):** Process/Monitoring 是真正的根本原因，通常是 Why 3-5")
        lines.append("\n> 💡 **RCA 原則：** 不要停在近端原因 (Level 1)，要追溯到組織/系統層面 (Level 3-4)")

        return [TextContent(type="text", text="\n".join(lines))]
