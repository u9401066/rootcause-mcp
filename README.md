# RootCause MCP - 臨床根因分析 MCP Server

> 🏥 專為醫療品質改善設計的根因分析工具

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-1.10+-green.svg)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🎯 專案願景

讓 AI Agent 能夠引導臨床人員進行**結構化、可追溯、可學習**的根因分析。

## ✨ 核心功能

### Phase 1: Foundation (MVP)
- 🐟 **Fishbone (6M)** - 醫療特化的魚骨圖分析
- 🔍 **5-Why** - 深層原因探索
- 📊 **HFACS** - 人因分類自動建議
- 📝 **Domain Config** - 可配置的領域知識

### Phase 2: Ontology (Planned)
- 🧠 知識圖譜整合
- 🔗 相似案例比對

### Phase 3: Causal (Planned)
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

```
rootcause-mcp/
├── src/rootcause_mcp/
│   ├── domain/           # 領域模型 (DDD)
│   │   ├── entities/     # 實體
│   │   ├── value_objects/# 值物件
│   │   └── services/     # 領域服務
│   ├── application/      # 應用層
│   │   ├── commands/     # 命令處理
│   │   └── queries/      # 查詢處理
│   ├── infrastructure/   # 基礎設施
│   │   ├── persistence/  # SQLite + SQLModel
│   │   └── external/     # 外部整合
│   └── interface/        # 介面層
│       └── mcp/          # MCP Tools
├── config/domains/       # 領域配置 YAML
├── tests/               # 測試
├── docs/                # 文件 (含 spec_v2.md)
└── memory-bank/         # 專案記憶
```

## 📚 文件

- [完整規格書](docs/spec_v2.md) - v2.5.0
- [架構說明](docs/ARCHITECTURE.md)

## 🔧 開發

```bash
# 執行測試
pytest

# 程式碼檢查
ruff check src tests
mypy src

# 安全掃描
bandit -r src
```

## 📄 License

MIT License - 詳見 [LICENSE](LICENSE)
