# RootCause MCP API

> MCP SDK 2.0 tool index. The live JSON Schemas returned by `tools/list` are the
> authoritative contract.

## Common Contract

Every tool name begins with `rc_`, accepts an object `input_schema`, and declares a
structured `output_schema` requiring a `status` field.

Typical status values:

- `success`: operation completed
- `not_found`: requested case entity does not exist
- `error`: request was understood but could not be completed

Legacy RCA tools also return Markdown/text content for interactive clients. The same
text is included in `structuredContent.content`.

## Medical Reasoning Workflow

| Tool | Required intent |
| --- | --- |
| `rc_add_evidence` | Register a traceable clinical finding and quality grade |
| `rc_get_evidence` | Retrieve evidence by ID |
| `rc_verify_evidence` | Record independent evidence verification |
| `rc_propose_hypothesis` | Create a diagnosis hypothesis with prior and explicit rationale |
| `rc_link_evidence_to_hypothesis` | Apply a likelihood ratio and retain its rationale |
| `rc_get_differential_diagnosis` | Return active hypotheses ranked by posterior probability |
| `rc_exclude_hypothesis` | Exclude a hypothesis with reviewer and reason |
| `rc_get_reasoning_chain` | Retrieve orchestrator-generated audit steps |
| `rc_export_reasoning_chain` | Export the reasoning chain under the configured export root |
| `rc_generate_contract_report` | Generate JSON or FHIR-compatible report output |

### `rc_add_evidence`

Required fields: `session_id`, `content`.

Important optional fields: `evidence_type`, `source_document`, `source_location`,
`collected_by`, `clinical_strength`, `source_reliability`, `clinical_context`.

```json
{
  "session_id": "case-001",
  "content": "Troponin I 2.5 ng/mL",
  "evidence_type": "LAB_RESULT",
  "source_document": "lab-report.pdf",
  "source_location": "page 1",
  "clinical_strength": "STRONG",
  "source_reliability": "GRADE_A"
}
```

### `rc_propose_hypothesis`

Required fields include the diagnosis plus explicit reasoning controls:

- `clinical_reasoning`
- `differential_diagnoses_considered`
- `evidence_supporting`
- `uncertainty_factors`
- `confidence_rationale`

```json
{
  "session_id": "case-001",
  "diagnosis": "Acute myocardial infarction",
  "icd10_code": "I21.9",
  "prior_probability": 0.3,
  "clinical_reasoning": "Chest pain, ECG findings, and troponin support acute MI.",
  "differential_diagnoses_considered": [
    {
      "diagnosis": "Pulmonary embolism",
      "reason_rejected": "No hypoxemia or right-heart strain"
    }
  ],
  "evidence_supporting": ["EVD-12345678"],
  "uncertainty_factors": ["Serial ECG pending"],
  "confidence_rationale": "Typical presentation with one important pending test"
}
```

### `rc_link_evidence_to_hypothesis`

`likelihood_ratio` must be between 0.01 and 100. `rationale` should cite the source
or clinical basis for the value.

```json
{
  "session_id": "case-001",
  "evidence_id": "EVD-12345678",
  "hypothesis_id": "HYP-12345678",
  "likelihood_ratio": 5.0,
  "supports": true,
  "rationale": "Marked troponin elevation strongly supports myocardial injury."
}
```

## Cognitive Transparency

These tools store agent-authored rationales. They do not expose hidden model states.

| Tool | Purpose |
| --- | --- |
| `rc_think_aloud` | Record explicit rationale, alternatives, uncertainty, and bias |
| `rc_reflect` | Record a meta-cognitive review |
| `rc_identify_gaps` | Register missing or conflicting information |
| `rc_challenge_assumption` | Challenge a stated assumption |
| `rc_get_thinking_chain` | Retrieve the cognitive record for a case |

## RCA and Human Factors

| Category | Tools |
| --- | --- |
| Session | `rc_start_session`, `rc_get_session`, `rc_list_sessions`, `rc_archive_session` |
| Fishbone | `rc_init_fishbone`, `rc_add_cause`, `rc_get_fishbone`, `rc_export_fishbone` |
| Why Tree | `rc_ask_why`, `rc_get_why_tree`, `rc_mark_root_cause`, `rc_add_causal_link`, `rc_export_why_tree`, `rc_build_teaching_case` |
| HFACS-MES | `rc_suggest_hfacs`, `rc_confirm_classification`, `rc_get_hfacs_framework`, `rc_get_6m_hfacs_mapping`, `rc_list_learned_rules`, `rc_reload_rules` |
| Verification | `rc_verify_causation` |

`rc_verify_causation` is conservative: absent explicit counterfactual or mechanism
support, a relationship cannot be fully verified.

## Persistence and Exports

Medical reasoning Evidence, Hypothesis, ThinkingChain, and ReasoningChain records are
persisted through SQLModel repositories. Generated artifacts are confined to:

```text
ROOTCAUSE_DATA_DIR/exports/<session_id>/
```

The legacy Why Tree repository is currently process-local. See
[ROADMAP.md](../ROADMAP.md) for planned persistence work.
