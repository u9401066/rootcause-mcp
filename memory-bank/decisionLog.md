# Decision Log - RootCause MCP

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-15 | 漸進式輸入設計 (Level 1/2/3) | 降低使用門檻，自然語言優先 |
| 2026-01-15 | HFACS 自動建議機制 | AI 協助分類，但由人確認 |
| 2026-01-15 | MVP 聚焦 10 核心工具 | 35 工具過多，先驗證核心價值 |
| 2026-01-15 | 不儲存 PHI/PII | 合規要求，只保留結構化分析資料 |
| 2026-01-15 | SQLite + SQLModel | 輕量、跨平台、易部署 |
| 2026-01-15 | DDD 分層架構 | 業務邏輯與基礎設施分離 |
| 2026-01-15 | 移除 owlready2，改用規則引擎+Agent | 4年無更新，Agent 語義能力更強 |
| 2026-01-15 | 多框架支援 (HFACS-MES, Fishbone, WHO ICPS) | 讓 Agent 根據場景選擇適合框架 |
| 2026-01-15 | YAML-based Keyword Rules System | 規則可維護、可學習、可擴展 |
| 2026-01-15 | **「推論式」RCA 取代「填表式」** | 避免流於形式，引導真正根因探索 |
| 2026-01-15 | Counterfactual Testing Framework | 因果驗證 4 準則:時序、必要性、機轉、充分性 |
| 2026-01-16 | **重新定位專案價值主張** | AI能秒答≠不需要工具。重點是將AI洞察轉化為可稽核、可協作、可累積的組織智慧 |
| 2026-08-09 | **MCP SDK 1.x → 2.0 升級** | 不考慮 1.x 相容；typed BaseModel input/output；McpError 統一錯誤處理 |
| 2026-08-09 | **Evidence as First-Class Entity** | `list[str]` 改為結構化 Evidence（來源、品質、雙向連結），法律稽核需求 |
| 2026-08-09 | **Differential Diagnosis Tree** | 新增 Hypothesis entity + Bayesian LR 更新機制，取代 0/1 確認 |
| 2026-08-09 | **Externalized Reasoning Audit Persistence** | ReasoningStep 持久化 Agent 主動提供的 rationale／decision record；不擷取或要求模型隱藏 chain-of-thought |
| 2026-08-09 | **CONTRACT-level Report** | 提供 deterministic、content-hashed 的統一報告 snapshot 與 FHIR-like presenter；finalized 不等於 WORM storage |
| 2026-08-09 | **Evidence Quality Grading** | Oxford CEBM 啟發的 Strength×Reliability 二維品質矩陣 |
| 2026-08-09 | **DB: JSON array 儲存 ID 關聯** | 不用外鍵 JOIN，SQLite 效能 + 彈性，Evidence↔Cause many-to-many |
| 2026-08-09 | **🔴 深度審計發現 P0 缺陷** | server_v2 路由對 5 個舊 handlers 呼叫不存在的 `handle()` → 19/36 tools 運行時 AttributeError；Orchestrator 未整合；3 個新 repos 是死代碼。詳見審計報告 |
| 2026-08-09 | **P0/P1 審計缺陷完成修復** | 36-tool registry、aggregate persistence、真實 ContractReport、保守因果驗證與品質閘門皆已完成 |
| 2026-08-09 | **不宣稱醫療 production-ready** | 工程品質閘門通過，但 Why Tree persistence 與 deployment security/governance 尚未完成 |
| 2026-08-09 | **MCP 僅保存外顯推理記錄** | Agent 才是推理主體；ThinkingStep 是 agent-authored rationale，不宣稱擷取模型隱藏 chain-of-thought |
| 2026-08-09 | **圖表採 Mermaid source + structured graph** | 保持 MCP transport 輕量、跨 client 可預覽；SVG/PNG/HTML renderer 留作 optional integration，不在核心 server 內啟動瀏覽器 |
| 2026-08-09 | **FHIR mapping 屬 Interface presenter** | Domain 保留臨床概念與報告狀態，FHIR JSON、system URI 與容錯映射由 Interface 負責，維持 DDD 依賴方向 |
| 2026-08-09 | **Token efficiency 是核心產品契約** | 使用 tool profiles、compact structured transport、persisted state 與 deterministic report automation，避免 Agent 重複載入/重算/重寫；不宣稱省去 raw 病歷閱讀與臨床判斷 |
| 2026-08-14 | **8 Facade Tools Profile (`condensed`)** | 將 43 個離散工具濃縮為 8 個多型 Facade 工具，降低 >80% Tool Schema Token 消耗，並透過 action 多型派發保留 100% 功能 |
| 2026-08-14 | **MCP Static Resources (`clinical://*`)** | 支援零 Tool Call 讀取臨床協議、專科 Playbook 與 Markdown 報告範本 |
| 2026-08-14 | **MCP Dynamic Session Resource Templates** | 支援透過 URI 即時訂閱與檢驗案例報告、時序圖、推理導引與衝突清單 |
| 2026-08-14 | **MCP Pre-Configured Clinical Prompts** | 提供麻醉 M&M、危機鑑別、Near Miss 屏障與延遲診斷 4 大臨床 Prompt 範本 |
| 2026-08-14 | **Server-Level Instructions & Meta-Prompt** | 連線握手時自動注入系統級臨床推理 Meta-Prompt，鎖定 4-Tier 倒推因果與證據血緣 |
| 2026-08-14 | **SQLite WhyTree 持久化** | 實作 `SQLiteWhyTreeRepository` 與 `WhyChainModel`，消除 WhyTree 記憶體遺失缺陷 |
| 2026-08-14 | **臨床衝突與遺漏檢測 (`ClinicalGapAnalyzer`)** | 確定性偵測診斷矛盾、藥物反常惡化反應與臨床指引監測遺漏 (`rc_detect_conflicts`) |
| 2026-08-14 | **完整性保護案例快照 (`CaseCheckpointService`)** | 支援帶 SHA-256、session binding 與受限路徑的案例狀態快照與分支實驗 (`rc_create_checkpoint`, `rc_restore_checkpoint`)；不宣稱為 WORM storage |
| 2026-08-14 | **確定性時序圖與 Mermaid 語法稽核** | 支援 5 種臨床時間軸模式 (`rc_render_timeline`) 與通用圖表語法修復 (`rc_validate_diagram`) |
| 2026-08-14 | **確定性證據溯源 (Deterministic Provenance)** | Evidence 可綁定 raw snippet 與 SHA-256，由 ProvenanceVerifier 在 allowlisted roots 比對支援的純文字來源；這只證明片段匹配，不證明臨床解讀正確，也不負責 PDF OCR/表格分割 |
| 2026-08-14 | **Flash 模型多輪導引狀態機** | 輕量模型易提早收斂與漏項；ClinicalGuidanceService 在每次工具回傳中注入 stage、checklist、missing prerequisites 與 next prompt，引導 Flash 模型在多輪對話中循序完成完整臨床思考鏈 |
| 2026-08-14 | **臨床範本與 Agent-readable Playbook 體系** | 支援 allowlisted Markdown 報告範本、SOP 與次專科手冊 resources；目前只有部分 HFACS YAML 有 runtime consumer，其他規則變更仍可能需要程式修改 |
| 2026-08-14 | **麻醉專科 4-Tier 倒推因果框架** | 針對術中死亡/重症案例，禁止停留在終末停跳表面，強制執行 4-Tier 逆推：Tier 0 (終末心律) → Tier 1 (ACLS 5H5T) → Tier 2 (術中三方觸發流：病人體質 vs 外科機械 vs 麻醉藥理) → Tier 3 (HFACS 系統漏洞) |
| 2026-08-14 | **WhyTree 持久化升級 (SQLiteWhyTreeRepository)** | 解決 WhyTree 僅存於記憶體的已知限制；實作 SQLModel `WhyChainModel` 與 `CausalLinkModel`，達到 100% 重啟還原 |
| 2026-08-14 | **自動化衝突與指引缺口偵測 (ClinicalGapAnalyzer)** | 實作 `ClinicalGapAnalyzer` 領域服務與 `rc_detect_conflicts` 工具，自動偵測診斷矛盾、反常藥物反應與危急值監測遺漏 |
| 2026-08-14 | **個案快照與分支恢復 (CaseCheckpointService)** | 實作 `CaseCheckpointService` 與快照工具 (`rc_create_checkpoint`, `rc_restore_checkpoint`)，以路徑限制、SHA-256、session binding 與原子寫入保護跨輪恢復 |
| 2026-08-17 | **多來源先建立 manifest，再登錄 atomic evidence** | 每份來源使用穩定 document ID、whole-file SHA-256、媒體型別與處理狀態；來源覆蓋缺口必須出現在標準報告，不能由 Agent 敘事補齊 |
| 2026-08-17 | **Bayesian API 接受 direct applied LR** | 支持證據通常 LR >= 1、反證 LR <= 1、中性／無可靠定量值使用 1.0；server 不倒數 LR，也不從單一 observation 偽造 LR+/LR- 配對 |
| 2026-08-17 | **內容驗證不等於檔案存在** | 只有 exact/安全 normalized snippet match，或 operator allowlist 中具名 reviewer 的明確人工確認，才能標記 evidence verified；location/file existence 僅是未驗證 metadata |
| 2026-08-17 | **標準報告採 unified read model 與 gated final snapshot** | 同一產物聚合 DDx、provenance、timeline、認知安全、Fishbone、5-Why、HFACS、因果稽核與 readiness；finalization 產生 approval/hash，但真正 write-once retention 由部署 records system 負責 |
| 2026-08-17 | **MCP 不負責 raw binary ingestion** | PDF/DOCX/image/EHR batch 由 host 或經核准 extractor 產生 citation-ready spans；RootCause 只接收結構化 atomic findings，不能把 inaccessible binary 宣稱為已驗證 |
| 2026-08-17 | **protocol/domain YAML 目前是 Agent-readable 規格，不是完整 runtime policy engine** | readiness、gap 與 timeline 部分規則仍在 Python；文件不得宣稱修改 YAML 一定改變執行結果。未來需 versioned PolicyCatalog、session pin 與 policy digest |
| 2026-08-17 | **不得把工程 alpha 宣稱為自主診斷或臨床 production system** | 人工審閱、RBAC、tenant isolation、encryption-at-rest、retention、正式 migration 與受監管驗證仍是 production 前置條件 |
| 2026-08-17 | **Final report 必須 deterministic recompute，不信任 Agent 自報 PASS** | Typed nested schema、完整 `conformance_checks[]`、root/audit lineage、DDx/test disposition、reviewer/time/hash 與 recursive immutability 共同構成 fail-closed final boundary |
| 2026-08-17 | **Public eval corpus 不是 blinded case/gold** | 正式 Agent MVP 評估需要 repo 外 private case bundle、分離的 private holdout、至少三個真實 runtime、可信 server/proxy trace、36 個 clean-root jobs，以及每個 job 兩名 clinical reviewers 盲評與分歧裁決；目前為 `AGENT_EVAL_NOT_ESTABLISHED` |
| 2026-08-18 | **Unknown 與來源時間是 typed evidence，不是陰性或假 chronology** | Evidence 使用 `instant/date/range/relative/unknown`；只有來源自帶 offset 的 instant 可排序或支持 temporality，其他狀態合法保留為 unpositioned |
| 2026-08-18 | **Final clinical semantics 必須由 explicit ledger state 決定** | Leading diagnosis 由 append-only selection event 指定；非中性 LR cross-link verified LITERATURE calibration evidence；source 與 HFACS review 均需 allowlisted reviewer，不能信任 array order、caller citation 或 suggestion |
| 2026-08-18 | **2.0.0a2 仍標示 engineering alpha** | Deterministic conformance 可證明 artifact mechanics 與 unsafe finalization 阻擋，不證明 unseen-case DDx、臨床有效性或 causal truth；formal private 36-run 與雙 clinician 盲評仍未建立 |
| 2026-08-19 | **共享 MCP 設定必須由 execution host 解析** | VS Code／Copilot workspace config 只保存 portable `uv` 與 locked project launch；不得提交單一開發機 absolute executable、repo-local clinical data root 或 reviewer identity。Remote／Windows／Linux 啟動由 MCP doctor 與跨平台 CI 驗證 |

