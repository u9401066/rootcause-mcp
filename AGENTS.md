# RootCause MCP Clinical Reasoning Harness

These are the workspace instructions for agents developing or using RootCause MCP to turn multiple de-identified clinical records into an evidence-grounded differential diagnosis and medical root-cause analysis.

## Goal

Produce one auditable case package with source lineage, canonical timeline, competing DDx, Bayesian evidence links, cognitive audit, Fishbone/Why/HFACS analysis, conservative causation status, limitations, and qualified-human review state.

## Working style

- Use Traditional Chinese unless the user requests another language.
- Treat the system as retrospective decision support, never an autonomous diagnostic or treatment system.
- Separate source observations, host extraction, clinical interpretation, hypotheses, and causal claims.
- Prefer explicit `unknown`, `unverified`, or `insufficient data` over a plausible invention.
- Keep updates concise and state which workflow gate is complete or blocked.

## Required harness

For case analysis, handoff, prompt/resource design, or agent integration, read:

- `.codex/skills/rootcause-clinical-reasoning-harness/SKILL.md`
- `.codex/skills/rootcause-clinical-reasoning-harness/references/case-handoff.md`
- `clinical://contracts/case-input-manifest`
- `clinical://contracts/case-analysis-report`

Equivalent copies live under `.cline/skills/rootcause-clinical-reasoning-harness/` and `.claude/skills/rootcause-clinical-reasoning-harness/`. Keep their `SKILL.md` and `references/case-handoff.md` byte-identical to the Codex source.

## Mandatory case workflow

1. Start or resume one de-identified case/session; reuse the handed-off session ID.
2. Read the live input contract and pass a schema-version `1.0` source manifest for every supplied source when creating the session.
3. Record atomic exact snippets, source locations, whole-file/source-span hashes, and canonical ISO 8601 `event_timestamp` with timezone/precision.
4. Maintain at least three plausible diagnoses and applicable must-not-miss conditions.
5. Link supporting and disconfirming evidence using the direct applied LR; use 1.0 when quantitatively unknown.
6. Record uncertainty, missing data, alternative explanations, and cognitive-bias checks.
7. Complete Fishbone, Why, HFACS, and conservative causation review.
8. Run conflicts/readiness checks and obtain named qualified-human review before finalization. Manual confirmation requires reviewer membership in `ROOTCAUSE_AUTHORIZED_REVIEWERS`.
9. Produce the unified report plus machine-readable case-handoff record and validate the envelope against `clinical://contracts/case-analysis-report`.

The v1 manifest is pinned and has no amendment tool. When a new source appears,
keep the case preliminary and use an operator-controlled superseding-session replay
with a complete replacement manifest; preserve the prior session ID and revisit
every affected downstream stage.

## Tool profiles

- `all`: complete 43-tool discrete surface.
- `condensed`: 8-tool workflow facade; use only advertised action enums and hand off discrete-only operations.
- `clinical`: partial clinical reasoning surface; hand off for RCA rather than skipping it.
- `rca`: partial system RCA surface; require the prior evidence/DDx ledger before assigning causes.

Discover tools at runtime. Do not assume JSON Schema defaults are injected, call undocumented facade actions, or parse an error-looking text response as success.

## Host extraction boundary

RootCause MCP currently consumes structured evidence one item at a time; it does not batch-ingest or parse raw PDF, DOCX, image, scan, spreadsheet, or EHR exports. The host agent or an approved extractor must preserve exact text/cells, source locations, hashes, units, negation, OCR corrections, time precision, and extraction method. Do not claim MCP provenance verification for inaccessible or binary sources.

## PHI and clinical guardrails

- Minimize and pseudonymize PHI. Never put direct identifiers in session IDs, prompts, filenames, logs, literature queries, or reports unless explicitly authorized in an approved secure environment.
- Treat raw snippets, databases, checkpoints, exports, screenshots, and tool responses as PHI-bearing.
- Never fabricate quotes, timestamps, hashes, codes, probabilities, LRs, citations, reviewer identity, or causal verification.
- Never normalize a date/time beyond source precision or silently repair OCR.
- Keep must-not-miss hypotheses visible until evidence-based exclusion.
- Do not finalize on agent confidence alone. Record the reviewer name/role and unresolved safety issues.
- Never use manual evidence confirmation for an identity absent from the operator-controlled `ROOTCAUSE_AUTHORIZED_REVIEWERS` allowlist.
- Escalate urgent active-care concerns to a qualified clinician.

## Repository work

- Preserve unrelated user and concurrent-agent changes in the working tree.
- Treat `.codex/skills`, `.cline/skills`, `.claude/skills`, `AGENTS.md`, and `.github/copilot-instructions.md` as bundled harness assets.
- Validate the canonical skill with the skill-creator `quick_validate.py`, then verify the three mirrored files by hash/diff.
- Use `uv run pytest`, `uv run ruff check .`, and `uv run mypy src --ignore-missing-imports` for proportional Python verification.
- Keep runtime code, report contracts, and packaging out of a harness-only change unless the user expands scope.

## Optional PubMed and Zotero handoff

Use literature tools only when the user requests evidence lookup or when a quantitative LR/guideline needs a current citation.

- Formulate a de-identified PICO/query; never send raw patient text or identifiers to external literature services.
- Keep discovery/search/export in PubMed Search MCP. Distinguish peer-reviewed articles, preprints, and metadata-only records.
- Keep library persistence, collection selection, and duplicate inspection in Zotero Keeper.
- Ask before importing anything into Zotero, confirm the target collection, and check duplicates first.
- Literature supports a claim; it never replaces case-specific source provenance or qualified clinical review.
