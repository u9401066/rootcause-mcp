# Agent Integration Guide: How to Use RootCause MCP

> **For AI Agents**: Claude Code, Codex, OpenClaw, Cline, Z.ai, etc.  
> **Purpose**: Transform your medical reasoning into auditable, structured output

The bundled
[RootCause clinical reasoning harness](../.codex/skills/rootcause-clinical-reasoning-harness/SKILL.md)
is the canonical operating workflow. Read the live
`clinical://contracts/case-input-manifest` and
`clinical://contracts/case-analysis-report` resources before starting or finalizing
a case; their schemas override copied examples in this guide.

---

## 🎯 Core Principle

**You (the Agent) do the thinking. We (MCP) provide the structure.**

RootCause MCP is NOT a diagnostic AI. It's a **reasoning harness** that helps you:
- Structure your differential diagnosis process
- Track evidence with provenance
- Express uncertainty without inventing precision
- Generate auditable reports

The Agent performs the clinical interpretation. MCP has no independent thinking
ability and does not parse raw PDF, DOCX, image, scan, spreadsheet, or EHR batches.
The host or an approved extractor must preserve citation-ready text/cells, source
locations, hashes, time precision, units, negation, OCR corrections, and extraction
method before registering atomic evidence.

For clinician-facing output, use Traditional Chinese prose while keeping canonical
diagnosis, test, drug, device, and procedure names in English. An established
abbreviation may receive an optional Traditional Chinese gloss on first use; exact
source quotations and units remain unchanged. The focused harness reference is
[Clinician DDx Discussion (zh-TW)](../.codex/skills/rootcause-clinical-reasoning-harness/references/clinician-ddx-discussion-zh-tw.md).

### Token-efficient operating mode

For diagnosis-focused work, configure `ROOTCAUSE_TOOL_PROFILE=clinical`; use `rca`
for HFACS/Fishbone/Why Tree work and `all` only when both surfaces are required.
Keep `ROOTCAUSE_RESPONSE_MODE=compact` when your MCP host supports SDK 2.0
`structuredContent`.

Do not repeatedly retrieve complete evidence, thinking, and reasoning chains merely
to write the report. Generate a preliminary artifact first:

```json
{
    "session_id": "sess_001",
    "format": "markdown",
    "detail_level": "standard",
    "locale": "zh-TW",
    "audience": "clinician",
    "finalize": false
}
```

The server deterministically generates the source inventory, ranked DDx, evidence
matrix, uncertainty/bias review, RCA artifacts, completeness warnings, audit trail,
Evidence Graph, and machine-readable `conformance_checks[]`. Use `brief` for
context-efficient checkpoints and `full` for human audit.

`finalize=true` recomputes every hard check and fails closed. It requires a reviewed
multi-source manifest, complete final sections, no high/critical conflicts, at least
three unique diagnoses across at least two non-`UNKNOWN` mechanisms with typed
candidate/evidence/test dispositions, safe leading and must-not-miss challenges,
Fishbone/Why artifacts, exact root/audit/evidence lineage,
safe root dispositions, and an `approved_by` identity in
`ROOTCAUSE_AUTHORIZED_REVIEWERS`. Finalization adds reviewer/time/hash metadata and
recursively freezes the domain snapshot. Durable WORM storage still belongs to the
deployment's approved records system.

An allowlisted reviewer is operator-authorized, not automatically a qualified
clinician. The deployment must verify the reviewer role independently.

---

## 🚨 Critical: Candidate Records Force Transparency

Our tools have **required fields** that force you to expose your reasoning:

### ❌ Bad Example (Thin Reasoning)

```json
{
  "session_id": "sess_001",
  "diagnosis": "Acute Myocardial Infarction"
}
```

**Problem**: We do not know why it was considered, which mechanisms were searched,
which evidence is source-linked, or what remains unknown.

---

### ✅ Good Example (Deep Reasoning)

```json
{
  "session_id": "sess_001",
  "diagnosis": "Acute Myocardial Infarction",
  "icd10_code": "I21.9",
  "mechanism_category": "VASCULAR",
  "diagnostic_role": "ETIOLOGIC",
  "reasoning_basis": "MECHANISM_INFERENCE",
  "certainty": "POSSIBLE",
  "must_not_miss": true,

  "clinical_reasoning": "Inference: EV-001 and EV-002 form a compatible ischemic phenotype; Acute Myocardial Infarction is considered, but the mechanism is not confirmed.",

  "differential_diagnoses_considered": [],

  "uncertainty_factors": [
    "not measured: serial ECG; competing ischemic and non-ischemic mechanisms remain open",
    "not documented: prior ECG comparison",
    "unverified: EV-002 exact source match"
  ],

  "confidence_rationale": "POSSIBLE: compatible source-linked observations exist, but no completed discriminating test supports a higher certainty label. Any server compatibility prior is an implementation placeholder, not a clinical probability.",
  "planned_tests": [
    {
      "name": "Serial ECG",
      "purpose": "DISCONFIRM",
      "expected_supporting_result": "Persistent territorial ischemic change",
      "expected_refuting_result": "Adequate serial studies without ischemic change",
      "status": "PLANNED"
    }
  ]
}
```

