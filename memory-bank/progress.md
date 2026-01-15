# Progress - RootCause MCP (Updated: 2026-01-15)

## Done

- ✅ 規格書 v2.5.0 完成 (docs/spec_v2.md, 3700+ 行)
- ✅ 35 個 MCP Tools 定義完成
- ✅ 漸進式輸入設計 (Level 1/2/3)
- ✅ HFACS 自動建議機制設計
- ✅ 專案風險 RCA (dogfooding)
- ✅ 專案結構建立 (from template)
- ✅ pyproject.toml 配置
- ✅ Git 初始化 + GitHub Repo 建立
  - Repo: https://github.com/u9401066/rootcause-mcp
  - Topics: mcp, root-cause-analysis, healthcare, hfacs, fishbone-diagram
  - Labels: phase1-mvp, phase2-fishbone, phase3-collab, domain-entities, mcp-tools, etc.
- ✅ 架構決策：移除 owlready2，改用 Rule Engine + Agent 方案
- ✅ 文獻回顧完成 (docs/literature_review_clinical_rca.md)
  - HFACS-MES 5 層 25 類完整架構
  - WHO ICPS 分類系統
  - 重要機構資源連結
- ✅ 多框架 YAML 配置建立
  - config/hfacs/frameworks.yaml (框架選擇器)
  - config/hfacs/hfacs_mes.yaml (HFACS-MES 完整分類)
  - config/hfacs/fishbone_6m.yaml (醫療 6M)
  - config/hfacs/who_icps.yaml (WHO ICPS)
- ✅ 麻醉事件專題資源補充 (Section 7)
  - ASA Closed Claims Project
  - NACOR 資料庫
  - UK NAP 系列 (NAP4-NAP7)
  - Emergency Manual / 危機檢核表
  - 藥物錯誤與緩解策略

## Doing

- 🔄 準備開始 MVP 實作 (Phase 1)

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
- ✅ owlready2 已決定移除，使用 Rule Engine + Agent 替代方案
