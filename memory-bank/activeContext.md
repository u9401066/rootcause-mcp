# Active Context - RootCause MCP

> 📌 此檔案記錄當前工作焦點，每次工作階段開始時檢視，結束時更新。
> 
> **Last Updated**: 2026-08-09

## 🎯 當前焦點

**🔴 v2.0.0-alpha 深度審計完成 — 發現 4 個 P0 缺陷**

審計結論：v2.0.0-alpha **不適合發布**。核心問題：
1. server_v2 路由對 5 個舊 handlers 呼叫不存在的 `handle()` → 53% tools 損壞
2. `ClinicalReasoningOrchestrator` 設計了但未整合（import 後未使用）
3. Evidence/Hypothesis/ThinkingChain 無持久化（repos 是死代碼，handlers 用 in-memory dict）
4. test_mcp_tools.py 崩潰（SDK 1.x API），覆蓋率僅 46%

### 下一步行動（依優先級）
1. **P0**：為 5 個舊 handlers 加上 `handle()` dispatcher，或遷移為 dict-returning 風格
2. **P0**：修正 `isError` → `is_error`（server_v2.py:280,303）
3. **P0**：修復或移除 test_mcp_tools.py（import 舊 server.py）
4. **P1**：決定 Orchestrator 去留 — 整合進 handlers 或刪除
5. **P1**：接通 3 個新 repositories 的持久化，或刪除
6. **P1**：ContractHandlers 接通真實資料來源
7. **P2**：補 Hypothesis ON_HOLD setter、Evidence update/delete


## 📝 專案狀態

| 階段 | 狀態 |
|------|------|
| 規格設計 | ✅ 完成 (spec_v2.md v2.5.0) |
| 專案結構 | ✅ 完成 (DDD 架構) |
| Git/GitHub | ✅ 完成 |
| 領域模型 | ✅ 完成 (Entities, Value Objects, Services) |
| Infrastructure | ✅ 完成 (SQLite + SQLModel + InMemory) |
| MCP Tools | ✅ **19 Tools 完成** |
| **DDD 重構** | ✅ **完成 (模組化 interface/)** |
| **Application Layer** | ✅ **SessionProgressTracker + GuidedResponseBuilder** |
| **Export 功能** | ✅ **自動存檔至 `data/exports/`** |
| **測試案例** | ✅ **AHRQ WebM&M 案例測試通過** |
| 測試 | 🔄 手動測試通過，待正式 pytest |

## 📂 Export 功能 (新增)

```
data/exports/
└── {session_id}/
    ├── fishbone_20260116_010216.md   # Mermaid 圖 + 時間戳
    └── why_tree_20260116_012345.md   # 可在 VS Code 預覽
```

- **觸發**: `rc_export_fishbone` 或 `rc_export_why_tree`
- **格式**: Mermaid/Markdown → `.md`, JSON → `.json`
- **預覽**: 安裝 `bierner.markdown-mermaid` 擴展

## 🛠️ 已實作 MCP Tools (19)

### HFACS Tools (6)
- `rc_suggest_hfacs` - HFACS 代碼建議
- `rc_confirm_classification` - 確認分類並學習
- `rc_get_hfacs_framework` - 取得框架結構
- `rc_get_6m_hfacs_mapping` - 🆕 6M↔HFACS 對照表
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

## 🔮 Cartridge 系統 (ROADMAP Phase 6-8)

```
┌────────────────────────────────────────────────────────┐
│                  RootCause MCP                         │
│           Multi-Model RCA Framework                    │
├────────────────────────────────────────────────────────┤
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐   │
│  │ Prospective  │ │ Retrospective│ │   Systemic   │   │
│  │  Cartridge   │ │   Cartridge  │ │  Cartridge   │   │
│  │              │ │      ✅      │ │              │   │
│  │ • HFMEA      │ │ • HFACS ✅   │ │ • STAMP/STPA │   │
│  │ • HVA        │ │ • 5-Whys ✅  │ │ • FRAM       │   │
│  │ • Bowtie     │ │ • Fishbone ✅│ │ • AcciMap    │   │
│  └──────────────┘ └──────────────┘ └──────────────┘   │
└────────────────────────────────────────────────────────┘
```

## 💡 重要技術細節

- **Database**: `data/rca_sessions.db` (SQLite)
- **入口點**: `rootcause_mcp.interface.server:main` (新 DDD 入口)
- **Legacy 入口**: `rootcause_mcp.server:main` (向後相容)
- **配置**: `.vscode/mcp.json`

## 🔜 下一步

1. ✅ **Git Commit** 今日變更 (Export + Bug fixes + 案例)
2. **Phase 3**: 擴充 Retrospective 工具
   - Stage tools (execute/get/rollback)
   - Action tools (SMART criteria)
3. **Phase 4**: GuidedResponse 完整整合
4. **相關專案**: `asset-aware-mcp` 用於資料拆解前處理

---
*Last updated: 2026-01-16T01:30*