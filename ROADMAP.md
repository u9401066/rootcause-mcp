# Roadmap - RootCause MCP

醫療根因分析 MCP Server 發展路線圖。

## 已完成 ✅

### Phase 0: 規格與設計 (2026-01-14)
- [x] 規格書 v2.5.0 完成 (docs/spec_v2.md)
- [x] 35 個 MCP Tools 定義
- [x] HFACS-MES 框架整合
- [x] 醫療 6M 魚骨圖設計
- [x] 漸進式輸入設計 (Level 1/2/3)

### Phase 1: 核心架構 (2026-01-15)
- [x] Domain Layer 實作 (Entities, Value Objects, Services)
- [x] Infrastructure Layer (SQLite + SQLModel)
- [x] YAML-based 規則系統
- [x] MCP Server 基礎架構

### Phase 2: MVP Tools (2026-01-15)
- [x] HFACS Tools (5)
  - rc_suggest_hfacs, rc_confirm_classification
  - rc_get_hfacs_framework, rc_list_learned_rules, rc_reload_rules
- [x] Session Tools (4)
  - rc_start_session, rc_get_session
  - rc_list_sessions, rc_archive_session
- [x] Fishbone Tools (4)
  - rc_init_fishbone, rc_add_cause
  - rc_get_fishbone, rc_export_fishbone
- [x] 測試通過 (tests/test_mcp_tools.py)

## 進行中 🚧

### Phase 3: VS Code 整合
- [ ] VS Code MCP Server 整合測試
- [ ] Copilot Chat 呼叫驗證
- [ ] 正式 pytest 測試套件

## 計劃中 📋

### Phase 4: 進階 Tools
- [ ] rc_verify_causation (因果驗證)
- [ ] rc_execute_stage (階段流轉)
- [ ] rc_create_action (改善措施)
- [ ] rc_generate_report (報告生成)

### Phase 5: 協作功能
- [ ] 多使用者支援
- [ ] 角色權限管理
- [ ] 審核流程

### 長期目標
- [ ] FHIR 整合
- [ ] HL7 v2 訊息解析
- [ ] 匿名化資料匯出
- [ ] 統計分析儀表板
