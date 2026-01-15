# Decision Log - RootCause MCP

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-15 | 漸進式輸入設計 (Level 1/2/3) | 降低使用門檻，自然語言優先 |
| 2026-01-15 | HFACS 自動建議機制 | AI 協助分類，但由人確認 |
| 2026-01-15 | MVP 聚焦 10 核心工具 | 35 工具過多，先驗證核心價值 |
| 2026-01-15 | 不儲存 PHI/PII | 合規要求，只保留結構化分析資料 |
| 2026-01-15 | SQLite + SQLModel | 輕量、跨平台、易部署 |
| 2026-01-15 | DDD 分層架構 | 業務邏輯與基礎設施分離 |

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
