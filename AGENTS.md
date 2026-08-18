# RootCause MCP Clinical Reasoning Harness

These are the workspace instructions for agents developing or using RootCause MCP to turn multiple de-identified clinical records into an evidence-grounded differential diagnosis and medical root-cause analysis.

## Goal

Produce one auditable case package with source lineage, canonical timeline, competing DDx, Bayesian evidence links, cognitive audit, Fishbone/Why/HFACS analysis, conservative causation status, limitations, and qualified-human review state.

## Working style

- Use Traditional Chinese unless the user requests another language.
- For clinician-facing prose, keep canonical diagnosis, test, drug, and procedure names in English. On first use, an established abbreviation may be written with an optional Traditional Chinese gloss; never invent a translation or expand an ambiguous abbreviation.
- Treat the system as retrospective decision support, never an autonomous diagnostic or treatment system.
- Separate source observations, host extraction, clinical interpretation, hypotheses, and causal claims.
- Treat `unknown`, `unverified`, and `insufficient data` as reasoning inputs: state which mechanisms remain open and what evidence would discriminate them instead of turning missingness into a negative finding.
- Never fabricate a probability or likelihood ratio. An uncalibrated compatibility default is an implementation placeholder, not clinical probability, rank, or certainty.
- Keep updates concise and state which workflow gate is complete or blocked.

## Required harness

For case analysis, handoff, prompt/resource design, or agent integration, read:

- `.codex/skills/rootcause-clinical-reasoning-harness/SKILL.md`
- `.codex/skills/rootcause-clinical-reasoning-harness/references/case-handoff.md`
- `.codex/skills/rootcause-clinical-reasoning-harness/references/clinician-ddx-discussion-zh-tw.md` when writing a clinician-facing DDx discussion
- `clinical://contracts/case-input-manifest`
- `clinical://contracts/case-analysis-report`

Equivalent copies live under `.cline/skills/rootcause-clinical-reasoning-harness/` and `.claude/skills/rootcause-clinical-reasoning-harness/`. Keep the three harness files byte-identical to the Codex source.

## Mandatory case workflow

1. Start or resume one de-identified case/session; reuse the handed-off session ID.
2. Read the live input contract and pass a schema-version `1.0` source manifest for every supplied source when creating the session.
3. After extraction, append one authorized `rc_adjudicate_source` review per source. Keep the manifest identity and digest immutable; finalization requires reviewed, de-identified, independence-adjudicated source events with reviewer, time, and rationale.
4. Record atomic exact snippets, source locations, whole-file/source-span hashes, and typed source-faithful time. Use an aware `instant` only when the source contains an offset; retain `date`, `range`, `relative`, or `unknown` without inventing chronology.
5. Build the maximum reasonable mechanism-based DDx for the phenotype and time course. Choose a syndrome-appropriate breadth framework and review every required framework cell; a final PRIMARY audit may retain `REVIEWED_INSUFFICIENT_DATA` with unknowns/tests but no `NOT_ASSESSED`. Three unique diagnoses, two non-`UNKNOWN` mechanisms, and one applicable must-not-miss diagnosis are deterministic finalization floors, not a clinical target or cap; avoid both premature closure and an unbounded laundry list.
6. For every active candidate, record why it was considered, mechanism and diagnostic role, source-linked support/refutation/neutral evidence, candidate-specific unknowns, a discriminating test or genuine evidence disposition, and a qualitative certainty label. Select the leading hypothesis explicitly with a reason; array order and compatibility values never select it.
7. Link evidence using the direct applied LR: `>1` supports, `<1` refutes, and `1.0` is neutral or quantitatively unknown. A non-neutral LR requires a distinct, verified `LITERATURE` calibration-evidence record plus the patient evidence it is applied to. Do not count `1.0` as support/refutation or display an uncalibrated prior/posterior as clinical probability.
8. Record uncertainty, missing data, alternative explanations, and cognitive-bias checks. Keep observation, inference, and causal claim explicitly separated.
9. Complete Fishbone and Why analysis. Every Fishbone cause needs an authorized persisted HFACS `CONFIRMED` or `NOT_APPLICABLE` review, and every proposed Why root needs a conservative causation audit with exact ledger lineage.
10. Run conflicts/readiness checks and obtain named qualified-human review before finalization. Manual confirmation, source/HFACS adjudication, and finalization require reviewer membership in `ROOTCAUSE_AUTHORIZED_REVIEWERS`.
11. Produce the unified report plus machine-readable case-handoff record and validate the envelope against `clinical://contracts/case-analysis-report`.

The v1 manifest is pinned and has no amendment tool. When a new source appears,
keep the case preliminary and use an operator-controlled superseding-session replay
with a complete replacement manifest; preserve the prior session ID and revisit
every affected downstream stage. `rc_adjudicate_source` appends processing/review
state for a registered source; it never adds, removes, or rewrites manifest identity.

## Tool profiles

- `all`: complete 46-tool discrete surface.
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
