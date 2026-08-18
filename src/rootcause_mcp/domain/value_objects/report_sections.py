"""Typed nested sections for the unified clinical reasoning report.

The report presenter historically consumed ordinary dictionaries.  These
``TypedDict`` contracts deliberately preserve that runtime interface while
making every stable report section visible in the generated JSON Schema.
Optional keys allow an explicitly incomplete preliminary report; final-release
completeness is enforced by conformance gates rather than by inventing values.
"""

# mypy: disable-error-code=call-arg

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import ConfigDict, JsonValue
from typing_extensions import TypedDict


class ClinicalConceptRecord(TypedDict, total=False, extra_items=JsonValue):
    """Coded or local diagnosis concept."""

    code: str
    display: str
    system: str
    version: str | None


class LikelihoodRatioRecord(TypedDict, total=False, extra_items=JsonValue):
    """Direct likelihood ratio applied to one evidence relationship."""

    evidence_id: str
    lr_positive: float | None
    lr_negative: float | None
    applied_likelihood_ratio: float | None
    supports: bool | None
    rationale: str


class BayesianUpdateRecord(TypedDict, total=False, extra_items=JsonValue):
    """One auditable probability update."""

    timestamp: datetime
    evidence_id: str
    prior_probability: float
    likelihood_ratio: float
    posterior_probability: float
    updated_by: str


class HypothesisStatusChangeRecord(TypedDict, total=False, extra_items=JsonValue):
    """One hypothesis lifecycle transition."""

    timestamp: datetime
    previous_status: str
    new_status: str
    changed_by: str
    reason: str


class TestDispositionRecord(TypedDict, total=False, extra_items=JsonValue):
    """Observed or planned test used to disposition an active diagnosis."""

    test: str
    status: Literal["OBSERVED", "PLANNED", "NOT_AVAILABLE", "NOT_APPLICABLE"]
    evidence_ids: list[str]
    expected_direction: str | None
    result_or_plan: str


class DiagnosticAlternativeRecord(TypedDict, total=False, extra_items=JsonValue):
    """Competing diagnosis and its explicit disposition rationale."""

    diagnosis: str
    reason_rejected: str
    disposition: str


class PlannedDiagnosticTestRecord(TypedDict, total=False, extra_items=JsonValue):
    """Persisted plan or result used to confirm, refute, or discriminate a DDx."""

    test_id: str
    name: str
    purpose: Literal["DISCONFIRM", "RULE_OUT", "CONFIRM", "DISCRIMINATE"]
    target_hypothesis_id: str
    expected_supporting_result: str
    expected_refuting_result: str
    status: Literal["PLANNED", "ORDERED", "COMPLETED", "CANCELLED"]
    result_evidence_id: str | None
    result_summary: str | None


class HypothesisRecord(TypedDict, total=False, extra_items=JsonValue):
    """Differential-diagnosis entry retained in the report ledger."""

    id: str
    diagnosis: ClinicalConceptRecord
    prior_probability: float
    current_probability: float
    inclusion_criteria: list[str]
    exclusion_criteria: list[str]
    must_not_miss: bool
    alternatives_considered: list[DiagnosticAlternativeRecord]
    uncertainty_factors: list[str]
    confidence_rationale: str
    likelihood_ratios: list[LikelihoodRatioRecord]
    supporting_evidence_ids: list[str]
    contradicting_evidence_ids: list[str]
    planned_tests: list[PlannedDiagnosticTestRecord]
    test_disposition: list[TestDispositionRecord]
    status: str
    status_history: list[HypothesisStatusChangeRecord]
    created_at: datetime
    created_by: str
    bayesian_history: list[BayesianUpdateRecord]
    clinical_rationale: str


class EvidenceQualityRecord(TypedDict, total=False, extra_items=JsonValue):
    """Strength and reliability labels for one observation."""

    strength: str
    reliability: str


class EvidenceSourceRecord(TypedDict, total=False, extra_items=JsonValue):
    """Exact source lineage for one evidence item."""

    document_id: str | None
    location: str | None
    raw_snippet: str | None
    content_hash: str | None
    extraction_method: str | None
    collected_by: str
    collection_timestamp: datetime
    source_system: str | None


class EvidenceRecord(TypedDict, total=False, extra_items=JsonValue):
    """Atomic evidence observation and its links."""

    id: str
    content: str
    evidence_type: str
    clinical_context: str | None
    quality: EvidenceQualityRecord
    source: EvidenceSourceRecord
    event_timestamp: datetime | None
    supports_cause_ids: list[str]
    supports_hypothesis_ids: list[str]
    contradicts_hypothesis_ids: list[str]
    verified: bool
    verifier: str | None
    verification_method: str | None
    matched_lines: list[int]
    verification_timestamp: datetime | None
    tags: list[str]


