# RootCause Case Handoff Contract

Use this contract whenever an agent starts, resumes, transfers, previews, or finalizes a case. Preserve stable IDs and append corrections; do not overwrite an earlier observation without an audit note.

Before constructing payloads, read these MCP resources and follow their current JSON Schemas:

- `clinical://contracts/case-input-manifest`
- `clinical://contracts/case-analysis-report`

The live resources override examples in this file if the server contract evolves.

## Stage gates

| Gate | Minimum evidence to proceed |
| --- | --- |
| Case | One de-identified `case_id`/`session_id`, purpose, scope, timezone, and active tool profile |
| Sources | A schema-version `1.0` manifest is pinned to the session; every supplied record appears once with identity, whole-file hash, type, extraction status, and limitations; final release requires every source to be `reviewed` |
| Evidence | Each asserted finding has an atomic observation, source ID, exact snippet/location, canonical time state, and verification state |
| DDx | At least three normalized, non-duplicate plausible hypotheses, including applicable must-not-miss diagnoses; every active item has an evidence/test disposition |
| Bayesian | The leading and every must-not-miss diagnosis have genuine support plus contradiction or a typed pending `DISCONFIRM`/`RULE_OUT` test; every numeric LR is the direct applied LR with rationale/source |
| Cognitive | Missing data, uncertainty, alternative explanations, and relevant bias risks are recorded |
| RCA | Fishbone, Why, and HFACS are addressed; each Why/root/audit uses the same stable ID, exact description, and evidence set; every proposed root has a persisted conservative causation audit |
| Review | Conflicts/readiness checked; a named independently qualified human has reviewed any final clinical or causal claim and is present in the operator allowlist |
| Output | Unified package contains typed nested sections, source-to-claim lineage, limitations, machine-readable `conformance_checks[]`, review/finalization metadata, schema/config versions, and artifact hashes |

A failed gate blocks finalization, not investigation. Continue with `PRELIMINARY` and state exactly what is missing.

## Host-agent extraction boundary

RootCause currently accepts structured findings one at a time; it is not a raw-document upload or parser.

The host agent must:

1. Inventory every input before analysis, including later additions and replacements.
2. Extract PDF/DOCX/image/OCR/spreadsheet/EHR content with an approved local or user-authorized tool.
3. Preserve exact text or cell values, source page/line/cell/segment, file hash when available, original units, negation, and extraction method/version.
4. Record OCR corrections separately from the source text. Never present corrected text as a verbatim quote.
5. Keep binary sources and direct identifiers outside the MCP prompt unless the environment is explicitly approved for them.

RootCause MCP may verify accessible plain-text extracts under configured source roots. If it cannot access or exactly match the source, record `UNVERIFIED`; a host extraction, file presence, or plausible wording is not an exact match.

## Canonical time rules

- Store `event_time_raw` exactly as shown and `event_time_canonical` as ISO 8601 only when normalization is defensible.
- Include timezone or UTC offset. If unknown, retain `timezone: unknown`; do not assume local time.
- Record precision as `instant`, `minute`, `hour`, `date`, `range`, `relative`, or `unknown`.
- Resolve relative labels such as POD 1 only against an explicitly sourced anchor. Otherwise leave canonical time unresolved.
- Preserve conflicting timestamps as separate claims and flag the conflict; do not average or silently select one.
- Pass a defensible canonical ISO 8601 value through `rc_add_evidence.event_timestamp` or `rc_evidence(action="add").event_timestamp`; RootCause persists it separately from ingestion time. Retain the raw time text, precision, timezone assumptions, and unresolved conflicts in the handoff ledger.

## Manual confirmation rules

- Prefer deterministic exact snippet verification against an allowed source root.
- Use `manual_confirmation=true` only for independent human review when deterministic matching is unavailable.
- Require `verified_by` to match an operator-configured entry in the comma-separated `ROOTCAUSE_AUTHORIZED_REVIEWERS` environment variable.
- Treat generic identities such as `agent` or `system`, empty allowlists, and invented reviewer names as unverified.
- Record reviewer role and review time in the handoff; allowlist membership proves authorization, not clinical correctness.

## Direct likelihood-ratio rules

- Pass the applied `likelihood_ratio` directly: `>1` supports, `<1` contradicts, `1.0` is neutral.
- Pass the matching support/contradiction flag. Never rely on a weight-to-LR heuristic or invert an LR inside the agent.
- Cite a guideline/study or explain a defensible case-specific rationale. If no quantitative LR is justified, use `1.0` and record a qualitative relationship.
- Test the leading diagnosis against at least one genuinely disconfirming finding or planned test.
- Keep must-not-miss hypotheses visible until evidence-based exclusion; low probability alone is not exclusion.
- For every active hypothesis, persist a typed `planned_tests` entry when refuting evidence is pending. It must include `name`, `purpose`, `expected_supporting_result`, `expected_refuting_result`, and `status`.
- Only `purpose: DISCONFIRM` or `RULE_OUT` with `status: PLANNED` or `ORDERED` counts as a pending refuting disposition. Free-text gaps do not count.

