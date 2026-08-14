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
- 實作 6 個真實案例端到端臨床試跑器 `scripts/run_case_trial.py` (包含 SAM、PRIS、MTP 高血鉀、術後肺栓塞、LVAD 幫浦吸附、延遲診斷等 6 大案例，31 個原始檔案 100% 驗證，0.039s 完成)
- 實作 Mermaid 語法稽核與自動修復工具 `rc_validate_diagram` 與時序圖渲染工具 `rc_render_timeline`
- 實作 5 大臨床時序演變模式 (`perioperative_sequence`, `acute_crisis`, `delayed_diagnosis`, `barrier_failure`, `device_incident`)
- 實作非死亡醫療不良事件與 Near Miss RCA 規範 (`non_death_adverse_event_protocol.yaml`) 與專用報告範本 (`near_miss_adverse_event_rca_template.md`)
- 實作 `SQLiteWhyTreeRepository` 持久化儲存庫，支援 WhyChain, WhyNode 與 CausalLink 100% 重啟還原
- 實作 `ClinicalGapAnalyzer` 領域服務與 `rc_detect_conflicts` 工具，自動偵測診斷矛盾、藥物反常惡化反應與指引監測遺漏
- 實作 `CaseCheckpointService` 快照服務與快照工具 (`rc_create_checkpoint`, `rc_restore_checkpoint`, `rc_list_checkpoints`)
- 實作 **Tool Condensation Profile (`condensed`)**，將 43 個離散工具濃縮為 **8 個多型 Facade 工具**，大幅降低 >80% Tool Schema Token 消耗
- 實作 **MCP Static Resources (`clinical://*`)** 與 **Dynamic Session Resource Templates**
- 實作 **MCP Pre-Configured Clinical Prompts** (`anesthesia_mm_investigation`, 等 4 大臨床 Prompt)
- 實作 **Server-Level Instructions & Meta-Prompt** 握手自動注入
- 通過 102 個檔案的嚴格 mypy 型別檢查與 82 項單元/整合測試 (80.73% 覆蓋率)

## Doing

- 準備 v2.0.0-alpha 的發佈前審查
- 更新 memory bank 與 Git 階段性 commit

## Next

- 建立正式資料庫 migration 機制 (Alembic)
- 補 authentication、encryption-at-rest、tenant isolation 與 PHI governance
- 將共用 output envelope 細化為每個 tool 的 domain-specific output schema
- 發布 v2.0.0-alpha（不得宣稱為醫療器材或自主診斷系統）
