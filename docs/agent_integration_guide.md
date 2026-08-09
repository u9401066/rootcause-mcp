# Agent Integration Guide: How to Use RootCause MCP

> **For AI Agents**: Claude Code, Codex, OpenClaw, Cline, Z.ai, etc.  
> **Purpose**: Transform your medical reasoning into auditable, structured output

---

## 🎯 Core Principle

**You (the Agent) do the thinking. We (MCP) provide the structure.**

RootCause MCP is NOT a diagnostic AI. It's a **reasoning harness** that helps you:
- Structure your differential diagnosis process
- Track evidence with provenance
- Quantify uncertainty
- Generate auditable reports

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
  
  "clinical_reasoning": "65M with acute onset substernal chest pain radiating to left arm, elevated troponin I (2.5 ng/mL), and ST elevation in leads II, III, aVF. Recent CABG 3 days ago increases suspicion for graft failure or perioperative MI.",
  
  "differential_diagnoses_considered": [
    {
      "diagnosis": "Pulmonary Embolism",
      "reason_rejected": "No dyspnea, no tachycardia out of proportion, no hemoptysis. However, recent surgery is a risk factor, so will order D-dimer to definitively rule out.",
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
  
  "evidence_supporting": [
    "EVD-001",
    "EVD-003",
    "EVD-005"
  ],
  
  "evidence_contradicting": [
    "EVD-002"
  ],
  
  "uncertainty_factors": [
    "Troponin trend pending (only one value available)",
    "No prior ECG for comparison",
    "Patient on beta-blockers which may blunt tachycardic response",
    "Recent surgery makes interpretation of inflammatory markers difficult"
  ],
  
  "confidence_rationale": "Assigned moderate prior probability (0.3) because: (1) Classic presentation with chest pain + troponin elevation, (2) Recent CABG is a strong risk factor, (3) However, atypical features (no diaphoresis, patient on beta-blockers) and pending troponin trend prevent higher confidence."
}
```

---

## 📋 Tool Usage Patterns

### Pattern 1: Systematic Differential Diagnosis

```python
# Step 1: Register each source-grounded finding
troponin = await rc_add_evidence(
    session_id="sess_001",
    content="Troponin I: 2.5 ng/mL",
    evidence_type="LAB_RESULT",
    source_document="lab_results.pdf",
    source_location="Page 1, Table 1",
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
    evidence_supporting=[troponin.evidence_id],
    uncertainty_factors=["Serial ECG pending"],
    confidence_rationale="Typical presentation with one important pending test"
)
```

---

### Pattern 2: Evidence-Based Bayesian Updating

```python
# Add evidence with quality grading
evidence = await rc_add_evidence(
    session_id="sess_001",
    content="Troponin I: 2.5 ng/mL (normal < 0.04)",
    evidence_type="LAB_RESULT",
    source_document="lab_results.pdf",
    source_location="Page 1, Table 1",
    clinical_strength="STRONG",  # Direct lab measurement
    source_reliability="GRADE_A"  # Primary source
)

# Link to hypothesis with likelihood ratio
await rc_link_evidence_to_hypothesis(
    session_id="sess_001",
    evidence_id=evidence.id,
    hypothesis_id="HYP-001",
    likelihood_ratio=10.0,  # Troponin elevation is 10x more likely in MI
    supports=True,
    rationale="Troponin I > 99th percentile is highly specific for myocardial necrosis. LR+ = 10 based on meta-analysis (PMID: 12345678)."
)
```

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
    thinking_type="PATTERN_RECOGNIZED",
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

## 🧠 Cognitive Best Practices

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

```
Agent reads documents → Agent thinks internally → Agent calls MCP with conclusion
                                                    ↓
                                            MCP records result
                                                    ↓
                                            Human: "Why did you conclude this?"
                                            Agent: "Um... because...?"
```

### ✅ Deep MCP (What We're Building)

```
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
MCP generates ContractReport with complete audit trail
    ↓
Human: "Why did you conclude this?"
System: "Here's the complete reasoning chain, including alternatives considered, 
         uncertainty factors, and potential biases identified."
```

---

## 📊 What Gets Recorded

### ReasoningChain (What You Did)
- Every tool call with timestamp
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
- Complete evidence graph
- Differential diagnosis tree with probabilities
- Reasoning chain
- Thinking chain
- Quality metrics (evidence coverage, hypothesis coverage, avg confidence)

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

1. Read the case documents
2. Call `rc_add_evidence` for each traceable finding
3. Call `rc_think_aloud` to record the explicit decision frame
4. For each hypothesis, call `rc_propose_hypothesis` with FULL reasoning
5. Call `rc_link_evidence_to_hypothesis` to perform Bayesian updating
6. Call `rc_get_differential_diagnosis` to inspect the ranked DDx
7. Call `rc_reflect` to identify biases
8. Call `rc_generate_contract_report` to produce final auditable report

---

**Remember**: We're not here to replace your reasoning. We're here to make it **auditable, transparent, and defensible**.

**Your thinking. Our structure. Better outcomes.**

---

**Version**: 1.0  
**Last Updated**: 2026-08-09  
**For**: All AI Agents (Claude Code, Codex, OpenClaw, Cline, Z.ai, etc.)
