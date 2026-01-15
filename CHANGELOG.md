# Changelog

所有重要變更都會記錄在此檔案中。

格式基於 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.0.0/)，
專案遵循 [語義化版本](https://semver.org/lang/zh-TW/)。

## [Unreleased]

### Added
- **DDD 架構重構** - 將 2057 行 monolithic server.py 拆分為模組化結構
  - `interface/tools/` - 5 個 Tool 定義模組 (HFACS/Session/Fishbone/WhyTree/Verification)
  - `interface/handlers/` - 5 個 Handler 實作模組
  - `interface/server.py` - 精簡入口點 (~350 行)
- **Session-aware 進度追蹤機制**
  - `application/session_progress.py` - SessionProgressTracker 追蹤完成度
  - `application/guided_response.py` - GuidedResponseBuilder 引導式回應
  - 支援「逼問」(Push Questions) 機制引導 Agent 深入分析
- **18 個 MCP Tools 完整支援**
  - HFACS: `rc_suggest_hfacs`, `rc_confirm_classification`, `rc_get_hfacs_framework`, `rc_list_learned_rules`, `rc_reload_rules`
  - Session: `rc_start_session`, `rc_get_session`, `rc_list_sessions`, `rc_archive_session`
  - Fishbone: `rc_init_fishbone`, `rc_add_cause`, `rc_get_fishbone`, `rc_export_fishbone`
  - Why Tree: `rc_ask_why`, `rc_get_why_tree`, `rc_mark_root_cause`, `rc_export_why_tree`
  - Verification: `rc_verify_causation`

### Changed
- 更新 `pyproject.toml` 入口點指向 DDD server
- 保留 `rootcause-mcp-legacy` 入口點相容舊版

## [0.1.0] - 2025-12-15

### Added
- 初始化專案結構
- 新增 Claude Skills 支援
  - `git-doc-updater` - Git 提交前自動更新文檔技能
- 新增 Memory Bank 系統
  - `activeContext.md` - 當前工作焦點
  - `productContext.md` - 專案上下文
  - `progress.md` - 進度追蹤
  - `decisionLog.md` - 決策記錄
  - `projectBrief.md` - 專案簡介
  - `systemPatterns.md` - 系統模式
  - `architect.md` - 架構文檔
- 新增 VS Code 設定
  - 啟用 Claude Skills
  - 啟用 Agent 模式
  - 啟用自定義指令檔案
