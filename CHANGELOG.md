# Changelog

所有重要變更都會記錄在此檔案中。

格式基於 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.0.0/)，
專案遵循 [語義化版本](https://semver.org/lang/zh-TW/)。

## [Unreleased]

## [2.0.0a3] - 2026-08-19

### Added - Portable Copilot and VS Code startup

- Added a repository-native `.mcp.json` for Copilot CLI and Agent Host, alongside
  the VS Code workspace MCP definition, using one canonical `rootcauseMcp`
  identity and PATH-resolved `uv`.
- Added `scripts/mcp_doctor.py`, which validates both workspace configurations,
  launches the production stdio server, checks profile-specific catalog counts,
  and reads and parses both live clinical contracts.
- Added Ubuntu and Windows MCP startup CI covering generated-config drift,
  installer regressions, real SDK initialization, discovery, contract reads, and
  the PowerShell Copilot setup path.

### Changed - Host-safe installation and documentation

- Workspace configurations now use `uv run --locked` and resolve the repository
  from the execution host instead of persisting a developer-machine executable.
- The installer and shell wrappers now support the `copilot` target and
  `condensed` profile, fail closed on doctor errors, and explain that `uv` must be
  installed on the actual local, WSL, SSH, or dev-container extension host.
- Removed repository-local clinical data paths, reviewer allowlists, invalid
  debug metadata, and unrelated user-specific MCP definitions from the shared
  workspace configuration.
- Stopped tracking the legacy runtime SQLite database and generated report
  exports so new release source archives no longer package mutable case state.
  This tip-level cleanup does not rewrite earlier Git history.
- Updated the bilingual README, website, architecture guide, and Copilot
  instructions with Remote-host troubleshooting and safe restart guidance.

### Fixed - Windows and Remote extension hosts

- Fixed Copilot startup failing before MCP initialization with
  `spawn C:\\...\\uv.EXE ENOENT` when a Windows-specific executable path was
  evaluated on a different Remote extension host or no longer existed.
- Fixed the installer from regenerating host-specific absolute `uv` paths in
  committed workspace configuration.
- Replaced non-ASCII startup/status logging in Windows-sensitive paths so
  legacy console encodings cannot crash the server or installer before the MCP
  handshake.

This release remains an engineering alpha. These checks establish portable MCP
startup and deterministic artifact mechanics; they do not establish clinical
validity, diagnostic accuracy, or causality.

## [2.0.0a2] - 2026-08-18

### Added - Clinician-facing DDx contracts

- Added typed DDx classifications for mechanism category, diagnostic role,
  reasoning basis, and qualitative certainty, kept independent from numeric
  prior/posterior values.
- Added a typed differential-breadth audit with syndrome-appropriate built-in or
  custom frameworks, exact cell coverage, explicit insufficient-data handling,
  candidate linkage, typed planned discriminators, and a documented stop rule.
- Expanded the current catalog to 46 discrete tools in `all`, 25 in
  `clinical`, and 24 in `rca`; `condensed` remains 8 facade tools.
- Added built-in Markdown `locale="zh-TW"` and `audience="clinician"` output. The
  renderer localizes fixed explanatory copy while preserving persisted English
  medical names, quotations, codes, enums, JSON/FHIR data, and custom-template
  language.
- Added the general `clinician_ddx_discussion_zh_tw` MCP prompt and a focused,
  byte-identical clinician DDx reference for the Codex, Cline, and Claude
  harness mirrors.
- Added typed source-faithful time (`instant`, `date`, `range`, `relative`, or
  `unknown`) across evidence, timeline, persistence, MCP schemas, and final
  cross-ledger conformance. Only source-aware instants may support chronology.
- Added append-only source review/adjudication and explicit leading-hypothesis
  selection tools with persisted transition history.
- Added the complete typed `source_review_ledger` to final artifacts; final
  inventory projections, manifest binding, event counts, reviewer/time lineage,
  and append-only transitions are recomputed from that ledger.
- Added per-Fishbone-cause authorized HFACS `CONFIRMED` / `NOT_APPLICABLE`
  review lineage and a deterministic `HFACS_REVIEW_LINEAGE` final gate.

### Changed - Bounded clinical reasoning and release claims

- Changed the harness from a fixed-three DDx instruction to maximum reasonable
  mechanism-based breadth. Three unique diagnoses, two non-`UNKNOWN`
  mechanisms, and an applicable must-not-miss entry remain deterministic
  finalization floors, not the clinical target or cap.
- A final PRIMARY breadth audit must review every framework cell. A
  `REVIEWED_INSUFFICIENT_DATA` cell keeps decision-relevant unknowns and typed
  discriminators; `NOT_ASSESSED` remains incomplete, and coverage does not prove
  diagnostic correctness.
- Every active candidate now carries why considered, source-linked
  support/refutation/neutral evidence, candidate-specific unknowns, a genuine
  evidence/test disposition, and qualitative certainty. `LR=1.0` is neutral and
  no uncalibrated compatibility prior/posterior is presented as clinical
  probability or certainty.
- Non-neutral LRs now require a distinct verified `LITERATURE` calibration
  evidence record with exact source lineage; citation-looking free text cannot
  satisfy quantitative calibration. Neutral LR remains 1.0.
- Guidance and finalization now require an explicit ledger-valid leading
  selection. Array order and uncalibrated compatibility numbers cannot select
  the lead, rank FHIR conclusions, or change hard conformance.
- Updated the Agent integration guide, API reference, bilingual READMEs, harness
  instructions, and bilingual website for 2.0.0a2. The release remains an
  engineering alpha and is not clinically validated.
- Final multi-source conformance now counts independently acquired source roots
  rather than derivative files. Source manifests can declare independent/derived
  lineage, groups, parents, and derivation methods; unknown lineage blocks only
  finalization, not preliminary work.
- Bundled domain playbooks are now explicitly non-normative retrospective DDx
  prompts. Embedded patient-specific rescue steps and doses were removed from
  the packaged resources and report templates.

### Fixed - Report transport and epistemic labels

- Fixed the production SDK output contract so normal stdio `call_tool` accepts
  Markdown string content, and made dynamic session report resources render the
  built-in Traditional Chinese clinician view.
- Removed placeholder prior/posterior percentages from clinician and custom
  Markdown reports. Omitted priors use a neutral `0.5` uncalibrated internal
  baseline, non-neutral LR updates require an explicit rationale, and `LR=1.0`
  remains context-only.
- Source/date/time missingness remains typed unknown instead of being converted
  into a negative finding, a sortable synthetic timestamp, or an active-care
  instruction. Gap summaries, readiness facts, and conservative causation
  dispositions are recomputed from their underlying ledgers.
- Report IDs now retain the full session ID, evidence graphs treat neutral LR
  links separately, provenance wording stays inside the registered-source
  boundary, and resuscitation events no longer fall into the baseline timeline
  phase.
- The bilingual website reports the current table-driven hard-mutation set and
  now tests that its displayed count stays synchronized with the authoritative
  P0 parametrization table.
- Final snapshots now use immutable Mapping/Sequence wrappers that cannot be
  mutated through unbound `dict`/`list` base methods. Final JSON reloads require
  an operator-controlled reviewer allowlist context, and finalization rejects
  missing authorization or lifecycle time earlier than report generation.
- Domain playbooks and report templates now state their non-normative,
  retrospective scope; they do not provide active-care management,
  treatment/rescue instructions, patient-specific dosing, or automatic approval
  of proposed corrective actions.

### Added - Multi-source clinical reasoning acceptance (2026-08-17)

- Added the versioned `CaseInputManifest` contract and live MCP JSON Schema
  resources for multi-document input and unified case-analysis output.
- Added the RootCause clinical reasoning harness for Codex, Claude, and Cline,
  with a shared handoff contract, extraction boundary, direct-LR rules, PHI
  guardrails, readiness gates, and preliminary-first reporting workflow.
- Added a public MCP transport acceptance test covering three physical sources,
  exact provenance, canonical event time, a three-item DDx with a must-not-miss
  diagnosis, direct Bayesian updates, cognitive audit, Fishbone, 5-Why, HFACS,
  persisted causation review, preview, approval blocking, and unified report
  generation.
- Added a PHI/data-handling policy, runtime artifact ignore rules, secure export
  permissions, and Python 3.12/3.13 CI for quality, security, packaging, and
  installed-wheel smoke tests.
- Added typed nested CONTRACT-report sections and machine-readable
  `conformance_checks[]`, including deterministic source, DDx, root-lineage,
  disposition, reviewer, and final-integrity checks.
- Added typed pending diagnostic-test dispositions for active, leading, and
  must-not-miss hypotheses.
- Added a neutral six-case public Agent-eval corpus, reference rubrics, schemas,
  and a fail-closed runner scaffold. Public rubrics are explicitly non-blinded;
  formal evaluation requires repository-external private case bundles plus
  separately protected private holdout gold.

### Changed - Release boundaries and standardized output (2026-08-17)

- Unified CONTRACT output now carries the source inventory, DDx/evidence,
  timeline, reasoning and cognitive audit, Fishbone, Why/root causes, HFACS,
  causation results, conflicts/readiness, approval state, and artifact hashes.
- Finalization is now a gated, content-hashed snapshot. It requires complete
  reasoning readiness, no unresolved high/critical conflict, a reviewed
  multi-source manifest, persisted RCA artifacts, a causation-review attempt for
  each proposed root, and an operator-authorized approver. The domain snapshot
  recursively rejects mutation and carries a recomputable hash; durable WORM
  retention remains a deployment records-system responsibility.
- Causation validation is now documented and serialized as a conservative
  proof-obligation audit with `clinical_causality_established=false`, not as
  clinical causal proof. Rejected claims are removed from the root bucket and
  insufficient-data candidates remain proposed.
- Runtime data defaults to the operating system's user-data directory; packaged
  configuration is read-only and learned HFACS rules are written to user data.
- The six-case runner is explicitly a synthetic preliminary regression/demo and
  no longer claims release acceptance or final clinical validation.

### Fixed - Clinical correctness and provenance (2026-08-17)

- Fixed refuting evidence increasing posterior probability by inverting an
  already-applied LR; support now uses LR > 1, contradiction LR < 1, and
  omitted or quantitatively unknown LR is neutral at 1.0.
- Prevented duplicate evidence updates and removed synthetic reciprocal LR
  metadata that could falsely satisfy disconfirming-test readiness.
- Removed file-existence, location-only, blank-line, and reverse-containment
  provenance false positives. Only matched content or an allowlisted human
  confirmation can mark evidence verified.
- Filtered excluded/on-hold hypotheses from leading report and FHIR conclusions,
  while retaining them in the audit record.
- Fixed the async console entry point, installed-wheel configuration discovery,
  static-resource and template path traversal, checkpoint confinement/integrity,
  installer failure propagation, and unsafe package contents.

### Security - Dependency and artifact controls (2026-08-17)

- Raised runtime dependency floors to patched releases identified by the frozen
  lock audit and added a reproducible dependency-vulnerability gate.
- Constrained provenance reads, templates, exports, and checkpoints to approved
  roots; exports/checkpoints use atomic writes and restrictive POSIX permissions.
- Source distributions no longer ship runtime databases, exports, raw examples,
  editor configuration, or hook state.

### Quality - Acceptance baseline (2026-08-17)

- Added table-driven mutation probes that require every hard finalization
  invariant to fail closed, plus nested-schema/hash/immutability coverage.
- Test count, coverage, typing, security, dependency, packaging, and installed-wheel
  results are reported by the current CI/release run rather than hard-coded here.
  These engineering gates do not establish Agent clinical performance.

### Added - MCP SDK 2.0 Advanced Harness & Tool Condensation (2026-08-14)

- Added **Tool Condensation Profile** (`condensed` / `facade`) consolidating 43 discrete tools
  into **8 polymorphic facade tools** (`rc_evidence`, `rc_hypothesis`, `rc_thinking`, `rc_audit`,
  `rc_report`, `rc_diagram`, `rc_checkpoint`, `rc_rca`), reducing tool schema context consumption
  by **>80%** while preserving 100% discrete functionality via action-based dispatch.
- Added **MCP Static Resources** exposing clinical protocols, playbooks, and report templates
  under standard URIs (`clinical://protocols/*`, `clinical://domains/*`, `clinical://templates/*`)
  for zero-tool-call inspection by AI agents.
- Added **MCP Dynamic Session Resource Templates** (`clinical://sessions/{session_id}/report`,
  `clinical://sessions/{session_id}/timeline`, `clinical://sessions/{session_id}/guidance`,
  `clinical://sessions/{session_id}/conflicts`) for polling and inspecting case state without generating tool calls.
- Added **MCP Pre-Configured Clinical Prompts** (`anesthesia_mm_investigation`,
  `perioperative_crisis_differential`, `near_miss_barrier_analysis`, `delayed_diagnosis_investigation`)
  enabling one-click clinical RCA workflows in Claude Desktop, VS Code, and Cline.
- Injected **MCP Server-Level Instructions & Meta-Prompt** during connection handshake to anchor
  AI agents to rigorous source grounding, 4-tier backward causal reasoning, disconfirming hypothesis testing,
  and cognitive bias transparency.
- Expanded automated integration test suite (`tests/test_sdk_advanced_features.py`) verifying
  full MCP SDK 2.0 lifespan, tool profiling, resource reading, and prompt resolution.

### Added - Automated Installer & Clinical Trial Harness (2026-08-14)

- Added persistent `SQLiteWhyTreeRepository` with `WhyChainModel` and `CausalLinkModel`
  SQLModel tables, eliminating in-memory loss and enabling 100% restart rehydration
  for 5-Why analysis trees and causal feedback links.
- Added `ClinicalGapAnalyzer` domain service and `rc_detect_conflicts` MCP tool for
  automated detection of diagnostic contradictions, paradoxical drug reactions,
  and guideline monitoring omissions (e.g., MTP without K+/ABG, high-dose Propofol without lipids).
- Added `CaseCheckpointService` and snapshotting MCP tools (`rc_create_checkpoint`,
  `rc_restore_checkpoint`, `rc_list_checkpoints`) enabling agents to preserve
  integrity-checked state snapshots and resume/branch cases without context loss.
- Expanded tool catalog to 43 tools (23 clinical profile, 23 RCA profile, 43 all profile).
- Added subspecialty perioperative crisis playbooks: `anaphylaxis_crisis.yaml` (Anaphylaxis shock),
  `local_anesthetic_toxicity.yaml` (LAST Lipid rescue), and `difficult_airway_crisis.yaml` (CICO eFONA).
- Added cross-platform automated setup scripts:
  - `scripts/setup.ps1` (PowerShell for Windows)
  - `scripts/setup.sh` (Bash for Linux / macOS / WSL)
  - `scripts/install.py` (Universal Python CLI configurator)
- Added automatic registration across client hosts: VS Code (`.vscode/mcp.json`),
  Claude Desktop (`claude_desktop_config.json`), and Cline (`cline_mcp_settings.json`).
- Added preliminary regression/demo runner `scripts/run_case_trial.py` supporting
  6 multi-file case fixtures (`dynamic_lvot_obstruction_sam`,
  `pris_status_epilepticus`, `trauma_hyperkalemia_arrest`, `postop_pe_death`,
  `lvad_suction_event`, and `realistic_delayed_diagnosis`). It checks provenance
  and preview plumbing; it is not a release-acceptance or clinical-validity suite.
- Added `rc_validate_diagram` MCP tool for auditing, linting, and auto-sanitizing
  custom agent Mermaid diagram syntax with delimiter balancing and label escaping.
- Added `rc_render_timeline` MCP tool and 5 Clinical Timeline Patterns (`perioperative_sequence`,
  `acute_crisis`, `delayed_diagnosis`, `barrier_failure`, `device_incident`, `custom`, `auto`).
- Added Non-Death Adverse Event & Near Miss RCA template (`config/templates/near_miss_adverse_event_rca_template.md`),
  investigation protocol (`config/protocols/non_death_adverse_event_protocol.yaml`), and
  domain playbooks (`config/domains/lvad_mechanical_crisis.yaml`, `delayed_diagnosis_systems.yaml`).
- Expanded MCP tool catalog to 39 tools (19 clinical profile, 23 RCA profile, 39 all profile).
- Added deterministic Chronological Event Timeline & Mermaid timeline generation
  (`build_timeline`, `render_timeline_mermaid`, `render_timeline_table`) with clinical phase
  clustering and Markdown contract report integration (`{{timeline_diagram}}`, `{{timeline_table}}`).
- Added resilient alias normalization for `EvidenceStrength` (`PATHOGNOMONIC`, `CRITICAL`,
  `HIGH`, `STRONG`), `EvidenceReliability` (`GRADE_A`, `PRIMARY`, `DIRECT`),
  and `EvidenceType` (`LAB`, `IMAGING`, `DEVICE_LOG`, `MEDICATION`).
- Enhanced `rc_propose_hypothesis` and `rc_link_evidence_to_hypothesis` to support
  flexible agent rationale and direction/weight parameter aliases.
- Added customizable Markdown report templates (`config/templates/anesthesia_mm_rca_report_template.md`
  and `config/templates/clinical_reasoning_report_template.md`) with deterministic slot-filling
  via `template_file` parameter in `rc_generate_contract_report`.
- Added 4-Tier Anesthesiology backward causal protocol (`config/protocols/anesthesia_mm_rca_protocol.yaml`)
  and subspecialty playbooks (`config/domains/anesthesia_perioperative_arrest.yaml`,
  `perioperative_shock.yaml`, `toxicology_sedation.yaml`, `pediatric_opioid.yaml`).

### Added - Deterministic Provenance & Multi-Loop Guidance (2026-08-14)

- Added `ProvenanceVerifier` domain service for deterministic, zero-hallucination
  verification of evidence quotes against raw clinical documents (TXT, CSV, HL7, XML)
  with SHA-256 cryptographic digests and line location indexing.
- Added `ClinicalGuidanceService` and `ReasoningGuidance` value object to guide
  lightweight (Flash/mini) models through structured multi-turn completion
  (stages, readiness checklists, missing prerequisites, next prompt directives,
  and Socratic push questions).
- Added `rc_audit_reasoning_state` MCP tool to inspect case readiness before report
  generation (bringing total tools to 37: 17 clinical, 21 RCA, 37 all).
- Integrated automatic guidance payloads into `rc_add_evidence`,
  `rc_propose_hypothesis`, `rc_link_evidence_to_hypothesis`, `rc_think_aloud`,
  `rc_reflect`, and `rc_get_differential_diagnosis`.
- Added automated report warnings against premature diagnostic closure (<3
  differential hypotheses) and ungrounded/unverified evidence records.

### Added - Token-Efficient Reasoning Harness (2026-08-09)

- Added `clinical`, `rca`, and `all` tool profiles that constrain both advertised
  schemas and executable dispatch.
- Added compact SDK 2.0 text fallbacks while preserving complete authoritative
  `structuredContent`; verbose compatibility mode remains configurable.
- Added deterministic brief/standard/full Markdown clinical reasoning reports with
  ranked DDx, evidence matrix, uncertainty/bias review, structural warnings,
  quality metrics, reasoning audit, and Evidence Graph.
- Added exact regression byte proxies: clinical schema context is 48.4% smaller
  and synthetic structured-response text duplication is 99.7% smaller.
- Report responses declare deterministic generation and zero server-side LLM tokens.

### Added - Auditable Visualizations (2026-08-09)

- Added shared Mermaid presenters for Fishbone, Why Tree, Reasoning Chain, and
  CONTRACT Evidence Graph artifacts.
- Added deterministic evidence-graph `nodes` / `edges`, support/contradiction
  relationships, provenance labels, and graph-integrity warnings.
- Added 6M Ishikawa spine layout with causes and sub-causes.
- Added structural Mermaid regression tests and validated all four diagram types
  with Mermaid CLI 11.16.

### Fixed - Generated Artifacts (2026-08-09)

- Fixed `rc_export_reasoning_chain(format="mermaid")` returning prose Markdown
  under a misleading extension.
- Fixed CONTRACT include flags being ignored, removed unimplemented HTML, and
  replaced placeholder Markdown with deterministic report generation.
- Fixed duplicate Why Tree parent/cross-link lines and contradictory cause-type
  labels.
- Fixed unstable Python `hash()`-based custom diagnosis identifiers.
- Fixed coding-system validators that previously accepted malformed ICD-10 and
  SNOMED CT values.
- Moved FHIR presentation out of the Domain value object, preserved diagnosis
  coding systems, ranked conclusions, skipped malformed persisted diagnoses, and
  emitted FHIR JSON with a `.json` extension.
- Aligned package metadata and project URLs with the Apache-2.0 repository.
- Excluded ephemeral runtime exports from version control.

### Quality - Artifact and Token-Efficiency Audit (2026-08-09)

- 61 tests pass with 81.54% branch-aware coverage.
- Ruff, strict mypy for 76 source files, Bandit, Vulture, `uv lock --check`, and
  wheel/sdist builds pass.

### Fixed - Repository Audit (2026-08-09)

- Replaced the obsolete SDK 1.x test/entry path with MCP SDK 2.0 lifecycle tests.
- Fixed `server_v2` startup to use the real synchronous `Database` API.
- Replaced prefix routing with an explicit 36-tool dispatch registry.
- Added structured output envelopes and `output_schema` to all 36 tools.
- Connected Evidence, Hypothesis, ThinkingChain, and ReasoningChain repositories to
  the shared `ServerState` aggregate with restart rehydration.
- Replaced in-memory placeholder repositories with SQLModel persistence.
- Included real ThinkingChain metrics and content in CONTRACT reports.
- Constrained generated artifact paths to `ROOTCAUSE_DATA_DIR/exports`.
- Unified causation verification behind `CausationValidator`; unsupported
  counterfactual/mechanism claims are no longer marked fully verified.
- Restored `ClinicalConcept.to_fhir_coding()` and added auditable hypothesis status
  transitions.
- Added HFACS-MES 2024 codes while preserving legacy-code readability.
- Removed the unsupported SDK 1.x `server.py` and the obsolete legacy adapter.

### Quality - Repository Audit (2026-08-09)

- 48 tests pass, including MCP transport workflows and full aggregate restart tests.
- Branch-aware coverage gate passes at 80%.
- Ruff passes for `src` and `tests`.
- Strict mypy passes for 71 source files.
- Bandit medium/high severity scan passes.
- Vulture reports no findings at 80% confidence.

### 🎯 Major Release: v2.0.0-alpha (2026-08-09)

**核心定位轉向**：從「通用 RCA 工具」→「醫學推理專用 MCP Harness」

#### Added - Application Layer (2026-08-09)
- **ClinicalReasoningOrchestrator** 🆕
  - Agent-friendly API hiding medical complexity
  - Automatic Bayesian updating with likelihood ratios
  - Evidence quality auto-grading (Oxford CEBM)
  - Complete reasoning chain tracking
  - Summary statistics and quality metrics

#### Added - MCP Tools (2026-08-09)
- **15 New MCP Tools** for medical reasoning:
  - Cognitive Layer (5): `rc_think_aloud`, `rc_reflect`, `rc_identify_gaps`, `rc_challenge_assumption`, `rc_get_thinking_chain`
  - Evidence Management (3): `rc_add_evidence`, `rc_get_evidence`, `rc_verify_evidence`
  - Differential Diagnosis (4): `rc_propose_hypothesis`, `rc_link_evidence_to_hypothesis`, `rc_get_differential_diagnosis`, `rc_exclude_hypothesis`
  - Reasoning Chain (2): `rc_get_reasoning_chain`, `rc_export_reasoning_chain`
  - CONTRACT Report (1): `rc_generate_contract_report`

#### Added - Handlers (2026-08-09)
- **5 New Handlers** implementing all new tools:
  - `ThinkingHandlers` - Cognitive layer transparency
  - `EvidenceHandlers` - Evidence CRUD with quality grading
  - `DDHandlers` - Bayesian differential diagnosis
  - `ReasoningHandlers` - Reasoning chain management
  - `ContractHandlers` - CONTRACT report generation

#### Added - Persistence Layer (2026-08-09)
- **SQLite Repositories**:
  - `SQLiteEvidenceRepository` - Evidence persistence
  - `SQLiteHypothesisRepository` - Hypothesis persistence
  - `SQLiteThinkingChainRepository` - Thinking chain persistence

#### Added - Domain Layer (2026-08-09)
- **ContractReport VO** - Immutable, auditable report
  - `EvidenceCoverageMetrics` - Evidence quality metrics
  - `ReasoningQualityMetrics` - Reasoning quality metrics
  - FHIR export support
  - Content hash for immutability

#### Added - Testing (2026-08-09)
- **Smoke Test** (`tests/test_smoke.py`) - 8 tests, all passing
  - Tool loading and schema validation
  - Handler instantiation
  - Basic functionality tests
- **End-to-End Test** (`tests/test_e2e.py`) - 3 tests, all passing
  - Complete clinical reasoning workflow
  - Persistence layer functionality
  - ContractReport value object

#### Added - Core Architecture
- **MCP SDK 2.0 遷移** - 完全重寫，不相容 1.x
  - Typed input/output with Pydantic BaseModel
  - Structured content support (outputSchema)
  - Automatic validation with `validate_input=True`
  - Version bump: `mcp[cli]>=1.10.1` → `mcp>=2.0.0`

- **Evidence as First-Class Entity** 🆕
  - `domain/entities/evidence.py` - Structured evidence with provenance
  - `EvidenceQuality` VO - Oxford CEBM-inspired Strength × Reliability matrix
  - `EvidenceSource` - Chain of custody (who, when, where)
  - Many-to-many linking: Evidence ↔ Cause/Hypothesis
  - Independent verification workflow

- **Differential Diagnosis Engine** 🆕
  - `domain/entities/hypothesis.py` - Bayesian hypothesis with LR updating
  - Prior/posterior probability tracking
  - Likelihood ratio (LR) based evidence integration
  - Inclusion/exclusion criteria management
  - Bayesian update audit trail

- **Clinical Concept Standardization** 🆕
  - `domain/value_objects/clinical_concept.py` - Medical terminology VO
  - Support for SNOMED CT, ICD-10, RxNorm, LOINC, CPT
  - FHIR-compatible coding export
  - Regex validation for each coding system

- **Strong-Typed Identifiers** 🆕
  - `EvidenceId` (EVD-xxxxxxxx)
  - `HypothesisId` (HYP-xxxxxxxx)
  - `ReasoningStepId` (RS-xxxxxxxx)
  - Prevents ID mixing bugs at compile time

#### Changed
- **README.md 完全重寫** - 反映新定位
  - 新增 Mermaid 架構圖（5 層架構）
  - 新增 SVG 架構圖（`docs/architecture/medical_reasoning_harness.svg`）
  - 強調「Agent-friendly API」設計原則
  - 新增與現有工具對比表（DDx vs RCA vs RootCause MCP）
  - 27 個 MCP Tools 列表（19 現有 + 8 新增規劃）

- **版本號更新**: `0.1.0` → `2.0.0a1` (alpha)

#### Design Decisions
- 參考 [MEDDxAgent](https://github.com/nec-research/meddxagent) 的 DDxDriver 架構
- 參考 [ClinClaw](https://github.com/rbr7/ClinClaw) 的 Harness pattern
- 採用 [fastmcp](https://github.com/PrefectHQ/fastmcp) 作為 SDK 2.0 參考實作
- 保留自定義 schema，後續可選配 FHIR adapter

#### Documentation
- Memory Bank 更新：decisionLog.md, activeContext.md, progress.md
- 新增 `docs/architecture/medical_reasoning_harness.svg`
- 完整調查報告：GitHub 開源醫療 AI 專案全景（見對話記錄）

---

## [0.1.0] - 2026-01-16

### Added
- **Deep RCA Framework v2.0 架構設計** - 5 層分析架構 + 10 個新工具規劃
  - 設計文件：`docs/architecture/deep_rca_framework_v2.md` (794 行)
  - Layer 1: Evidence Gathering (現有 5-Why, Fishbone, HFACS)
  - Layer 2: Knowledge Enrichment (PubMed RAG, Case Matching)
  - Layer 3: Multi-Model Analysis (Swiss Cheese, Bowtie, Systems Dynamics)
  - Layer 4: Validation (Triangulation, Counterfactual, Expert Consensus)
  - Layer 5: Synthesis (Barrier Analysis, Priority Matrix, Report Generation)
- **擬真化測試案例** - `examples/realistic_delayed_diagnosis/`
  - 5 個模擬真實 HIS 資料的測試檔案（含噪音：咖啡訂單、停車通知、錯字）
  - 測試情境：44 天延遲肺癌診斷案例
- **Mermaid 圖表增強** - Fishbone 和 Why Tree 圖表優化
  - Fishbone: 魚頭/魚骨/分類/原因 4 種樣式
  - Why Tree: 5 層深度漸層色彩 + 根因標記
- **Export 自動存檔功能** - Fishbone/WhyTree 匯出時自動儲存至 `data/exports/{session_id}/`
  - 支援 Mermaid/Markdown (`.md`) 和 JSON (`.json`) 格式
  - 時間戳命名：`fishbone_20260116_010216.md`
  - 可在 VS Code 中直接預覽 Mermaid 圖 (需安裝 `bierner.markdown-mermaid`)
- **AHRQ WebM&M 測試案例**
  - `examples/ahrq_webmm_001_pediatric_opioid/case_rawdata.md` - 測試輸入
  - `examples/ahrq_webmm_001_pediatric_opioid/expert_commentary.md` - 專家解答
- **DDD 架構重構** - 將 2057 行 monolithic server.py 拆分為模組化結構
  - `interface/tools/` - 5 個 Tool 定義模組 (HFACS/Session/Fishbone/WhyTree/Verification)
  - `interface/handlers/` - 5 個 Handler 實作模組
  - `interface/server.py` - 精簡入口點 (~350 行)
- **Session-aware 進度追蹤機制**
  - `application/session_progress.py` - SessionProgressTracker 追蹤完成度
  - `application/guided_response.py` - GuidedResponseBuilder 引導式回應
  - 支援「逼問」(Push Questions) 機制引導 Agent 深入分析
- **18 個 MCP Tools 完整支援**
  - HFACS: `rc_suggest_hfacs`, `rc_confirm_classification`, `rc_get_hfacs_framework`, `rc_list_learned_rules`, `rc_reload_rules`
  - Session: `rc_start_session`, `rc_get_session`, `rc_list_sessions`, `rc_archive_session`
  - Fishbone: `rc_init_fishbone`, `rc_add_cause`, `rc_get_fishbone`, `rc_export_fishbone`
  - Why Tree: `rc_ask_why`, `rc_get_why_tree`, `rc_mark_root_cause`, `rc_export_why_tree`
  - Verification: `rc_verify_causation`

### Fixed
- **session_progress.py Bug 修復**
  - `FishboneCategory` 使用 `.has_causes` 和 `.cause_count` 屬性（非 len()）
  - `WhyChain.nodes` 是 list 不是 dict（移除 `.values()`）

### Changed
- **Ruff 程式碼格式化**
  - 所有 Handler 檔案 Import 排序標準化
  - 使用 `collections.abc.Sequence` 替代 `typing.Sequence`
- 更新 `pyproject.toml` 入口點指向 DDD server
- 保留 `rootcause-mcp-legacy` 入口點相容舊版

## [0.1.0] - 2025-12-15

### Added
- 初始化專案結構
- 新增 Claude Skills 支援
  - `git-doc-updater` - Git 提交前自動更新文檔技能
- 新增 Memory Bank 系統
  - `activeContext.md` - 當前工作焦點
  - `productContext.md` - 專案上下文
  - `progress.md` - 進度追蹤
  - `decisionLog.md` - 決策記錄
  - `projectBrief.md` - 專案簡介
  - `systemPatterns.md` - 系統模式
  - `architect.md` - 架構文檔
- 新增 VS Code 設定
  - 啟用 Claude Skills
  - 啟用 Agent 模式
  - 啟用自定義指令檔案