---

## [2026-08-09] v2.0.0-alpha 深度審計結果

### 審計發現摘要（Critical）

1. **server_v2 路由損壞（P0）**：Fishbone/HFACS/Session/Verification/WhyTree 5 個舊 handlers 無 `handle(tool_name, args)` dispatcher，server_v2.py:258-278 呼叫 `.handle()` 必然 AttributeError。19/36 tools (53%) 在 production 不可用。
2. **MCP SDK API 錯誤（P0）**：`CallToolResult(isError=...)` 應為 `is_error`（server_v2.py:280,303）。
3. **回傳型別二分法（P0）**：新 handlers 回傳 `dict`，舊 handlers 回傳 `Sequence[TextContent]`，server_v2 只處理 dict/str 分支。
4. **ClinicalReasoningOrchestrator 未整合（P0）**：server_v2.py:69 import 但從未實例化；DDHandlers/EvidenceHandlers 重複實作其邏輯且各自維護獨立 in-memory stores。
5. **ReasoningHandlers 死路（P1）**：`_reasoning_chains` 無寫入路徑，`rc_get_reasoning_chain` 永遠 not_found。
6. **3 個新 Repositories 是死代碼（P1）**：SQLiteEvidence/Hypothesis/ThinkingChainRepository 無 domain interface、無 handlers 使用、僅被 test_e2e 以 `None` db 實例化 → Evidence/Hypothesis/ThinkingChain 全無持久化。
7. **CausationValidator 290 行未被使用（P1）**：VerificationHandlers 重新實作 temporality/necessity 測試。
8. **ContractHandlers 空殼（P1）**：回傳硬編碼假資料，ContractReport VO 136 行未被使用。
9. **Hypothesis 狀態機不完整（P1）**：ON_HOLD 無 setter；`mark_excluded(excluded_by, reason)` 丟棄 audit 參數；CONFIRMED 無對應 tool。
10. **clinical_concept.py:99 unreachable code（P2）**：`__str__` return 後的 to_fhir_coding 邏輯成死代碼，FHIR 轉換方法丟失。
11. **測試崩潰（P0）**：test_mcp_tools.py import 舊 server.py（SDK 1.x decorator API）→ collection 階段 AttributeError。覆蓋率 46.13%（要求 80%）。
12. **靜態分析**：ruff 673 errors、mypy 75 errors、vulture 大量 60% confidence dead code。

