# Copilot 自定義指令

此文件為 VS Code GitHub Copilot 及 Claude Code 提供專案上下文與操作規範。

---

## 專案概述

這是 **RootCause MCP 2.x 臨床推理與醫療根因分析專案**。它以 MCP SDK 2 提供 43 個 discrete tools 或 8 個 condensed facade tools，讓不同 host agent 將多來源、去識別化病歷整理成具來源血緣的時間線、鑑別診斷、Bayesian evidence links、認知偏誤審查、Fishbone／Why／HFACS 因果分析與標準化交接產物。

RootCause 是回溯性決策支援與稽核 harness，不是自主診斷或治療系統。所有 case workflow 必須遵守 exact provenance、PHI 最小化、保守因果判定及 qualified-human review。

---

## 開發哲學 💡

> **「想要寫文件的時候，就更新 Memory Bank 吧！」**
> 
> **「想要零散測試的時候，就寫測試檔案進 tests/ 資料夾吧！」**

- 不要另開檔案寫筆記，直接寫進 Memory Bank
- 今天的零散測試，就是明天的回歸測試

---

## 法規層級

```
CONSTITUTION.md          ← 最高原則（不可違反）
  │
  ├── .github/bylaws/    ← 子法（細則規範）
  │     ├── ddd-architecture.md
  │     ├── git-workflow.md
  │     ├── python-environment.md
  │     └── memory-bank.md
  │
  └── .codex/skills/rootcause-clinical-reasoning-harness/  ← RootCause case workflow canonical skill
```

你必須遵守以下法規層級：
1. **憲法**：`CONSTITUTION.md` - 最高原則，不可違反
2. **子法**：`.github/bylaws/*.md` - 細則規範
3. **技能**：`.codex/skills/rootcause-clinical-reasoning-harness/SKILL.md` - RootCause 操作程序；相容鏡像位於 `.cline/skills/rootcause-clinical-reasoning-harness/` 與 `.claude/skills/rootcause-clinical-reasoning-harness/`

---

## 架構原則

### DDD (Domain-Driven Design)
- **Domain Layer 不依賴外部**
- **DAL (Data Access Layer) 必須獨立**
- 使用 Repository Pattern
- 依賴方向：`Presentation → Application → Domain ← Infrastructure`

詳見：`.github/bylaws/ddd-architecture.md`

### 目錄結構約定

#### 後端 (Python/Go/Rust)
```
src/
├── Domain/           # 核心領域（無外部依賴）
├── Application/      # 應用層（用例編排）
├── Infrastructure/   # 基礎設施（DAL、外部服務）
└── Presentation/     # 呈現層（API、CLI）
```

#### 前端 (React/Vue)
```
src/
├── domain/           # 型別定義、業務規則
├── application/      # Hooks、Stores、Services
├── infrastructure/   # API Client、Storage
└── presentation/     # Components、Pages、Layouts
```

---

## Python 環境（uv 優先）

- **優先使用 uv** 管理套件和虛擬環境
- 新專案必須建立 `pyproject.toml` + `uv.lock`
- 禁止全域安裝套件

```bash
# 初始化環境
uv venv
uv sync --all-extras

# 安裝依賴
uv add package-name
uv add --dev pytest ruff mypy bandit vulture
```

詳見：`.github/bylaws/python-environment.md`

---

## Memory Bank 同步

每次重要操作必須更新 Memory Bank：

| 操作 | 更新文件 |
|------|----------|
| 完成任務 | `progress.md` (Done) |
| 開始任務 | `progress.md` (Doing), `activeContext.md` |
| 重大決策 | `decisionLog.md` |
| 架構變更 | `architect.md` |

詳見：`.github/bylaws/memory-bank.md`

---

## Git 工作流

提交前必須執行檢查清單：
1. ✅ Memory Bank 同步（必要）
2. 📖 README 更新（如需要）
3. 📋 CHANGELOG 更新（如需要）
4. 🗺️ ROADMAP 標記（如需要）

詳見：`.github/bylaws/git-workflow.md`

---

## 可用 Skills