The example records one candidate; it is not a complete differential. Expand the
phenotype/time course across the maximum reasonable distinct mechanisms, then prune
synonyms and candidates with no plausible mechanism or decision impact. Three unique
diagnoses, two non-`UNKNOWN` mechanisms, and one applicable must-not-miss diagnosis are
finalization floors, not a clinical target or cap. Each active candidate needs its own
why-considered rationale, uncertainty, evidence/test disposition, and certainty label.

The legacy `evidence_supporting` and `evidence_contradicting` proposal fields are
deprecated context-only inputs: they do not create or persist an association. Call
`rc_link_evidence_to_hypothesis` once for each supporting or contradicting item.

---

## 📋 Tool Usage Patterns

### Pattern 1: Systematic Differential Diagnosis

```python
# Step 1: Register each source-grounded finding
troponin = await rc_add_evidence(
    session_id="sess_001",
    content="Troponin I: 2.5 ng/mL",
    evidence_type="LAB_RESULT",
    source_document="approved-extract/lab_results.txt",
    source_location="Line 12",
    raw_snippet="Troponin I: 2.5 ng/mL",
    event_timestamp="2026-08-17T10:15:00+08:00",
    clinical_strength="STRONG",
    source_reliability="GRADE_A"
)

# Step 2: Record the explicit decision frame
await rc_think_aloud(
    session_id="sess_001",
    thinking_type="DECISION_POINT",
    content="Acute MI is currently the leading diagnosis",
    internal_reasoning="Chest pain, ECG findings, and troponin support acute MI.",
    alternatives=[
        {
            "alternative": "Pulmonary embolism",
            "reason_rejected": "No hypoxemia or right-heart strain"
        }
    ],
    confidence=agent_declared_workflow_confidence,
    uncertainty_factors=["Serial ECG pending"]
)

# Step 3: Propose the hypothesis with a complete rationale contract
await rc_propose_hypothesis(
    session_id="sess_001",
    diagnosis="Acute myocardial infarction",
    icd10_code="I21.9",
    mechanism_category="VASCULAR",
    diagnostic_role="ETIOLOGIC",
    reasoning_basis="MECHANISM_INFERENCE",
    certainty="POSSIBLE",
    clinical_reasoning="Chest pain, ECG findings, and troponin support acute MI.",
    differential_diagnoses_considered=[],
    uncertainty_factors=["Serial ECG pending"],
    confidence_rationale=(
        "POSSIBLE because observations are compatible but the discriminating test "
        "is pending; any compatibility prior is not a clinical probability"
    ),
    planned_tests=[
        {
            "name": "Serial ECG",
            "purpose": "DISCONFIRM",
            "expected_supporting_result": "Persistent territorial ischemic change",
            "expected_refuting_result": (
                "Adequate serial studies without ischemic change"
            ),
            "status": "PLANNED",
        }
    ],
)
```

Repeat across the maximum reasonable distinct mechanisms. The deterministic report
floor is at least three normalized diagnoses across two non-`UNKNOWN` mechanisms plus
one applicable must-not-miss entry; it is not a breadth target or cap. The server
assigns each planned test a stable `test_id` and binds it to the new
`target_hypothesis_id`; free-text gaps are not equivalent to a typed test.

Select a syndrome-appropriate framework and call `rc_audit_differential_breadth`
(condensed: `rc_hypothesis(action="audit_breadth")`). Built-in `VINDICATE`,
`FIVE_H_FIVE_T`, `ANATOMIC_SYSTEM`, and `MEDICATION_DEVICE_EXPOSURE` audits require
every exact canonical cell from the live tool schema. A `CUSTOM` audit requires an
explicit name and at least two cells.

Every cell must be `CANDIDATES_PRESENT`, `REVIEWED_NO_PLAUSIBLE_CANDIDATE`,
`REVIEWED_INSUFFICIENT_DATA`, or `NOT_ASSESSED`. A final PRIMARY audit may contain no
`NOT_ASSESSED`. Insufficient data is still reviewed coverage only when the cell keeps
explicit unknowns and typed planned discriminators; it is never evidence of exclusion.
The breadth audit demonstrates systematic review, not clinical correctness.