### 審計評分

| 維度 | 分數 |
|------|------|
| 程式碼品質 | 3/10 |
| 安全性 | 7/10 |
| 架構合規 | 4/10 |
| 測試覆蓋 | 3/10 |
| 文檔同步 | 5/10 |
| **總分** | **4.4/10** |

---

## [2026-08-09] Contract-Level DD 架構設計

### 背景

現有 Evidence 機制為自由文字串列（`list[str]`），無來源追蹤、無品質評估、無雙向連結。
MCP SDK 將從 1.x 升至 2.0，需要同步進行架構升級。

### 新增核心 Domain 物件

| Entity/VO | 類型 | 職責 |
|-----------|------|------|
| `Evidence` | Entity | 結構化證據（來源、品質、連結） |
| `Hypothesis` | Entity | DD 假說（Bayesian 機率、inclusion/exclusion criteria） |
| `ReasoningStep` | Entity | Agent 外顯 rationale／決策稽核步驟（不含隱藏 chain-of-thought） |
| `EvidenceQuality` | Value Object | Strength × Reliability 品質矩陣 |
| `ClinicalConcept` | Value Object | SNOMED/ICD-10 概念封裝 |
| `ContractReport` | Value Object | gated、content-hashed CONTRACT 報告 snapshot |

### SDK 2.0 遷移策略