class SourceInventoryRecord(TypedDict, total=False, extra_items=JsonValue):
    """Manifest document plus report evidence coverage."""

    document: str | None
    source_uri: str | None
    sha256: str | None
    media_type: str | None
    source_kind: str | None
    revision: str | None
    captured_at: datetime | None
    parser_name: str | None
    parser_version: str | None
    de_identified: bool | None
    evidence_count: int
    verified_count: int
    coverage_status: str


class TimelineEventRecord(TypedDict, total=False, extra_items=JsonValue):
    """Canonical timeline event linked to a source observation."""

    id: str
    time: str
    phase: str
    content: str
    source_document: str | None
    verified: bool
    evidence_type: str


class TimelineRecord(TypedDict, total=False, extra_items=JsonValue):
    """Canonical events plus deterministic presentation derivatives."""

    pattern: str
    title: str
    events: list[TimelineEventRecord]
    mermaid: str
    table: str


class ReasoningStepRecord(TypedDict, total=False, extra_items=JsonValue):
    """One public, concise reasoning-audit step."""

    id: str
    sequence_number: int
    timestamp: datetime
    step_type: str
    content: str
    rationale: str
    evidence_ids: list[str]
    hypothesis_ids: list[str]
    cause_ids: list[str]
    agent_id: str
    agent_model: str | None
    confidence: float | None
    tokens_used: int | None
    chain_of_thought: dict[str, JsonValue] | None


class AlternativeRecord(TypedDict, total=False, extra_items=JsonValue):
    """Alternative explicitly considered by the agent."""

    alternative: str
    reason_rejected: str
    confidence_if_chosen: float | None


class ThinkingStepRecord(TypedDict, total=False, extra_items=JsonValue):
    """Auditable cognitive-safety note; never a hidden scratchpad requirement."""

    id: str
    timestamp: datetime
    thinking_type: str
    content: str
    internal_reasoning: str
    alternatives: list[AlternativeRecord]
    confidence: float
    uncertainty_factors: list[str]
    related_evidence_ids: list[str]
    related_hypothesis_ids: list[str]
    assumptions_made: list[str]
    potential_biases: list[str]
    structured_data: dict[str, JsonValue]


class EvidenceGraphNodeRecord(TypedDict, total=False, extra_items=JsonValue):
    """Evidence graph node."""

    id: str
    type: str
    label: str
    status: str
    probability: float


class EvidenceGraphEdgeRecord(TypedDict, total=False, extra_items=JsonValue):
    """Evidence graph relationship."""

    source: str
    target: str
    relationship: str


class EvidenceGraphRecord(TypedDict, total=False, extra_items=JsonValue):
    """Evidence-to-hypothesis/cause graph."""

    nodes: list[EvidenceGraphNodeRecord]
    edges: list[EvidenceGraphEdgeRecord]
    warnings: list[str]
    mermaid: str


class RCASessionRecord(TypedDict, total=False, extra_items=JsonValue):
    """Case-level RCA aggregate metadata."""

    session_id: str
    case_type: str
    case_title: str
    status: str
    current_stage: str
    problem_statement: str | None
    initial_description: str
    progress: dict[str, str]
    created_at: datetime
    updated_at: datetime
    created_by: str
    source_manifest_digest: str | None
    source_document_count: int


class FishboneCauseRecord(TypedDict, total=False, extra_items=JsonValue):
    """One cause in a Fishbone category."""

    cause_id: str
    description: str
    sub_causes: list[str]
    hfacs_code: str | None
    evidence: list[str]
    verified: bool


class FishboneCategoryRecord(TypedDict, total=False, extra_items=JsonValue):
    """Fishbone category and its causes."""

    category: str
    causes: list[FishboneCauseRecord]


class FishboneRecord(TypedDict, total=False, extra_items=JsonValue):
    """Fishbone aggregate snapshot."""

    fishbone_id: str
    problem_statement: str
    categories: list[FishboneCategoryRecord]
    created_at: datetime
    updated_at: datetime


class WhyNodeRecord(TypedDict, total=False, extra_items=JsonValue):
    """One node in a Why analysis."""

    id: str
    level: int
    question: str
    answer: str
    is_root_cause: bool
    is_proximate: bool
    evidence: list[str]
    parent_id: str | None


class CausalLinkRecord(TypedDict, total=False, extra_items=JsonValue):
    """Explicit link between Why nodes."""

    source_id: str
    target_id: str
    relationship: str
    strength: float
    evidence: list[str]
    note: str
    bidirectional: bool


class FeedbackLoopRecord(TypedDict, total=False, extra_items=JsonValue):
    """Detected Why graph feedback loop."""

    node_ids: list[str]
    summary: str


