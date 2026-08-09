# Product Context - RootCause MCP

> 📌 此檔案描述專案的技術架構和產品定位，專案初期建立後較少更新。

## 📋 專案概述

**專案名稱**：RootCause MCP (臨床根因分析 MCP Server)

**一句話描述**：讓 AI Agent 能引導醫療人員進行結構化、可追溯、可學習的根因分析。

**目標用戶**：醫療品質管理人員、臨床安全團隊、使用 AI 進行 RCA 的臨床人員

## 🏗️ 架構

```
MCP Server (rootcause-mcp)
├── Interface Layer (MCP Tools)
├── Application Layer (Use Cases)
├── Domain Layer (Entities, Services)
└── Infrastructure Layer (SQLite, External APIs)
```

### DDD 分層

```
src/rootcause_mcp/
├── interface/mcp/      # MCP Tools 定義
├── application/        # Commands, Queries
├── domain/             # Entities, Value Objects, Services
└── infrastructure/     # Persistence, External
```

## ✨ 核心功能

- 🐟 **Fishbone (6M)** - 醫療特化魚骨圖分析
- 🔍 **5-Why Analysis** - 深層原因探索
- 📊 **HFACS Integration** - 人因分類自動建議
- 📝 **Domain Configuration** - 可配置的領域知識
- 📤 **Report Export** - Markdown/JSON 報告匯出

## 🔧 技術棧

| 類別 | 技術 |
|------|------|
| 語言 | Python 3.12+ |
| MCP 框架 | FastMCP |
| ORM | SQLModel + aiosqlite |
| 圖分析 | networkx |
| 驗證 | Pydantic v2 |
| 日誌 | structlog |
| 套件管理 | uv |
| Linting | ruff, mypy |
| 測試 | pytest, pytest-asyncio |
| 安全 | bandit |

## 📦 依賴

### 核心依賴

```toml
mcp[cli]>=1.10.1
pydantic>=2.0
pydantic-settings>=2.0
sqlmodel>=0.0.22
aiosqlite>=0.20.0
networkx>=3.0
structlog>=24.0
```

### 可選依賴 (Phase 2/3)

```toml
# Phase 2: Ontology
owlready2>=0.46

# Phase 3: Causal Inference
dowhy[gcm]>=0.11
causal-learn>=0.1.3
```

### 開發依賴

```toml
pytest>=8.0
pytest-cov>=4.0
pytest-asyncio>=0.23
ruff>=0.5.0
mypy>=1.10
bandit>=1.7
```

---
*Last updated: 2026-01-15*

## Project Description

RootCause MCP v2.0.0-alpha: 醫學推理專用 MCP Harness，讓任意通用 AI Agent 都能執行專業級醫學推理分析與鑑別診斷。核心創新是「認知層 MCP」，透過 ThinkingStep 記錄 Agent 的思考過程，不只是結果。36 個 MCP tools 涵蓋：認知層(5)、Evidence(3)、DDx(4)、Reasoning(2)、CONTRACT(1)、HFACS(6)、Session(4)、Fishbone(4)、WhyTree(6)、Verification(1)。完整實作包含 Domain/Application/Infrastructure/Interface 四層 DDD 架構。



## Architecture

DDD 四層架構：Domain (Entities: Evidence, Hypothesis, ReasoningStep, ThinkingStep; VOs: EvidenceQuality, ClinicalConcept, ContractReport) → Application (ClinicalReasoningOrchestrator) → Infrastructure (SQLite Repositories) → Interface (36 MCP Tools, 10 Handlers)



## Technologies

- Python 3.12+
- MCP SDK 2.0
- Pydantic v2
- SQLModel
- SQLite
- NetworkX
- pytest
- uv



## Libraries and Dependencies

- mcp>=2.0.0
- pydantic>=2.0
- sqlmodel>=0.0.22
- aiosqlite>=0.20.0
- networkx>=3.0
- structlog>=24.0