1. 所有 tool input 換成 typed `BaseModel`（SDK 2.0 原生支援）
2. 所有 tool output 換成 typed `BaseModel`（CONTRACT enforcement）
3. `raise ValueError` → `raise McpError(INVALID_PARAMS, msg)`
4. 新增 8 個 Evidence/DD/Reasoning tools（總計 27 tools）
5. 舊 `Cause.evidence: list[str]` 保留但 deprecate，漸進遷移

### 遷移分支策略

- 分支：`feat/sdk-2-contract-level-dd`
- Phase 1-2（環境+Tool遷移）：Day 1-4
- Phase 3-5（新Domain層）：Day 3-8
- Phase 6-8（新Tools+測試+文件）：Day 7-13

---

## [2026-01-16] 專案價值主張重新定位

### 問題背景

使用者質疑：**「AI agent已經能瞬間推理出根本原因，那這個RCA工具還有什麼價值？」**

這是一個核心存在性問題。如果AI（如Claude Sonnet 4.5）可以在30秒內找出根因，為何還需要結構化工具？

### 初始回應的盲點

原本的價值主張聚焦在「AI輔助分析」，但這暗示了：
- AI 本身不夠好，需要輔助
- 工具主要是提升AI能力

這是**錯誤的**。現代LLM的推理能力已經超越許多人類專家。

### 關鍵洞察

使用者的挫折感揭示了真相：

> "人類專家都要想一下的都被秒解答，這樣RCA淪為AI的文書作業"

**問題不在於「找到答案」，而在於「如何防禦答案」。**

### 重新定位

| 舊定位 | 新定位 |
|--------|--------|
| AI-guided structured RCA | Transform AI insights into auditable organizational intelligence |
| 提升AI分析能力 | 讓AI洞察變得可稽核、可協作、可累積 |
| 輔助找根因 | 建立可防禦30年的證據鏈 |

### 核心價值重構

RootCause MCP 的真正價值在於：

1. **🔒 法律盔甲 (Legal Armor)**
   - AI說「這是根因」→ 法庭不認可
   - 結構化報告+方法論證明 → 符合標準

2. **👥 協作基板 (Collaboration Substrate)**
   - 個人AI對話 → 各說各話
   - 共享Fishbone → 多科別共識

3. **📚 知識圖譜 (Knowledge Graph)**
   - AI對話結束 → 知識消失
   - learned_rules.yaml → 組織記憶

4. **🎓 教育框架 (Educational Scaffold)**
   - AI給答案 → 左耳進右耳出
   - 引導式5-Why → 批判性思考內化

