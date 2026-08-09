# Changelog

所有重要變更都會記錄在此檔案中。

格式基於 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.0.0/)，
專案遵循 [語義化版本](https://semver.org/lang/zh-TW/)。

## [Unreleased]

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
- **10 New MCP Tools** for medical reasoning:
  - Evidence Management (3): `rc_add_evidence`, `rc_get_evidence`, `rc_verify_evidence`
  - Differential Diagnosis (4): `rc_propose_hypothesis`, `rc_link_evidence_to_hypothesis`, `rc_get_differential_diagnosis`, `rc_exclude_hypothesis`
  - Reasoning Chain (2): `rc_get_reasoning_chain`, `rc_export_reasoning_chain`
  - CONTRACT Report (1): `rc_generate_contract_report`

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
