# Active Context - RootCause MCP

> Last updated: 2026-08-14

## Current Focus

Hard-coded provenance verification and multi-loop clinical guidance engine are complete.

Verified provenance and guidance outcomes:

- `ProvenanceVerifier` scans raw physical files (TXT, CSV, HL7, XML) for verbatim snippets, line indexing, and SHA-256 cryptographic digests without LLM calls.
- `ClinicalGuidanceService` drives multi-loop reasoning state machine for lightweight (Flash/mini) models with stage progression, readiness checklists, missing prerequisites, next prompt directives, and Socratic push questions.
- `rc_audit_reasoning_state` MCP tool added (bringing total tools to 37: 17 clinical, 21 RCA, 37 all).
- Tool profiles frozen per server lifespan; compact text responses include `stage`, `completeness`, and `next_prompt`.
- Automated completeness checks in Markdown reports catch premature closure (<3 differential hypotheses) and unverified evidence.

Verified token-efficiency outcomes:

- Clinical/RCA/all profiles are frozen per server lifespan and constrain list/dispatch.
- Clinical schema context: 40,557 -> 20,937 UTF-8 bytes (48.4% reduction).
- Synthetic 50-record duplicate text: 51,743 -> 174 bytes (99.7% reduction).
- Compact text points unsupported hosts to `ROOTCAUSE_RESPONSE_MODE=verbose`.
- Brief/standard/full Markdown reports use zero server-side LLM tokens.
- Reports automate DD ranking, evidence matrix, cognitive safety, structural checks,
  quality metrics, reasoning audit, and Evidence Graph generation.

Generated-artifact and visualization audit remains complete.

Verified state:

- 37 total MCP tools with exact dispatch; profiles expose 17 clinical, 21 RCA, or all
- Shared `ServerState` plus `ClinicalReasoningOrchestrator` case aggregate
- SQLite persistence and restart rehydration for Evidence, Hypothesis,
  ThinkingChain, and ReasoningChain
- CONTRACT reports populated from real aggregate data
- Conservative causation validation through one Domain Service
- HFACS-MES 2024 codes accepted while legacy codes remain readable
- SDK 1.x entry point removed; `rootcause_mcp.server_v2:main` is the sole entry
- Safe exports under `ROOTCAUSE_DATA_DIR/exports`

## Quality Baseline

| Gate | Result |
| --- | --- |
| Tests | 66 passed |
| Coverage | 81.56% branch-aware |
| Ruff | Passed for `src` and `tests` |
| Mypy | Strict mode passed for 79 source files |
| Bandit | Medium/high severity scan passed |
| Vulture | No findings at 80% confidence |

## Deployment Status

Engineering alpha is suitable for controlled evaluation. It must not yet be
represented as a regulated clinical production system or autonomous diagnosis tool.

Remaining deployment blockers:

1. Why Tree still uses an in-memory repository.
2. No formal database migration framework exists.
3. Authentication, tenant isolation, encryption-at-rest, and PHI governance are
   deployment responsibilities not yet implemented in this repository.
4. Shared output envelope exists, but tool-specific output schemas can be made more
   precise.
5. HFACS handler presentation constants still contain some legacy labels and should be
   fully normalized to the 2024 taxonomy.
6. SVG/PNG, Cytoscape, D3, and interactive HTML rendering are not bundled; current
   diagram output is Mermaid source plus structured graph data.
7. Raw document reading and clinical inference still consume Agent tokens. The next
   efficiency slice is a transactional/idempotent batch case bundle plus compact
   checkpoint/resume artifacts.

## Entry Points

- CLI / stdio: `uv run rootcause-mcp`
- Python: `rootcause_mcp.server_v2:main`
- Database: `${ROOTCAUSE_DATA_DIR:-data}/rca_sessions.db`
- Exports: `${ROOTCAUSE_DATA_DIR:-data}/exports/`