5. **🧪 驗證層 (Verification Layer)**
   - AI推理 → 黑盒
   - Counterfactual testing → 可檢驗

### 類比說明

| 領域 | AI能力 | 但仍需工具 |
|------|--------|-----------|
| 法律 | Claude可寫法律意見書 | 但要用Case Management System |
| 會計 | Claude可做財務分析 | 但要用QuickBooks產生正式報表 |
| **RCA** | **Claude可找根本原因** | **但要用Fishbone產生稽核報告** |

### 新的Slogan

```
"AI can find the answer in 30 seconds. 
 We help you defend it for 30 years."
```

### README重寫策略

將README重構為三部分：

1. **Why This Matters** (前置)
   - 直接回答「AI都能秒答了為何還需要工具」
   - 對比表：AI推理 vs RCA工具
   - 真實情境：法庭、M&M會議、組織學習

2. **What We Do** (功能)
   - 5大價值主張
   - 技術特性

3. **When to Use** (適用情境)
   - ❌ 不適用：個人學習、非監管環境
   - ✅ 適用：稽核、團隊、訴訟、教學

### 影響

- README.md 完全重寫
- README.zh-TW.md 同步更新
- 未來溝通都以「可防禦性」為核心訴求

### 結論

**這個專案的價值不在於「找到答案」，而在於「證明答案」。**

AI是推理引擎，RCA工具是證據鏈建構器。兩者互補，缺一不可。
---

## [2026-01-15] 漸進式輸入設計

### 背景

用戶在使用 RCA 工具時，需要決定是用代碼 (HFACS-A123) 還是自然語言描述原因。

### 選項

1. 只接受結構化代碼 - 精確但門檻高
2. 只接受自然語言 - 易用但難分類
3. **漸進式設計** - 自然語言必填，代碼選填 + 系統建議

### 決定

採用選項 3：漸進式輸入

### 設計

- **Level 1 (必填)**: `description` 自然語言
- **Level 2 (建議)**: `hfacs_code` 系統自動建議，用戶確認
- **Level 3 (進階)**: `evidence`, `confidence`, `verified`

### 影響

- `rc_add_cause` 增加 HFACS suggestion 回傳
- 需建立 keyword → HFACS mapping

---

## [2026-01-15] MVP 範圍限制

### 背景

spec_v2 定義了 35 個 MCP Tools，但一次實作全部風險過高。

### 決定

Phase 1 MVP 聚焦 10 核心工具：

1. `rc_create_session`
2. `rc_set_problem`
3. `rc_add_cause`
4. `rc_ask_why`
5. `rc_get_fishbone`
6. `rc_get_analysis_tree`
7. `rc_suggest_next`
8. `rc_validate_chain`
9. `rc_export_report`
10. `rc_list_sessions`

### 理由

- 覆蓋完整分析流程
- 可驗證核心價值
- 降低初期複雜度

---

## [2026-01-15] 移除 owlready2，改用規則引擎 + Agent 分類

### 問題背景

原 spec 規劃使用 `owlready2` 進行 HFACS 本體推理，但該套件已 4 年無更新。

### 選項評估

| 方案 | 複雜度 | 維護性 | 說明 |
|------|--------|--------|------|
| A. owlready2 + Pellet | 高 | ❌ 4年無更新 | 完整 OWL 推理 |
| B. rdflib + 自建規則 | 中 | ✅ 活躍維護 | 需自己實現推理 |
| C. 純 Python 規則引擎 | 低 | ✅ 完全掌控 | YAML 規則 |
| **D. 規則引擎 + Agent** | 低 | ✅ 最佳 | Agent 處理語義 |

### 最終決定

採用 **方案 D: 規則引擎 + Agent 分類**

### 架構設計

```
Layer 1: Rule Engine (Fast Path) ⚡
  - YAML 規則匹配 (keywords, patterns)
  - 高信心度直接返回

Layer 2: Agent Classification (Smart Path) 🧠
  - 返回完整分類上下文給 Agent
  - Agent 使用其語義理解能力分類
  - 結構化回應

Layer 3: Feedback Loop (Learning Path) 📚
  - 確認的分類存入 learned_rules.yaml
  - 系統逐漸自我進化
```

### 優點

- ✅ 無過時依賴
- ✅ 規則透明可審核
- ✅ Agent 語義能力碾壓傳統 embedding
- ✅ 系統可自我學習進化

### 影響

- 從 `pyproject.toml` 移除 `owlready2`
- 建立 `config/hfacs/` 目錄結構
- 新增 MCP Tools: `rc_suggest_hfacs`, `rc_confirm_hfacs`

