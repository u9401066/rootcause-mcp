# Progress (Updated: 2026-08-14)

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
- 完成 66 tests、81.56% coverage、Ruff、strict mypy、Bandit、Vulture 閘門
- 重寫中英文 README、API 文件與 Agent 整合指南
- 完成 Fishbone、Why Tree、Reasoning Chain、Evidence Graph 四種 Mermaid 視覺化
- 修復 CONTRACT include flags、FHIR coding、穩定 custom diagnosis code 與套件 metadata
- 使用 Mermaid CLI 11.16 實際渲染四種圖表
- 完成 clinical/RCA tool profiles 與 compact SDK 2.0 structured transport
- 完成 deterministic brief/standard/full Markdown reasoning report 與 completeness checks
- 實作 `ProvenanceVerifier` 領域服務（raw snippet 逐字引文、行號比對、SHA-256 密碼學錨定）
- 實作 `ClinicalGuidanceService` 狀態機（階段推進、完備度清單、下一步 Prompt 指令、蘇格拉底式詰問）
- 新增 `rc_audit_reasoning_state` MCP 工具（總計 37 tools）
- 實作跨平台一鍵自動安裝與註冊腳本 (`scripts/setup.ps1`, `scripts/setup.sh`, `scripts/install.py`)
- 實作 4 個真實案例端到端臨床試跑器 `scripts/run_case_trial.py` (包含 SAM、PRIS、MTP 高血鉀停跳、術後肺栓塞等 4 大麻醉重症案例，21 個原始檔案 100% 驗證，0.027s 完成)
- 實作確定性事件/證據時序圖引擎 (`build_timeline`, `render_timeline_mermaid`, `render_timeline_table`) 與 Markdown 報告範本整合
- 實作麻醉科專屬 4-Tier 倒推因果推論規範 (`anesthesia_mm_rca_protocol.yaml`)、次專科手冊 (`config/domains/`) 與 M&M 報告範本 (`anesthesia_mm_rca_report_template.md`)
- 強化臨床參數別名容錯 (`EvidenceStrength`, `EvidenceReliability`, `EvidenceType`, `rc_propose_hypothesis`, `rc_link_evidence_to_hypothesis`)
- 通過 94 個檔案的嚴格 mypy 型別檢查與 69 項單元/整合測試 (81.59% 覆蓋率)

## Doing

- 準備 v2.0.0-alpha 的發佈前審查
- 校正 HFACS handler 展示資料與 2024 taxonomy 的剩餘 legacy 命名

## Next

- 設計具 idempotent client aliases 與 rollback 的 batch case bundle
- 新增 compact case checkpoint/resume artifact，避免 Agent 重讀完整 chain
- 評估 SVG/PNG renderer 作為 optional deployment integration
- 將 legacy Why Tree 從 InMemory repository 遷移到 SQLite
- 建立正式資料庫 migration 機制
- 補 authentication、encryption-at-rest、tenant isolation 與 PHI governance
- 將共用 output envelope 細化為每個 tool 的 domain-specific output schema
- 發布 v2.0.0-alpha（不得宣稱為醫療器材或自主診斷系統）
