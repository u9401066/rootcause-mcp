# Progress - RootCause MCP (Updated: 2026-01-15)

## Done

- ✅ 規格書 v2.5.0 完成 (docs/spec_v2.md, 3700+ 行)
- ✅ 35 個 MCP Tools 定義完成
- ✅ 漸進式輸入設計 (Level 1/2/3)
- ✅ HFACS 自動建議機制設計
- ✅ 專案風險 RCA (dogfooding)
- ✅ 專案結構建立 (from template)
- ✅ pyproject.toml 配置

## Doing

- 🔄 Memory Bank 初始化

## Next (MVP Phase)

1. 建立 Domain Entities
   - `Session`, `Cause`, `FishboneCategory`
   - `HFACSCode`, `WhyNode`

2. 實作 10 核心 MCP Tools
   - `rc_create_session`
   - `rc_set_problem`
   - `rc_add_cause`
   - `rc_ask_why`
   - `rc_get_fishbone`
   - `rc_get_analysis_tree`
   - `rc_suggest_next`
   - `rc_validate_chain`
   - `rc_export_report`
   - `rc_list_sessions`

3. 設計 SQLite Schema

4. 撰寫單元測試

## Blocked

- (無)

## Risk Notes

- 🔴 PHI/PII 資料治理待補充
- 🟠 35 工具可能過多，先聚焦 MVP 10 工具
