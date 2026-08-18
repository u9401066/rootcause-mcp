---
name: rootcause-clinical-reasoning-harness
description: "Run evidence-grounded, multi-source clinical case analysis through RootCause MCP and produce a safe, standardized differential-diagnosis plus root-cause handoff. Use for raw or extracted medical records, timelines, M&M or adverse-event review, DDx, Fishbone, 5-Why, HFACS, causation review, report generation, and continuation of a case across Codex, Claude, Cline, or Copilot agents."
---

# RootCause Clinical Reasoning Harness

Use RootCause MCP as an auditable reasoning ledger, not as an autonomous clinician. Keep observations, interpretations, hypotheses, and causal claims visibly separate.

## Load the case contract

Read [references/case-handoff.md](references/case-handoff.md) before starting, resuming, handing off, or finalizing a case. Before writing case state, also read `clinical://contracts/case-input-manifest` and `clinical://contracts/case-analysis-report`; treat those live JSON Schemas as authoritative over copied examples.

Read [references/clinician-ddx-discussion-zh-tw.md](references/clinician-ddx-discussion-zh-tw.md) when expanding a differential or preparing clinician-facing Traditional Chinese output. It defines the bounded breadth, candidate-level reasoning, language, and quantification rules; do not load it for a code-only repository task.

## Select the tool surface

- Discover the advertised tools before acting; never call an unadvertised tool or facade action.
- Prefer `condensed` for the 8-tool workflow facade or `all` for the complete 46-tool surface. Consult the mapping for discrete-only operations.
- Treat `clinical` and `rca` as partial profiles. Hand off the same `session_id` and ledger to an agent/profile with the missing tools rather than silently skipping stages.
- Reuse the handed-off `session_id`. Never create a second case because an intermediate tool returns no state.

## Follow every stage in order

1. **Case/session** — Start or resume one de-identified case. Record scope, analysis purpose, timezone, profile, and stable session ID.
2. **Multi-source manifest** — Pass a schema-version `1.0` `source_manifest` to session creation. Register every supplied document with a stable ID, approved URI, whole-file SHA-256, media type, source kind, and extraction state before extracting findings.
3. **Source review** — After extraction, append an authorized `rc_adjudicate_source` event for every registered source. Record processing status, de-identification, independence/group lineage, reviewer, and rationale without changing the pinned manifest identity or digest.
4. **Exact evidence and time** — Add one atomic finding per evidence item with document ID, exact snippet, precise location, and a typed source-faithful `temporal` record. Only use `kind=instant` when the source includes an explicit offset; retain `date`, `range`, `relative`, or `unknown` without inventing order. Verify exact text when possible; retain `UNVERIFIED` otherwise.
5. **Differential expansion** — Build the maximum reasonable mechanism-based DDx for the phenotype and time course. Choose a syndrome-appropriate framework and persist a PRIMARY breadth audit after reviewing every required framework cell; a final audit may retain `REVIEWED_INSUFFICIENT_DATA` with unknowns and typed discriminators but no `NOT_ASSESSED`. Three unique diagnoses, two non-`UNKNOWN` mechanisms, and one applicable must-not-miss diagnosis are deterministic finalization floors, not a clinical target or cap. Prune duplicate labels and candidates with no plausible mechanism or decision impact instead of producing an unbounded laundry list.
6. **Candidate disposition** — For every active diagnosis, persist why it was considered, `mechanism_category`, `diagnostic_role`, `reasoning_basis`, qualitative `certainty`, source-linked support/refutation/neutral evidence, candidate-specific unknowns, and either genuine evidence or a typed discriminating test. A must-not-miss flag expresses safety priority, not likelihood. Use `rc_select_leading_hypothesis` with a reason and actor; never let numeric compatibility or array order choose the lead.
7. **Evidence testing** — Link evidence using the direct applied LR. Use LR > 1 for support, LR < 1 for contradiction, and 1.0 when neutral or quantitatively unknown; neutral links do not count as support or refutation. A non-neutral LR requires both the target patient evidence and a distinct verified `LITERATURE` evidence record that preserves the quantitative source. Never invent or invert an LR or present an uncalibrated compatibility prior/posterior as clinical probability. When refuting evidence is pending, persist a typed `planned_tests` entry with purpose, expected supporting/refuting results, and `PLANNED` or `ORDERED` status.
8. **Uncertainty and bias** — Treat unknowns as inputs: say which mechanisms remain open and what result would discriminate them. Keep source observation, host/clinical inference, and causal claim explicitly separate. Record concise rationale, missing data, competing explanations, disconfirming tests, and anchoring/confirmation/premature-closure risks. Do not emit hidden chain-of-thought or private scratch work.
9. **System RCA** — Build Fishbone and Why structures. Persist an authorized HFACS review for every Fishbone cause as `CONFIRMED` with a recognized code or `NOT_APPLICABLE` without a code; suggestions and codes supplied while adding a cause remain unreviewed. Persist a causation-review attempt linked to every proposed root. Keep the Why/root/audit ID, exact description, and evidence ID set identical. The validator is a conservative proof-obligation audit, not clinical causal proof: omit `REJECTED` claims from the root-cause bucket, retain `INSUFFICIENT_DATA` only as `PROPOSED`, and label an audit pass `AUDIT_OBLIGATIONS_PASSED` even if a compatibility enum says `VERIFIED`.
10. **Readiness and review** — Run conflict/readiness checks. Keep the case preliminary until named qualified humans review sources, HFACS dispositions, clinical safety, causal claims, and proposed actions. Manual evidence confirmation, source/HFACS adjudication, and finalization are valid only when the named reviewer is present in the operator-controlled `ROOTCAUSE_AUTHORIZED_REVIEWERS` allowlist; allowlist membership alone does not establish clinical qualification.
11. **Unified output** — Produce the standardized handoff/report package in the reference. For the built-in clinician renderer, request Markdown with `locale="zh-TW"` and `audience="clinician"`; JSON/FHIR payload values and custom templates retain their original language. Preview before finalization, inspect machine-readable `conformance_checks[]`, and identify every incomplete or unverified section. Finalization must recompute every hard check using the operator-supplied reviewer allowlist and include reviewer, timezone-aware time, and a recomputable content hash. The domain snapshot rejects nested mutation; the hash is integrity metadata, not durable WORM storage.

