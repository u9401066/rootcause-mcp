# System Architect

> 📌 此檔案記錄重大架構決策，架構變更時更新。

## 🌐 系統架構圖

```
┌─────────────────────────────────────────────┐
│              專案模板結構                      │
├─────────────────────────────────────────────┤
│  🏔️ 規則層                                        │
│  ┌─────────────┐                                  │
│  │ CONSTITUTION │ ───┐                             │
│  └─────────────┘     │                             │
│        │            ▼                             │
│        │     ┌────────────┐                        │
│        ├────▶│  Bylaws   │                        │
│        │     └────────────┘                        │
│        │            │                             │
│        ▼            ▼                             │
│  ┌───────────────────────┐                      │
│  │    Claude Skills      │                      │
│  └───────────────────────┘                      │
├─────────────────────────────────────────────┤
│  🧠 記憶層                                        │
│  ┌───────────────────────┐                      │
│  │     Memory Bank       │                      │
│  │  (7 markdown files)   │                      │
│  └───────────────────────┘                      │
├─────────────────────────────────────────────┤
│  ⚙️ 工具層                                        │
│  ┌────────┐ ┌─────────┐ ┌─────────┐           │
│  │ CI/CD  │ │ Testing │ │ Linting │           │
│  └────────┘ └─────────┘ └─────────┘           │
└─────────────────────────────────────────────┘
```

## 🏛️ 架構決策紀錄

### ADR-001: 採用憲法-子法層級架構

**日期**：2025-12-15

**背景**：需要一個清晰的規則層級系統

**決定**：採用憲法 → 子法 → Skills 三層結構

**理由**：
- 最高原則集中在 CONSTITUTION.md
- 細則可在 bylaws/ 擴展
- Skills 專注於操作程序

### ADR-002: DDD + DAL 獨立

**日期**：2025-12-15

**背景**：確保業務邏輯與資料存取分離

**決定**：Repository 介面在 Domain，實作在 Infrastructure

**理由**：
- 提高可測試性
- Domain 不依賴資料庫技術
- 可替換儲存實作

### ADR-003: uv 優先套件管理

**日期**：2025-12-15

**背景**：Python 套件管理工具選擇

**決定**：優先使用 uv，後備 pip

**理由**：
- 比 pip 快 10-100 倍
- 原生支援 lockfile
- 與 pip 完全相容

### ADR-004: ServerState 作為醫學推理 Aggregate Registry

**日期**：2026-08-09

**背景**：Evidence、Hypothesis、ThinkingChain、ReasoningChain 曾分散在各 Handler 的
in-memory store，造成跨工具斷鏈與重啟資料遺失。

**決定**：以 `ServerState` 管理每個 session 的 `ClinicalReasoningOrchestrator`，並透過
Domain repository contracts 注入 SQLModel repositories。

**理由**：
- 所有醫學推理工具共享同一 aggregate
- 支援完整 case rehydration
- Handler 維持薄介面層，不重複 Domain/Application 邏輯
- ContractReport 可從單一資料來源產生

**限制**：legacy Why Tree 仍使用 InMemory repository，列為下一個 persistence 工作。

### ADR-005: 圖表與交換格式使用 Interface Presenters

**日期**：2026-08-09

**背景**：Fishbone、Why Tree、Reasoning Chain 各自在 handler 內拼接 Mermaid，造成
重複 escaping、錯誤格式宣稱與難以驗證的版型；FHIR mapping 也混入 Domain VO。

**決定**：將 Mermaid 與 FHIR 映射集中在 Interface presenters。Domain 提供 typed
entities/value objects，Interface 負責 Mermaid/FHIR 表示，Infrastructure 僅處理安全路徑
與持久化。CONTRACT Evidence Graph 同時輸出 deterministic nodes/edges 與 Mermaid。

**理由**：
- 生成器可做純函式單元測試與 renderer-level 驗證
- Mermaid label escaping、node identity 與 graph integrity 使用單一規則
- Domain 不依賴 FHIR 或圖表格式
- MCP 核心不需內建 Chromium/Node renderer

**限制**：目前不直接產生 SVG、PNG、Cytoscape、D3 或互動 HTML。

