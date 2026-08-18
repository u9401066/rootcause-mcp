"""
Causation Audit Domain Service.

Audits submitted causal obligations without proving clinical causality.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from rootcause_mcp.domain.value_objects.enums import CausalStrength, VerificationResult
from rootcause_mcp.domain.value_objects.scores import ConfidenceScore


class VerificationLevel(str, Enum):
    """Level of verification depth."""

    STANDARD = "standard"  # Temporality + Necessity
    COMPREHENSIVE = "comprehensive"  # All 4 tests


@dataclass
class CauseEvent:
    """An event in a causal relationship."""

    description: str
    event_id: str | None = None
    timestamp: datetime | None = None
    evidence: list[str] | None = None


@dataclass
class TemporalityResult:
    """Result of temporality check."""

    passed: bool
    cause_time: datetime | None = None
    effect_time: datetime | None = None
    time_diff_minutes: int | None = None
    conclusion: str = ""


@dataclass
class NecessityResult:
    """Result of necessity (counterfactual) check."""

    passed: bool
    counterfactual_question: str
    counterfactual_answer: str  # "likely", "unlikely", "uncertain"
    confidence: ConfidenceScore
    reasoning: str


@dataclass
class MechanismResult:
    """Result of mechanism plausibility check."""

    passed: bool
    causal_pathway: list[str]
    mechanism_plausibility: str  # "high", "medium", "low"
    domain_knowledge_support: bool


@dataclass
class SufficiencyResult:
    """Result of sufficiency check."""

    passed: bool
    analysis: str
    confounders_identified: list[str]
    conclusion: str


@dataclass
class VerificationTestResults:
    """All test results from causation verification."""

    temporality: TemporalityResult | None = None
    necessity: NecessityResult | None = None
    mechanism: MechanismResult | None = None
    sufficiency: SufficiencyResult | None = None


@dataclass
class CausationVerificationResult:
    """Complete result of causation verification."""

    verification_id: str
    verification_level: VerificationLevel
    cause: str
    effect: str
    tests: VerificationTestResults
    overall_result: VerificationResult
    confidence: ConfidenceScore
    causal_strength: CausalStrength | None = None
    interpretation: str = ""
    next_steps: list[str] | None = None
    caveats: list[str] | None = None


class CausationValidator:
    """
    Conservative audit service for submitted causal relationships.

    Implements the Counterfactual Testing Framework with 4 tests:
    1. Temporality: Cause must precede effect
    2. Necessity: Effect wouldn't occur without cause
    3. Mechanism: Plausible causal pathway exists
    4. Sufficiency: Cause alone is enough to produce effect
    """

    def validate(
        self,
        cause: CauseEvent,
        effect: CauseEvent,
        level: VerificationLevel = VerificationLevel.STANDARD,
    ) -> CausationVerificationResult:
        """
        Audit a proposed causal relationship between two events.

        Args:
            cause: The proposed cause event
            effect: The proposed effect event
            level: Verification depth (standard or comprehensive)

        Returns:
            CausationVerificationResult with test results and overall verdict
        """
        import uuid

        verification_id = f"ver_{uuid.uuid4().hex[:8]}"
        tests = VerificationTestResults()

        # Always run temporality check
        tests.temporality = self._check_temporality(cause, effect)

        # A known reverse chronology rejects the claim. Missing timestamps are
        # insufficient data, not evidence that chronology was satisfied.
        if cause.timestamp and effect.timestamp and not tests.temporality.passed:
            return CausationVerificationResult(
                verification_id=verification_id,
                verification_level=level,
                cause=cause.description,
                effect=effect.description,
                tests=tests,
                overall_result=VerificationResult.REJECTED,
                confidence=ConfidenceScore(0.95),
                interpretation=(
                    "提交的時序義務未通過；此結果不建立或否定完整臨床因果關係"
                ),
                next_steps=["檢查事件時間順序", "確認事件描述是否正確"],
            )

        # Run necessity check
        tests.necessity = self._check_necessity(cause, effect)

        # For standard level, stop here
        if level == VerificationLevel.STANDARD:
            return self._build_result(verification_id, level, cause, effect, tests)

        # For comprehensive level, run additional tests
        tests.mechanism = self._check_mechanism(cause, effect)
        tests.sufficiency = self._check_sufficiency(cause, effect)

        return self._build_result(verification_id, level, cause, effect, tests)

    def _check_temporality(
        self,
        cause: CauseEvent,
        effect: CauseEvent,
    ) -> TemporalityResult:
        """Check if cause precedes effect temporally."""
        # If timestamps are available, do precise check
        if cause.timestamp and effect.timestamp:
            time_diff = (effect.timestamp - cause.timestamp).total_seconds() / 60
            passed = time_diff > 0

            return TemporalityResult(
                passed=passed,
                cause_time=cause.timestamp,
                effect_time=effect.timestamp,
                time_diff_minutes=int(time_diff) if passed else None,
                conclusion=(
                    f"時序正確：原因在結果前 {int(time_diff)} 分鐘發生"
                    if passed
                    else "時序錯誤：結果發生在原因之前"
                ),
            )

        # Without timestamps, temporality cannot be verified.
        return TemporalityResult(
            passed=False,
            conclusion="無法驗證時序（缺少原因或結果時間戳）",
        )

    def _check_necessity(
        self,
        cause: CauseEvent,
        effect: CauseEvent,
    ) -> NecessityResult:
        """
        Check if cause is necessary for effect (counterfactual test).

        In MVP, this uses heuristic rules. Phase 3 will use DoWhy-GCM.
        """
        counterfactual_question = (
            f"若「{cause.description}」未發生，「{effect.description}」是否仍會發生？"
        )

        # Evidence attached to both events increases confidence, but cannot by itself
        # establish the counterfactual claim.
        has_evidence = bool(cause.evidence and effect.evidence)

        return NecessityResult(
            passed=False,
            counterfactual_question=counterfactual_question,
            counterfactual_answer="uncertain",
            confidence=ConfidenceScore(0.6 if has_evidence else 0.4),
            reasoning="缺少明確反事實評估，不能將必要性視為已通過",
        )

    def _check_mechanism(
        self,
        cause: CauseEvent,
        effect: CauseEvent,
    ) -> MechanismResult:
        """
        Check if there's a plausible causal mechanism.

        This checks if there's a logical pathway from cause to effect.
        """
        # A plausible mechanism must be supplied or supported; do not infer one
        # merely from the event descriptions.
        return MechanismResult(
            passed=False,
            causal_pathway=[
                cause.description,
                "[需要 Agent 補充中間步驟]",
                effect.description,
            ],
            mechanism_plausibility="low",
            domain_knowledge_support=False,
        )

    def _check_sufficiency(
        self,
        cause: CauseEvent,
        effect: CauseEvent,
    ) -> SufficiencyResult:
        """
        Check if cause is sufficient for effect.

        This identifies potential confounders that might also be needed.
        """
        # In MVP, return a template for Agent to analyze
        return SufficiencyResult(
            passed=False,  # Conservative: assume not sufficient alone
            analysis=f"分析「{cause.description}」是否足以單獨導致「{effect.description}」",
            confounders_identified=["[需要 Agent 識別其他必要因素]"],
            conclusion="MVP 階段：假設原因為貢獻因素而非充分條件",
        )

    def _build_result(
        self,
        verification_id: str,
        level: VerificationLevel,
        cause: CauseEvent,
        effect: CauseEvent,
        tests: VerificationTestResults,
    ) -> CausationVerificationResult:
        """Build the final verification result based on test outcomes."""
        # Count passed tests
        passed_count = 0
        total_count = 0

        if tests.temporality:
            total_count += 1
            if tests.temporality.passed:
                passed_count += 1

        if tests.necessity:
            total_count += 1
            if tests.necessity.passed:
                passed_count += 1

        if tests.mechanism:
            total_count += 1
            if tests.mechanism.passed:
                passed_count += 1

        if tests.sufficiency:
            total_count += 1
            if tests.sufficiency.passed:
                passed_count += 1

        # Determine overall result
        if total_count > 0 and passed_count == total_count:
            overall = VerificationResult.VERIFIED
            confidence = 0.85
            # Passing submitted obligations does not establish clinical causal
            # strength.  Root/contributing-factor attribution remains a human
            # review decision outside this conservative audit service.
            strength = None
            interpretation = "提交的稽核義務已通過；這不是臨床因果關係的證明"
        else:
            overall = VerificationResult.INSUFFICIENT_DATA
            confidence = 0.4
            strength = None
            interpretation = "資料不足；僅可保留為提議關係，不能宣稱臨床因果"

        # Build caveats
        caveats: list[str] = []
        if tests.temporality and not tests.temporality.passed:
            caveats.append("時序性尚未驗證")
        if tests.necessity and not tests.necessity.passed:
            caveats.append("必要性測試未通過")
        if tests.mechanism and not tests.mechanism.passed:
            caveats.append("機制性測試未通過")
        if tests.sufficiency and not tests.sufficiency.passed:
            caveats.append("充分性測試未通過，可能存在其他必要因素")

        return CausationVerificationResult(
            verification_id=verification_id,
            verification_level=level,
            cause=cause.description,
            effect=effect.description,
            tests=tests,
            overall_result=overall,
            confidence=ConfidenceScore(confidence),
            causal_strength=strength,
            interpretation=interpretation,
            next_steps=self._get_next_steps(tests),
            caveats=caveats if caveats else None,
        )

    def _get_next_steps(self, tests: VerificationTestResults) -> list[str]:
        """Get recommended next steps based on test results."""
        steps: list[str] = []

        if tests.temporality and not tests.temporality.passed:
            steps.append("重新確認事件發生的時間順序")

        if tests.necessity and tests.necessity.confidence.value < 0.7:
            steps.append("收集更多證據以支持因果必要性")

        if tests.mechanism and not tests.mechanism.domain_knowledge_support:
            steps.append("查詢領域知識以驗證因果機制")

        if tests.sufficiency and tests.sufficiency.confounders_identified:
            steps.append("分析識別出的其他因素是否也是必要條件")

        if not steps:
            steps.append("提交的因果稽核義務已通過；仍需合格人員審查臨床因果主張")

        return steps