---

## [2026-01-15] 多框架支援架構

### 問題背景

HFACS 有多個變體 (原始版、Healthcare 版、MES 版)，加上 WHO ICPS、Fishbone 等框架，需要讓系統支援多種分類方式。

### 決定

建立多框架支援架構，讓 Agent 根據場景選擇適合的框架。

### 支援框架

| 框架 | 檔案 | 複雜度 | 適用場景 |
|------|------|--------|----------|
| HFACS-MES | `hfacs_mes.yaml` | 高 | 深度系統分析 |
| Fishbone 6M | `fishbone_6m.yaml` | 低 | 快速分類 |
| WHO ICPS | `who_icps.yaml` | 中 | 標準化報告 |

### 檔案結構

```
config/hfacs/
├── frameworks.yaml      # 框架總覽與選擇規則
├── hfacs_mes.yaml       # HFACS-MES (5層25類)
├── fishbone_6m.yaml     # Fishbone 6M
└── who_icps.yaml        # WHO ICPS (10類別)
```

### 選擇邏輯

- 預設: Fishbone 6M (簡單易用)
- 警訊事件: HFACS-MES (深度分析)
- 國際報告: WHO ICPS (標準化)

### 文獻參考

主要依據 **Jalali et al. 2024 (PMID:38394116)** 的 HFACS-MES 框架，該研究：
- 經 Delphi 法驗證
- 用 180 個醫療不良事件驗證因果路徑
- 新增第 5 層「組織外部因素」
- 新增 6 個因素類別

詳見: `docs/literature_review_clinical_rca.md`

---

## [2026-01-15] YAML-based Keyword Rules System

### 問題背景 (Keyword Rules)

原本的 `HFACSSuggester` 將關鍵字規則 hardcoded 在 Python 程式碼中，不易維護和擴展。

### 決定 (Keyword Rules)

建立 YAML-based 關鍵字規則系統：

1. **keyword_rules.yaml** - 領域規則 + 配置
   - 麻醉相關 keywords (基於文獻回顧 Section 7)
   - 通用醫療 keywords
   - 匹配配置 (min_confidence, max_suggestions 等)

2. **learned_rules.yaml** - 學習規則
   - Agent 確認後寫入
   - Session 分析批次學習
   - 人工策展

3. **HFACSSuggester 重構**
   - 從 YAML 動態載入規則
   - 支援多來源 (base, domain, learned)
   - 規則優先級：learned > domain > base

### 學習機制設計

| 方式 | 觸發 | 說明 |
| ---- | ---- | ---- |
| Agent 學習 | `rc_confirm_classification` | 用戶確認後 Agent 寫入 |
| Session 學習 | 批次處理 | 從 verified Cause 提取 |
| 人工策展 | PR 審核 | 專家新增專業術語 |

### 檔案結構 (Keyword Rules)

```text
config/hfacs/
├── keyword_rules.yaml    # 領域規則
├── learned_rules.yaml    # 學習規則
├── frameworks.yaml       # 框架選擇器
├── hfacs_mes.yaml        # HFACS-MES (含 keywords)
├── fishbone_6m.yaml      # Fishbone 6M (含 keywords)
└── who_icps.yaml         # WHO ICPS
```

### 優點 (Keyword Rules)

- ✅ 規則可讀、可審核
- ✅ 系統可自我學習進化
- ✅ 領域專家可直接貢獻
- ✅ 版本控制追蹤變更

---

## [2026-01-15] Session-aware Tools + 引導式問答

### 問題背景 (Guided RCA)

目前的 Tools 設計是「被動式」：
- Agent 決定何時呼叫哪個 tool
- 沒有進度追蹤
- 沒有引導下一步

這導致分析可能不完整，Agent 可能過早停止。

### 使用者洞察

> "讓 agent 每次 call 的時候就被告知已完成多少步驟，以及現在的答案，
> 同時填入這個答案的下一個問題（逼問，除非覺得是真因就填結束詞）"

### 決定 (Guided RCA)

實作 **Session-aware Guided Response** 機制：

每個 Tool 回應包含：
1. **進度指標** - 已完成步驟 / 總步驟
2. **當前狀態** - 目前的答案/分析結果
3. **下一問題** - 引導性問題（逼問）
4. **是否結束** - 若認為是根因則標記結束

### Response Schema

