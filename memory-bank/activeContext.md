# Active Context - RootCause MCP

> Last updated: 2026-08-14

## Current Focus

Mermaid syntax auditing, universal diagram verification (`rc_validate_diagram`), timeline pattern rendering (`rc_render_timeline`), and non-death near-miss adverse event RCA protocols are complete.

Verified Outcomes:

- `rc_validate_diagram` tool provides deterministic syntax auditing, bracket balancing, unescaped label quote sanitization, and diagnostics for custom agent Mermaid code.
- `rc_render_timeline` tool and `build_timeline()` support 5 clinical timeline patterns (`perioperative_sequence`, `acute_crisis`, `delayed_diagnosis`, `barrier_failure`, `device_incident`, `custom`, `auto`).
- `config/templates/near_miss_adverse_event_rca_template.md` provides specialized non-death RCA reporting with Swiss Cheese barrier failure analysis, NCC MERP severity grading, and error-proofing action plans.
- `scripts/run_case_trial.py` benchmark expanded to 6 multi-file clinical cases:
  1. `dynamic_lvot_obstruction_sam` (SAM perioperative shock arrest)
  2. `pris_status_epilepticus` (PRIS sedation toxicity shock)
  3. `trauma_hyperkalemia_arrest` (Trauma MTP hyperkalemia arrest)
  4. `postop_pe_death` (Post-op PE death from expired prophylaxis)
  5. `lvad_suction_event` (Non-death LVAD suction vs pump thrombosis device incident)
  6. `realistic_delayed_diagnosis` (Non-death lung cancer 44-day delayed diagnosis)
  - All 6 cases executed in **0.039s total** with 100% provenance verification across 31 heterogeneous raw files.
- Catalog expanded to **39 tools** (19 clinical, 23 RCA, 39 all).

## Quality Baseline

| Gate | Result |
| --- | --- |
| Tests | 72 passed |
| Coverage | 81.49% branch-aware |
| Ruff | Passed for `src`, `tests`, `scripts` |
| Mypy | Strict mode passed for all 94 source files |
| Bandit | Medium/high severity scan passed |
| Vulture | No findings at 80% confidence |
| Trials | 6/6 clinical benchmark cases passed (0.039s total) |

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
