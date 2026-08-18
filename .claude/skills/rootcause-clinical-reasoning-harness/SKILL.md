---
name: rootcause-clinical-reasoning-harness
description: "Run evidence-grounded, multi-source clinical case analysis through RootCause MCP and produce a safe, standardized differential-diagnosis plus root-cause handoff. Use for raw or extracted medical records, timelines, M&M or adverse-event review, DDx, Fishbone, 5-Why, HFACS, causation review, report generation, and continuation of a case across Codex, Claude, Cline, or Copilot agents."
---

# RootCause Clinical Reasoning Harness

Use RootCause MCP as an auditable reasoning ledger, not as an autonomous clinician. Keep observations, interpretations, hypotheses, and causal claims visibly separate.

## Load the case contract

Read [references/case-handoff.md](references/case-handoff.md) before starting, resuming, handing off, or finalizing a case. Before writing case state, also read `clinical://contracts/case-input-manifest` and `clinical://contracts/case-analysis-report`; treat those live JSON Schemas as authoritative over copied examples.

## Select the tool surface

- Discover the advertised tools before acting; never call an unadvertised tool or facade action.
- Prefer `condensed` for the 8-tool workflow facade or `all` for the complete 43-tool surface. Consult the mapping for discrete-only operations.
- Treat `clinical` and `rca` as partial profiles. Hand off the same `session_id` and ledger to an agent/profile with the missing tools rather than silently skipping stages.
- Reuse the handed-off `session_id`. Never create a second case because an intermediate tool returns no state.

## Follow every stage in order

1. **Case/session** — Start or resume one de-identified case. Record scope, analysis purpose, timezone, profile, and stable session ID.
2. **Multi-source manifest** — Pass a schema-version `1.0` `source_manifest` to session creation. Register every supplied document with a stable ID, approved URI, whole-file SHA-256, media type, source kind, and extraction state before extracting findings.
3. **Exact evidence and time** — Add one atomic finding per evidence item with document ID, exact snippet, precise location, and canonical ISO 8601 `event_timestamp`. Verify exact text when possible; retain `UNVERIFIED` otherwise.
4. **Differential expansion** — Maintain at least three normalized, non-duplicate plausible diagnoses and explicitly flag applicable must-not-miss conditions. Do not collapse to one diagnosis early.
5. **Bayesian testing** — Link supporting and disconfirming evidence using the direct applied LR. Use LR > 1 for support, LR < 1 for contradiction, and 1.0 when neutral or quantitatively unknown. Never invent or invert an LR. Every active diagnosis needs an evidence/test disposition; when refuting evidence is pending, persist a typed `planned_tests` entry with purpose, expected supporting/refuting results, and `PLANNED` or `ORDERED` status.
6. **Uncertainty and bias** — Record concise rationale, missing data, competing explanations, disconfirming tests, and anchoring/confirmation/premature-closure risks. Do not emit hidden chain-of-thought or private scratch work.
7. **System RCA** — Build Fishbone and Why structures, classify HFACS factors, and persist a causation-review attempt linked to every proposed root. Keep the Why/root/audit ID, exact description, and evidence ID set identical. The validator is a conservative proof-obligation audit, not clinical causal proof: omit `REJECTED` claims from the root-cause bucket, retain `INSUFFICIENT_DATA` only as `PROPOSED`, and label an audit pass `AUDIT_OBLIGATIONS_PASSED` even if a compatibility enum says `VERIFIED`.
8. **Readiness and review** — Run conflict/readiness checks. Keep the case preliminary until a named qualified human reviews sources, clinical safety, causal claims, and proposed actions. Manual evidence confirmation/finalization is valid only when the reviewer is present in the operator-controlled `ROOTCAUSE_AUTHORIZED_REVIEWERS` allowlist; allowlist membership alone does not establish clinical qualification.
9. **Unified output** — Produce the standardized handoff/report package in the reference. Preview before finalization, inspect machine-readable `conformance_checks[]`, and identify every incomplete or unverified section. Finalization must recompute every hard check and include reviewer, timezone-aware time, and a recomputable content hash. The domain snapshot rejects nested mutation; the hash is integrity metadata, not durable WORM storage.

The v1 manifest is pinned at session creation and currently has no amendment tool. If a new source arrives, keep the existing case preliminary; use an operator-controlled superseding session/replay with a complete replacement manifest, preserve the prior session ID in the handoff, and repeat stages 3–8. Never smuggle an undeclared source into the old ledger.

## Enforce clinical and PHI guardrails

- Minimize and pseudonymize PHI. Do not place names, MRNs, dates of birth, contact details, or other direct identifiers in session IDs, prompts, filenames, logs, literature queries, or reports unless explicitly authorized in an approved secure environment.
- Treat databases, checkpoints, exports, raw snippets, screenshots, and tool responses as PHI-bearing artifacts. Do not upload them to an external service without explicit authorization.
- Never fabricate a source, quote, location, timestamp, hash, diagnosis code, probability, LR, citation, causal mechanism, reviewer, or verification state.
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

Validate the unified package against `clinical://contracts/case-analysis-report`. Require typed nested evidence/timeline lineage, Fishbone/Why/HFACS outputs, conservative causation results, safe root dispositions, at least three unique DDx entries, typed active/test dispositions, limitations, human-review metadata, and machine-readable conformance checks before calling a schema-valid envelope complete; optional preliminary fields are not permission to skip final workflow gates.