```python
{
    "result": {...},           # 原本的回傳
    "session_progress": {
        "completed_steps": 3,
        "total_expected": 8,
        "current_stage": "WHY_ANALYSIS",
        "completion_rate": "38%"
    },
    "current_state": {
        "fishbone_coverage": "66%",  # 6M 填了幾個
        "why_depth": 3,              # 問了幾層 Why
        "root_causes_found": 0       # 已識別根因數
    },
    "next_action": {
        "required": true,
        "tool": "rc_ask_why",
        "question": "為什麼 '護理師未使用計算輔助工具'？請繼續追問。",
        "hint": "思考：是訓練不足？系統故障？還是時間壓力？"
    },
    "is_complete": false,
    "completion_criteria": [
        "❌ Why 分析深度 < 3 (目前: 3)",
        "❌ 尚未標記任何根本原因",
        "❌ Fishbone 尚有空白類別: Monitoring"
    ]
}
```

### 影響 (Guided RCA)

- 所有 Tools 需要回傳統一的引導結構
- 需要 Session 層級的進度追蹤
- 重構 server.py 以支援此機制

---

## [2026-01-15] server.py DDD 模組重構

### 問題背景 (DDD Refactor)

`server.py` 已膨脹至 2000+ 行，違反單一職責原則：
- Tool 定義 (list_tools)
- Tool 路由 (call_tool)
- 18 個 Handler 實作
- 輔助函數

### 決定 (DDD Refactor)

按 DDD 分層重構：

```
src/rootcause_mcp/
├── interface/              # 表現層 (MCP 介面)
│   ├── __init__.py
│   ├── server.py          # MCP Server 入口 (~100 行)
│   ├── tools/             # Tool 定義
│   │   ├── __init__.py
│   │   ├── hfacs_tools.py
│   │   ├── session_tools.py
│   │   ├── fishbone_tools.py
│   │   └── why_tree_tools.py
│   └── handlers/          # Tool 實作
│       ├── __init__.py
│       ├── hfacs_handlers.py
│       ├── session_handlers.py
│       ├── fishbone_handlers.py
│       └── why_tree_handlers.py
│
├── application/           # 應用層 (Use Cases)
│   ├── __init__.py
│   ├── session_service.py     # Session 進度追蹤
│   ├── guided_response.py     # 引導式回應生成
│   └── rca_orchestrator.py    # RCA 流程編排
│
├── domain/               # (現有)
└── infrastructure/       # (現有)
```

### 優點 (DDD Refactor)

- ✅ 每個模組 < 300 行
- ✅ 職責清晰
- ✅ 易於測試
- ✅ 易於擴展

---

## [2026-01-15] 「推論式」RCA 取代「填表式」

### 問題背景 (Why Tree)

原系統設計聚焦於分類和記錄（Fishbone + HFACS），但缺乏引導用戶進行真正的根因推論。用戶可能只是：
1. 填入一個原因
2. 選擇/確認一個 HFACS 代碼
3. 結束分析 → **流於形式**

### 使用者洞察

> "覺得問題點應該是怎樣推論找原因ㄝ? 不然只會流於形式作業填一個碼就結束了?"
> — 使用者反饋 (2026-01-15)

### 決定 (Why Tree)

實作 **5-Why Analysis** 作為核心推論引擎，從「填表式」轉為「推論式」RCA。

### 新增工具

| 工具 | 功能 | 說明 |
|------|------|------|
| `rc_ask_why` | 迭代問 Why | 核心推論工具，最多 5 層 |
| `rc_get_why_tree` | 取得分析樹 | 階層視覺化 |
| `rc_mark_root_cause` | 標記根因 | 結束分析 |
| `rc_export_why_tree` | 匯出格式 | Mermaid/JSON/Markdown |

### 設計原則

1. **強制深入**：鼓勵至少問 3 次 Why
2. **保留證據**：每個 Why 可附加 evidence
3. **信心分數**：根據證據強度調整
4. **可視化**：Mermaid 圖表呈現推論鏈

### 儲存決定

Why Tree 使用 **InMemory 儲存**（而非 SQLite），因為：
- Why 分析是對話過程，非長期資料
- 簡化架構，快速迭代
- 最終結果可整合到 Fishbone/Cause

---

## [2026-01-15] Counterfactual Testing Framework

### 問題背景 (Verification)

找到可能的原因後，如何驗證它確實是「真正的原因」而非只是「相關」？

### 選項評估 (Verification)

| 方法 | 說明 | 適用性 |
|------|------|--------|
| A. 統計相關性 | 需要大量數據 | ❌ 個案分析不適用 |
| B. 專家判斷 | 主觀、難標準化 | ⚠️ 可作為補充 |
| C. **Counterfactual Testing** | 反事實推理 | ✅ 適合個案分析 |

### 決定 (Verification)

採用 **Counterfactual Testing Framework**，實作 4 個驗證準則：

### 4 準則設計

