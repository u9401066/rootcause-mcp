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
- Quantify uncertainty
- Generate auditable reports

The Agent performs the clinical interpretation. MCP has no independent thinking
ability and does not parse raw PDF, DOCX, image, scan, spreadsheet, or EHR batches.
The host or an approved extractor must preserve citation-ready text/cells, source
locations, hashes, time precision, units, negation, OCR corrections, and extraction
method before registering atomic evidence.

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
    "finalize": false
}
```

The server deterministically generates the source inventory, ranked DDx, evidence
matrix, uncertainty/bias review, RCA artifacts, completeness warnings, audit trail,
Evidence Graph, and machine-readable `conformance_checks[]`. Use `brief` for
context-efficient checkpoints and `full` for human audit.

`finalize=true` recomputes every hard check and fails closed. It requires a reviewed
multi-source manifest, complete final sections, no high/critical conflicts, at least
three unique diagnoses with typed evidence/test dispositions, safe leading and
must-not-miss challenges, Fishbone/Why artifacts, exact root/audit/evidence lineage,
safe root dispositions, and an `approved_by` identity in
`ROOTCAUSE_AUTHORIZED_REVIEWERS`. Finalization adds reviewer/time/hash metadata and
recursively freezes the domain snapshot. Durable WORM storage still belongs to the
deployment's approved records system.

An allowlisted reviewer is operator-authorized, not automatically a qualified
clinician. The deployment must verify the reviewer role independently.

---

## 🚨 Critical: Required Fields Force Transparency

Our tools have **required fields** that force you to expose your reasoning:

### ❌ Bad Example (Thin Reasoning)

```json
{
  "session_id": "sess_001",
  "diagnosis": "Acute MI",
  "prior_probability": 0.3
}
```

**Problem**: We don't know WHY you think it's MI, WHAT ELSE you considered, or WHAT makes you uncertain.

---

### ✅ Good Example (Deep Reasoning)

```json
{
  "session_id": "sess_001",
  "diagnosis": "Acute MI",
  "icd10_code": "I21.9",
  "prior_probability": 0.3,
  "must_not_miss": true,
  
  "clinical_reasoning": "65M with acute onset substernal chest pain radiating to left arm, elevated troponin I (2.5 ng/mL), and ST elevation in leads II, III, aVF. Recent CABG 3 days ago increases suspicion for graft failure or perioperative MI.",
  
  "differential_diagnoses_considered": [
    {
      "diagnosis": "Pulmonary Embolism",
      "reason_rejected": "No dyspnea, no disproportionate tachycardia, and no right-heart strain. Recent surgery still makes PE a must-not-miss condition, so an adequate definitive imaging plan is required.",
      "likelihood_if_not_rejected": "moderate"
    },
    {
      "diagnosis": "Aortic Dissection",
      "reason_rejected": "Pain is not tearing/ripping quality, no blood pressure differential between arms, no widened mediastinum on portable CXR.",
      "likelihood_if_not_rejected": "low"
    },
    {
      "diagnosis": "Pneumonia",
      "reason_rejected": "No fever, no productive cough, WBC normal, no infiltrate on CXR.",
      "likelihood_if_not_rejected": "low"
    },
    {
      "diagnosis": "Post-pericardiotomy Syndrome",
      "reason_rejected": "No pericardial friction rub, pain is not positional, troponin is elevated (not typical for post-pericardiotomy).",
      "likelihood_if_not_rejected": "moderate"
    }
  ],
  
  "uncertainty_factors": [
    "Troponin trend pending (only one value available)",
    "No prior ECG for comparison",
    "Patient on beta-blockers which may blunt tachycardic response",
    "Recent surgery makes interpretation of inflammatory markers difficult"
  ],
  
  "confidence_rationale": "Assigned moderate prior probability (0.3) because: (1) Classic presentation with chest pain + troponin elevation, (2) Recent CABG is a strong risk factor, (3) However, atypical features (no diaphoresis, patient on beta-blockers) and pending troponin trend prevent higher confidence.",
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
    confidence=0.7,
    uncertainty_factors=["Serial ECG pending"]
)

