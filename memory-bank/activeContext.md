# Active Context - RootCause MCP

> Last updated: 2026-08-14

## Current Focus

Automated 1-click installation suite, 4 god-level anesthesia/ICU benchmark trials, deterministic chronological event timeline generation, and 4-tier M&M backward causal reasoning are complete and verified.

Verified Trial Run & Benchmark Outcomes:

- `scripts/run_case_trial.py` executes end-to-end multi-loop diagnostic trials across 4 god-level multi-file clinical cases:
  1. `dynamic_lvot_obstruction_sam`: Intraoperative shock worsening with Epinephrine (SAM) across 5 raw files (TXT, CSV, XML). 100% provenance verification, top hypothesis P=1.000.
  2. `pris_status_epilepticus`: Propofol Infusion Syndrome misdiagnosed as sepsis/pancreatitis across 5 raw files. 100% provenance verification, top hypothesis P=1.000.
  3. `trauma_hyperkalemia_arrest`: Massive transfusion (MTP) older blood hyperkalemic cardiac arrest across 5 raw files (TXT, CSV, XML). 100% provenance verification, top hypothesis P=1.000.
  4. `postop_pe_death`: Post-THA pulmonary embolism PEA arrest due to expired/held DVT prophylaxis across 5 raw files. 100% provenance verification, top hypothesis P=1.000.
  - All 4 cases executed in **0.027s combined** with 100% exact line provenance matching across 21 heterogeneous raw files.
- Deterministic Chronological Event Timeline (`build_timeline`, `render_timeline_mermaid`, `render_timeline_table`) with clinical phase clustering (Baseline, Induction, Crisis, Diagnostics, Collapse) integrated into contract report templates.
- 4-Tier Anesthesiology backward causal protocol (`config/protocols/anesthesia_mm_rca_protocol.yaml`), domain playbooks (`config/domains/`), and customizable M&M conference report templates (`config/templates/`).
- `scripts/setup.ps1` (Windows PowerShell), `scripts/setup.sh` (Linux/macOS), and `scripts/install.py` (Universal Python CLI) configure VS Code, Claude Desktop, and Cline with self-check tests and automated trial validation.

## Quality Baseline

| Gate | Result |
| --- | --- |
| Tests | 69 passed |
| Coverage | 81.59% branch-aware |
| Ruff | Passed for `src`, `tests`, `scripts` |
| Mypy | Strict mode passed for all 94 source files |
| Bandit | Medium/high severity scan passed |
| Vulture | No findings at 80% confidence |
| Trials | 4/4 anesthesia benchmark cases passed (0.027s total) |

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
