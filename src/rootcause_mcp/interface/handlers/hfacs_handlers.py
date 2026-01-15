"""
HFACS Handler implementations.

Handles 5 HFACS-related tools:
- rc_suggest_hfacs
- rc_confirm_classification
- rc_get_hfacs_framework
- rc_list_learned_rules
- rc_reload_rules
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Sequence

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
                f"❌ **Failed to save classification**\n\n"
                f"Please check the logs for details."
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
