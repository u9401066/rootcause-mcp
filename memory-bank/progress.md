# Progress - RootCause MCP (Updated: 2026-01-15)

## Done

- ✅ 規格書 v2.5.0 完成 (docs/spec_v2.md, 3700+ 行)
- ✅ 35 個 MCP Tools 定義完成
- ✅ 漸進式輸入設計 (Level 1/2/3)
- ✅ HFACS 自動建議機制設計
- ✅ 專案風險 RCA (dogfooding)
- ✅ 專案結構建立 (from template)
- ✅ pyproject.toml 配置
- ✅ Git 初始化 + GitHub Repo 建立
  - Repo: https://github.com/u9401066/rootcause-mcp
  - Topics: mcp, root-cause-analysis, healthcare, hfacs, fishbone-diagram
  - Labels: phase1-mvp, phase2-fishbone, phase3-collab, domain-entities, mcp-tools, etc.
- ✅ 架構決策：移除 owlready2，改用 Rule Engine + Agent 方案
- ✅ 文獻回顧完成 (docs/literature_review_clinical_rca.md)
  - HFACS-MES 5 層 25 類完整架構
  - WHO ICPS 分類系統
  - 重要機構資源連結
- ✅ 多框架 YAML 配置建立
  - config/hfacs/frameworks.yaml (框架選擇器)
  - config/hfacs/hfacs_mes.yaml (HFACS-MES 完整分類)
  - config/hfacs/fishbone_6m.yaml (醫療 6M)
  - config/hfacs/who_icps.yaml (WHO ICPS)
- ✅ 麻醉事件專題資源補充 (Section 7)
  - ASA Closed Claims Project
  - NACOR 資料庫
  - UK NAP 系列 (NAP4-NAP7)
  - Emergency Manual / 危機檢核表
  - 藥物錯誤與緩解策略
- ✅ Domain Layer 實作完成
  - Entities: Session, Cause, Fishbone, WhyNode
  - Value Objects: HFACSCode, ConfidenceScore, Identifiers
  - Repositories: SessionRepository, CauseRepository, FishboneRepository
  - Services: HFACSSuggester, CausationValidator, LearnedRulesService
- ✅ Infrastructure Layer 實作完成
  - SQLite + SQLModel 持久化
  - Repository 實作
- ✅ **YAML-based Keyword Rules System** (2026-01-15)
  - config/hfacs/keyword_rules.yaml (領域規則 + 麻醉專用)
  - config/hfacs/learned_rules.yaml (學習規則結構)
  - HFACSSuggester 重構：從 YAML 動態載入規則
  - 麻醉領域 keywords 補充 (基於 Section 7)
  - HFACSLevel 新增 LEVEL_5 (HFACS-MES 新增層)
- ✅ **MCP Server 基礎架構** (2026-01-15)
  - server.py 建立
  - 5 核心 HFACS Tools 實作
- ✅ **VS Code MCP 配置** (2026-01-15)
  - .vscode/mcp.json 建立
  - ARCHITECTURE.md 更新 (含完整資料流)
- ✅ **Session & Fishbone Tools 完成** (2026-01-15)
  - **13 個 MCP Tools 總計**：
    - HFACS (5): suggest, confirm, get_framework, list_rules, reload
    - Session (4): start, get, list, archive  
    - Fishbone (4): init, add_cause, get, export
  - 整合 SQLite 持久化 (SessionRepository, FishboneRepository)
  - 支援 Mermaid / Markdown / JSON 匯出格式
  - 測試全部通過 (tests/test_mcp_tools.py)
- ✅ **5-Why Analysis & Causation Verification 完成** (2026-01-15)
  - **18 個 MCP Tools 總計**：
    - HFACS (5): suggest, confirm, get_framework, list_rules, reload
    - Session (4): start, get, list, archive  
    - Fishbone (4): init, add_cause, get, export
    - **Why Tree (4)**: ask_why, get_why_tree, mark_root_cause, export_why_tree
    - **Verification (1)**: verify_causation
  - **核心哲學轉變**：從「填表式」轉為「推論式」RCA
  - 實作 Counterfactual Testing Framework (4 準則)：
    - Temporality: 時間序列 (因先於果)
    - Necessity: 必要性 (無因則無果)
    - Mechanism: 機轉 (合理因果路徑)
    - Sufficiency: 充分性 (因是否足以產生果)
  - WhyTreeRepository + InMemoryWhyTreeRepository
  - 支援 Mermaid / Markdown / JSON 匯出
  - 測試全部通過
- ✅ **DDD 模組重構** (2026-01-15)
  - 將 2057 行 monolithic `server.py` 拆分為模組化結構
  - **interface/tools/** - 5 個 Tool 定義模組
    - hfacs_tools.py (5 tools)
    - session_tools.py (4 tools)
    - fishbone_tools.py (4 tools)
    - why_tree_tools.py (4 tools)
    - verification_tools.py (1 tool)
  - **interface/handlers/** - 5 個 Handler 實作模組
    - HFACSHandlers
    - SessionHandlers
    - FishboneHandlers
    - WhyTreeHandlers
    - VerificationHandlers
  - **interface/server.py** - 精簡入口點 (~350 行)
  - **application/** - Session-aware 機制
    - SessionProgressTracker (進度追蹤)
    - GuidedResponseBuilder (引導式回應 + 逼問)
  - 18 個 MCP Tools 全部測試通過

## Doing

- (無 - DDD 重構完成)

## Next (Phase 4)

1. **整合 GuidedResponse 到 Handlers**
   - 每個 Handler 回傳標準化 session_progress
   - 實作「逼問」機制 (push questions)

2. **VS Code 整合測試**
   - 在 VS Code 中啟動 MCP Server
   - 測試 Copilot Chat 呼叫 Tools

3. **進階 Tools**
   - rc_execute_stage (階段流轉)
   - rc_create_action (改善措施)
   - rc_link_why_to_cause (連結 Why Tree 和 Fishbone)

4. **撰寫正式單元測試**
   - pytest 測試框架
   - 覆蓋率報告

## Blocked

- (無)

## Risk Notes

- 🔴 PHI/PII 資料治理待補充
- 🟠 35 工具可能過多，先聚焦 MVP 18 工具 ✅
- ✅ owlready2 已決定移除，使用 Rule Engine + Agent 替代方案
- ✅ 「填表式→推論式」哲學轉變已實現
- ✅ DDD 模組重構完成，程式碼更易維護
