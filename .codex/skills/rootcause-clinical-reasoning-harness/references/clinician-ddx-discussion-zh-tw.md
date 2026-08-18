# Clinician DDx Discussion（zh-TW）

Use this reference when the host Agent expands a differential diagnosis or writes a clinician-facing discussion. RootCause MCP records and validates the ledger; it does not perform clinical reasoning. The host Agent remains responsible for the interpretation, and a qualified clinician remains responsible for review.

The live schemas at `clinical://contracts/case-input-manifest` and `clinical://contracts/case-analysis-report` are authoritative. If a field or enum below differs from the connected server, retain the meaning in the handoff and use only the advertised schema.

## Language contract

- Write headings, transitions, uncertainty statements, limitations, and clinician discussion in Traditional Chinese.
- Preserve canonical diagnosis, test, drug, device, and procedure names in English. On first use, an established abbreviation may include an optional Traditional Chinese gloss, for example `Pulmonary Embolism（PE；肺栓塞）`; use the established English abbreviation thereafter.
- Do not invent a Chinese translation or expand an ambiguous abbreviation. Record `unknown` and ask for clarification when the expansion is not source-supported.
- Preserve source quotations, measurements, units, codes, and source-language wording exactly. Do not translate text presented as verbatim evidence.
- Keep JSON keys, enum values, IDs, hashes, and machine-readable clinical values unchanged.
- For mixed audiences, put the stable English term first so another runtime can match the same candidate without language-dependent normalization.

## Three reasoning layers

Label each statement as one of these layers in the ledger and keep the prose distinction visible:

1. **Observation** — a source-linked fact, exact snippet, measurement, documented diagnosis, or documented action. It must carry a source/evidence ID and verification state.
2. **Inference** — the host Agent's clinical interpretation of observations. State the evidence IDs, alternative explanations, certainty, and what would change the inference.
3. **Causal claim** — a proposed relationship for RCA. It needs Why/root/audit lineage and conservative causation review; even an audit pass is not proof of clinical causality.

Never rewrite an inference as though it were observed. Never use coherent narrative, temporal order, Agent agreement, or a validator pass as independent causal proof.

## Treat unknown as an input

Classify missingness before interpreting it:

- `not documented`: the supplied source does not state it;
- `not measured`: the test or observation was not performed;
- `pending`: a result or independent review is outstanding;
- `conflicting`: available sources disagree;
- `unverified`: the exact source match or reviewer confirmation is absent;
- `unknown`: the subtype cannot yet be determined.

An unknown is not a negative finding. For each decision-relevant unknown, state:

- which mechanisms and candidates remain open;
- whether it affects support, refutation, certainty, or safety priority;
- the source, examination, test, or review that could resolve it;
- whether the proposed discriminator is available, appropriate, and still pending.

## Build maximum reasonable breadth

Define the syndrome or phenotype and time course before naming diagnoses. Expand across distinct plausible mechanisms rather than adding synonyms. The current mechanism categories are:

- `VASCULAR`
- `INFECTIOUS`
- `INFLAMMATORY_IMMUNE`
- `NEOPLASTIC`
- `DRUG_TOXIN_IATROGENIC`
- `METABOLIC_ENDOCRINE`
- `TRAUMATIC_MECHANICAL`
- `CONGENITAL_GENETIC`
- `DEGENERATIVE`
- `FUNCTIONAL_PHYSIOLOGIC`
- `OTHER`
- `UNKNOWN`

Three normalized diagnoses, two non-`UNKNOWN` mechanism categories, and one applicable must-not-miss diagnosis are deterministic finalization floors. They are not a clinical stopping target and not a cap.

Include a candidate when at least one of these applies:

- its mechanism plausibly explains the phenotype and time course;
- source-linked evidence makes it a genuine competing explanation;
- the harm of missing it justifies must-not-miss tracking;
- a feasible discriminating result could materially change ranking, exclusion, monitoring, or escalation.

Prune or merge a candidate when it is only a synonym, a nested label with no separate decision, contradicted by verified mechanism-level evidence, or has no plausible mechanism and no decision impact. Document the reason for exclusion. This stop rule avoids both premature closure and an unbounded laundry list.

## Audit the search space

Choose the syndrome-appropriate framework: `VINDICATE`, `FIVE_H_FIVE_T`, `ANATOMIC_SYSTEM`, `MEDICATION_DEVICE_EXPOSURE`, or `CUSTOM`. A `CUSTOM` framework needs an explicit name, rationale, and at least two defined cells.

Use `rc_audit_differential_breadth` or condensed `rc_hypothesis(action="audit_breadth")`. Persist the framework rationale, `PRIMARY` or `SUPPLEMENTAL` role, every framework cell, and the stop rationale. Each cell must have exactly one review status:

- `CANDIDATES_PRESENT`: include linked hypothesis IDs and mechanism categories; the IDs/categories must agree with the hypothesis ledger.
- `REVIEWED_NO_PLAUSIBLE_CANDIDATE`: state why no plausible candidate remains after review; this is not a shortcut for missing information.
- `REVIEWED_INSUFFICIENT_DATA`: retain the decision-relevant unknowns and typed planned discriminators; do not count it as exclusion.
- `NOT_ASSESSED`: review has not occurred. A final PRIMARY audit must contain none.