---

### Pattern 2: Evidence-Based Bayesian Updating

```python
# Add evidence with quality grading
evidence = await rc_add_evidence(
    session_id="sess_001",
    content="Troponin I: 2.5 ng/mL (normal < 0.04)",
    evidence_type="LAB_RESULT",
    source_document="approved-extract/lab_results.txt",
    source_location="Line 12",
    raw_snippet="Troponin I: 2.5 ng/mL (normal < 0.04)",
    clinical_strength="STRONG",  # Direct lab measurement
    source_reliability="GRADE_A"  # Primary source
)

# Link to hypothesis with likelihood ratio
await rc_link_evidence_to_hypothesis(
    session_id="sess_001",
    evidence_id=evidence.id,
    hypothesis_id="HYP-001",
    likelihood_ratio=validated_applied_lr,
    supports=True,
    rationale=validated_lr_source_or_case_specific_rationale,
)
```

`validated_applied_lr` must be the direct LR supported by an approved source or a
documented local calibration. Never invent a value or citation. If no quantitative
LR is justified, use `1.0` and record the qualitative relationship; note that a
neutral LR does not count as genuine support or contradiction for final conformance.

---

### Pattern 3: Decision-Point Records

```python
# Decision point 1: Initial assessment
await rc_think_aloud(
    session_id="sess_001",
    thinking_type="DECISION_POINT",
    content="Initial differential includes ACS, PE, and aortic dissection",
    internal_reasoning="Acute chest pain requires simultaneous exclusion of time-critical causes.",
    confidence=agent_declared_workflow_confidence
)

# Decision point 2: After ECG
await rc_think_aloud(
    session_id="sess_001",
    thinking_type="EVIDENCE_EVALUATED",
    content="Inferior STEMI pattern identified",
    internal_reasoning="ST elevation in II, III, aVF with reciprocal changes supports inferior STEMI.",
    confidence=agent_declared_workflow_confidence
)

# Reflection after key evidence
await rc_reflect(
    session_id="sess_001",
    reflection_content="Acute MI is likely, but competing causes of myocardial injury remain possible.",
    identified_gaps=["Serial ECG and echocardiography pending"],
    identified_biases=["Anchoring on the first ECG"]
)
```

---

### Pattern 4: Verbatim Provenance & Cryptographic Grounding

```python
# Add evidence with exact raw snippet and line locator
finding = await rc_add_evidence(
    session_id="sess_001",
    content="Grade 2/6 Systolic Murmur at Left Sternal Border on pre-op exam",
    evidence_type="OBSERVATION",
    source_document="DATA_SOURCE_01_PRE_ANESTHESIA_EVALUATION.txt",
    source_location="CV line 14",
    raw_snippet="CV: RRR, Grade 2/6 Systolic Murmur at LSB (Left Sternal Border).",
    clinical_strength="STRONG",
    source_reliability="GRADE_A",
    auto_verify=True  # Server verifies verbatim quote on disk
)
```

---

### Pattern 5: Multi-Loop Guidance for Lightweight (Flash) Models

```python
# Check guidance state machine at any turn
audit = await rc_audit_reasoning_state(session_id="sess_001")

# If not ready for synthesis, follow the next recommended actions
if not audit["is_ready_for_report"]:
    print(f"Current stage: {audit['stage_display']}")
    print(f"Missing items: {audit['missing_prerequisites']}")
    print(f"Next prompt: {audit['next_recommended_actions'][0]}")
    # Flash agent executes the recommended tool in the next loop turn
```

### Pattern 6: Conservative Root Audit and Final Preview

For every Why node marked as a root, use the same stable root ID, exact Why answer,
and evidence ID set in the causation-audit cause event. Effect evidence must also
resolve to the case evidence ledger. The validator is a conservative proof-obligation
audit; it has no independent clinical reasoning and does not prove causality.

Interpret the latest audit result as follows:

| Audit result | Final root-cause bucket |
| --- | --- |
| `REJECTED` | Omit from `root_causes` |
| `INSUFFICIENT_DATA` | Retain only as `disposition="PROPOSED"` when disclosed |
| `VERIFIED` / `VERIFIED_WITH_CAVEATS` | Use `disposition="AUDIT_OBLIGATIONS_PASSED"`; never say causation was proven |

Preview JSON before requesting finalization and inspect every check, not just an
overall status:

