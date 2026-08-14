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

### Token-efficient transport

SDK 2.0 `structuredContent` is authoritative for modern tools. By default, the text
fallback contains only status, identifiers, counts, and a pointer to structured
content instead of duplicating the complete JSON payload. Set
`ROOTCAUSE_RESPONSE_MODE=verbose` only for hosts that do not expose
`structuredContent` to the Agent.

Use `ROOTCAUSE_TOOL_PROFILE` to reduce the schema catalog placed in Agent context:

| Profile | Advertised tools | Intended workflow |
| --- | ---: | --- |
| `clinical` | 17 | Evidence, DDx, cognitive audit, reasoning, guidance, report, causation |
| `rca` | 21 | Session, HFACS, Fishbone, Why Tree, causation |
| `all` | 37 | Complete catalog; default for compatibility |

Hidden profile tools are not dispatchable. This prevents accidental calls and makes
the advertised catalog match the executable surface.

## Medical Reasoning Workflow

| Tool | Required intent |
| --- | --- |
| `rc_add_evidence` | Register a traceable clinical finding, quality grade, verbatim raw snippet, and hash |
| `rc_get_evidence` | Retrieve evidence by ID |
| `rc_verify_evidence` | Deterministically verify raw snippet against files on disk or record reviewer audit |
| `rc_propose_hypothesis` | Create a diagnosis hypothesis with prior and explicit rationale |
| `rc_link_evidence_to_hypothesis` | Apply a likelihood ratio and retain its rationale |
| `rc_get_differential_diagnosis` | Return active hypotheses ranked by posterior probability |
| `rc_exclude_hypothesis` | Exclude a hypothesis with reviewer and reason |
| `rc_get_reasoning_chain` | Retrieve orchestrator-generated audit steps |
| `rc_export_reasoning_chain` | Export the reasoning chain under the configured export root |
| `rc_audit_reasoning_state` | Audit clinical reasoning completeness, stage progression, and next recommended actions |
| `rc_generate_contract_report` | Generate JSON, FHIR-compatible, or deterministic Markdown output |
| `rc_validate_diagram` | Audit, validate, and auto-sanitize Mermaid syntax across all diagram types |
| `rc_render_timeline` | Render structured event timelines with clinical pattern clustering |

### `rc_validate_diagram`

Audits, validates, and auto-sanitizes raw Mermaid diagram code submitted by AI agents or external tools. Checks for delimiter balance (`[...]`, `(...)`, `[()]`, `{}`), unescaped double quotes inside labels, unclosed `subgraph` blocks, colon delimiters in `timeline`, and broken arrow connectors (`->` vs `-->`).

```json
{
  "mermaid_source": "subgraph Process\n  A[\"Step 1: Administer \"Drug A\"\"] -> B[\"Step 2: Check vitals\"]\n",
  "diagram_type": "flowchart",
  "auto_fix": true
}
```

Returns:

- `is_valid`: Boolean flag indicating if syntax is valid / fixable
- `diagram_type`: Detected or specified diagram type (`flowchart`, `timeline`, etc.)
- `sanitized_mermaid`: Clean, executable Mermaid source code
- `preview_markdown`: Markdown-fenced preview block
- `warnings` / `errors`: Detailed syntax diagnostics

### `rc_render_timeline`

Renders structured chronological event timelines and Mermaid diagrams using clinical pattern clustering:

- `perioperative_sequence` (Baseline & Pre-op → Induction → Crisis → Findings → Resuscitation)
- `acute_crisis` (Pre-event → Precipitating trigger → Deterioration → Crisis recognition → Rescue → Outcome)
- `delayed_diagnosis` (Initial contact → Diagnostic test → Communication gap → Latent progression → Symptom flare → Late diagnosis)
- `barrier_failure` (Prescribing → Pharmacy barrier → Nursing barrier → Monitoring barrier → Interception/Harm)
- `device_incident` (Baseline setting → Mechanical disturbance → Controller alarm → Clinical action → Rescue)
- `auto` (Automatically selects best pattern based on content keywords)
- `custom` (Custom event stages)

