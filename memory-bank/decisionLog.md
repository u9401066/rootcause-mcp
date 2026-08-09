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
| 2026-08-09 | **Chain of Thought Persistence** | ReasoningStep entity 持久化，提供完整推理 audit trail |
| 2026-08-09 | **CONTRACT-level Report** | 不可變的 ContractReport（finalized 後禁止修改），符合 FHIR-like 標準 |
| 2026-08-09 | **Evidence Quality Grading** | Oxford CEBM 啟發的 Strength×Reliability 二維品質矩陣 |
| 2026-08-09 | **DB: JSON array 儲存 ID 關聯** | 不用外鍵 JOIN，SQLite 效能 + 彈性，Evidence↔Cause many-to-many |

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
| `ReasoningStep` | Entity | 推理鏈步驟（chain of thought 持久化） |
| `EvidenceQuality` | Value Object | Strength × Reliability 品質矩陣 |
| `ClinicalConcept` | Value Object | SNOMED/ICD-10 概念封裝 |
| `ContractReport` | Value Object | 不可變 CONTRACT 報告 |

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
