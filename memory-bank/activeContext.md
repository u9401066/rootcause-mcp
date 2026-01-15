# Active Context - RootCause MCP

> 📌 此檔案記錄當前工作焦點，每次工作階段開始時檢視，結束時更新。

## 🎯 當前焦點

- **DDD 模組重構完成！** 2057 行 monolithic server.py → 模組化架構
- **Session-aware 進度追蹤機制** 設計完成
- **18 個 MCP Tools** 全部測試通過
- 準備進入 Phase 4: GuidedResponse 整合 + VS Code 測試

## 📝 專案狀態

| 階段 | 狀態 |
|------|------|
| 規格設計 | ✅ 完成 (spec_v2.md v2.5.0) |
| 專案結構 | ✅ 完成 (DDD 架構) |
| Git/GitHub | ✅ 完成 |
| 領域模型 | ✅ 完成 (Entities, Value Objects, Services) |
| Infrastructure | ✅ 完成 (SQLite + SQLModel + InMemory) |
| MCP Tools | ✅ **18 Tools 完成** |
| **DDD 重構** | ✅ **完成 (模組化 interface/)** |
| **Application Layer** | ✅ **SessionProgressTracker + GuidedResponseBuilder** |
| 測試 | 🔄 手動測試通過，待正式 pytest |

## 📂 新架構 (DDD 重構後)

```
src/rootcause_mcp/
├── interface/
│   ├── server.py          # 精簡入口點 (~350 行)
│   ├── tools/             # Tool 定義模組 (5 檔案)
│   │   ├── hfacs_tools.py
│   │   ├── session_tools.py
│   │   ├── fishbone_tools.py
│   │   ├── why_tree_tools.py
│   │   └── verification_tools.py
│   └── handlers/          # Handler 實作模組 (5 檔案)
│       ├── hfacs_handlers.py
│       ├── session_handlers.py
│       ├── fishbone_handlers.py
│       ├── why_tree_handlers.py
│       └── verification_handlers.py
├── application/
│   ├── session_progress.py   # 進度追蹤
│   └── guided_response.py    # 引導式回應 + 逼問
├── domain/                   # (已存在)
└── infrastructure/           # (已存在)
```

## 🛠️ 已實作 MCP Tools (18)

### HFACS Tools (5)
- `rc_suggest_hfacs` - HFACS 代碼建議
- `rc_confirm_classification` - 確認分類並學習
- `rc_get_hfacs_framework` - 取得框架結構
- `rc_list_learned_rules` - 列出學習規則
- `rc_reload_rules` - 重新載入規則

### Session Tools (4)
- `rc_start_session` - 建立新 RCA Session
- `rc_get_session` - 取得 Session 詳情
- `rc_list_sessions` - 列出所有 Sessions
- `rc_archive_session` - 封存 Session

### Fishbone Tools (4)
- `rc_init_fishbone` - 初始化魚骨圖
- `rc_add_cause` - 新增原因
- `rc_get_fishbone` - 取得魚骨圖
- `rc_export_fishbone` - 匯出 (Mermaid/Markdown/JSON)

### Why Tree Tools (4)
- `rc_ask_why` - 5-Why 迭代提問 (核心推論工具)
- `rc_get_why_tree` - 取得完整分析樹
- `rc_mark_root_cause` - 標記根本原因
- `rc_export_why_tree` - 匯出 (Mermaid/Markdown/JSON)

### Verification Tools (1)
- `rc_verify_causation` - Counterfactual Testing Framework

## 💡 重要技術細節

- **Database**: `data/rca_sessions.db` (SQLite)
- **入口點**: `rootcause_mcp.interface.server:main` (新 DDD 入口)
- **Legacy 入口**: `rootcause_mcp.server:main` (向後相容)
- **配置**: `.vscode/mcp.json`

## 🔜 下一步 (Phase 4)

1. **整合 GuidedResponse 到 Handlers**
   - 每個 Tool 回傳標準化進度資訊
   - 實作「逼問」(push questions) 機制
2. 在 VS Code 中測試 MCP Server
3. 實作進階 Tools
4. 撰寫正式 pytest 測試

---
*Last updated: 2026-01-15*