```python
preview = await rc_generate_contract_report(
    session_id="sess_001",
    format="json",
    detail_level="full",
    finalize=False,
)

failed = [
    check
    for check in preview["conformance_checks"]
    if check["status"] == "FAIL"
]
```

Resolve hard failures through the corresponding evidence, hypothesis, RCA, or
review workflow. Do not edit the rendered report or fabricate `PASS` entries. Only
an operator-authorized, independently qualified reviewer may request `finalize=true`.

### 1. Explore Bounded Mechanism Breadth

Do not stop at one pattern-matched diagnosis or at the three-item conformance floor.
Define the phenotype and time course, map the plausible mechanism categories, retain
applicable must-not-miss candidates, and ask which feasible discriminator would alter
the disposition. Merge synonyms and prune candidates with no plausible mechanism or
decision impact. This produces maximum reasonable breadth without an infinite laundry
list.

For every candidate, persist canonical English diagnosis, `mechanism_category`,
`diagnostic_role`, `reasoning_basis`, qualitative `certainty`, why considered,
source-linked supporting/refuting/neutral evidence, candidate-specific unknowns, and a
discriminating test. Safety priority and certainty are separate dimensions.

---

### 2. Make Unknowns Decision-Relevant

Classify an unknown as `not documented`, `not measured`, `pending`, `conflicting`,
`unverified`, or `unknown`. It is not negative evidence. State which mechanisms remain
open, which candidates it affects, and what source/test/review could resolve it.

```python
# ❌ Bad
uncertainty_factors=["Not sure"]

# ✅ Good
uncertainty_factors=[
    "pending: serial ECG; affects VASCULAR candidate certainty",
    "not documented: prior ECG; baseline comparison remains open",
    "unverified: EV-002 exact source match; do not treat as confirmed"
]
```

---

### 3. Use Qualitative Certainty Without False Precision

Use `UNKNOWN`, `POSSIBLE`, `PROBABLE`, `HIGH_CONFIDENCE`, `CONFIRMED`, or `EXCLUDED`
and explain the evidence/test basis. `PROBABLE` or higher requires genuine evidence or
a completed discriminating test; `CONFIRMED` must match lifecycle status.

```python
# ❌ Bad: unexplained number presented as a clinical probability
prior_probability=guessed_number

# ✅ Good: qualitative label plus source-linked basis and a discriminator
certainty="POSSIBLE",
confidence_rationale=(
    "EV-001 is compatible but not specific; EV-002 is unverified and the serial "
    "ECG discriminator remains pending"
)
```

When the server supplies a numeric compatibility default, disclose it as an
implementation placeholder. Do not show it as clinical probability, ranking, or
certainty. A posterior number never automatically determines the certainty enum.

---

### 4. Acknowledge Your Biases

**We all have cognitive biases. Acknowledge them.**

```python
# Use rc_reflect to identify biases
await rc_reflect(
    session_id="sess_001",
    reflection_content="I realize I've been focusing on cardiac causes because the patient had recent CABG",
    identified_biases=[
        "Anchoring bias (first impression was cardiac)",
        "Availability bias (recent similar case was MI)",
        "Confirmation bias (seeking cardiac evidence)"
    ],
    alternative_approaches=[
        "Should systematically consider VINDICATE categories",
        "Should not overweight recent surgery as risk factor"
    ]
)
```

---

## 🔄 Workflow Comparison

### ❌ Thin MCP (What We Want to Avoid)

```text
Agent reads documents → Agent thinks internally → Agent calls MCP with conclusion
                                                    ↓
                                            MCP records result
                                                    ↓
                                            Human: "Why did you conclude this?"
                                            Agent: "Um... because...?"
```

### ✅ Deep MCP (What We're Building)

```text
Agent reads documents
    ↓
Agent calls rc_add_evidence for each source-grounded finding
    ↓
Agent calls rc_think_aloud to externalize the decision frame
    ↓
Agent calls rc_propose_hypothesis (forced to explain reasoning)
    ↓
Agent calls rc_link_evidence_to_hypothesis (forced to quantify evidence strength)
    ↓
Agent records key decision points with rc_think_aloud
    ↓
Agent calls rc_reflect (forced to identify biases)
    ↓
MCP generates ContractReport with persisted audit records
    ↓
Human: "Why did you conclude this?"
System: "Here's the recorded reasoning chain, including alternatives considered,
         uncertainty factors, and potential biases identified."
```

---

## 📊 What Gets Recorded

### ReasoningChain (What You Did)

