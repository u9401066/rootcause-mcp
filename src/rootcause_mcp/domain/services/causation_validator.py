"""
Causation Validator Domain Service.

Validates causal relationships using the Counterfactual Testing Framework.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from rootcause_mcp.domain.value_objects.enums import VerificationResult, CausalStrength
from rootcause_mcp.domain.value_objects.scores import ConfidenceScore


class VerificationLevel(str, Enum):
    """Level of verification depth."""

    STANDARD = "standard"  # Temporality + Necessity
    COMPREHENSIVE = "comprehensive"  # All 4 tests


@dataclass
class CauseEvent:
    """An event in a causal relationship."""

    description: str
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
    Domain service for validating causal relationships.

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
        Validate a causal relationship between two events.

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

        # If temporality fails, return early
        if not tests.temporality.passed:
            return CausationVerificationResult(
                verification_id=verification_id,
                verification_level=level,
                cause=cause.description,
                effect=effect.description,
                tests=tests,
                overall_result=VerificationResult.REJECTED,
                confidence=ConfidenceScore(0.95),
                interpretation="時序性測試失敗：原因必須在結果之前發生",
                next_steps=["檢查事件時間順序", "確認事件描述是否正確"],
            )

        # Run necessity check
        tests.necessity = self._check_necessity(cause, effect)

        # For standard level, stop here
        if level == VerificationLevel.STANDARD:
            return self._build_result(
                verification_id, level, cause, effect, tests
            )

        # For comprehensive level, run additional tests
        tests.mechanism = self._check_mechanism(cause, effect)
        tests.sufficiency = self._check_sufficiency(cause, effect)

        return self._build_result(
            verification_id, level, cause, effect, tests
        )

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

        # Without timestamps, we can't verify temporality precisely
        # Return a "needs more info" result
        return TemporalityResult(
            passed=True,  # Assume correct if no timestamps
            conclusion="無法精確驗證時序（缺少時間戳），假設時序正確",
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

        # Heuristic: If there's strong evidence linking them, assume necessity
        # This is a simplified version - Phase 3 will use proper causal inference
        has_evidence = bool(cause.evidence and effect.evidence)

        return NecessityResult(
            passed=True,  # Default to passed in MVP (needs Agent confirmation)
            counterfactual_question=counterfactual_question,
            counterfactual_answer="unlikely",  # Default assumption
            confidence=ConfidenceScore(0.6 if has_evidence else 0.4),
            reasoning="MVP 階段：需要 Agent 確認反事實推論結果",
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
        # In MVP, return a template for Agent to fill in
        return MechanismResult(
            passed=True,  # Default to passed, needs Agent to provide pathway
            causal_pathway=[
                cause.description,
                "[需要 Agent 補充中間步驟]",
                effect.description,
            ],
            mechanism_plausibility="medium",
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
        if passed_count == 0:
            overall = VerificationResult.REJECTED
            confidence = 0.9
            strength = CausalStrength.NOT_CAUSAL
            interpretation = "因果關係被拒絕"
        elif passed_count == total_count:
            overall = VerificationResult.VERIFIED
            confidence = 0.85
            strength = CausalStrength.ROOT_CAUSE if tests.sufficiency and tests.sufficiency.passed else CausalStrength.CONTRIBUTING_FACTOR
            interpretation = "因果關係已驗證"
        else:
            overall = VerificationResult.VERIFIED_WITH_CAVEATS
            confidence = 0.7
            strength = CausalStrength.CONTRIBUTING_FACTOR
            interpretation = "因果關係部分驗證，存在注意事項"

        # Build caveats
        caveats: list[str] = []
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
            steps.append("因果關係已充分驗證，可進行下一步分析")

        return steps