The v1 manifest is pinned at session creation and currently has no amendment tool. `rc_adjudicate_source` appends review/independence state for a registered source; it never adds or rewrites manifest identity. If a new source arrives, keep the existing case preliminary; use an operator-controlled superseding session/replay with a complete replacement manifest, preserve the prior session ID in the handoff, and repeat the affected downstream stages. Never smuggle an undeclared source into the old ledger.

## Enforce clinical and PHI guardrails

- Minimize and pseudonymize PHI. Do not place names, MRNs, dates of birth, contact details, or other direct identifiers in session IDs, prompts, filenames, logs, literature queries, or reports unless explicitly authorized in an approved secure environment.
- Treat databases, checkpoints, exports, raw snippets, screenshots, and tool responses as PHI-bearing artifacts. Do not upload them to an external service without explicit authorization.
- Never fabricate a source, quote, location, timestamp, hash, diagnosis code, probability, LR, citation, causal mechanism, reviewer, or verification state.
- Keep clinician-facing prose in Traditional Chinese while preserving canonical diagnosis, test, drug, and procedure names in English. An established abbreviation may receive a Traditional Chinese gloss on first use; never invent a translation or expand an ambiguous abbreviation.
- Preserve negation, uncertainty, units, reference ranges, and original time precision. Do not silently “correct” OCR or normalize a date beyond what the source supports.
- Do not mark file existence, a plausible narrative, or agent agreement as exact provenance.
- Never set `manual_confirmation=true` for `agent`, `system`, an invented identity, or a reviewer absent from `ROOTCAUSE_AUTHORIZED_REVIEWERS`.
- Never render `VERIFIED` from the conservative causation audit as clinical causality established; the persisted audit scope remains `CONSERVATIVE_CAUSATION_AUDIT` with `clinical_causality_established=false`.
- Do not use this workflow for autonomous diagnosis or treatment. Escalate urgent active-care concerns to a qualified clinician; label retrospective findings as decision support.

## Respect the current extraction boundary

The current RootCause MCP does not ingest or parse a batch of PDF, DOCX, image, spreadsheet, EHR export, or scanned records. Let the host agent or an approved extraction tool produce citation-ready text/cells while preserving source hashes and locations. Send only structured atomic findings into RootCause MCP. Do not claim MCP verification for binary or inaccessible sources.

## Keep Agent evaluation claims fail-closed

Treat the bundled public cases and rubrics as engineering regression assets, never as a blinded evaluation: stable public case IDs/content can leak or be memorized even when filenames omit diagnoses. A formal Agent claim requires repository-external private case bundles, separately protected private holdout gold, adapter filesystem isolation, trusted runtime/server MCP traces, at least three real runtimes over 6 cases × 2 repeats, and two blinded qualified-clinician reviews per job with disagreement adjudication. Until all conditions pass, report `AGENT_EVAL_NOT_ESTABLISHED` and call the project engineering alpha.

Run formal preflight with explicit `--corpus-file /secure/private-corpus/corpus.json`, `--gold-dir /secure/private-holdout`, and `--attest-holdout-isolation`; do not substitute the bundled public assets. Add `--authorize-provider-egress` only for approved de-identified synthetic inputs, never real clinical records or PHI.

Validate the unified package against `clinical://contracts/case-analysis-report`. Require typed nested evidence/timeline lineage, Fishbone/Why/HFACS outputs, conservative causation results, safe root dispositions, the DDx breadth floors plus typed candidate/evidence/test dispositions, limitations, human-review metadata, and machine-readable conformance checks before calling a schema-valid envelope complete; optional preliminary fields are not permission to skip final workflow gates.
