# Active Context - RootCause MCP

> Last updated: 2026-08-09

## Current Focus

MCP SDK 2.0 medical reasoning harness audit and remediation is complete.

Verified state:

- 36 MCP tools with exact dispatch registry, `input_schema`, and output envelope
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
| Tests | 48 passed |
| Coverage | 80% branch-aware gate passed |
| Ruff | Passed for `src` and `tests` |
| Mypy | Strict mode passed for 71 source files |
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

## Entry Points

- CLI / stdio: `uv run rootcause-mcp`
- Python: `rootcause_mcp.server_v2:main`
- Database: `${ROOTCAUSE_DATA_DIR:-data}/rca_sessions.db`
- Exports: `${ROOTCAUSE_DATA_DIR:-data}/exports/`
