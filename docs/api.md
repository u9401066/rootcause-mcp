# RootCause MCP API

> MCP SDK 2.0 tool index. The live JSON Schemas returned by `tools/list` are the
> authoritative contract.

RootCause MCP is an engineering-alpha reasoning ledger. The Agent supplies clinical
interpretation; the server supplies schemas, persistence, deterministic calculations,
workflow gates, and standardized artifacts. It does not think, diagnose, or parse
raw PDF/DOCX/image/scan/spreadsheet/EHR batches. A host or approved extractor must
preserve citation-ready source spans before calling the evidence tools.

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
| `condensed` | 8 | Unified polymorphic facades (`rc_evidence`, `rc_hypothesis`, `rc_thinking`, `rc_audit`, `rc_report`, `rc_diagram`, `rc_checkpoint`, `rc_rca`) for a smaller discovery surface |
| `clinical` | 23 | Evidence, DDx, cognitive audit, conflict detection, checkpoints, reasoning, guidance, report, causation |
| `rca` | 23 | Session, HFACS, Fishbone, Why Tree, checkpoints, diagrams, causation |
| `all` | 43 | Complete catalog; default for full compatibility |

Hidden profile tools are not dispatchable. This prevents accidental calls and makes
the advertised catalog match the executable surface.

## Condensed Facade Profile (8 Tools)

When using `ROOTCAUSE_TOOL_PROFILE=condensed`, the tool surface is consolidated into 8 action-based facade tools:

1. `rc_evidence`:
   - `action="add"`: Add structured clinical evidence with provenance and raw snippets.
   - `action="get"`: Retrieve evidence item.
   - `action="verify"`: Perform physical file snippet matching and SHA-256 validation.
2. `rc_hypothesis`:
   - `action="propose"`: Propose differential diagnosis hypothesis.
   - `action="link"`: Link evidence with likelihood ratios.
   - `action="rank"`: Retrieve posterior-ranked differential list.
   - `action="exclude"`: Exclude hypothesis with clinical justification.
3. `rc_thinking`:
   - `action="think"`: Record explicit diagnostic rationale and confidence.
   - `action="reflect"`: Record cognitive bias checks and reflection.
   - `action="gap"`: Record identified clinical data gaps.
   - `action="challenge"`: Question anchoring assumptions.
   - `action="get_chain"`: Retrieve full cognitive thinking chain.
4. `rc_audit`:
   - `action="stage_guidance"`: Inspect reasoning stage, checklist, and push questions.
   - `action="detect_conflicts"`: Run automated diagnostic contradiction and omission checks.
   - `action="verify_causation"`: Run a conservative causation proof-obligation
     audit; it does not prove clinical causality.
5. `rc_report`:
   - `action="preview"`: Generate a preliminary Markdown, JSON, or FHIR report.
   - `action="generate"`: Generate the report, return machine-readable
     `conformance_checks`, and optionally request gated finalization.
6. `rc_diagram`:
   - `action="timeline"`: Render clinical chronological event timeline and Mermaid diagram.
   - `action="validate"`: Universal Mermaid syntax auditor and sanitizer.
   - `action="reasoning_chain"`: Export the action audit trail.
   - `action="evidence_graph"`: Generate the report evidence graph.
7. `rc_checkpoint`:
   - `action="create"`: Take an integrity-checked JSON state snapshot.
   - `action="restore"`: Restore session to previously saved checkpoint.
   - `action="list"`: List existing checkpoints for a session.
8. `rc_rca`:
   - Route session lifecycle (`session_start`, `session_get`, `session_list`, `session_archive`), traditional 6M Fishbone (`fishbone_init`, `fishbone_add_cause`, `fishbone_get`, `fishbone_export`), 5-Why Tree (`why_ask`, `why_get`, `why_link`, `why_mark_root`, `why_export`, `why_teach`), and HFACS-MES (`hfacs_suggest`, `hfacs_confirm`, `hfacs_framework`).

`rc_get_reasoning_chain`, learned-rule administration, and the 6M/HFACS mapping
remain discrete-only. Read the live `tools/list` response rather than calling an
undocumented facade action.

## Discrete Medical Reasoning Tools