| 準則 | 問題 | 說明 |
|------|------|------|
| **Temporality** | 因先於果？ | 時間序列檢查 |
| **Necessity** | 無因則無果？ | 反事實必要性 |
| **Mechanism** | 有合理因果路徑？ | 機轉可解釋性 |
| **Sufficiency** | 因足以產生果？ | 單因素充分性 |

### 驗證層級

| 層級 | 測試 | 適用情境 |
|------|------|----------|
| Standard | Temporality + Necessity | 快速驗證 |
| Comprehensive | 全部 4 個 | 深度驗證 |

### 實作

新增 `rc_verify_causation` 工具，Agent 可引導用戶逐步驗證因果關係。

### 優點 (Verification)

- ✅ 結構化驗證，減少主觀偏差
- ✅ 標準化流程，可重現
- ✅ 教育意義，提升分析品質
- ✅ 區分「相關」與「因果」

| 2026-08-09 | 核心定位轉向：從「通用 RCA 工具」→「醫學推理專用 MCP Harness」 | 1. **獨特性**：市場上沒有同時整合 DDx + RCA 的工具
2. **核心價值**：讓任意通用 AI Agent 都能執行專業級醫學推理分析
3. **技術路線**：MCP Server + Harness = 醫學推理「賦能層」，不是另一個診斷引擎
4. **設計原則**：Agent-friendly API（隱藏 Bayesian/FHIR/HFACS 複雜度）
5. **參考架構**：MEDDxAgent (DDxDriver) + ClinClaw (Harness pattern) + fastmcp (SDK 2.0) |
| 2026-08-09 | MCP SDK 2.0 遷移策略：採用回調式 API（on_list_tools, on_call_tool） | SDK 2.0 完全移除 @server.list_tools() 和 @server.call_tool() decorator，改為在 Server.__init__() 傳入回調函數。需要重寫 server.py：

舊 API (1.x):
```python
server = Server("name")
@server.list_tools()
async def list_tools() -> list[Tool]: ...

@server.call_tool()
async def call_tool(name, arguments) -> ...
```

新 API (2.0):
```python
async def on_list_tools(ctx, params) -> ListToolsResult: ...
async def on_call_tool(ctx, params) -> CallToolResult: ...

server = Server(
    "name",
    on_list_tools=on_list_tools,
    on_call_tool=on_call_tool
)
```

影響範圍：server.py 完全重寫，所有 19 個現有 tools 需遷移。 |
| 2026-08-09 | 深度推理追蹤架構：從「薄 MCP」到「認知層 MCP」 | 問題：目前 MCP 只記錄結果，不記錄 Agent 的複雜思考過程

解決方案：建立「認知層 MCP」，透過以下機制捕捉 Agent 內部推理：

1. **Structured Thinking Protocol**
   - Agent 必須用特定格式輸出思考過程
   - 每個思考步驟都對應一個 MCP tool call
   - 例如：rc_think_aloud(thought_type, content, alternatives_considered)

2. **Hypothesis Space Exploration Tracking**
   - 記錄 Agent 考慮過哪些 hypotheses
   - 記錄為什麼排除某些 hypotheses
   - 記錄 decision points（關鍵決策點）

3. **Evidence Weighting Transparency**
   - 記錄 Agent 如何評估每個 evidence 的重要性
   - 記錄 conflicting evidence 如何被處理
   - 記錄 uncertainty quantification

4. **Meta-Cognitive Layer**
   - rc_reflect() - Agent 反思自己的推理
   - rc_identify_gaps() - Agent 主動發現知識缺口
   - rc_challenge_assumption() - Agent 質疑自己的假設

5. **Human-Readable Translation Layer**
   - 將 Agent 的 token-level 推理轉譯為醫學框架
   - 例如：Agent 的 attention weights → Bayesian LR
   - Agent 的 token probabilities → confidence scores |
| 2026-08-09 | Production-Ready 完成：Persistence + Real Cases + Coverage + Docs | Phase 1-4 全部完成：

1. **Persistence Layer** ✅
   - SQLite with SQLModel
   - EvidenceModel, HypothesisModel, ThinkingStepModel
   - Data survives restart

2. **Real Case Testing** ✅
   - 13/13 tests passing
   - E2E workflow verified
   - Persistence verified

3. **Test Coverage** ✅
   - Smoke tests (8)
   - E2E tests (3)
   - Persistence tests (2)

4. **Documentation** ✅
   - README.md (English) complete
   - docs/research/existing_solutions.md
   - docs/architecture/deep_reasoning_architecture.md
   - docs/agent_integration_guide.md

> 上述 2026-08-09 的「PRODUCTION-READY」結論已由 2026-08-17 審計取代。
> 目前只可稱為 **engineering alpha**；正式 Agent eval 與臨床 production controls
> 均尚未建立。
