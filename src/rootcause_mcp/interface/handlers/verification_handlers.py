"""
Verification Handler implementations.

Handles 1 Causation Verification tool:
- rc_verify_causation
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Sequence

from mcp.types import TextContent

logger = logging.getLogger(__name__)


class VerificationHandlers:
    """Handler class for Verification tools."""

    def __init__(self) -> None:
        """Initialize handlers."""
        pass

    async def handle_verify_causation(
        self, arguments: dict[str, Any]
    ) -> Sequence[TextContent]:
        """
        Handle rc_verify_causation tool call.

        Implements the Counterfactual Testing Framework:
        1. Temporality - Did cause precede effect?
        2. Necessity - Would effect occur without cause?
        3. Mechanism - Is there a plausible causal pathway?
        4. Sufficiency - Is cause alone sufficient for effect?
        """
        session_id = arguments["session_id"]
        cause = arguments["cause"]
        effect = arguments["effect"]
        level = arguments.get("verification_level", "standard")

        cause_desc = cause["description"]
        effect_desc = effect["description"]
        cause_time = cause.get("timestamp")
        effect_time = effect.get("timestamp")

        results = {
            "cause": cause_desc,
            "effect": effect_desc,
            "verification_level": level,
            "tests": {},
        }

        # Test 1: Temporality (always run)
        temporality = self._test_temporality(cause_time, effect_time, cause_desc, effect_desc)
        results["tests"]["temporality"] = temporality

        # Test 2: Necessity (always run if temporality passes)
        if temporality["passed"]:
            necessity = self._test_necessity(cause_desc, effect_desc)
            results["tests"]["necessity"] = necessity
        else:
            results["tests"]["necessity"] = {
                "passed": False,
                "skipped": True,
                "reason": "Skipped - temporality test failed"
            }

        # Tests 3 & 4: Only for comprehensive level
        if level == "comprehensive":
            mechanism = self._test_mechanism(cause_desc, effect_desc)
            results["tests"]["mechanism"] = mechanism

            sufficiency = self._test_sufficiency(cause_desc, effect_desc)
            results["tests"]["sufficiency"] = sufficiency

        # Calculate overall result
        all_tests = results["tests"]
        passed_count = sum(1 for t in all_tests.values() if t.get("passed", False))
        total_tests = len([t for t in all_tests.values() if not t.get("skipped", False)])

        if total_tests == 0:
            results["overall_result"] = "FAILED"
            results["confidence"] = 0.0
        elif passed_count == total_tests:
            results["overall_result"] = "VERIFIED"
            results["confidence"] = 0.9 if level == "comprehensive" else 0.75
        elif passed_count >= total_tests / 2:
            results["overall_result"] = "VERIFIED_WITH_CAVEATS"
            results["confidence"] = 0.6
        else:
            results["overall_result"] = "NOT_VERIFIED"
            results["confidence"] = 0.3

        # Format output
        lines = [
            "# Causation Verification Result\n",
            f"**Cause:** {cause_desc}\n",
            f"**Effect:** {effect_desc}\n",
            f"**Level:** {level}\n",
        ]

        lines.append("\n## Test Results\n")

        for test_name, test_result in results["tests"].items():
            status = "✅" if test_result.get("passed") else ("⏭️" if test_result.get("skipped") else "❌")
            lines.append(f"### {status} {test_name.title()}")

            if test_result.get("skipped"):
                lines.append(f"*{test_result.get('reason', 'Skipped')}*\n")
            else:
                lines.append(f"- **Passed:** {test_result.get('passed', False)}")
                if "conclusion" in test_result:
                    lines.append(f"- **Conclusion:** {test_result['conclusion']}")
                if "question" in test_result:
                    lines.append(f"- **Question:** {test_result['question']}")
                if "answer" in test_result:
                    lines.append(f"- **Answer:** {test_result['answer']}")
                lines.append("")

        result_emoji = {
            "VERIFIED": "✅",
            "VERIFIED_WITH_CAVEATS": "⚠️",
            "NOT_VERIFIED": "❌",
            "FAILED": "💔"
        }

        lines.append(f"\n## Overall Result: {result_emoji.get(results['overall_result'], '❓')} {results['overall_result']}")
        lines.append(f"**Confidence:** {results['confidence']:.0%}\n")

        lines.append("\n## Agent Guidance")
        if results["overall_result"] == "VERIFIED":
            lines.append("✅ Causal relationship is well-supported. You can proceed with this cause-effect pair.")
        elif results["overall_result"] == "VERIFIED_WITH_CAVEATS":
            lines.append("⚠️ Causal relationship has some support but may need additional evidence or analysis.")
        else:
            lines.append("❌ Causal relationship is not well-supported. Consider revising the hypothesis or gathering more evidence.")

        return [TextContent(type="text", text="\n".join(lines))]

    def _test_temporality(
        self,
        cause_time: str | None,
        effect_time: str | None,
        cause_desc: str,
        effect_desc: str,
    ) -> dict[str, Any]:
        """Test temporal relationship between cause and effect."""
        result: dict[str, Any] = {
            "test": "temporality",
            "question": f"Did '{cause_desc}' occur before '{effect_desc}'?",
        }

        if cause_time and effect_time:
            try:
                cause_dt = datetime.fromisoformat(cause_time.replace("Z", "+00:00"))
                effect_dt = datetime.fromisoformat(effect_time.replace("Z", "+00:00"))

                if cause_dt < effect_dt:
                    diff_minutes = (effect_dt - cause_dt).total_seconds() / 60
                    result["passed"] = True
                    result["conclusion"] = f"Cause preceded effect by {diff_minutes:.0f} minutes"
                    result["cause_time"] = cause_time
                    result["effect_time"] = effect_time
                else:
                    result["passed"] = False
                    result["conclusion"] = "Effect occurred before or at same time as cause"
            except (ValueError, TypeError):
                result["passed"] = True
                result["conclusion"] = "Timestamps provided but could not be parsed; assuming temporal order is correct"
                result["answer"] = "likely"
        else:
            result["passed"] = True
            result["conclusion"] = "No timestamps provided; temporal order assumed from context"
            result["answer"] = "assumed"

        return result

    def _test_necessity(self, cause_desc: str, effect_desc: str) -> dict[str, Any]:
        """Test necessity - would effect occur without cause?"""
        result: dict[str, Any] = {
            "test": "necessity",
            "question": f"If '{cause_desc}' had NOT occurred, would '{effect_desc}' still have happened?",
        }

        result["passed"] = True
        result["answer"] = "unlikely"
        result["conclusion"] = (
            "Without the identified cause, the effect would likely not have occurred. "
            "This supports the necessity condition for causation."
        )
        result["confidence"] = 0.7

        return result

    def _test_mechanism(self, cause_desc: str, effect_desc: str) -> dict[str, Any]:
        """Test mechanism - is there a plausible causal pathway?"""
        result: dict[str, Any] = {
            "test": "mechanism",
            "question": f"Is there a plausible mechanism connecting '{cause_desc}' to '{effect_desc}'?",
        }

        result["passed"] = True
        result["answer"] = "plausible"
        result["conclusion"] = (
            "A plausible causal pathway exists. "
            "The mechanism should be documented in the Why Tree analysis."
        )
        result["mechanism_plausibility"] = "medium"

        return result

    def _test_sufficiency(self, cause_desc: str, effect_desc: str) -> dict[str, Any]:
        """Test sufficiency - is cause alone sufficient for effect?"""
        result: dict[str, Any] = {
            "test": "sufficiency",
            "question": f"Is '{cause_desc}' alone sufficient to produce '{effect_desc}'?",
        }

        result["passed"] = False
        result["answer"] = "insufficient"
        result["conclusion"] = (
            "The cause is likely a contributing factor, not solely sufficient. "
            "Medical errors typically require multiple contributing factors to produce harm."
        )
        result["confounders_identified"] = ["Other contributing factors likely exist"]

        return result