RootCause canonical skill 位於 `.codex/skills/rootcause-clinical-reasoning-harness/`，並鏡像至 `.cline/skills/` 與 `.claude/skills/` 的同名目錄。其他通用開發 skills 仍位於 `.claude/skills/`：

### 核心技能
| Skill | 用途 | 觸發詞 |
|-------|------|--------|
| **rootcause-clinical-reasoning-harness** | 多來源病歷的 evidence-grounded DDx + RCA 與跨-agent handoff | RootCause, raw 病歷, DDx, RCA, M&M, Fishbone, HFACS, causation |
| **git-precommit** | Git 提交前編排器 | GIT, gc, commit, push, 提交, 推送 |
| **ddd-architect** | DDD 架構輔助（前後端） | DDD, arch, 架構, 新功能, scaffold |
| **code-refactor** | 主動重構與模組化 | RF, refactor, 重構, 拆分, 模組化 |
| **code-reviewer** | 程式碼審查 | CR, review, 審查, 檢查, PR |
| **test-generator** | 測試生成 + 靜態分析 | TG, test, 測試, coverage, pytest |
| **security-reviewer** | 安全性審查 (OWASP) | SEC, security, 安全, OWASP, 漏洞 |

### 記憶管理
| Skill | 用途 | 觸發詞 |
|-------|------|--------|
| **memory-updater** | Memory Bank 同步 | MB, memory, 記憶, 進度, 更新記憶 |
| **memory-checkpoint** | 記憶檢查點 | CP, checkpoint, 存檔, 保存, dump |

### 文檔管理
| Skill | 用途 | 觸發詞 |
|-------|------|--------|
| **readme-updater** | README 智能更新 | readme, 說明, 文檔同步 |
| **readme-i18n** | 多語言 README | i18n, 翻譯, 多語言, bilingual |
| **changelog-updater** | CHANGELOG 更新 | CL, changelog, 變更, 版本 |
| **roadmap-updater** | ROADMAP 狀態追蹤 | RM, roadmap, 路線, 里程碑 |
| **git-doc-updater** | Git 提交前文檔檢查 | docs, 文檔, sync docs, release |

### 專案管理
| Skill | 用途 | 觸發詞 |
|-------|------|--------|
| **project-init** | 專案初始化 | init, new, 新專案, bootstrap |
| **skill-generator** | 生成新 Skill | SG, new skill, 建立技能 |

### 工作流 Skills（組合多個 Skills）
| Skill | 用途 | 觸發詞 |
|-------|------|--------|
| **feature-development** | 完整功能開發流程 | FD, 新功能, 開發功能, feature |
| **bug-fix** | 結構化 Bug 修復 | BF, 修 bug, fix bug, debug |
| **code-review-workflow** | 完整程式碼審查 | PRW, 審查流程, review workflow |
| **release** | 版本發布準備 | REL, release, 發布, 版本發布 |

---

## 💸 Memory Checkpoint 規則

為避免對話被 Summarize 壓縮時遺失重要上下文：

### 主動觸發時機
1. 對話超過 **10 輪**
2. 累積修改超過 **5 個檔案**
3. 完成一個 **重要功能/修復**
4. 使用者說要 **離開/等等**

### 執行指令
- 「記憶檢查點」「checkpoint」「存檔」
- 「保存記憶」「sync memory」

### 必須記錄
- 當前工作焦點
- 變更的檔案列表（完整路徑）
- 待解決事項
- 下一步計畫

---

## 常用指令

```
「準備 commit」       → 執行完整提交流程
「快速 commit」       → 只同步 Memory Bank
「建立新功能 X」      → 生成 DDD 結構
「review 程式碼」     → 程式碼審查
「更新 memory bank」  → 同步專案記憶
「checkpoint」        → 記憶檢查點
「新功能開發」        → 完整功能開發流程
「修 bug」            → 結構化 Bug 修復
```

---

## 回應風格

- 使用**繁體中文**
- 提供清晰的步驟說明
- 引用相關法規條文
- 執行操作後更新 Memory Bank

---

## 注意事項

- 修改程式碼前先更新規格文檔
- 程式碼是文檔的「編譯產物」
- 遵循 Conventional Commits 格式
- 前後端都採用 DDD 架構
