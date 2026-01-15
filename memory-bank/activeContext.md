# Active Context - RootCause MCP

> 📌 此檔案記錄當前工作焦點，每次工作階段開始時檢視，結束時更新。

## 🎯 當前焦點

- Git 設定完成，準備開始 Phase 1 MVP 實作
- GitHub Repo: [u9401066/rootcause-mcp](https://github.com/u9401066/rootcause-mcp)

## 📝 專案狀態

| 階段 | 狀態 |
|------|------|
| 規格設計 | ✅ 完成 (spec_v2.md v2.5.0) |
| 專案結構 | ✅ 完成 (DDD 架構) |
| Git/GitHub | ✅ 完成 |
| 領域模型 | ⏳ 待開始 |
| MCP Tools | ⏳ 待開始 |
| 測試 | ⏳ 待開始 |

## ⚠️ 待解決

- PHI/PII 資料治理政策需補充
- MVP 範圍需確認 (10 核心工具)

## 💡 重要決定

- **漸進式輸入設計** (v2.5.0)
  - Level 1: 必填（自然語言描述）
  - Level 2: 系統建議（HFACS 自動推薦）
  - Level 3: 選填進階

- **HFACS 自動建議機制**
  - 根據 description 比對 keywords
  - 返回 confidence 分數和替代選項

## 📁 核心檔案

```
docs/spec_v2.md          # 完整規格書 (3700+ 行)
config/domains/          # 領域配置 YAML
src/rootcause_mcp/       # 實作程式碼
```

## 🔜 下一步

1. 建立 Domain Entities (Session, Cause, FishboneCategory)
2. 實作 `rc_create_session` 工具
3. 設計 SQLite Schema

---
*Last updated: 2026-01-15*