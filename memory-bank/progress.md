# Progress (Updated: 2026-08-18)

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
- 實作 6 組案例 fixture 的 preliminary regression/demo `scripts/run_case_trial.py`
  （SAM、PRIS、MTP 高血鉀、術後肺栓塞、LVAD 幫浦吸附、延遲診斷）；
  它檢查片段比對與 preview plumbing，不代表 release acceptance 或臨床正確性
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
- 完成 multi-source manifest、whole-file SHA-256、exact provenance、strict canonical
  timestamp、direct-LR DDx、RCA lineage 與 gated unified report 的 native MCP 驗收
- 完成 patched runtime dependency lock、frozen `pip-audit`、Python 3.12／3.13、
  package／installed-wheel release gate 定義；實際結果以當次 CI/release run 為準
- 完成 Codex／Claude／Cline RootCause harness 鏡像與 Copilot／AGENTS 整合，並明示
  raw binary extraction、PHI、人工核准與 preliminary-first 邊界
- 完成 typed nested final report、machine-readable `conformance_checks[]`、root/audit
  lineage/disposition、unique DDx、typed planned tests、authorized reviewer/time/hash
  與 recursive final immutability 的 deterministic P0 gates
- 建立去診斷／檔名提示的六案例 public engineering corpus 與 fail-closed eval
  runner scaffold；public reference rubrics 不作 blinded gold claim
- 完成 2.0.0a2 typed source review、source-faithful temporal record、mechanism breadth
  audit、explicit leading selection、verified literature LR calibration、per-cause
  HFACS review、root/causation/readiness/hash recomputation 與 immutable final gates
- 完成繁體中文 clinician Markdown（專有名詞保留 English）、46/25/24/8 tool
  profiles、5 prompts、雙語 README／harness／API／Pages 同步
- 本機 release QA：431 tests、84.36% branch coverage、Ruff、Mypy、Bandit、Vulture、
  pip-audit、build/Twine、installed-wheel normal MCP stdio、desktop/mobile Playwright
  全部通過

## Doing

- 將 2.0.0a2 分段 commit、push、PR 合併至 default `master`，等待 GitHub CI／Pages
  成功後建立 prerelease tag
- 正式跨-Agent 36-run、private case bundle、分離的 private holdout、trusted trace、
  兩名臨床 reviewer 與裁決仍為 `AGENT_EVAL_NOT_ESTABLISHED`

## Next

- 將 protocol/domain/timeline YAML 收斂為 versioned runtime PolicyCatalog，session
  pin policy version/digest，並用行為測試證明設定變更真正生效
- 以至少三個真實 runtime 完成 3 × 6 × 2 formal matrix，使用 repo 外 private case
  bundle、分離的 private holdout、trusted server/proxy trace、兩名 qualified clinical
  reviewers 與分歧裁決
- 建立正式資料庫 migration 機制 (Alembic)
- 補 authentication、trusted reviewer RBAC、encryption-at-rest、tenant isolation、
  retention enforcement 與 PHI governance
- 將 corrective action、owner、due date 與 effectiveness measure 建成 first-class
  domain/report contract
- 將共用 output envelope 細化為每個 tool 的 domain-specific output schema
- 完成 private 36-run 與臨床盲評後再評估是否能從 engineering alpha 升格；不得
  宣稱醫療器材、自主診斷或已建立臨床因果
