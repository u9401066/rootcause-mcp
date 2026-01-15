# RootCause MCP - Clinical Root Cause Analysis MCP Server

> 🏥 AI-guided structured Root Cause Analysis for healthcare quality improvement

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-1.10+-green.svg)](https://modelcontextprotocol.io/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![GitHub](https://img.shields.io/github/stars/u9401066/rootcause-mcp?style=social)](https://github.com/u9401066/rootcause-mcp)
[![Tools](https://img.shields.io/badge/MCP_Tools-19-purple.svg)](#-available-tools)

**English** | [中文版](README.zh-TW.md)

## 🎯 Vision

Enable AI Agents to guide clinical staff through **structured, traceable, and learnable** Root Cause Analysis.

RootCause MCP supports three categories of analysis models through **Domain Cartridges**:

```text
┌─────────────────────────────────────────────────────────────────┐
│                      RootCause MCP                              │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ PROSPECTIVE │  │RETROSPECTIVE│  │   SYSTEMIC  │             │
│  │  Proactive  │  │Investigation│  │  Complexity │             │
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

## ✨ Core Features

### Retrospective Cartridge (Implemented ✅)

| Feature | Description | Status |
|---------|-------------|--------|
| 🐟 **Fishbone (6M)** | Healthcare-specialized Ishikawa diagram | ✅ 4 tools |
| 🔍 **5-Why Analysis** | Deep cause exploration with Proximate/Ultimate classification | ✅ 4 tools |
| 📊 **HFACS-MES** | Human Factors Analysis auto-suggestion (5-level, 25 categories) | ✅ 6 tools |
| ✅ **Causation Verify** | Bradford Hill criteria-based verification | ✅ 1 tool |
| 🔗 **6M-HFACS Mapping** | Cross-reference between taxonomies | ✅ 1 tool |
| 💾 **Session Management** | Persistent analysis sessions | ✅ 4 tools |

### Prospective Cartridge (Planned 📋)

- **HFMEA** - Healthcare Failure Mode and Effect Analysis
- **HVA** - Hazard Vulnerability Analysis
- **Bowtie** - Threat and consequence analysis

### Systemic Cartridge (Planned 📋)

- **STAMP/STPA** - Control loop analysis
- **FRAM** - Functional Resonance Analysis Method

## 🔧 Available Tools

### HFACS Tools (6)
| Tool | Description |
|------|-------------|
| `rc_suggest_hfacs` | Auto-suggest HFACS codes from cause description |
| `rc_confirm_classification` | Confirm or override HFACS classification |
| `rc_get_hfacs_framework` | Get full HFACS-MES framework structure |
| `rc_list_learned_rules` | List learned classification rules |
| `rc_reload_rules` | Hot-reload YAML rules |
| `rc_get_6m_hfacs_mapping` | Get 6M-HFACS cross-reference table |

### Session Tools (4)
| Tool | Description |
|------|-------------|
| `rc_start_session` | Create new RCA session |
| `rc_get_session` | Get session details |
| `rc_list_sessions` | List all sessions |
| `rc_archive_session` | Archive completed session |

### Fishbone Tools (4)
| Tool | Description |
|------|-------------|
| `rc_init_fishbone` | Initialize fishbone diagram |
| `rc_add_cause` | Add cause to 6M category |
| `rc_get_fishbone` | Get fishbone structure |
| `rc_export_fishbone` | Export as Mermaid/Markdown/JSON |

### Why Tree Tools (4)
| Tool | Description |
|------|-------------|
| `rc_ask_why` | Progressive 5-Why questioning |
| `rc_get_why_tree` | Get Why tree structure |
| `rc_mark_root_cause` | Mark node as root cause |
| `rc_export_why_tree` | Export as Mermaid/Markdown/JSON |

### Verification Tools (1)
| Tool | Description |
|------|-------------|
| `rc_verify_causation` | Verify causation with 4-criteria test |

## 🚀 Quick Start

```bash
# Install with uv (recommended)
uv pip install -e .

# Or development mode
uv pip install -e ".[dev]"

# Run MCP Server
python -m rootcause_mcp.interface.server
```

### VS Code Integration

Add to your `.vscode/mcp.json`:

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

## 📁 Project Structure

```text
rootcause-mcp/
├── src/rootcause_mcp/
│   ├── domain/           # Domain Layer (DDD)
│   │   ├── entities/     # Session, Cause, Fishbone, WhyNode
│   │   ├── value_objects/# HFACSCode, Scores, Identifiers
│   │   ├── repositories/ # Repository interfaces
│   │   └── services/     # HFACSSuggester, CausationValidator
│   ├── application/      # Application Layer
│   │   ├── session_progress_tracker.py
│   │   └── guided_response_builder.py
│   ├── infrastructure/   # Infrastructure Layer
│   │   └── persistence/  # SQLite + SQLModel
│   └── interface/        # Interface Layer
│       ├── tools/        # MCP Tool definitions
│       ├── handlers/     # Tool handlers
│       └── server.py     # MCP Server entry
├── config/hfacs/         # YAML configurations
│   ├── hfacs_mes.yaml    # HFACS-MES framework
│   ├── fishbone_6m.yaml  # Healthcare 6M categories
│   └── keyword_rules.yaml# Classification rules
├── tests/                # Test suites
├── docs/                 # Documentation
│   └── spec_v2.md        # Full specification v2.5.0
└── memory-bank/          # Project memory (for AI)
```

## 🔗 Related MCPs

| MCP | Purpose | Integration |
|-----|---------|-------------|
| [asset-aware-mcp](https://github.com/u9401066/asset-aware-mcp) | Data decomposition & table refactoring | Pre-processing |
| HHRAG MCP | Knowledge graph retrieval | Context enrichment |
| CGU MCP | Creative divergent thinking | Cause brainstorming |

## 📚 Documentation

- [Full Specification](docs/spec_v2.md) - v2.5.0 (3700+ lines)
- [Architecture](ARCHITECTURE.md) - DDD layers
- [Roadmap](ROADMAP.md) - Cartridge expansion plan
- [Literature Review](docs/literature_review_clinical_rca.md) - HFACS-MES research

## 🔧 Development

```bash
# Run tests
pytest tests/ -v

# Code linting
ruff check src tests
mypy src --strict

# Security scan
bandit -r src

# Dead code detection
vulture src
```

## 🤝 Contributing

Contributions welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md).

## 📄 License

Apache 2.0 License - See [LICENSE](LICENSE)

---

**Made with ❤️ for Healthcare Quality Improvement**
