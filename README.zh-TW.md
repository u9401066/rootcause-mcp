# RootCause MCP - 臨床根因分析 MCP 伺服器

> 🏥 AI 引導的結構化醫療品質根因分析

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-1.10+-green.svg)](https://modelcontextprotocol.io/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![GitHub](https://img.shields.io/github/stars/u9401066/rootcause-mcp?style=social)](https://github.com/u9401066/rootcause-mcp)

[English](README.md) | **中文版**

## 🎯 願景

讓 AI Agent 能引導臨床人員進行**結構化、可追溯、可學習**的根因分析 (Root Cause Analysis)。

## ✨ 核心功能

### Phase 1：基礎架構 (MVP)

- 🐟 **魚骨圖 (6M)** - 醫療專用魚骨圖分析
- 🔍 **5-Why** - 深入原因探索
- 📊 **HFACS** - 人因分析自動建議
- 📝 **領域配置** - 可配置的領域知識

### Phase 2：本體論 (規劃中)

- 🧠 知識圖譜整合
- 🔗 相似案例匹配

### Phase 3：因果推論 (規劃中)

- 📈 因果推論分析
- 🧪 反事實測試

## 🚀 快速開始

```bash
# 使用 uv 安裝
uv pip install -e .

# 或開發模式
uv pip install -e ".[dev]"

# 執行 MCP Server
rootcause-mcp
```

## 📁 專案結構

```text
rootcause-mcp/
├── src/rootcause_mcp/
│   ├── domain/           # 領域模型 (DDD)
│   │   ├── entities/     # 實體
│   │   ├── value_objects/# 值物件
│   │   └── services/     # 領域服務
│   ├── application/      # 應用層
│   │   ├── commands/     # 命令處理器
│   │   └── queries/      # 查詢處理器
│   ├── infrastructure/   # 基礎設施
│   │   ├── persistence/  # SQLite + SQLModel
│   │   └── external/     # 外部整合
│   └── interface/        # 介面層
│       └── mcp/          # MCP Tools
├── config/domains/       # 領域配置 YAML
├── tests/               # 測試
├── docs/                # 文件
└── memory-bank/         # 專案記憶
```

## 📚 文件

- [完整規格書](docs/spec_v2.md) - v2.5.0
- [架構文件](ARCHITECTURE.md)

## 🔧 開發

```bash
# 執行測試
pytest

# 程式碼檢查
ruff check src tests
mypy src

# 安全性掃描
bandit -r src
```

## 🤝 貢獻

歡迎貢獻！請參閱 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 📄 授權

Apache 2.0 授權 - 詳見 [LICENSE](LICENSE)
