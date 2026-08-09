# Progress (Updated: 2026-08-09)

## Done

- 完成開源專案調查（MEDDxAgent, ClinClaw, fastmcp, fhir.resources）
- 確認核心定位：醫學推理 + 鑑別診斷專用 MCP Harness
- 建立 feat/sdk-2-contract-level-dd 分支
- 升級 MCP SDK 1.27.0 → 2.0.0
- 實作 EvidenceQuality VO (Oxford CEBM 啟發)
- 實作 ClinicalConcept VO (SNOMED/ICD-10/RxNorm/LOINC)
- 實作 Evidence Entity (first-class, 含 provenance tracking)
- 實作 Hypothesis Entity (Bayesian DDx, LR updating)
- 新增 EvidenceId, HypothesisId, ReasoningStepId 強型別 ID
- 實作 ReasoningStep Entity (Chain of Thought)
- 建立 docs/research/existing_solutions.md 研究文件
- 建立 server_v2.py (SDK 2.0 callback API)
- Merge feat/sdk-2-contract-level-dd → master
- 實作 ClinicalReasoningOrchestrator (Agent-friendly API)
- 新增 10 個 MCP Tools (Evidence/DD/Reasoning/CONTRACT)
- 修復 SDK 2.0 inputSchema → input_schema 參數名
- 完成 36-tool 精確 dispatch registry 與 structured output envelope
- 接通 Evidence/Hypothesis/Thinking/Reasoning SQLModel persistence 與重啟還原
- ContractReport 納入真實 ThinkingChain/ReasoningChain 與品質指標
- 因果驗證統一委派 CausationValidator，移除過度自信預設
- 支援 HFACS-MES 2024 代碼並保留 legacy code 讀取
- 移除 MCP SDK 1.x server 與 legacy adapter
- 完成 48 tests、80% coverage、Ruff、strict mypy、Bandit、Vulture 閘門
- 重寫中英文 README、API 文件與 Agent 整合指南

## Doing

- 準備 v2.0.0-alpha 的發佈前審查
- 校正 HFACS handler 展示資料與 2024 taxonomy 的剩餘 legacy 命名

## Next

- 將 legacy Why Tree 從 InMemory repository 遷移到 SQLite
- 建立正式資料庫 migration 機制
- 補 authentication、encryption-at-rest、tenant isolation 與 PHI governance
- 將共用 output envelope 細化為每個 tool 的 domain-specific output schema
- 發布 v2.0.0-alpha（不得宣稱為醫療器材或自主診斷系統）