| Tool | Required intent |
| --- | --- |
| `rc_add_evidence` | Register a traceable clinical finding, quality grade, verbatim raw snippet, and hash |
| `rc_get_evidence` | Retrieve evidence by ID |
| `rc_verify_evidence` | Deterministically verify raw snippet against files on disk or record reviewer audit |
| `rc_propose_hypothesis` | Create a diagnosis hypothesis with prior and explicit rationale |
| `rc_link_evidence_to_hypothesis` | Apply a likelihood ratio and retain its rationale |
| `rc_get_differential_diagnosis` | Return active hypotheses ranked by posterior probability |
| `rc_exclude_hypothesis` | Exclude a hypothesis with reviewer and reason |
| `rc_detect_conflicts` | Detect diagnostic contradictions, paradoxical drug reactions, and guideline omissions |
| `rc_create_checkpoint` | Create an integrity-checked JSON state snapshot with SHA-256 hash |
| `rc_restore_checkpoint` | Restore session state from a previously saved checkpoint |
| `rc_list_checkpoints` | List all saved checkpoints for a session |
| `rc_get_reasoning_chain` | Retrieve orchestrator-generated audit steps |
| `rc_export_reasoning_chain` | Export the reasoning chain under the configured export root |
| `rc_audit_reasoning_state` | Audit clinical reasoning completeness, stage progression, and next recommended actions |
| `rc_generate_contract_report` | Generate JSON, FHIR-compatible, or deterministic Markdown output |
| `rc_validate_diagram` | Audit, validate, and auto-sanitize Mermaid syntax across all diagram types |
| `rc_render_timeline` | Render structured event timelines with clinical pattern clustering |

## MCP Resources & Prompts

### Static Resources (`clinical://*`)

- `clinical://contracts/case-input-manifest`: Canonical multi-source input manifest schema.
- `clinical://contracts/case-analysis-report`: Canonical standardized report schema.
- `clinical://protocols/anesthesia-mm-rca-protocol`: 4-Tier backward causal reasoning SOP.
- `clinical://protocols/clinical-reasoning-sop`: Core diagnostic investigation playbook.
- `clinical://templates/anesthesia-mm-rca-report-template`: Anesthesia M&M Markdown template.
- `clinical://templates/near-miss-adverse-event-rca-template`: Near-miss & barrier failure template.
- `clinical://domains/*`: Specialized crisis playbooks.

### Dynamic Resource Templates

- `clinical://sessions/{session_id}/report`: Current preliminary unified DDx/RCA
  preview from live state; reading it does not persist an export.
- `clinical://sessions/{session_id}/timeline`: Chronological event timeline.
- `clinical://sessions/{session_id}/guidance`: Multi-loop reasoning guidance.
- `clinical://sessions/{session_id}/conflicts`: Gap analysis & conflict audit report.

### Clinical Prompts

- `anesthesia_mm_investigation`: Launch 4-Tier backward causal analysis.
- `perioperative_crisis_differential`: Crisis differential expansion.
- `near_miss_barrier_analysis`: Swiss Cheese non-death adverse event analysis.
- `delayed_diagnosis_investigation`: Diagnostic trajectory and cognitive bias investigation.

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
- `event_timestamp`: Canonical ISO 8601 clinical event time, separate from ingestion time
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

Deterministically matches verbatim quotes against allowlisted plain-text files. File
existence or a line locator alone never verifies the finding. Manual confirmation
requires `manual_confirmation=true` and a `verified_by` identity present in the
operator-controlled `ROOTCAUSE_AUTHORIZED_REVIEWERS` allowlist.

### `rc_audit_reasoning_state`

Evaluates the multi-loop reasoning progress for AI agents (especially lightweight Flash/mini models). Returns:

- `current_stage`: Current clinical reasoning stage (`EVIDENCE_COLLECTION`, `DIFFERENTIAL_EXPANSION`, `BAYESIAN_EVALUATION`, `COGNITIVE_AUDIT`, `READY_FOR_SYNTHESIS`)
- `completeness_score`: Numerical score (0.0 to 1.0)
- `checklist`: Detailed readiness checks (minimum 3 hypotheses, evidence linkage, disconfirming tests, uncertainty acknowledged, bias audited)
- `next_recommended_actions`: Actionable tool call directives for the agent's next turn
- `push_questions`: Socratic clinical prompts to deepen analysis

### `rc_generate_contract_report`

Generates a preliminary or finalized CONTRACT report in JSON, FHIR
`DiagnosticReport`, or deterministic Markdown without invoking an LLM. The report
combines source inventory, DDx/evidence, reasoning/thinking chains, Fishbone, Why
Tree/root causes, HFACS, conflicts, readiness, and artifact hash. Supports:

- `format`: `"json"`, `"fhir"`, or `"markdown"` (default: `"json"`)
- `detail_level`: `"brief"`, `"standard"`, or `"full"` (default: `"standard"`)
- `template_file`: Optional relative Markdown filename under the configured template allowlist
- `finalize`: Request gated, content-hashed finalization; defaults to `false`
- `approved_by`: Explicit approver identity required for finalization; it must be
  present in the operator-controlled `ROOTCAUSE_AUTHORIZED_REVIEWERS` allowlist