class WhyTreeRecord(TypedDict, total=False, extra_items=JsonValue):
    """Complete Why analysis snapshot."""

    initial_problem: str
    depth: int
    is_complete: bool
    nodes: list[WhyNodeRecord]
    root_causes: list[str]
    causal_links: list[CausalLinkRecord]
    feedback_loops: list[FeedbackLoopRecord]


class RootCauseRecord(TypedDict, total=False, extra_items=JsonValue):
    """Root-cause candidate admitted by deterministic lineage gates."""

    id: str
    answer: str
    question: str
    level: int
    parent_id: str | None
    evidence: list[str]
    confidence: float | None
    causation_verification_id: str | None
    causation_result: str | None
    disposition: Literal["PROPOSED", "AUDIT_OBLIGATIONS_PASSED"]


class HFACSClassificationRecord(TypedDict, total=False, extra_items=JsonValue):
    """Human-confirmable HFACS classification linked to a cause."""

    cause_id: str
    cause: str
    category: str
    hfacs_code: str
    confidence: float | None
    evidence: list[str]
    verified: bool
    source: str


class CausalEventRecord(TypedDict, total=False, extra_items=JsonValue):
    """Cause/effect event submitted to the conservative audit."""

    id: str | None
    description: str
    timestamp: datetime | None
    evidence: list[str]


class ConfidenceRecord(TypedDict, total=False, extra_items=JsonValue):
    """Serialized bounded confidence value object."""

    value: float


class TemporalityTestRecord(TypedDict, total=False, extra_items=JsonValue):
    """Temporal-order audit result."""

    passed: bool
    cause_time: datetime | None
    effect_time: datetime | None
    time_diff_minutes: int | None
    conclusion: str


class NecessityTestRecord(TypedDict, total=False, extra_items=JsonValue):
    """Counterfactual necessity audit result."""

    passed: bool
    counterfactual_question: str
    counterfactual_answer: str
    confidence: ConfidenceRecord | float
    reasoning: str


class MechanismTestRecord(TypedDict, total=False, extra_items=JsonValue):
    """Mechanism audit result."""

    passed: bool
    causal_pathway: list[str]
    mechanism_plausibility: str
    domain_knowledge_support: bool


class SufficiencyTestRecord(TypedDict, total=False, extra_items=JsonValue):
    """Sufficiency/confounder audit result."""

    passed: bool
    analysis: str
    confounders_identified: list[str]
    conclusion: str


class CausationTestsRecord(TypedDict, total=False, extra_items=JsonValue):
    """Individual conservative causation audit tests."""

    temporality: TemporalityTestRecord | None
    necessity: NecessityTestRecord | None
    mechanism: MechanismTestRecord | None
    sufficiency: SufficiencyTestRecord | None


class CausationVerificationRecord(TypedDict, total=False, extra_items=JsonValue):
    """Persisted conservative causation audit; never clinical proof by itself."""

    verification_id: str
    verification_level: str
    cause: str
    effect: str
    cause_event: CausalEventRecord
    effect_event: CausalEventRecord
    tests: CausationTestsRecord
    overall_result: str
    confidence: ConfidenceRecord | float
    causal_strength: str | None
    interpretation: str
    next_steps: list[str] | None
    caveats: list[str] | None
    audit_scope: Literal["CONSERVATIVE_CAUSATION_AUDIT"]
    clinical_causality_established: bool


class GapConflictRecord(TypedDict, total=False, extra_items=JsonValue):
    """Detected clinical or workflow conflict."""

    conflict_id: str
    severity: str
    category: str
    title: str
    description: str
    conflicting_evidence_ids: list[str]
    involved_hypothesis_ids: list[str]
    actionable_remedy: str


class GapAnalysisRecord(TypedDict, total=False, extra_items=JsonValue):
    """Deterministic gap/conflict audit snapshot."""

    session_id: str
    total_conflicts: int
    critical_count: int
    high_count: int
    conflicts: list[GapConflictRecord]
    guideline_alerts: list[str]
    safety_invariants_met: bool


class ReportReadinessRecord(TypedDict, total=False, extra_items=JsonValue):
    """Clinical reasoning workflow readiness snapshot."""

    session_id: str
    current_stage: str
    stage_display: str
    completeness_score: float
    checklist: dict[str, JsonValue]
    missing_prerequisites: list[str]
    next_recommended_actions: list[str]
    push_questions: list[str]
    is_ready_for_report: bool


# Parent report models reject unknown top-level fields.  Section records remain
# explicitly extensible so an older reader preserves newly added leaf fields;
# their stable properties above are still type-checked and documented.
for _record_type in tuple(globals().values()):
    if (
        isinstance(_record_type, type)
        and _record_type.__module__ == __name__
        and hasattr(_record_type, "__required_keys__")
    ):
        _record_type.__pydantic_config__ = ConfigDict(  # type: ignore[attr-defined]
            extra="allow"
        )
del _record_type