# Step 3: Propose the hypothesis with a complete rationale contract
await rc_propose_hypothesis(
    session_id="sess_001",
    diagnosis="Acute myocardial infarction",
    icd10_code="I21.9",
    prior_probability=0.3,
    clinical_reasoning="Chest pain, ECG findings, and troponin support acute MI.",
    differential_diagnoses_considered=[
        {
            "diagnosis": "Pulmonary embolism",
            "reason_rejected": "No hypoxemia or right-heart strain"
        }
    ],
    uncertainty_factors=["Serial ECG pending"],
    confidence_rationale="Typical presentation with one important pending test",
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

Repeat the proposal for at least three normalized, non-duplicate diagnoses. The
server assigns each planned test a stable `test_id` and binds it to the new
`target_hypothesis_id`; free-text gaps are not equivalent to a typed test.

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
    confidence=0.5
)

# Decision point 2: After ECG
await rc_think_aloud(
    session_id="sess_001",
    thinking_type="EVIDENCE_EVALUATED",
    content="Inferior STEMI pattern identified",
    internal_reasoning="ST elevation in II, III, aVF with reciprocal changes supports inferior STEMI.",
    confidence=0.85
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

### 1. Always Consider Alternatives

**Don't just propose ONE diagnosis. Show us what else you considered.**

```python
# ❌ Bad
await rc_propose_hypothesis(diagnosis="MI", ...)

# ✅ Good
await rc_propose_hypothesis(
    diagnosis="MI",
    differential_diagnoses_considered=[
        {"diagnosis": "PE", "reason_rejected": "...", ...},
        {"diagnosis": "Pneumonia", "reason_rejected": "...", ...},
        {"diagnosis": "Aortic dissection", "reason_rejected": "...", ...}
    ],
    ...
)
```

---

### 2. Quantify Your Uncertainty

**Don't just say "I'm not sure". Tell us WHAT makes you unsure.**

```python
# ❌ Bad
uncertainty_factors=["Not sure"]

# ✅ Good
uncertainty_factors=[
    "Troponin trend pending (only one value)",
    "No prior ECG for comparison",
    "Patient on beta-blockers (may mask tachycardia)",
    "Recent surgery makes inflammatory markers hard to interpret"
]
```

---

### 3. Explain Your Confidence

**Don't just give a number. Explain WHY.**

```python
# ❌ Bad
prior_probability=0.3

# ✅ Good
prior_probability=0.3,
confidence_rationale="""
Moderate confidence (0.3) because:
- Classic presentation (chest pain + troponin elevation) → increases confidence
- Recent CABG (strong risk factor) → increases confidence
- BUT: Atypical features (no diaphoresis, on beta-blockers) → decreases confidence
- AND: Troponin trend pending → prevents higher confidence
"""
```

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
- At least three unique diagnoses with active/test dispositions and must-not-miss flags
- Reasoning chain
- Thinking chain
- Fishbone, Why Tree/root causes, HFACS, and conflict/readiness sections
- Conservative causation audits with explicit non-proof scope and safe root dispositions
- Quality metrics (evidence coverage, hypothesis coverage, avg confidence)
- Machine-readable `conformance_checks[]`
- Final-only reviewer, timezone-aware finalization time, and recomputable content hash

---

## 🎯 Summary: Your Responsibilities as an Agent

1. **Think deeply** — Don't just pattern match, reason through the case
2. **Consider alternatives** — Always list what else you considered
3. **Quantify uncertainty** — Tell us what makes you unsure
4. **Explain confidence** — Don't just give a number, explain why
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
4. Maintain at least three hypotheses, flag applicable must-not-miss conditions, and
   call `rc_propose_hypothesis` with full explicit rationale and typed
   `planned_tests` where observed refuting evidence is not yet available.
5. Call `rc_link_evidence_to_hypothesis` with the direct applied LR for supporting and
   disconfirming evidence.
6. Call `rc_reflect`, conflict detection, the conservative causation audit, and the
   Fishbone/Why/HFACS workflow. Keep root ID/description/evidence exactly aligned;
   omit rejected claims and keep insufficient-data candidates proposed.
7. Run `rc_audit_reasoning_state` until every prerequisite is resolved or explicitly
   left as a preliminary limitation.
8. Call `rc_generate_contract_report(format="markdown", finalize=false)` for review.
   Inspect `conformance_checks[]`; only a named, operator-authorized, independently
   qualified human may approve a gated final artifact.

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

**Version**: 1.3
**Last Updated**: 2026-08-17
**For**: All AI Agents (Claude Code, Codex, OpenClaw, Cline, Z.ai, etc.)