Successful preview/final report responses and finalization-blocker responses include
machine-readable `conformance_checks[]`. Finalization recomputes the complete hard
set server-side and is rejected unless all of these conditions hold:

- Workflow readiness passes, no high/critical conflict remains, and mandatory final
  sections are present.
- A reviewed manifest pins at least two source documents and every evidence item
  resolves to that manifest.
- Fishbone and stable 5-Why roots exist. Each root's ID, description, and evidence
  set exactly match the Why/evidence ledgers and its latest persisted conservative
  causation audit.
- A `REJECTED` audit result is absent from the root-cause bucket;
  `INSUFFICIENT_DATA` remains `PROPOSED`; an audit pass is labelled
  `AUDIT_OBLIGATIONS_PASSED`, never clinical causal proof.
- At least three normalized unique diagnoses exist. Every active diagnosis has a
  genuine evidence/test disposition; the leading and every must-not-miss diagnosis
  have genuine support plus contradiction or a typed pending disconfirm/rule-out
  test.
- `approved_by` is operator-authorized.

The finalized nested object is recursively immutable and carries `reviewed_by`,
`approved_by`, a timezone-aware `finalized_at`, all conformance results, and a
recomputable SHA-256 `content_hash`. This integrity boundary is not a substitute for
an approved write-once records repository. Generate a preview while any gate remains
open. See [MVP conformance and evaluation](mvp_conformance_and_evaluation.md) for the
stable hard-check codes and release interpretation.

```json
{
  "session_id": "case-001",
  "format": "markdown",
  "detail_level": "full",
  "template_file": "anesthesia_mm_rca_report_template.md",
  "finalize": false
}
```

One final `conformance_checks[]` item has this stable machine-readable shape:

```json
{
  "code": "DIFFERENTIAL_MINIMUM_UNIQUE",
  "status": "PASS",
  "severity": "HARD",
  "message": "The differential contains at least three normalized unique diagnoses.",
  "refs": ["#/hypotheses"],
  "details": {}
}
```

Caller-supplied hard `PASS` values are not trusted. The report lifecycle recomputes
them before finalization and verifies the stored set and content hash again when a
final-only snapshot is materialized.

### `rc_propose_hypothesis`

Required fields include the diagnosis plus explicit reasoning controls:

- `clinical_reasoning`
- `differential_diagnoses_considered`
- `uncertainty_factors`
- `confidence_rationale`

Optional `planned_tests` entries use a typed disposition rather than free text:

- `name`
- `purpose`: `DISCONFIRM`, `RULE_OUT`, `CONFIRM`, or `DISCRIMINATE`
- `expected_supporting_result`
- `expected_refuting_result`
- `status`: `PLANNED` or `ORDERED`

The server assigns `test_id` and binds `target_hypothesis_id` to the newly created
hypothesis. A pending test can satisfy a final refuting disposition only when its
purpose is `DISCONFIRM` or `RULE_OUT` and both expected-result fields are present.

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
  "uncertainty_factors": ["Serial ECG pending"],
  "confidence_rationale": "Typical presentation with one important pending test",
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

The legacy `evidence_supporting` and `evidence_contradicting` fields are deprecated,
context-only proposal inputs. They do not persist evidence associations or perform a
Bayesian update; use `rc_link_evidence_to_hypothesis` for every actual link.

### `rc_link_evidence_to_hypothesis`

`likelihood_ratio` must be between 0.01 and 100 and is applied directly. Supporting
evidence normally uses LR > 1; contradicting/refuting evidence uses LR < 1; neutral
or quantitatively unknown evidence uses 1.0. The server never takes a reciprocal.
`rationale` should cite the calibration source or clinical basis.

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

`rc_verify_causation` is a conservative proof-obligation audit, not a clinical
causality prover. Missing or reversed chronology fails temporality rather than being
assumed safe. Every persisted record declares
`audit_scope="CONSERVATIVE_CAUSATION_AUDIT"` and
`clinical_causality_established=false`. Compatibility results such as `VERIFIED`
mean only that the implemented audit obligations passed; they must not be rendered
as “causation proven.” `REJECTED` and `INSUFFICIENT_DATA` remain explicit release
dispositions.

## Persistence and Exports

Medical reasoning Evidence, Hypothesis, ThinkingChain, and ReasoningChain records are
persisted through SQLModel repositories. Generated artifacts are confined to:

```text
ROOTCAUSE_DATA_DIR/exports/<session_id>/
```

Runtime exports are ephemeral and excluded from version control. Curated,
license-reviewed benchmark inputs and expected artifacts belong under `examples/`
with provenance and data-license metadata.

Why Trees, Fishbone diagrams, session manifests, clinical reasoning records, and
checkpoints are persisted. Generated clinical exports are atomically written with
owner-only permissions on POSIX systems.