Finalization requires at least one complete PRIMARY breadth audit. A reviewed insufficient-data cell is acceptable when its uncertainty and discriminator are explicit; an unassessed cell is not. The audit proves documented coverage of a search framework, not clinical correctness.

## Candidate record

For every active candidate, record all of the following:

- `diagnosis`: canonical English name;
- `mechanism_category`: one advertised enum value;
- `diagnostic_role`: `ETIOLOGIC`, `SYNDROMIC`, `COMPLICATION`, `MIMIC`, or `UNKNOWN`;
- `reasoning_basis`: `OBSERVED_DIAGNOSIS`, `MECHANISM_INFERENCE`, or `UNKNOWN`;
- `certainty`: `UNKNOWN`, `POSSIBLE`, `PROBABLE`, `HIGH_CONFIDENCE`, `CONFIRMED`, or `EXCLUDED`;
- safety/priority role: leading, must-not-miss, other active, or excluded, kept separate from certainty;
- why considered: a concise phenotype/mechanism rationale;
- support: source-linked evidence with direct LR when justified;
- refutation: source-linked disconfirming evidence with direct LR when justified;
- neutral evidence: relevant `LR=1.0` links, explicitly not counted as support or refutation;
- candidate-specific unknowns and alternative explanations;
- discriminating test: name, purpose, status, expected supporting result, and expected refuting result.

Every active candidate needs genuine `LR != 1.0` evidence or a pending typed test with purpose `DISCONFIRM`, `RULE_OUT`, or `DISCRIMINATE`. The leading and each must-not-miss candidate need genuine support plus refuting evidence or a pending refuting test.

`must_not_miss=true` expresses safety priority, not likelihood. Do not elevate certainty merely because a condition is dangerous.

## Certainty and quantification

- Use qualitative `certainty` independently from ranking and safety priority.
- `PROBABLE`, `HIGH_CONFIDENCE`, and `CONFIRMED` require genuine source-linked evidence or a completed discriminating test. `CONFIRMED` must agree with the persisted hypothesis status.
- Do not infer certainty from a posterior number, and do not present a posterior as a calibrated clinical probability unless an authorized, documented calibration method exists.
- Omit `prior_probability` when the connected preliminary schema permits omission. If the server inserts or requires a compatibility value, identify it as an implementation placeholder in the narrative; it is not clinical probability, rank, or certainty.
- Never fabricate a probability, LR, confidence percentage, diagnostic accuracy, or citation.
- Apply LR directly: `>1` supports, `<1` refutes, and `1.0` is neutral or quantitatively unknown. Do not invert it, convert an internal weight, or count `1.0` toward support/refutation readiness.

## Clinician-facing discussion template

```markdown
## 臨床問題與分析狀態

- 狀態：PRELIMINARY／FINALIZED
- 臨床問題：...
- 主要資料限制：...
- 安全聲明：本產物為 retrospective decision support，須由 qualified clinician 審閱。

## 關鍵 observations

- [EV-...] 原始 observation、時間、來源位置與 verification state。

## Differential Diagnosis

### 1. English diagnosis name — POSSIBLE／PROBABLE／...

- 角色：leading／must-not-miss／other；mechanism：...；diagnostic role：...
- Why considered：...
- 支持：EV-...；direct LR ...／qualitative only。
- 反證：EV-...；direct LR ...／尚無 genuine refuting evidence。
- Neutral：EV-...（LR=1.0；不計為支持或反證）。
- Unknown：類型、保留的 mechanism、對 certainty／safety 的影響。
- Discriminating test：名稱；purpose；status；支持結果；反證結果。

## 綜合 interpretation

- Observation：...
- Inference：...（evidence IDs、certainty、alternatives）。
- Causal claim：PROPOSED／AUDIT_OBLIGATIONS_PASSED／INSUFFICIENT_DATA；不代表 clinical causality established。

## 仍需處理與 clinician review

- 未解 conflicts、missing data、must-not-miss disposition、reviewer 與下一步。
```

Do not fill an empty field with plausible prose. Write the missing state and the specific discriminator instead.

## Renderer boundary

For the built-in contract Markdown renderer, request:

```text
rc_generate_contract_report(
    format="markdown",
    locale="zh-TW",
    audience="clinician",
    finalize=false,
)
```

The condensed equivalent is `rc_report` with the connected server's advertised preview/generate action. The localized static copy applies only to the built-in Markdown renderer. Custom templates retain their own authored language. JSON and FHIR-compatible data, persisted medical strings, IDs, codes, and enum values are not translated.

## Review checklist

- The DDx covers the maximum reasonable distinct mechanisms for the defined phenotype and time course.
- Every candidate has why considered, source-linked support/refutation/neutral evidence, unknowns, a discriminator, and a qualitative certainty label.
- The leading and must-not-miss entries have genuine support and a real refuting disposition.
- No unknown was treated as negative evidence, and no `LR=1.0` link was counted as support/refutation.
- No probability, LR, translation, citation, or causal claim was invented.
- Observation, inference, and causal claim remain visibly separate.
- Traditional Chinese prose and stable English medical names follow the language contract.
- A named qualified clinician reviews safety-critical content before finalization.
