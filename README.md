# RootCause MCP - Clinical Root Cause Analysis MCP Server

> 🏥 AI-guided structured Root Cause Analysis for healthcare quality improvement

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-1.10+-green.svg)](https://modelcontextprotocol.io/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![GitHub](https://img.shields.io/github/stars/u9401066/rootcause-mcp?style=social)](https://github.com/u9401066/rootcause-mcp)

**English** | [中文版](README.zh-TW.md)

## 🎯 Vision

Enable AI Agents to guide clinical staff through **structured, traceable, and learnable** Root Cause Analysis.

## ✨ Core Features

### Phase 1: Foundation (MVP)

- 🐟 **Fishbone (6M)** - Healthcare-specialized Fishbone diagram analysis
- 🔍 **5-Why** - Deep cause exploration
- 📊 **HFACS** - Human Factors Analysis auto-suggestion
- 📝 **Domain Config** - Configurable domain knowledge

### Phase 2: Ontology (Planned)

- 🧠 Knowledge Graph integration
- 🔗 Similar case matching

### Phase 3: Causal (Planned)

- 📈 Causal inference analysis
- 🧪 Counterfactual testing

## 🚀 Quick Start

```bash
# Install with uv
uv pip install -e .

# Or development mode
uv pip install -e ".[dev]"

# Run MCP Server
rootcause-mcp
```

## 📁 Project Structure

```text
rootcause-mcp/
├── src/rootcause_mcp/
│   ├── domain/           # Domain models (DDD)
│   │   ├── entities/     # Entities
│   │   ├── value_objects/# Value Objects
│   │   └── services/     # Domain Services
│   ├── application/      # Application layer
│   │   ├── commands/     # Command handlers
│   │   └── queries/      # Query handlers
│   ├── infrastructure/   # Infrastructure
│   │   ├── persistence/  # SQLite + SQLModel
│   │   └── external/     # External integrations
│   └── interface/        # Interface layer
│       └── mcp/          # MCP Tools
├── config/domains/       # Domain config YAML
├── tests/               # Tests
├── docs/                # Documentation
└── memory-bank/         # Project memory
```

## 📚 Documentation

- [Full Specification](docs/spec_v2.md) - v2.5.0
- [Architecture](ARCHITECTURE.md)

## 🔧 Development

```bash
# Run tests
pytest

# Code linting
ruff check src tests
mypy src

# Security scan
bandit -r src
```

## 📄 License

Apache 2.0 License - See [LICENSE](LICENSE)
