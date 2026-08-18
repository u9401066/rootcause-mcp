# RootCause MCP

> Medical reasoning, differential diagnosis, and clinical RCA harness for any MCP-compatible AI agent.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![MCP SDK 2.0](https://img.shields.io/badge/MCP_SDK-2.0-green.svg)](https://modelcontextprotocol.io/)
[![Tools](https://img.shields.io/badge/MCP_tools-43_discrete_%2F_8_condensed-purple.svg)](#tool-catalog)
[![Status](https://img.shields.io/badge/status-engineering_alpha-orange.svg)](#mvp-status)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

**English** | [繁體中文](README.zh-TW.md)

## Mission

RootCause MCP enables general-purpose agents such as Claude Code, Codex, Cline,
OpenCode, OpenClaw, and Z.ai agents to perform a specialized workflow:

1. Inventory and extract de-identified clinical documents through the host agent.
2. Register source-grounded evidence and provenance with exact raw snippets.
3. Build and update differential diagnoses with Bayesian likelihood ratios.
4. Record explicit rationales, alternatives, uncertainty, and possible bias.
5. Connect diagnostic reasoning to Fishbone, 5-Why, HFACS-MES, and a conservative
   causation proof-obligation audit.
6. Produce a typed, machine-readable report with explicit source lineage and
   deterministic conformance results.

The **agent performs the reasoning**. The MCP server does not inspect hidden model
states or raw private chain-of-thought. It provides schemas, workflow constraints,
persistence, calculations, and audit records for reasoning the agent explicitly
chooses to externalize.

> This project is not a medical device and must not autonomously diagnose or treat
> patients. Clinical use requires qualified human review, local governance, privacy
> controls, and independent verification of source documents.

## MVP Status

The deterministic final-report boundary is implemented: nested report sections are
typed, every report carries machine-readable `conformance_checks[]`, and unsafe
finalization is blocked for source, DDx, root-lineage, causation-disposition,
reviewer, or integrity failures. Final snapshots carry a reviewer, timezone-aware
time, recomputable SHA-256 hash, and recursively reject mutation.

This is still an **engineering alpha**, not a clinically validated Agent MVP. The
public six-case corpus and runner are engineering references. A formal result
requires at least 3 real Agent runtimes × 6 cases × 2 repeats, repository-external
private case bundles, separately protected private holdout gold, filesystem
isolation, trusted runtime/server MCP traces, and two blinded qualified clinical
reviewers per job with adjudication of disagreement. That evaluation is currently
`AGENT_EVAL_NOT_ESTABLISHED`. See
[MVP conformance and evaluation](docs/mvp_conformance_and_evaluation.md).

## Why This Harness Saves Work

A general Agent can read every document and write a report in one long prompt. That
approach works, but repeatedly spends context on tool schemas, prior facts,
formatting, probability arithmetic, graph construction, completeness checks, and
report prose. RootCause MCP moves those repeatable operations into deterministic
code while leaving clinical judgment with the Agent.

| Work | Agent-only workflow | RootCause MCP assistance |
| --- | --- | --- |
| Tool context | Load all schemas | `clinical` / `rca` profiles expose only the relevant surface |
| Tool results | Re-read duplicate text and JSON | Complete SDK 2.0 `structuredContent` plus a compact text fallback |
| Probability updates | Recalculate and narrate | Deterministic Bayesian update with retained LR rationale |
| Case continuity | Re-inject earlier conversation | Persisted aggregate and restart rehydration |
| Report assembly | Rewrite DDx, evidence, gaps, metrics, and graphs | Deterministic `brief` / `standard` / `full` Markdown artifact |
| Quality review | Remember every checklist item | Automatic structural traceability warnings |

![Token-efficient medical reasoning](docs/architecture/token_efficient_reasoning.svg)

Tokenizer-independent regression fixtures compare tool-profile schema bytes,
duplicated text fallbacks, and deterministic report generation. Use the current CI
artifacts as the source of truth because schema changes alter those measurements.
These byte proxies are not promises about a specific model tokenizer. The Agent
still must read the source extracts, generate clinically plausible hypotheses,
choose defensible likelihood ratios, and review the final artifact.

## Multi-Loop Guidance for Lightweight (Flash) Models

Lightweight or fast models (such as Flash/mini variants) commonly struggle with
complex clinical cases: they tend to jump to conclusions, stop after a single
hypothesis (premature closure), neglect disconfirming tests, and skip cognitive
reflections.

RootCause MCP acts as an active **Reasoning State Machine**:

- Every core tool call returns a structured `guidance` payload evaluating the case state.
- **Stage Progression**: Automatically tracks progress through `EVIDENCE_COLLECTION` → `DIFFERENTIAL_EXPANSION` → `BAYESIAN_EVALUATION` → `COGNITIVE_AUDIT` → `READY_FOR_SYNTHESIS`.
- **Readiness Checklist**: Requires verified source content, at least three unique competing diagnoses, an applicable must-not-miss diagnosis, evidence/test disposition for every active diagnosis, support plus contradiction or a typed rule-out plan for leading/must-not-miss diagnoses, and explicit uncertainty/bias review.
- **Next Prompt Directives**: Provides explicit `next_recommended_actions` with exact tool names and Socratic `push_questions` in each response, allowing Flash agents to loop iteratively until the case is complete.
- **Audit Tool**: Agents or external orchestrators can call `rc_audit_reasoning_state` at any turn to inspect remaining prerequisites before report generation.

## Deterministic Provenance and Data Lineage

Inspired by data integration and ETL lineage architectures (such as Airbyte's stream/source verification models), RootCause MCP establishes deterministic, cryptographic evidence grounding without relying on probabilistic LLM memory:

- **Verbatim Snippets & Lineage Anchors**: Evidence records capture exact `raw_snippet` quotes, file paths, line locators, and SHA-256 digests.
- **Deterministic Provenance Verification**: The `ProvenanceVerifier` domain service scans physical raw files on disk (TXT, CSV, HL7, XML) to verify substring matches and line numbers without invoking an LLM.
- **Tamper & Hallucination Detection**: If an agent invents a quote, references an unavailable source, or presents a source whose bytes no longer match the pinned manifest, the server keeps the evidence unverified and returns audit diagnostics.
- **Clean Architecture Boundary**: RootCause MCP focuses on reasoning contracts and
  provenance checks; it does not parse raw PDF, DOCX, image, scan, spreadsheet, or
  EHR-export batches.

The host agent or an approved extractor must produce citation-ready text/cells while
preserving exact content, source locations, hashes, units, negation, time precision,
OCR corrections, and extraction method. Send only structured atomic findings into
RootCause MCP, and do not claim MCP verification for binary or inaccessible sources.

## Protocol Resources, Templates & 4-Tier Anesthesia M&M Reasoning

The packaged YAML protocols and domain playbooks are versioned MCP resources that
the bundled agent harness tells agents to read. Markdown templates are deterministic
rendering inputs. Runtime readiness thresholds and gap rules are still implemented
in Python; editing a protocol YAML alone does **not** change those gates.

- **Configurable SOP & Domain Playbooks (`config/protocols/`, `config/domains/`)**:
  - `anesthesia_mm_rca_protocol.yaml`: 4-Tier backward causal framework (Tier 0 Terminal Rhythm → Tier 1 ACLS 5H5T → Tier 2 Tri-stream Triggers [Patient baseline vs Surgical insult vs Anesthesia pharmacology] → Tier 3 HFACS Latent System Gaps).
  - `perioperative_shock.yaml` & `toxicology_sedation.yaml`: Domain criteria for Dynamic LVOT Obstruction (SAM) and Propofol Infusion Syndrome (PRIS).
- **Customizable Markdown Templates (`config/templates/`)**:
  - `anesthesia_mm_rca_report_template.md`: Specialized departmental M&M conference review format with deterministic slot filling.
  - `clinical_reasoning_report_template.md`: General clinical reasoning and patient safety action report.

## Architecture

```mermaid
graph TB
    A[General-purpose AI Agent] -->|MCP SDK 2.0| T[8 facade or 23 / 23 / 43 discrete tools]
    D[Clinical documents] --> A

    subgraph Harness
        T --> S[ServerState / case aggregate]
        S --> O[ClinicalReasoningOrchestrator]
        O --> E[Evidence + provenance + hash]
        O --> H[Hypotheses + Bayesian updates]
        O --> R[ReasoningChain]
        O --> G[Clinical Guidance Engine]
        S --> C[ThinkingChain: explicit rationale records]
    end

    E --> DB[(SQLite / SQLModel)]
    H --> DB
    R --> DB
    C --> DB

    S --> CR[CONTRACT report]
    CR --> J[JSON]
    CR --> F[FHIR-compatible DiagnosticReport]
    CR --> M[Deterministic Markdown]

    T --> RCA[Fishbone / 5-Why / HFACS-MES / conservative causation audit]
```

![Medical reasoning harness architecture](docs/architecture/medical_reasoning_harness.svg)

The dependency direction follows DDD:

```text
Interface -> Application -> Domain <- Infrastructure
```

## What Is Persisted

The SDK 2.0 server persists the medical reasoning aggregate in SQLite:

- Structured Evidence and source metadata
- Differential-diagnosis hypotheses and Bayesian update history
- Explicit ThinkingStep records supplied by the agent
- ReasoningStep audit records generated by the orchestrator
- RCA sessions, source manifests, Fishbone diagrams, and Why Trees

Authentication, encryption-at-rest, tenant isolation, reviewer-role authorization,
database migrations, and regulated deployment controls must be supplied by the
deployment environment before clinical production use. See the
[PHI and clinical-data policy](docs/PHI_DATA_POLICY.md).

## Quick Start & Automated Installation

### 🚀 One-Click Automated Setup

You can automatically detect `uv`, synchronize virtual environments, configure client MCP harnesses (`.vscode/mcp.json`, Claude Desktop, Cline), and run self-diagnostic checks with a single command:

**Windows PowerShell:**

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
```

**Linux / macOS / WSL:**

```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

**Universal Python CLI:**

```powershell
uv run python scripts/install.py --profile all --target all
```

### 🔬 Scripted Synthetic Case Regression

Run the six bundled synthetic scenarios (SAM, PRIS, transfusion hyperkalemia,
post-operative PE, LVAD suction, and delayed diagnosis). This script is a developer
regression/demo, not a substitute for the native manifest/finalization acceptance
tests or clinical validation:

```powershell
uv run python scripts/run_case_trial.py --case all
```

### Agent Evaluation Scaffold

The public corpus dry-run checks runner/artifact mechanics only and deliberately
returns `AGENT_EVAL_NOT_ESTABLISHED`:

```bash
eval_output="$(mktemp -d)"
uv run python scripts/run_agent_eval.py dry-run \
  --output-root "$eval_output" \
  --repeats 2
```

Formal runs must use repository-external private cases and separately protected
private gold. Start with the fail-closed preflight:

```bash
uv run python scripts/run_agent_eval.py \
  --preflight \
  --matrix /secure/adapter-matrix.json \
  --corpus-file /secure/private-corpus/corpus.json \
  --gold-dir /secure/private-holdout \
  --attest-holdout-isolation \
  --authorize-provider-egress
```

See the [evaluation protocol](docs/mvp_conformance_and_evaluation.md) before any
formal run. Egress authorization applies only to approved de-identified synthetic
inputs, never real clinical records or PHI.

### 🛠️ Manual Installation & Server Launch

```powershell
# Install the locked environment
uv sync --all-extras

# Run the MCP SDK 2.0 stdio server
uv run rootcause-mcp
```

VS Code `.vscode/mcp.json`:

```json
{
  "servers": {
    "rootcause-mcp": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "rootcause-mcp"],
      "cwd": "${workspaceFolder}"
    }
  }
}
```

Environment variables:

| Variable | Purpose | Default |
| --- | --- | --- |
| `ROOTCAUSE_DATA_DIR` | SQLite database, checkpoints, learned rules, and generated exports | OS user-data directory |
| `ROOTCAUSE_CONFIG_DIR` | Optional configuration override containing `hfacs/`, `domains/`, `protocols/`, `templates/` | Packaged `rootcause_mcp/config` |
| `ROOTCAUSE_SOURCE_ROOTS` | OS-path-separated allowlist of roots for exact plain-text provenance checks | Current working directory |
| `ROOTCAUSE_AUTHORIZED_REVIEWERS` | Comma-separated operator-controlled identities allowed to manually verify/finalize | Empty (manual/final approval disabled) |
| `ROOTCAUSE_TOOL_PROFILE` | Tool catalog: `condensed` (8 facade tools), `clinical` (23), `rca` (23), or `all` (43) | `all` |
| `ROOTCAUSE_RESPONSE_MODE` | `compact` structured fallback or `verbose` JSON text | `compact` |

## Agent Workflow

A compatible agent can use either the discrete tool workflow or the ultra-compact 8-facade workflow:

### Discrete Tool Workflow

```text
rc_start_session(source_manifest={...})
  -> rc_add_evidence
  -> rc_think_aloud / rc_identify_gaps / rc_challenge_assumption
  -> rc_propose_hypothesis(planned_tests=[...])
  -> rc_link_evidence_to_hypothesis
  -> rc_get_differential_diagnosis
  -> rc_get_reasoning_chain
  -> rc_detect_conflicts
  -> rc_create_checkpoint
  -> rc_verify_causation  # conservative audit, not clinical causal proof
  -> rc_generate_contract_report(format="markdown", detail_level="standard", finalize=false)
```

### Ultra-Compact Facade Workflow (8 Tools Profile)

```text
rc_rca(action="session_start")
  -> rc_evidence(action="add")
  -> rc_thinking(action="think" / "gap" / "challenge" / "reflect")
  -> rc_hypothesis(action="propose" / "link" / "rank")
  -> rc_audit(action="stage_guidance" / "detect_conflicts")
  -> rc_checkpoint(action="create")
  -> rc_diagram(action="timeline" / "validate")
  -> rc_report(action="preview")
```

`rc_propose_hypothesis` (or `rc_hypothesis(action="propose")`) requires the agent to provide clinical rationale,
alternatives considered, supporting evidence, uncertainty factors, and confidence
rationale. These are explicit agent-authored records, not a dump of hidden model
reasoning.

See [Agent Integration Guide](docs/agent_integration_guide.md) for payload examples.

## MCP SDK 2.0 Advanced Features

RootCause MCP leverages the full spectrum of MCP SDK 2.0 primitives to deliver maximum agent ergonomics:

### 1. 🧰 Tool Condensation (8 Unified Facade Tools)

When using `ROOTCAUSE_TOOL_PROFILE=condensed`, the advertised surface is consolidated
into **8 polymorphic facade tools**, reducing discovery/schema overhead. A few
administrative operations remain discrete-only; the bundled harness lists the exact
mapping and hands the same session to an appropriate profile instead of silently
skipping them:

- `rc_evidence`: Add, get, or verify physical provenance.
- `rc_hypothesis`: Propose, link evidence, get differentials, update, or exclude.
- `rc_thinking`: Record clinical rationale, reflect on cognitive bias, identify gaps, or challenge assumptions.
- `rc_audit`: Query multi-loop guidance, audit reasoning completeness, or detect contradictions/omissions.
- `rc_report`: Generate deterministic contract reports or export audit artifacts.
- `rc_diagram`: Render chronological event timelines, audit Mermaid syntax, or export graphs.
- `rc_checkpoint`: Create, list, or restore integrity-checked case state snapshots.
- `rc_rca`: Route traditional Fishbone (6M), 5-Why trees, and HFACS-MES taxonomy workflows.

### 2. 📚 MCP Static & Dynamic Resources

Inspect domain knowledge and case states with **0 tool call overhead**:

- **Static Protocol & Template URIs**:
  - `clinical://contracts/case-input-manifest`: canonical multi-source handoff schema.
  - `clinical://contracts/case-analysis-report`: canonical standardized output schema.
  - `clinical://protocols/anesthesia-mm-rca-protocol`: 4-Tier backward causal reasoning SOP.
  - `clinical://protocols/clinical-reasoning-sop`: Core diagnostic investigation playbook.
  - `clinical://templates/anesthesia-mm-rca-report-template`: Markdown report template.
  - `clinical://templates/near-miss-adverse-event-rca-template`: Swiss Cheese & barrier failure template.
  - `clinical://domains/*`: 7 perioperative subspecialty crisis playbooks (`perioperative-shock`, `anaphylaxis`, `last-toxicity`, `difficult-airway`, `lvad-crisis`, `delayed-diagnosis`, `trauma-hyperkalemia`).
- **Dynamic Case Resource Templates**:
  - `clinical://sessions/{session_id}/report`: Current rendered case report.
  - `clinical://sessions/{session_id}/timeline`: Current chronological event timeline.
  - `clinical://sessions/{session_id}/guidance`: Live reasoning stage, checklist, and Socratic push questions.
  - `clinical://sessions/{session_id}/conflicts`: Live contradiction, paradox, and omission audit.

### 3. 🎯 MCP Pre-Configured Clinical Prompts

Launch standardized clinical investigation workflows with one click in Claude Desktop, VS Code, or Cline:

- `anesthesia_mm_investigation`: 4-Tier Backward Anesthesia M&M investigation.
- `perioperative_crisis_differential`: Crisis differential expansion with 5H5T triage.
- `near_miss_barrier_analysis`: Swiss Cheese non-death adverse event barrier RCA.
- `delayed_diagnosis_investigation`: Diagnostic trajectory and cognitive bias investigation.

### 4. 🧠 Server-Level Instructions & Meta-Prompt

The server automatically supplies system-level meta-instructions during the MCP handshake, anchoring AI agents to rigorous source grounding, 4-tier backward causal reasoning, disconfirming hypothesis testing, and cognitive bias transparency.

## Tool Catalog

| Category | Count | Purpose |
| --- | ---: | --- |
| Cognitive transparency | 5 | Explicit rationale, reflection, gaps, assumptions, thinking-chain retrieval |
| Evidence & Provenance | 3 | Add, retrieve, and verify structured evidence with raw snippets and SHA-256 hash |
| Differential diagnosis | 4 | Propose, update, rank, and exclude hypotheses with Bayesian likelihood ratios |
| Reasoning chain & guidance | 3 | Retrieve audit action chain, export diagrams, and audit reasoning completion |
| Gap Analysis & Conflict Detection | 1 | Detect diagnostic contradictions, paradoxical drug responses, and monitoring omissions |
| Case Checkpointing | 3 | Create, restore, and list integrity-checked JSON case snapshots |
| CONTRACT report | 1 | Generate preliminary or gated-final JSON, FHIR-compatible, or deterministic Markdown output |
| HFACS-MES Taxonomy | 6 | Suggest, confirm, inspect, learn, reload, and map classifications |
| Session Management | 4 | Start, retrieve, list, and archive RCA sessions with SQLite persistence |
| Fishbone (Ishikawa 6M) | 4 | Initialize, add causes, inspect, and export |
| Why Tree (5-Why Analysis) | 6 | Ask why, inspect, cross-link, mark root causes, export, and teach (SQLite-persisted) |
| Verification & Diagrams | 3 | Conservative causation audit, Mermaid syntax auditor, and timeline renderer |
| **Total (Discrete)** | **43** | Exposes 43 discrete tools across `all`, 23 in `clinical`, 23 in `rca`, or **8 unified facades** in `condensed` |

## Visualization Outputs

| Artifact | Machine-readable output | Diagram output |
| --- | --- | --- |
| Fishbone | JSON | Mermaid 6M Ishikawa layout with spine, causes, and sub-causes |
| Why Tree | JSON | Mermaid hierarchy with root causes and cross-causal links |
| Reasoning Chain | JSON | Mermaid ordered audit trail with evidence/hypothesis references |
| Evidence Graph | CONTRACT JSON `nodes` / `edges` | Embedded Mermaid support/contradiction graph |
| Event Timeline | JSON `events` / Markdown table | Mermaid `timeline` with clinical phases & timestamps |

## Quality Gates

The repository and CI define these engineering gates:

```powershell
uv run pytest -W error::ResourceWarning
uv run ruff check .
uv run ruff format --check .
uv run mypy src --ignore-missing-imports
uv run bandit -c pyproject.toml -r src --severity-level low --confidence-level medium
uv run vulture src tests --min-confidence 80
uv export --frozen --no-dev --no-emit-project --no-hashes --quiet --output-file requirements-audit.txt
uvx --from "pip-audit==2.9.0" pip-audit --strict --requirement requirements-audit.txt
uv build
uvx --from "twine==6.2.0" twine check dist/*
```

Use the current CI run and release artifacts as the source of truth for test counts,
coverage, security findings, and packaging results. These engineering gates validate
software behavior; they do not establish Agent clinical performance or clinical
validity.

## Project Layout

```text
src/rootcause_mcp/
├── domain/          # Entities, value objects, repository contracts, services
├── application/     # Case aggregate, orchestration, progress guidance
├── infrastructure/  # SQLModel repositories and safe export paths
├── interface/       # MCP tool schemas and handlers
└── server_v2.py     # Sole MCP SDK 2.0 entry point
```

## Documentation

- [Architecture](ARCHITECTURE.md)
- [Deep reasoning architecture](docs/architecture/deep_reasoning_architecture.md)
- [MCP API reference](docs/api.md)
- [Agent integration guide](docs/agent_integration_guide.md)
- [MVP conformance and Agent evaluation](docs/mvp_conformance_and_evaluation.md)
- [RootCause agent harness](.codex/skills/rootcause-clinical-reasoning-harness/SKILL.md)
- [PHI and clinical-data policy](docs/PHI_DATA_POLICY.md)
- [Existing solutions research](docs/research/existing_solutions.md)
- [Roadmap](ROADMAP.md)
- [Changelog](CHANGELOG.md)

## Research and Attribution

The design references publicly available work including MEDDxAgent, ClinClaw,
HFACS-MES, Oxford CEBM concepts, FHIR conventions, and the MCP Python SDK. See the
[research survey](docs/research/existing_solutions.md) for licenses and design notes.

## License

Apache License 2.0. See [LICENSE](LICENSE).
