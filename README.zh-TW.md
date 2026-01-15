# RootCause MCP - 臨床根因分析 MCP 伺服器

> 🏥 AI 引導的結構化醫療品質根因分析

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-1.10+-green.svg)](https://modelcontextprotocol.io/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![GitHub](https://img.shields.io/github/stars/u9401066/rootcause-mcp?style=social)](https://github.com/u9401066/rootcause-mcp)
[![Tools](https://img.shields.io/badge/MCP_Tools-19-purple.svg)](#-可用工具)

[English](README.md) | **中文版**

## 🎯 願景

讓 AI Agent 能引導臨床人員進行**結構化、可追溯、可學習**的根因分析 (Root Cause Analysis)。

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

**以 ❤️ 打造，致力於醫療品質改善**
