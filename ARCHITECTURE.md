# Architecture

RootCause MCP - 醫療根因分析 MCP Server 架構文檔

## 設計哲學

> **「Agent 決定，Tool 執行」**
> 
> MCP Tools 提供能力，Agent 決定何時、如何使用。
> 避免 hardcode 業務邏輯，讓 Agent 有彈性。

---

## 系統架構圖

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           VS Code / AI Client                            │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                     GitHub Copilot / Claude                        │  │
│  │                                                                    │  │
│  │   "請分析這個醫療事件的根本原因"                                    │  │
│  │                         │                                          │  │
│  │                         ▼                                          │  │
│  │   ┌─────────────────────────────────────────────────────────────┐ │  │
│  │   │              Agent (LLM) 決策層                              │ │  │
│  │   │  1. 理解用戶意圖                                            │ │  │
│  │   │  2. 選擇適當的 MCP Tools                                    │ │  │
│  │   │  3. 組合 Tool 調用順序                                      │ │  │
│  │   │  4. 解讀結果並回應用戶                                      │ │  │
│  │   └──────────────────────┬──────────────────────────────────────┘ │  │
│  │                          │ MCP Protocol                           │  │
│  └──────────────────────────┼────────────────────────────────────────┘  │
└─────────────────────────────┼───────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      RootCause MCP Server (stdio)                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                        MCP Tools Layer                           │    │
│  │  ┌───────────────┐ ┌───────────────┐ ┌───────────────────────┐  │    │
│  │  │rc_suggest_    │ │rc_confirm_    │ │rc_build_fishbone      │  │    │
│  │  │hfacs          │ │classification │ │                       │  │    │
│  │  └───────┬───────┘ └───────┬───────┘ └───────────┬───────────┘  │    │
│  │          │                 │                     │               │    │
│  │  ┌───────────────┐ ┌───────────────┐ ┌───────────────────────┐  │    │
│  │  │rc_list_       │ │rc_get_hfacs   │ │rc_reload_rules        │  │    │
│  │  │learned_rules  │ │_framework     │ │                       │  │    │
│  │  └───────┬───────┘ └───────┬───────┘ └───────────┬───────────┘  │    │
│  │          │                 │                     │               │    │
│  └──────────┼─────────────────┼─────────────────────┼───────────────┘    │
│             │                 │                     │                    │
│             ▼                 ▼                     ▼                    │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    Domain Layer (DDD)                            │    │
│  │                                                                  │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │    │
│  │  │  Entities   │  │   Value     │  │      Services           │  │    │
│  │  │             │  │   Objects   │  │                         │  │    │
│  │  │ - Session   │  │ - HFACSCode │  │ - HFACSSuggester        │  │    │
│  │  │ - Cause     │  │ - HFACSLevel│  │ - LearnedRulesService   │  │    │
│  │  │ - Fishbone  │  │ - Scores    │  │ - CausationValidator    │  │    │
│  │  │ - WhyNode   │  │ - Enums     │  │                         │  │    │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────┘  │    │
│  │                          │                                       │    │
│  │                          ▼                                       │    │
│  │  ┌─────────────────────────────────────────────────────────────┐│    │
│  │  │                   Repositories (Interface)                   ││    │
│  │  │  SessionRepository │ CauseRepository │ FishboneRepository   ││    │
│  │  └─────────────────────────────────────────────────────────────┘│    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                 │                                        │
│                                 ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                   Infrastructure Layer                           │    │
│  │                                                                  │    │
│  │  ┌─────────────────┐    ┌─────────────────────────────────────┐ │    │
│  │  │   SQLite +      │    │         YAML Config                 │ │    │
│  │  │   SQLModel      │    │                                     │ │    │
│  │  │                 │    │  config/hfacs/                      │ │    │
│  │  │  data/jobs/*.db │    │  ├── hfacs_mes.yaml (框架定義)      │ │    │
│  │  │                 │    │  ├── keyword_rules.yaml (領域規則)  │ │    │
│  │  │                 │    │  └── learned_rules.yaml (學習規則)  │ │    │
│  │  └─────────────────┘    └─────────────────────────────────────┘ │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 資料流

### 1. HFACS 分類建議流程

```
User: "護理師因疲勞給錯藥，發生 syringe swap"
                │
                ▼
┌───────────────────────────────────────────────────────────┐
│ Agent 分析意圖：需要 HFACS 分類                           │
│                                                           │
│ 決策：調用 rc_suggest_hfacs tool                          │
└───────────────────────────────────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────────────────┐
│ Tool: rc_suggest_hfacs                                    │
│                                                           │
│ Input:                                                    │
│   description: "護理師因疲勞給錯藥，發生 syringe swap"    │
│   domain: "anesthesia" (optional)                         │
│   max_suggestions: 5                                      │
│                                                           │
│ Process:                                                  │
│   1. HFACSSuggester.suggest(description)                  │
│   2. 載入規則：base + domain + learned                    │
│   3. 關鍵字匹配：疲勞, 給錯藥, syringe swap              │
│   4. 計算信心度並排序                                     │
│                                                           │
│ Output:                                                   │
│   [                                                       │
│     {code: "PP-AMS", confidence: 0.85, reason: "..."},   │
│     {code: "UA-SBE", confidence: 0.80, reason: "..."},   │
│     ...                                                   │
│   ]                                                       │
└───────────────────────────────────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────────────────┐
│ Agent 解讀結果，向用戶說明：                              │
│                                                           │
│ "根據描述，最可能的 HFACS 分類是：                        │
│  1. PP-AMS (注意力/記憶/警覺) - 疲勞影響認知              │
│  2. UA-SBE (技能錯誤) - syringe swap 操作失誤             │
│  ..."                                                     │
│                                                           │
│ Agent 可能追問：                                          │
│ "您確認這個分類嗎？還是需要調整？"                        │
└───────────────────────────────────────────────────────────┘
                │
                ▼ (如果用戶確認)
┌───────────────────────────────────────────────────────────┐
│ Tool: rc_confirm_classification                           │
│                                                           │
│ Input:                                                    │
│   description: "護理師因疲勞給錯藥，發生 syringe swap"    │
│   hfacs_code: "UA-SBE"                                    │
│   reason: "藥物注射器交換操作錯誤"                        │
│                                                           │
│ Process:                                                  │
│   LearnedRulesService.add_rule(...)                       │
│   → 寫入 learned_rules.yaml                               │
│                                                           │
│ Output:                                                   │
│   {status: "success", message: "已加入學習規則"}          │
└───────────────────────────────────────────────────────────┘
```

### 2. 魚骨圖建構流程 (Phase 2)

```
User: "幫我建立這個事件的魚骨圖分析"
                │
                ▼
┌───────────────────────────────────────────────────────────┐
│ Agent 決策序列：                                          │
│                                                           │
│ 1. rc_get_hfacs_framework → 了解 HFACS 結構和引導問題     │
│ 2. 與用戶對話收集資訊                                     │
│ 3. rc_suggest_hfacs → 為每個原因建議 HFACS               │
│ 4. rc_confirm_classification → 確認分類                   │
│ 5. rc_build_fishbone → 產生魚骨圖 (未來)                  │
└───────────────────────────────────────────────────────────┘
```

---

## MCP Tools 設計

### 核心原則

| 原則 | 說明 |
|------|------|
| **Tool = 能力** | Tool 提供單一、明確的能力 |
| **Agent = 決策** | Agent 決定調用哪些 Tools、順序、參數 |
| **無 Hardcode 流程** | 業務邏輯在 Tool 內，流程由 Agent 決定 |
| **可組合** | Tools 可自由組合完成複雜任務 |

### Tool 清單 (Phase 1 MVP)

| Tool | 功能 | Agent 使用情境 |
|------|------|----------------|
| `rc_suggest_hfacs` | 建議 HFACS 代碼 | 用戶描述事件原因時 |
| `rc_confirm_classification` | 確認並學習分類 | 用戶同意建議的分類 |
| `rc_list_learned_rules` | 列出學習規則 | 檢視/管理已學習規則 |
| `rc_get_hfacs_framework` | 取得 HFACS 框架結構 | 了解分類層級和引導問題 |
| `rc_reload_rules` | 重新載入規則 | 規則檔案修改後 |

### Tool 詳細設計

#### `rc_suggest_hfacs`
```
描述: 根據原因描述建議 HFACS-MES 分類代碼

參數:
  - description: str (必填) - 原因描述文字
  - domain: str (選填) - 領域上下文 (e.g., "anesthesia", "surgery")  
  - max_suggestions: int (選填, default=3) - 最大建議數量

回傳:
  - suggestions: List[{code, confidence, reason}]
```

#### `rc_confirm_classification`
```
描述: 確認 HFACS 分類為正確，系統會學習這個規則

參數:
  - description: str (必填) - 原始原因描述
  - hfacs_code: str (必填) - 確認的 HFACS 代碼
  - reason: str (必填) - 為什麼這個分類正確
  - confidence: float (選填, default=0.8) - 信心度

回傳:
  - status: "success" | "error"
  - message: str
```

#### `rc_get_hfacs_framework`
```
描述: 取得 HFACS-MES 框架結構和類別定義

參數:
  - level: str (選填) - 特定層級 (EF, OI, US, PC, UA)

回傳:
  - framework: HFACS-MES 結構 (5 層 25 類)
  - 包含每個類別的定義、範例、引導問題
```

---

## DDD 分層架構

```
┌─────────────────────────────────────────────────────────────┐
│                    Interface Layer                           │
│                                                              │
│  server.py - MCP Server Entry Point                          │
│  • 註冊 Tools                                                │
│  • 處理 MCP Protocol                                         │
│  • 不含業務邏輯                                              │
└──────────────────────────────┬──────────────────────────────┘
                               │ 調用
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                     Domain Layer                             │
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  Entities   │  │   Value     │  │     Services        │  │
│  │             │  │   Objects   │  │                     │  │
│  │ Session     │  │ HFACSCode   │  │ HFACSSuggester      │  │
│  │ Cause       │  │ HFACSLevel  │  │ LearnedRulesService │  │
│  │ Fishbone    │  │ Confidence  │  │ CausationValidator  │  │
│  │ WhyNode     │  │ Enums       │  │                     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│                                                              │
│  • 核心業務邏輯                                              │
│  • 不依賴外部（無 I/O）                                      │
│  • 可獨立測試                                                │
└──────────────────────────────┬──────────────────────────────┘
                               │ 透過 Repository Interface
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                  Infrastructure Layer                        │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐│
│  │               Persistence                                ││
│  │                                                          ││
│  │  SQLite + SQLModel                                       ││
│  │  • SessionRepository (實作)                              ││
│  │  • CauseRepository (實作)                                ││
│  │  • FishboneRepository (實作)                             ││
│  └─────────────────────────────────────────────────────────┘│
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐│
│  │               Configuration                              ││
│  │                                                          ││
│  │  YAML Loader                                             ││
│  │  • hfacs_mes.yaml (HFACS-MES 框架)                       ││
│  │  • keyword_rules.yaml (領域規則)                         ││
│  │  • learned_rules.yaml (學習規則)                         ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

---

## YAML 配置結構

### config/hfacs/ 目錄

```
config/hfacs/
├── frameworks.yaml        # 框架列表和元數據
├── hfacs_mes.yaml         # HFACS-MES 標準定義 (immutable)
├── fishbone_6m.yaml       # 魚骨圖 6M 分類
├── who_icps.yaml          # WHO ICPS 分類
├── keyword_rules.yaml     # 領域關鍵字規則 (可擴展)
└── learned_rules.yaml     # Agent 學習的規則 (動態成長)
```

### 規則載入優先級

```
┌─────────────────────────────────────────────────────────────┐
│                     Rule Priority                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. learned_rules.yaml (最高優先)                            │
│     └─ Agent 確認過的規則，可信度最高                        │
│                                                              │
│  2. keyword_rules.yaml (領域規則)                            │
│     └─ 特定領域（如麻醉）的專業規則                          │
│                                                              │
│  3. hfacs_mes.yaml (基礎規則)                                │
│     └─ 標準框架定義的 keywords                               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Memory Bank vs MCP Server

這是兩個**獨立**的系統：

| 系統 | 用途 | 對象 | 儲存 |
|------|------|------|------|
| **Memory Bank** | AI 開發輔助記憶 | 開發時的 Copilot | `memory-bank/*.md` |
| **MCP Server** | 醫療 RCA 工具 | 用戶端的 Agent | `data/` + `config/` |

```
memory-bank/                    # AI 開發記憶（開發時用）
├── activeContext.md
├── progress.md
├── decisionLog.md
└── ...

config/hfacs/                   # MCP Server 配置（運行時用）
├── learned_rules.yaml          # Agent 學習的規則
└── ...
```

---

## 技術選型

| 層級 | 技術 | 原因 |
|------|------|------|
| MCP Protocol | `mcp` (Python SDK) | 官方 SDK，stdio 傳輸 |
| Domain | Pure Python | 無依賴，可測試 |
| Persistence | SQLite + SQLModel | 輕量、嵌入式 |
| Configuration | YAML + PyYAML | 人類可讀、易編輯 |
| Validation | Pydantic | 型別安全 |

---

## 部署方式

### VS Code 整合

`.vscode/mcp.json`:
```json
{
  "servers": {
    "rootcauseMcp": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "rootcause-mcp"],
      "env": {
        "ROOTCAUSE_CONFIG_DIR": "${workspaceFolder}/config",
        "ROOTCAUSE_DATA_DIR": "${workspaceFolder}/data"
      }
    }
  }
}
```

### 獨立運行

```bash
# 安裝
uv sync

# 執行 (stdio mode)
uv run rootcause-mcp
```

---

## 開發路線圖

### Phase 1 - MVP (Current)
- [x] HFACS-MES YAML 框架定義
- [x] 關鍵字規則系統
- [x] HFACSSuggester 服務
- [x] 學習規則機制
- [x] MCP Server 基礎架構
- [x] 核心 Tools (suggest, confirm, list, framework, reload)

### Phase 2 - 魚骨圖
- [ ] Fishbone Entity 完善
- [ ] Session 管理
- [ ] 魚骨圖建構 Tool
- [ ] 報告匯出

### Phase 3 - 進階
- [ ] 5-Why 分析
- [ ] 多語言支援
- [ ] HTTP/SSE 傳輸
- [ ] 統計分析
