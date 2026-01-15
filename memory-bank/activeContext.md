# Active Context - RootCause MCP

> 📌 此檔案記錄當前工作焦點，每次工作階段開始時檢視，結束時更新。

## 🎯 當前焦點

- **Phase 3 完成！** 5-Why Analysis & Causation Verification 已實作
- **18 個 MCP Tools** 可用
- **核心哲學轉變**：從「填表式」轉為「推論式」RCA
- 準備進入 Phase 4: VS Code 整合測試 + 進階 Tools

## 📝 專案狀態

| 階段 | 狀態 |
|------|------|
| 規格設計 | ✅ 完成 (spec_v2.md v2.5.0) |
| 專案結構 | ✅ 完成 (DDD 架構) |
| Git/GitHub | ✅ 完成 |
| 領域模型 | ✅ 完成 (Entities, Value Objects, Services) |
| Infrastructure | ✅ 完成 (SQLite + SQLModel + InMemory) |
| MCP Tools | ✅ **18 Tools 完成** |
| 測試 | 🔄 手動測試通過，待正式 pytest |

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

### Why Tree Tools (4) 🆕
- `rc_ask_why` - 5-Why 迭代提問 (核心推論工具)
- `rc_get_why_tree` - 取得完整分析樹
- `rc_mark_root_cause` - 標記根本原因
- `rc_export_why_tree` - 匯出 (Mermaid/Markdown/JSON)

### Verification Tools (1) 🆕
- `rc_verify_causation` - Counterfactual Testing Framework
  - Temporality: 時間序列 (因先於果)
  - Necessity: 必要性 (無因則無果)
  - Mechanism: 機轉 (合理因果路徑)
  - Sufficiency: 充分性 (因是否足以產生果)

## 💡 重要技術細節

- **Database**: `data/rca_sessions.db` (SQLite)
- **Why Tree Storage**: InMemory (InMemoryWhyTreeRepository)
- **入口**: `uv run rootcause-mcp` 或 `uv run python -m rootcause_mcp.server`
- **配置**: `.vscode/mcp.json`
- **Bug Fix**: HFACSCode 驗證改為 `len >= 3` (支援 HFACS-MES 代碼如 `EO-N`)

## 📁 核心檔案

```
src/rootcause_mcp/server.py                              # MCP Server (18 Tools)
src/rootcause_mcp/domain/repositories/why_tree_repository.py  # 抽象介面
src/rootcause_mcp/infrastructure/persistence/why_tree_repository.py  # InMemory 實作
tests/test_mcp_tools.py                                  # 手動測試腳本
config/hfacs/                                            # YAML 配置 (框架/關鍵字/規則)
data/rca_sessions.db                                     # SQLite 資料庫
.vscode/mcp.json                                         # VS Code MCP 配置
```

## 🔜 下一步 (Phase 4)

1. 在 VS Code 中啟動 MCP Server 測試整合
2. 實作進階 Tools (execute_stage, create_action, link_why_to_cause)
3. 撰寫正式 pytest 測試
4. 連結 Why Tree 和 Fishbone (將分析結果整合)

---
*Last updated: 2026-01-15*