### ADR-006: Token-Efficient SDK 2.0 Transport and Deterministic Reports

**日期**：2026-08-09

**背景**：通用 Agent 可直接完成長篇推理報告，但完整 36-tool schema、text/structured
payload duplication 與重新撰寫 structured state 會反覆消耗 context。

**決定**：
- 以 `clinical` / `rca` / `all` profiles 同時限制 tools/list 與 dispatch surface
- SDK 2.0 structured content 保留完整結果，預設 text 只提供 bounded summary
- 從 persisted aggregate deterministic 生成 brief/standard/full Markdown
- 使用 UTF-8 bytes 作為 tokenizer-independent regression proxy

**理由**：將格式化、排序、Bayesian arithmetic、quality metrics、graph generation 與
structural checks 移出 LLM，可降低重複 tokens 並提高跨 Agent 的一致性。

**限制**：raw 文件閱讀、臨床 hypothesis generation、LR 選擇與最終醫師審查仍不可由
deterministic harness 取代。Batch ingest 必須先具備 aliases、idempotency 與 rollback。

### ADR-007: 確定性證據溯源與 Flash 模型多輪導引狀態機

**日期**：2026-08-14

**背景**：輕量 Flash 模型易過早診斷收斂 (premature closure)、提出單一假說、忽略否定性排除；且 Agent 自行提取的證據若無實體檔案比對可能存在幻覺。

**決定**：
- 實作 `ProvenanceVerifier` 領域服務，直接比對磁碟實體文件（TXT, CSV, HL7, XML），產生行號與 SHA-256 密碼學錨定，不使用神經網路；
- 實作 `ClinicalGuidanceService` 狀態機，在每次工具呼叫中注入階段、清單、缺項警告與下一步 Prompt 指令；
- 新增 `rc_audit_reasoning_state` 工具，讓 Agent 能主動稽核完備度。

**理由**：
- 100% 確定性防幻覺，實現可追溯至 raw data 的硬性資料血緣；
- 讓低階模型在多輪對話中被外在約束引擎驅動，達到專家級完整思考鏈。

**限制**：RootCause MCP 專注於推理契約與血緣比對，不重疊 Asset-Aware MCP 的 PDF OCR/表格分割角色。

### ADR-008: Typed Final Conformance 與 Append-only Clinical Review Ledgers

**日期**：2026-08-18

**背景**：Top-level schema、caller-authored readiness、numeric compatibility、自由文字
citation 與未綁定的 HFACS suggestion 都可能讓形式完整但語意不一致的報告通過。

**決定**：
- Finalization 由 Domain 重新計算固定 hard checks，並要求 operator 提供 reviewer allowlist。
- Source review、leading diagnosis selection 與 HFACS cause review 使用 append-only persisted events。
- Evidence time 採 source-faithful typed temporal record；非中性 LR 必須 cross-link verified
  patient evidence 與 distinct verified literature calibration evidence。
- Final snapshot 使用完整 canonical payload hash（只排除 hash 欄本身）並遞迴凍結。

**理由**：讓 final artifact 的來源、DDx、時間、RCA、review 與呈現內容都能從同一 ledger
重算，避免 Agent 敘事或 transport order 取代臨床語意。

**限制**：Allowlist 是 deployment authorization input，不是完整 IAM/RBAC 或臨床資格
證明；content hash 也不是 digital signature 或 WORM records system。

## 📦 元件圖

```
.claude/skills/          # 12 個 Skills
├── git-precommit/       # 編排器
├── ddd-architect/       # 架構
├── code-refactor/       # 重構
├── code-reviewer/       # 審查
├── test-generator/      # 測試
├── memory-updater/      # 記憶
├── memory-checkpoint/   # 檢查點
├── readme-updater/      # README
├── changelog-updater/   # CHANGELOG
├── roadmap-updater/     # ROADMAP
├── project-init/        # 初始化
└── git-doc-updater/     # 文檔更新

.github/bylaws/          # 4 個子法
├── ddd-architecture.md
├── git-workflow.md
├── memory-bank.md
└── python-environment.md
```

---
*Last updated: 2026-08-09*