## Conservative causation and root disposition

`rc_verify_causation` is a proof-obligation audit, not an independent clinical
causality prover. Every persisted audit must retain
`audit_scope: CONSERVATIVE_CAUSATION_AUDIT` and
`clinical_causality_established: false`.

- The audit `cause_event.id` must equal the Why root ID.
- The audit cause description and evidence set must exactly equal the Why ledger;
  cause and effect evidence IDs must exist in the evidence ledger.
- `verification_id` must be non-empty and unique, and the root record must point to
  the latest audit unless the claim was rejected.
- `REJECTED` claims must not remain in the `root_causes` bucket.
- `INSUFFICIENT_DATA` candidates remain `disposition: PROPOSED`.
- Compatibility results `VERIFIED` / `VERIFIED_WITH_CAVEATS` mean only that the
  implemented audit obligations passed; use `disposition: AUDIT_OBLIGATIONS_PASSED`
  and never state that clinical causality was proved.

## Final report conformance

Preview first and inspect every machine-readable check. Caller-authored `PASS`
records are not authoritative; the finalization boundary recomputes all hard checks.
Final release requires:

- typed nested report sections and every mandatory final section;
- reviewed multi-source manifest and declared evidence lineage;
- at least three unique diagnoses, active DDx dispositions, and challenged leading
  and must-not-miss diagnoses;
- Fishbone/Why presence plus exact root/evidence/audit lineage and safe dispositions;
- no unresolved high/critical safety conflict;
- an operator-authorized reviewer, timezone-aware `finalized_at`, and recomputable
  SHA-256 `content_hash`.

The finalized domain snapshot recursively rejects mutation. The hash is integrity
metadata; durable WORM retention and signature policy remain deployment concerns.

## Discrete and condensed mapping

Use only actions advertised by the connected server.

| Purpose | Discrete tool | Condensed facade |
| --- | --- | --- |
| Start/get/list/archive case; pin manifest on start | `rc_start_session(source_manifest=...)`, `rc_get_session`, `rc_list_sessions`, `rc_archive_session` | `rc_rca`: `session_start`, `session_get`, `session_list`, `session_archive` |
| Add/get/verify evidence | `rc_add_evidence`, `rc_get_evidence`, `rc_verify_evidence` | `rc_evidence`: `add`, `get`, `verify` |
| Propose/link/rank/exclude DDx | `rc_propose_hypothesis`, `rc_link_evidence_to_hypothesis`, `rc_get_differential_diagnosis`, `rc_exclude_hypothesis` | `rc_hypothesis`: `propose`, `link`, `rank`, `exclude` |
| Think/reflect/gap/challenge/get chain | `rc_think_aloud`, `rc_reflect`, `rc_identify_gaps`, `rc_challenge_assumption`, `rc_get_thinking_chain` | `rc_thinking`: `think`, `reflect`, `gap`, `challenge`, `get_chain` |
| Stage audit/conflicts/causation | `rc_audit_reasoning_state`, `rc_detect_conflicts`, `rc_verify_causation` | `rc_audit`: `stage_guidance`, `detect_conflicts`, `verify_causation` |
| Report preview/generate | `rc_generate_contract_report` | `rc_report`: `preview`, `generate` |
| Timeline/diagram validation | `rc_render_timeline`, `rc_validate_diagram` | `rc_diagram`: `timeline`, `validate` |
| Reasoning/evidence graph | `rc_export_reasoning_chain`; evidence graph through report generation | `rc_diagram`: `reasoning_chain`, `evidence_graph` |
| Checkpoint create/list/restore | `rc_create_checkpoint`, `rc_list_checkpoints`, `rc_restore_checkpoint` | `rc_checkpoint`: `create`, `list`, `restore` |
| Fishbone init/add/get/export | `rc_init_fishbone`, `rc_add_cause`, `rc_get_fishbone`, `rc_export_fishbone` | `rc_rca`: `fishbone_init`, `fishbone_add_cause`, `fishbone_get`, `fishbone_export` |
| Why ask/get/link/mark/export/teach | `rc_ask_why`, `rc_get_why_tree`, `rc_add_causal_link`, `rc_mark_root_cause`, `rc_export_why_tree`, `rc_build_teaching_case` | `rc_rca`: `why_ask`, `why_get`, `why_link`, `why_mark_root`, `why_export`, `why_teach` |
| HFACS suggest/confirm/framework | `rc_suggest_hfacs`, `rc_confirm_classification`, `rc_get_hfacs_framework` | `rc_rca`: `hfacs_suggest`, `hfacs_confirm`, `hfacs_framework` |

There is no advertised condensed equivalent for `rc_get_reasoning_chain`, `rc_list_learned_rules`, `rc_reload_rules`, or `rc_get_6m_hfacs_mapping`. Use `all`, `clinical`, or `rca` as appropriate; never call an undocumented facade action.