- Recorded orchestrator actions with timestamps
- Evidence added
- Hypotheses proposed
- Bayesian updates performed

### ThinkingChain (Why You Did It)

- Alternatives considered and rejected
- Uncertainty factors
- Confidence rationale
- Cognitive biases identified
- Assumptions made

### ContractReport (Auditable Output)

- Source manifest coverage and verification state
- Typed evidence graph and source-to-claim lineage
- A complete PRIMARY framework breadth audit plus the deterministic DDx floors, typed
  candidate/evidence/test dispositions, and must-not-miss flags
- Reasoning chain
- Thinking chain
- Fishbone, Why Tree/root causes, HFACS, and conflict/readiness sections
- Conservative causation audits with explicit non-proof scope and safe root dispositions
- Quality metrics (evidence coverage and hypothesis coverage; any workflow confidence
  scalar remains separate from clinical probability/certainty)
- Machine-readable `conformance_checks[]`
- Final-only reviewer, timezone-aware finalization time, and recomputable content hash

---

## 🎯 Summary: Your Responsibilities as an Agent

1. **Think explicitly** — Separate observation, clinical inference, and causal claim
2. **Cover mechanisms** — Build maximum reasonable breadth, not a fixed-three or infinite list
3. **Use unknowns** — State what remains open and what would discriminate it
4. **Label certainty** — Use qualitative labels with evidence/test support, not invented precision
5. **Acknowledge biases** — We all have them, identify yours
6. **Record decision points** — Use `rc_think_aloud` when the ranking changes
7. **Reflect regularly** — Use rc_reflect to audit your own reasoning

---

## 🚀 Getting Started

1. Inventory all de-identified source documents and start one session with a version
   `1.0` source manifest.
2. Call `rc_add_evidence` for each atomic traceable finding, preserving exact snippet,
   source location, and canonical event time when defensible.
3. Call `rc_think_aloud` to record the explicit decision frame.
4. Build the maximum reasonable mechanism-based DDx, choose a syndrome-appropriate
   framework, and record every cell with `rc_audit_differential_breadth` (or condensed
   `rc_hypothesis(action="audit_breadth")`). Treat three unique diagnoses,
   two non-`UNKNOWN` mechanisms, and one applicable must-not-miss entry as finalization
   floors, then call `rc_propose_hypothesis` with candidate classifications, rationale,
   uncertainty, certainty, and typed `planned_tests` where a discriminator is pending.
   A final PRIMARY breadth audit cannot leave `NOT_ASSESSED`; reviewed insufficient
   data stays open with unknowns and typed discriminators.
5. Call `rc_link_evidence_to_hypothesis` with the direct applied LR for supporting and
   disconfirming evidence.
6. Call `rc_reflect`, conflict detection, the conservative causation audit, and the
   Fishbone/Why/HFACS workflow. Keep root ID/description/evidence exactly aligned;
   omit rejected claims and keep insufficient-data candidates proposed.
7. Run `rc_audit_reasoning_state` until every prerequisite is resolved or explicitly
   left as a preliminary limitation.
8. Call `rc_generate_contract_report(format="markdown", locale="zh-TW",
   audience="clinician", finalize=false)` for clinician review. This localization is
   for the built-in Markdown renderer; custom templates retain their own language and
   JSON/FHIR values are not translated. Inspect `conformance_checks[]`; only a named,
   operator-authorized, independently qualified human may approve a gated final artifact.

## Agent MVP Evaluation Status

The public six-case corpus and `scripts/run_agent_eval.py dry-run` exercise runner
mechanics only. They are not blinded because the public reference rubrics are in the
same repository. The formal Agent eval remains `AGENT_EVAL_NOT_ESTABLISHED` until
there are at least three real runtimes, 36 clean-root runs, a repository-external
private case bundle, separately protected private holdout gold, filesystem isolation
that prevents adapters from discovering either parent/repository context or gold,
trusted runtime/server MCP traces, and two blinded qualified clinical reviews per
job with adjudication of disagreement.

See [MVP conformance and Agent evaluation](mvp_conformance_and_evaluation.md) for the
fail-closed protocol, artifact requirements, and acceptance thresholds. Until that
protocol passes, describe the repository as an **engineering alpha**, not a complete
Agent MVP.

---

**Remember**: We're not here to replace your reasoning. We're here to make it **auditable, transparent, and defensible**.

**Your thinking. Our structure. Better outcomes.**

---

**Version**: 2.0.0a2

**Last Updated**: 2026-08-18

**For**: All AI Agents (Claude Code, Codex, OpenClaw, Cline, Z.ai, etc.)
