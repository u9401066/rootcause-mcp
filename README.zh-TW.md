# RootCause MCP - 臨床根因分析 MCP 伺服器

> 🏥 **將 AI 洞察轉化為可稽核的組織智慧**  
> 從臨時推理到可追溯、可學習、可防禦的 RCA 工作流

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-1.10+-green.svg)](https://modelcontextprotocol.io/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![GitHub](https://img.shields.io/github/stars/u9401066/rootcause-mcp?style=social)](https://github.com/u9401066/rootcause-mcp)
[![Tools](https://img.shields.io/badge/MCP_Tools-19-purple.svg)](#-可用工具)

[English](README.md) | **中文版**

## 🎯 為何重要（當 AI 已經能秒解 RCA）

### 問題意識

**AI agent（如 Claude）可以瞬間找出根本原因。** 那為什麼還需要結構化 RCA 工具？

因為在受監管產業（醫療、航空、核能），**只有答案是不夠的**：

| 你需要什麼 | AI 直接推理 | RootCause MCP |
|-----------|-------------|---------------|
| ⚡ **速度** | ✅ 瞬間（秒級） | ⚠️ 較慢（引導式流程） |
| 🧠 **準確性** | ✅ 高（Claude Sonnet 4.5） | ✅ 高 + 框架約束 |
| 📜 **法律效力** | ❌ 「AI 這樣說」在法庭不成立 | ✅ 符合 TJC/AHRQ 標準的稽核軌跡 |
| 👥 **團隊協作** | ❌ 單人黑盒 | ✅ 共享魚骨圖 + 多審查者 |
| 📚 **知識累積** | ❌ 對話結束後就遺失 | ✅ 學習規則資料庫 |
| ✅ **監管合規** | ❌ 無法通過 JCAHO 稽核 | ✅ 結構化報告（Mermaid/PDF） |
| 🧪 **因果驗證** | ❌ 無反事實測試 | ✅ Bradford Hill 準則檢查 |

### 解決方案

**RootCause MCP 不取代 AI 推理—它讓 AI 推理變得可稽核、可協作、可累積。**

```
AI 洞察（30 秒） → RCA 工具（30 分鐘） → 可防禦報告（10 年）
```

### 真實情境

#### 情境 1：法律訴訟
```
❌ 「我們的 AI 判斷根本原因是..."
   律師：「你們的方法論是什麼？能重現嗎？」
   你：「呃... Claude 這樣說...」

✅ 「我們依照 WHO ICPS 進行 HFACS-MES 分類，
    執行 5-Why 分析並進行反事實驗證，
    記錄於魚骨圖並經 3 位專家審查。」
   律師：「好的，這符合標準流程。」
```

#### 情境 2：M&M 會議（多科別團隊）
```
❌ 各自用 AI 聊天 → 每個人結論不同 → 無共識

✅ 共享魚骨圖 → 所有科別新增原因 → 投票決定優先項目
```

#### 情境 3：組織學習
```
❌ AI 分析在對話封存後遺失

✅ 學習規則資料庫：
    「sigmoid septum + LVH + syncope」 → HOCM 風險（信心度：95%）
    → 下次案例觸發自動警告
```

---

## 🏗️ 領域卡匣

RootCause MCP 透過**領域卡匣 (Domain Cartridges)** 支援三大類分析模型：

```text
┌─────────────────────────────────────────────────────────────────┐
│                      RootCause MCP                              │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  前瞻性預防  │  │  回溯性調查  │  │  系統複雜性  │             │
│  │ PROSPECTIVE │  │RETROSPECTIVE│  │   SYSTEMIC  │             │
│  ├─────────────┤  ├─────────────┤  ├─────────────┤             │
│  │ • HFMEA     │  │ • HFACS  ✅ │  │ • STAMP/STPA│             │
│  │ • HVA       │  │ • 5-Whys ✅ │  │ • FRAM      │             │
│  │ • Bowtie    │  │ • Fishbone✅│  │ • AcciMap   │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                          ▼                                      │
│              ┌───────────────────────┐                          │
│              │   Unified Graph API   │                          │
│              │    (19 MCP Tools)     │                          │
│              └───────────────────────┘                          │
└─────────────────────────────────────────────────────────────────┘
```

## 💎 核心價值主張

### 這個工具實際在做什麼

1. **🔒 法律盔甲**
   - 產生符合 JCAHO、CMS、衛福部稽核的報告
   - 提供方法論可追溯性（「我們遵循 TJC 框架」）
   - 為訴訟建立可防禦的文件

2. **👥 協作基板**
   - 10 人可同時編輯的共享魚骨圖
   - 版本控制的因果鏈
   - 多利害關係人審查流程

3. **📚 知識圖譜**
   - `learned_rules.yaml` 隨每個案例變聰明
   - 模式識別：「最近 3 個 LVOT 梗阻案例都有這個特徵」
   - 不受人員流動影響的機構記憶

4. **🎓 教育框架**
   - 訓練住院醫師批判性思考（而非只求答案）
   - 教導反事實推理（「如果我們有識別 HOCM 會怎樣？」）
   - 提供結構化的 QI 能力練習

5. **🧪 驗證層**
   - 因果關係測試（時序性、必要性、充分性、機制）
   - 防止虛假相關性變成「根本原因」
   - 強制實證推理

---

## ✨ 核心功能

### 回溯性卡匣 (已實作 ✅)

| 功能 | 說明 | 狀態 |
|------|------|------|
| 🐟 **魚骨圖 (6M)** | 醫療專用石川圖分析 | ✅ 4 tools |
| 🔍 **5-Why 分析** | 深入原因探索，含近端/遠端原因分類 | ✅ 4 tools |
| 📊 **HFACS-MES** | 人因分析自動建議 (5 層 25 類) | ✅ 6 tools |
| ✅ **因果驗證** | 基於 Bradford Hill 準則的驗證 | ✅ 1 tool |
| 🔗 **6M-HFACS 對照** | 分類系統交叉參照 | ✅ 1 tool |
| 💾 **Session 管理** | 持久化分析 Session | ✅ 4 tools |

### 前瞻性卡匣 (規劃中 📋)

- **HFMEA** - 醫療失效模式與效應分析
- **HVA** - 危害脆弱性分析
- **Bowtie** - 威脅與後果分析

### 系統性卡匣 (規劃中 📋)

- **STAMP/STPA** - 控制迴路分析
- **FRAM** - 功能共振分析方法

## 🔧 可用工具

### HFACS 工具 (6)

| 工具 | 說明 |
|------|------|
| `rc_suggest_hfacs` | 從原因描述自動建議 HFACS 代碼 |
| `rc_confirm_classification` | 確認或覆蓋 HFACS 分類 |
| `rc_get_hfacs_framework` | 取得完整 HFACS-MES 框架結構 |
| `rc_list_learned_rules` | 列出學習的分類規則 |
| `rc_reload_rules` | 熱載入 YAML 規則 |
| `rc_get_6m_hfacs_mapping` | 取得 6M-HFACS 交叉對照表 |

### Session 工具 (4)

| 工具 | 說明 |
|------|------|
| `rc_start_session` | 建立新 RCA Session |
| `rc_get_session` | 取得 Session 詳情 |
| `rc_list_sessions` | 列出所有 Sessions |
| `rc_archive_session` | 歸檔已完成的 Session |

### 魚骨圖工具 (4)

| 工具 | 說明 |
|------|------|
| `rc_init_fishbone` | 初始化魚骨圖 |
| `rc_add_cause` | 新增原因到 6M 分類 |
| `rc_get_fishbone` | 取得魚骨圖結構 |
| `rc_export_fishbone` | 匯出為 Mermaid/Markdown/JSON |

### Why Tree 工具 (4)

| 工具 | 說明 |
|------|------|
| `rc_ask_why` | 漸進式 5-Why 提問 |
| `rc_get_why_tree` | 取得 Why 樹結構 |
| `rc_mark_root_cause` | 標記節點為根本原因 |
| `rc_export_why_tree` | 匯出為 Mermaid/Markdown/JSON |

### 驗證工具 (1)

| 工具 | 說明 |
|------|------|
| `rc_verify_causation` | 以 4 準則驗證因果關係 |

## 🚀 快速開始

```bash
# 使用 uv 安裝 (推薦)
uv pip install -e .

# 或開發模式
uv pip install -e ".[dev]"

# 執行 MCP Server
python -m rootcause_mcp.interface.server
```

### VS Code 整合

在 `.vscode/mcp.json` 加入：

```json
{
  "servers": {
    "rootcause-mcp": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "python", "-m", "rootcause_mcp.interface.server"],
      "cwd": "${workspaceFolder}"
    }
  }
}
```

## 📁 專案結構

```text
rootcause-mcp/
├── src/rootcause_mcp/
│   ├── domain/           # 領域層 (DDD)
│   │   ├── entities/     # Session, Cause, Fishbone, WhyNode
│   │   ├── value_objects/# HFACSCode, Scores, Identifiers
│   │   ├── repositories/ # Repository 介面
│   │   └── services/     # HFACSSuggester, CausationValidator
│   ├── application/      # 應用層
│   │   ├── session_progress_tracker.py
│   │   └── guided_response_builder.py
│   ├── infrastructure/   # 基礎設施層
│   │   └── persistence/  # SQLite + SQLModel
│   └── interface/        # 介面層
│       ├── tools/        # MCP Tool 定義
│       ├── handlers/     # Tool 處理器
│       └── server.py     # MCP Server 入口
├── config/hfacs/         # YAML 配置
│   ├── hfacs_mes.yaml    # HFACS-MES 框架
│   ├── fishbone_6m.yaml  # 醫療 6M 分類
│   └── keyword_rules.yaml# 分類規則
├── tests/                # 測試
├── docs/                 # 文件
│   └── spec_v2.md        # 完整規格書 v2.5.0
└── memory-bank/          # 專案記憶 (供 AI 使用)
```

## 🔗 相關 MCPs

| MCP | 用途 | 整合方式 |
|-----|------|----------|
| [asset-aware-mcp](https://github.com/u9401066/asset-aware-mcp) | 資料拆解與表格重構 | 前處理 |
| HHRAG MCP | 知識圖譜檢索 | 上下文豐富 |
| CGU MCP | 創意發散思考 | 原因腦力激盪 |

## 📚 文件

- [完整規格書](docs/spec_v2.md) - v2.5.0 (3700+ 行)
- [架構文件](ARCHITECTURE.md) - DDD 分層
- [路線圖](ROADMAP.md) - Cartridge 擴展計劃
- [文獻回顧](docs/literature_review_clinical_rca.md) - HFACS-MES 研究

## 🔧 開發

```bash
# 執行測試
pytest tests/ -v

# 程式碼檢查
ruff check src tests
mypy src --strict

# 安全性掃描
bandit -r src

# 死碼偵測
vulture src
```

## 🤝 貢獻

歡迎貢獻！請參閱 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 📄 授權

Apache 2.0 授權 - 詳見 [LICENSE](LICENSE)

---

## 🎯 何時該使用這個工具？

### ❌ 不要用這個如果：
- 你只是想快速學習個人練習
- 你單獨作業，不需要證明你的推理
- 你的組織不要求結構化 RCA

### ✅ 應該用這個如果：
- 🏥 你需要通過 JCAHO/CMS/衛福部稽核
- 👥 多科別需要協作（外科 + 麻醉 + 護理 + 藥局）
- 📚 你想建立機構知識庫
- 🎓 你在訓練住院醫師/研究員 RCA 方法論
- ⚖️ 你在準備潛在訴訟
- 🔬 你需要可重現、實證為本的分析

---

**以 ❤️ 打造，致力於醫療品質改善**  
*「AI 可以在 30 秒找到答案。我們幫你防禦 30 年。」*
