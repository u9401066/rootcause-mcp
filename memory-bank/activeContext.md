# Active Context - RootCause MCP

> Last updated: 2026-08-14

## Current Focus

Automated 1-click installation suite, multi-case clinical trial benchmark, resilient agent alias normalization, and strict 92-file typing verification are complete.

Verified Trial Run & Benchmark Outcomes:

- `scripts/run_case_trial.py` executes end-to-end multi-loop diagnostic trials across 2 god-level multi-file clinical cases:
  1. `dynamic_lvot_obstruction_sam`: Intraoperative shock worsening with Epinephrine across 5 raw files (TXT, CSV, XML). 100% provenance verification, top hypothesis P=1.000.
  2. `pris_status_epilepticus`: Propofol Infusion Syndrome misdiagnosed as sepsis/pancreatitis across 5 raw files. 100% provenance verification, top hypothesis P=1.000.
- `scripts/setup.ps1` (Windows PowerShell), `scripts/setup.sh` (Linux/macOS), and `scripts/install.py` (Universal Python CLI) configure:
  - `.vscode/mcp.json` (VS Code MCP Client)
  - `claude_desktop_config.json` (Claude Desktop)
  - `cline_mcp_settings.json` (Cline)
  - Self-check tests and automated trial validation in a single command.
- Resilient clinical alias normalization for `EvidenceStrength` (`PATHOGNOMONIC`, `CRITICAL`, `HIGH`, `STRONG`), `EvidenceReliability` (`GRADE_A`, `PRIMARY`, `DIRECT`), and `EvidenceType` (`LAB`, `IMAGING`, `DEVICE_LOG`, `MEDICATION`).
- Flexible agent parameters in `rc_propose_hypothesis` (`rationale` / `clinical_reasoning`) and `rc_link_evidence_to_hypothesis` (`direction` / `weight` / `likelihood_ratio`).

## Quality Baseline

| Gate | Result |
| --- | --- |
| Tests | 66 passed |
| Coverage | 81.33% branch-aware |
| Ruff | Passed for `src`, `tests`, `scripts` |
| Mypy | Strict mode passed for all 92 source files |
| Bandit | Medium/high severity scan passed |
| Vulture | No findings at 80% confidence |
| Trials | Both SAM and PRIS cases passed (0.016s combined) |

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