```json
{
  "session_id": "case-001",
  "pattern": "perioperative_sequence",
  "title": "Intraoperative Hemodynamic Timeline"
}
```

### `rc_add_evidence`

Required fields: `session_id`, `content`.

Important optional fields:

- `source_document`: File path or record ID (e.g., `"DATA_SOURCE_01_PRE_ANESTHESIA_EVALUATION.txt"`)
- `source_location`: Specific location within document (e.g., `"Line 14"`)
- `raw_snippet`: Exact verbatim excerpt from the physical file for cryptographic lineage
- `content_hash`: Optional SHA-256 digest (computed automatically if omitted)
- `extraction_method`: `"verbatim_quote"`, `"table_cell"`, `"structured_field"`, `"inference"`
- `auto_verify`: Automatically verify snippet against physical disk file (`default: true`)
- `clinical_strength`: `"STRONG"`, `"MODERATE"`, `"WEAK"`, `"ANECDOTAL"`
- `source_reliability`: `"GRADE_A"`, `"GRADE_B"`, `"GRADE_C"`, `"GRADE_D"`
- `evidence_type`: `"DOCUMENT"`, `"OBSERVATION"`, `"LAB_RESULT"`, `"IMAGING"`, etc.

```json
{
  "session_id": "case-001",
  "content": "Grade 2/6 Systolic Murmur at Left Sternal Border on pre-op exam",
  "evidence_type": "OBSERVATION",
  "source_document": "DATA_SOURCE_01_PRE_ANESTHESIA_EVALUATION.txt",
  "source_location": "CV line 14",
  "raw_snippet": "CV: RRR, Grade 2/6 Systolic Murmur at LSB (Left Sternal Border).",
  "clinical_strength": "STRONG",
  "source_reliability": "GRADE_A"
}
```

### `rc_verify_evidence`

Deterministically matches verbatim quotes against physical files on disk or records human reviewer sign-off. If the file exists and the snippet matches, the server computes line numbers and cryptographic SHA-256 checksums without using an LLM.

### `rc_audit_reasoning_state`

Evaluates the multi-loop reasoning progress for AI agents (especially lightweight Flash/mini models). Returns:

- `current_stage`: Current clinical reasoning stage (`EVIDENCE_COLLECTION`, `DIFFERENTIAL_EXPANSION`, `BAYESIAN_EVALUATION`, `COGNITIVE_AUDIT`, `READY_FOR_SYNTHESIS`)
- `completeness_score`: Numerical score (0.0 to 1.0)
- `checklist`: Detailed readiness checks (minimum 3 hypotheses, evidence linkage, disconfirming tests, uncertainty acknowledged, bias audited)
- `next_recommended_actions`: Actionable tool call directives for the agent's next turn
- `push_questions`: Socratic clinical prompts to deepen analysis

### `rc_generate_contract_report`

Generates a finalized CONTRACT report in JSON, FHIR `DiagnosticReport`, or deterministic Markdown format without invoking an LLM. Supports:

- `format`: `"json"`, `"fhir"`, or `"markdown"` (default: `"json"`)
- `detail_level`: `"brief"`, `"standard"`, or `"full"` (default: `"standard"`)
- `template_file`: Optional custom Markdown template path (e.g., `"config/templates/anesthesia_mm_rca_report_template.md"`)
- `finalize`: Boolean flag to make the report immutable and compute a cryptographic SHA-256 content hash

```json
{
  "session_id": "case-001",
  "format": "markdown",
  "detail_level": "full",
  "template_file": "config/templates/anesthesia_mm_rca_report_template.md",
  "finalize": true
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

Runtime exports are ephemeral and excluded from version control. Curated,
license-reviewed benchmark inputs and expected artifacts belong under `examples/`
with provenance and data-license metadata.

The legacy Why Tree repository is currently process-local. See
[ROADMAP.md](../ROADMAP.md) for planned persistence work.
