# Active Context - RootCause MCP

> Last updated: 2026-08-14

## Current Focus

MCP SDK 2.0 Advanced Harness Integration, Tool Condensation Profile (8 unified facade tools), SQLite WhyTree persistence, Case Checkpointing, Clinical Conflict Detection, and Cross-Platform Automation Suite are complete.

Verified Outcomes:

- **Tool Condensation Profile (`condensed`)**: Consolidates 43 discrete tools into 8 polymorphic facade tools (`rc_evidence`, `rc_hypothesis`, `rc_thinking`, `rc_audit`, `rc_report`, `rc_diagram`, `rc_checkpoint`, `rc_rca`), slashing tool schema token usage by >80%.
- **MCP Static Resources (`clinical://*`)**: Standard protocol, domain playbook, and report template resources accessible with 0 tool call overhead.
- **MCP Dynamic Session Resource Templates (`clinical://sessions/{session_id}/*`)**: Live reporting, timeline, reasoning state guidance, and conflict detection resources.
- **MCP Pre-Configured Prompts**: Clinical prompt templates (`anesthesia_mm_investigation`, `perioperative_crisis_differential`, `near_miss_barrier_analysis`, `delayed_diagnosis_investigation`) ready for one-click launch in client UIs.
- **Server-Level Instructions & Meta-Prompt**: Injected during MCP connection handshake.
- **Persistent `SQLiteWhyTreeRepository`**: 100% restart rehydration for 5-Why trees and causal feedback links.
- **Clinical Gap & Conflict Detection (`ClinicalGapAnalyzer`, `rc_detect_conflicts`)**: Automated detection of diagnostic contradictions, paradoxical drug reactions, and guideline omissions.
- **Case Checkpointing (`CaseCheckpointService`, `rc_create_checkpoint`, `rc_restore_checkpoint`, `rc_list_checkpoints`)**: Immutable JSON snapshots with SHA-256 digests.
- **Timeline Generator (`rc_render_timeline`) & Mermaid Syntax Auditor (`rc_validate_diagram`)**: Deterministic chronological event timeline and universal diagram sanitizer.
- **Cross-Platform Automated Setup**: `setup.ps1`, `setup.sh`, and `install.py` supporting auto-registration in VS Code, Claude Desktop, and Cline.
- **6-Case Benchmark Trials**: 100% physical provenance verification executed in 0.039s.

## Quality Baseline

| Gate | Result |
| --- | --- |
| Tests | 82 passed |
| Coverage | 80.73% branch-aware |
| Ruff | Passed (0 lint errors) |
| Mypy | Strict mode passed for all 102 source files |
| Bandit | Medium/high severity scan passed (0 findings) |
| Vulture | No findings at 80% confidence |
| Trials | 6/6 clinical benchmark cases passed (0.039s total) |

## Deployment Status

Engineering alpha is suitable for controlled evaluation. It must not yet be
represented as a regulated clinical production system or autonomous diagnosis tool.

Remaining deployment considerations:

1. No formal database migration framework exists (Alembic planned for multi-version schemas).
2. Authentication, tenant isolation, encryption-at-rest, and PHI governance are deployment responsibilities.
3. SVG/PNG, Cytoscape, D3, and interactive HTML rendering are client-side integrations; current diagram output is Mermaid source plus structured graph data.

## Entry Points

- CLI / stdio: `uv run rootcause-mcp`
- Python: `rootcause_mcp.server_v2:main`
- Database: `${ROOTCAUSE_DATA_DIR:-data}/rca_sessions.db`
- Exports: `${ROOTCAUSE_DATA_DIR:-data}/exports/`
