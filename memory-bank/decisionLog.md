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