If only the `clinical` profile is available, use one host-issued opaque session ID consistently and hand off for RCA. If only `rca` is available, require the clinical evidence/DDx ledger from the previous agent before assigning causes. Do not infer missing stages from narrative prose.

## Minimal handoff record

Use this shape in JSON, YAML, or equivalent structured Markdown. Omit direct identifiers and use `unknown`, `unverified`, or an empty list instead of fabricated values.

```yaml
schema_version: rootcause-case-handoff/1
case:
  case_id: deidentified-case-id
  session_id: stable-session-id
  purpose: retrospective-safety-review
  status: PRELIMINARY
  timezone: unknown
  tool_profile: condensed
  handed_off_from: agent-or-host
  handed_off_to: agent-or-host

source_manifest:
  schema_version: "1.0"
  patient_key: pseudonymous-patient-key
  encounter_key: pseudonymous-encounter-key
  default_timezone: Asia/Taipei
  documents:
    - document_id: SRC-001
      source_uri: file:///approved/deidentified-flowsheet.csv
      sha256: 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
      media_type: text/csv
      source_kind: flowsheet
      revision: "1"
      captured_at: "2026-08-17T08:30:00+08:00"
      parser_name: host-csv-extractor
      parser_version: "1.0"
      status: extracted
      de_identified: true

source_limitations:
  - document_id: SRC-001
    limitations: []

evidence_ledger:
  - local_key: EV-001
    mcp_evidence_id: unknown
    document_id: SRC-001
    observation: "Atomic, non-interpretive finding"
    raw_snippet: "Exact source text or cell value"
    source_location: "row 42, columns time/BP"
    event_time_raw: "08:18"
    event_timestamp: "2026-08-17T08:18:00+08:00"
    timezone: Asia/Taipei
    precision: minute
    verification_status: UNVERIFIED
    verification_method: none
    content_hash: unknown

hypotheses:
  - hypothesis_id: unknown
    diagnosis: candidate diagnosis
    must_not_miss: false
    prior_probability: 0.1
    evidence_links:
      - evidence_key: EV-001
        direction: supports
        applied_lr: 1.0
        lr_source_or_rationale: quantitative LR unavailable
    planned_tests: []
    disconfirming_test: unknown
    posterior_probability: unknown
    status: active

cognitive_audit:
  uncertainties: []
  missing_data: []
  alternatives_considered: []
  bias_risks: []

rca:
  fishbone_artifact: unknown
  why_tree_artifact: unknown
  hfacs_confirmations: []
  causation_results: []
  root_causes: []
  contributing_factors: []

readiness:
  conflicts_checked: false
  gates_passed: []
  blockers: []
  conformance_checks: []
  human_review:
    status: NOT_REVIEWED
    reviewer: unknown
    role: unknown
    reviewed_at: unknown
  finalization:
    is_finalized: false
    approved_by: null
    finalized_at: null
    content_hash: null

artifacts:
  input_contract_resource: clinical://contracts/case-input-manifest
  report_contract_resource: clinical://contracts/case-analysis-report
  clinical_report: unknown
  rca_exports: []
  unified_report: unknown
  content_hashes: {}
```

## Unified report order

Produce one package with these sections:

1. Status, scope, de-identification, human-review state, and safety disclaimer.
2. Source manifest and extraction limitations.
3. Canonical timeline with source links and unresolved conflicts.
4. Evidence ledger separating observed, inferred, and unverified content.
5. Ranked DDx, must-not-miss list, direct LR updates, disconfirming evidence, and exclusions.
6. Uncertainty, missing data, cognitive-bias audit, and contradictions.
7. Fishbone, Why Tree, confirmed HFACS factors, and conservative causation audit outcomes with explicit non-proof scope.
8. Root causes versus contributing factors; omit `REJECTED`, keep `INSUFFICIENT_DATA` proposed, and label audit passes `AUDIT_OBLIGATIONS_PASSED`.
9. Corrective actions with owner, due date, verification measure, and approval state when supplied by humans.
10. Machine-readable handoff record, `conformance_checks[]`, schema/config versions, reviewer/finalization metadata, artifact hashes, and audit trail validated against `clinical://contracts/case-analysis-report`.

Treat the native report schema as the canonical typed envelope. A final report still fails readiness when required workflow content is absent, even if optional schema fields allow a preliminary payload. Finalized state requires authorized reviewer, timezone-aware time, recomputable hash, and an unchanged nested snapshot. Label host-only supplements explicitly and preserve their hashes.

## Evaluation handoff boundary

Do not reuse this repository's public cases or reference rubrics for a formal blinded
Agent claim. Formal evaluation requires a repository-external private case bundle,
separately protected private gold, filesystem isolation preventing the adapter from
reading either gold or parent/repository context, and trusted runtime/server traces.
Without the complete 3-runtime × 6-case × 2-repeat matrix and two blinded qualified
clinical reviews per job (plus adjudication of disagreement), retain
`AGENT_EVAL_NOT_ESTABLISHED`.
