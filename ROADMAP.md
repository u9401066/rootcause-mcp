# Roadmap - RootCause MCP

醫療根因分析 MCP Server 發展路線圖。

---

## 🎯 願景：Multi-Model RCA Framework

本專案不僅是「事後調查 (RCA)」工具，而是完整的 **多模型因果分析框架**，透過 **領域卡匣 (Cartridge)** 支援三大類分析模型：

```text
┌───────────────────────────────────────────────────────────────────────┐
│                        RootCause MCP                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐         │
│  │  PROSPECTIVE    │  │  RETROSPECTIVE  │  │    SYSTEMIC     │         │
│  │  前瞻性預防     │  │  回溯性調查     │  │  系統複雜性     │         │
│  ├─────────────────┤  ├─────────────────┤  ├─────────────────┤         │
│  │ • HFMEA         │  │ • HFACS ✅      │  │ • STAMP/STPA    │         │
│  │ • HVA           │  │ • 5-Whys ✅     │  │ • FRAM          │         │
│  │ • Bowtie        │  │ • Fishbone ✅   │  │ • AcciMap       │         │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘         │
│           │                   │                    │                    │
│           └────────────────────────┼────────────────────┘                    │
│                               ▼                                         │
│                    ┌─────────────────────┐                              │
│                    │  Unified Graph API  │                              │
│                    │   (MCP Tools Layer) │                              │
│                    └─────────────────────┘                              │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 已完成 ✅

### Phase 0: 規格與設計 (2026-01-14)

- [x] 規格書 v2.5.0 完成 (docs/spec_v2.md)
- [x] 35 個 MCP Tools 定義
- [x] HFACS-MES 框架整合
- [x] 醫療 6M 魚骨圖設計
- [x] 漸進式輸入設計 (Level 1/2/3)

### Phase 1: 核心架構 (2026-01-15)

- [x] Domain Layer 實作 (Entities, Value Objects, Services)
- [x] Infrastructure Layer (SQLite + SQLModel)
- [x] YAML-based 規則系統
- [x] MCP Server 基礎架構

### Phase 2: MVP Tools - Retrospective Cartridge (2026-01-15)

- [x] HFACS Tools (5)
  - rc_suggest_hfacs, rc_confirm_classification
  - rc_get_hfacs_framework, rc_list_learned_rules, rc_reload_rules
- [x] Session Tools (4)
  - rc_start_session, rc_get_session
  - rc_list_sessions, rc_archive_session
- [x] Fishbone Tools (4)
  - rc_init_fishbone, rc_add_cause
  - rc_get_fishbone, rc_export_fishbone
- [x] 測試通過 (tests/test_mcp_tools.py)

### Phase 2.5: DDD 重構 + 進階功能 (2026-01-16)

- [x] Why Tree Tools (4) - **5-Whys Cartridge**
  - rc_ask_why, rc_get_why_tree
  - rc_mark_root_cause, rc_export_why_tree
- [x] Verification Tool (1)
  - rc_verify_causation (因果驗證 - Bradford Hill Criteria)
- [x] 6M-HFACS 對照工具 (1)
  - rc_get_6m_hfacs_mapping (表圖樹 Cross-Reference)
- [x] Proximate vs Ultimate Cause 概念實作
- [x] GuidedResponse 進度追蹤整合
- [x] 總計 19 個 MCP Tools 上線

### Phase 2.6: 可稽核圖表輸出 (2026-08-09)

- [x] Fishbone Mermaid 改為可辨識的 6M Ishikawa 主脊、骨枝與次因版型
- [x] Why Tree Mermaid 支援根因、跨因果連結與重複 parent edge 合併
- [x] Reasoning Chain 產生真正的有序 Mermaid 稽核鏈
- [x] CONTRACT Evidence Graph 提供 deterministic `nodes` / `edges` 與 Mermaid
- [x] Mermaid label 正規化與特殊字元逸出
- [x] 使用 Mermaid CLI 11.16 實際渲染四種圖表
- [ ] Optional SVG/PNG renderer
- [ ] Cytoscape/D3/interactive HTML export

### Phase 2.7: Token-Efficient Reasoning Harness (2026-08-09)

- [x] `clinical` / `rca` / `all` tool profiles
- [x] SDK 2.0 compact text fallback，完整資料只保留於 structured content
- [x] Deterministic brief/standard/full Markdown reasoning report
- [x] 自動 DD 排名、Evidence Matrix、uncertainty/bias 與 completeness checks
- [x] Schema/payload UTF-8 byte regression proxies
- [ ] Transactional batch case bundle（client aliases、idempotency、rollback）
- [ ] Compact checkpoint/resume artifact
- [ ] 實際 model tokenizer 與 end-to-end cost benchmark

### Phase 2.8: Hard-Coded Provenance & Multi-Loop Guidance (2026-08-14)

- [x] `ProvenanceVerifier` 領域服務：原始病歷逐字引文 (raw_snippet)、行號定位、SHA-256 密碼學錨定
- [x] 確定性實體檔案比對（TXT, CSV, HL7, XML），完全不依賴神經網路或 LLM
- [x] `ClinicalGuidanceService` 推理狀態機：自動評估階段、完備度評分、檢查清單、下一步 Prompt 指令與蘇格拉底式詰問
- [x] `rc_audit_reasoning_state` 工具上線（總計 37 tools）
- [x] 報告自動完整性警告：防範過早診斷收斂 (premature closure)、無來源引文與未驗證證據

### Phase 2.9: Persistence, Timeline & Conflict Detection (2026-08-14)

- [x] `SQLiteWhyTreeRepository` 持久化儲存庫：消除記憶體遺失，支援 5-Why 樹狀與因果反饋網絡 100% 重啟還原
- [x] `ClinicalGapAnalyzer` 領域服務與 `rc_detect_conflicts` 工具：自動偵測診斷矛盾、藥物反常惡化反應與指引監測遺漏
- [x] `CaseCheckpointService` 快照服務與快照工具 (`rc_create_checkpoint`, `rc_restore_checkpoint`, `rc_list_checkpoints`)：不可變 JSON 狀態快照與分支實驗
- [x] 確定性臨床事件時序圖 `build_timeline` 與渲染工具 `rc_render_timeline`（支援 5 種臨床時間軸模式）
- [x] 通用 Mermaid 語法稽核與修復工具 `rc_validate_diagram`
- [x] 跨平台自動化安裝套件 (`scripts/setup.ps1`, `scripts/setup.sh`, `scripts/install.py`)，自動註冊 VS Code, Claude Desktop, Cline
- [x] 6 大真實多檔案臨床案例測試基準 (`scripts/run_case_trial.py`)，0.039 秒完成 100% 物理引文驗證

### Phase 2.10: MCP SDK 2.0 Advanced Harness & Tool Condensation (2026-08-14)

- [x] **Tool Condensation Profile (`condensed`)**：將 43 個離散工具濃縮為 **8 個多型 Facade 工具** (`rc_evidence`, `rc_hypothesis`, `rc_thinking`, `rc_audit`, `rc_report`, `rc_diagram`, `rc_checkpoint`, `rc_rca`)，大幅節省 >80% Tool Schema Token 消耗
- [x] **MCP Static Resources**：支援零 Tool Call 讀取臨床協議、範本與專科 Playbooks (`clinical://protocols/*`, `clinical://domains/*`, `clinical://templates/*`)
- [x] **MCP Dynamic Session Resource Templates** (`clinical://sessions/{session_id}/report|timeline|guidance|conflicts`)
- [x] **MCP Pre-Configured Prompts** (`anesthesia_mm_investigation`, `perioperative_crisis_differential`, `near_miss_barrier_analysis`, `delayed_diagnosis_investigation`)
- [x] **MCP Server-Level Instructions**：在握手時自動注入系統級臨床推理 Meta-Prompt

---

## 進行中 🚧

### Phase 3: Academic RCA Framework 📚

**目標：** 從「LLM 秒解」提升至「學術 Case Report」深度討論

#### 3.1 強制鑑別診斷展開 (Differential Diagnosis)

| Tool | 說明 |
|------|------|
| `rc_generate_differentials` | 強制產生 ≥5 個鑑別診斷假設 |
| `rc_evaluate_hypothesis` | 逐一評估：支持/反對證據、排除理由 |
| `rc_rank_hypotheses` | 依 Pre-test probability 排序 |

**設計原則：** 不能直接跳到答案，必須展示完整推理過程

#### 3.2 證據評分系統 (Evidence Grading)

| Tool | 說明 |
|------|------|
| `rc_add_evidence` | 新增證據 (附類型與品質評分) |
| `rc_grade_evidence` | GRADE-like 證據等級評估 |
| `rc_identify_gaps` | 自動識別證據缺口 |

**證據類型權重：**
- `pathognomonic` (1.0) - 100% 確診
- `direct_observation` (0.9) - 直接觀察
- `objective_data` (0.8) - Lab/Monitor 數據
- `documentation` (0.6) - 文件記錄
- `testimony` (0.4) - 證詞
- `inference` (0.2) - 推論

#### 3.3 反事實分析 (Counterfactual Analysis)

| Tool | 說明 |
|------|------|
| `rc_counterfactual_analysis` | "如果當時..."分析 (強制 ≥3 個) |
| `rc_calculate_impact` | 計算介入對結果的影響機率 |
| `rc_timeline_intervention` | 時間軸上標註可介入點 |

**範例輸出：**
```
如果在 08:05 做 TEE → 85% 機率提早 10 分鐘診斷
如果沒給 Epinephrine → 75% 機率避免惡化
```

#### 3.4 機轉深度解析 (Pathophysiology Deep Dive)

| Tool | 說明 |
|------|------|
| `rc_deep_dive_mechanism` | 強制深度解釋 (不能只說 "因為 SAM") |
| `rc_add_equation` | 相關公式 (e.g., Gradient = 4V²) |
| `rc_visualize_mechanism` | 機轉圖解 (Mermaid 流程圖) |

**深度等級：** `student` → `resident` → `fellow` → `attending` → `expert`

#### 3.5 多層次系統分析 (Multi-Level System Analysis)

| Tool | 說明 |
|------|------|
| `rc_analyze_individual` | 個人層次分析 |
| `rc_analyze_team` | 團隊層次分析 |
| `rc_analyze_organization` | 組織層次分析 |
| `rc_analyze_regulatory` | 法規/制度層次分析 |
| `rc_cross_level_links` | 跨層次因果連結 |

#### 3.6 文獻整合 (Literature Integration) 🔗

| Tool | 說明 |
|------|------|
| `rc_search_literature` | 整合 PubMed MCP 搜尋相關文獻 |
| `rc_link_evidence_to_pmid` | 將證據連結到 PMID |
| `rc_fetch_case_reports` | 自動搜尋相似 Case Reports |
| `rc_extract_incidence` | 從文獻提取發生率數據 |

**與 pubmed-search MCP 整合：**
- 自動搜尋診斷相關 Case Reports
- 提取 Guidelines 建議
- 連結 Mechanism 文獻

#### 3.7 教學萃取 (Teaching Point Extraction)

| Tool | 說明 |
|------|------|
| `rc_extract_pearls` | 萃取 Clinical Pearls (一句話重點) |
| `rc_identify_pitfalls` | 識別常見錯誤 |
| `rc_generate_questions` | 生成 Board-style 考題 |
| `rc_create_teaching_case` | 轉換為教學案例格式 |

#### 3.8 學術報告生成 (Academic Report Generation)

| Tool | 說明 |
|------|------|
| `rc_generate_case_report` | 生成學術 Case Report 格式 |
| `rc_export_for_journal` | 匯出期刊投稿格式 |
| `rc_generate_m_and_m` | 生成 M&M Conference 簡報 |

**輸出結構：**
1. Case Presentation (純客觀)
2. Differential Diagnosis (≥5 假設)
3. Diagnostic Reasoning (排除過程)
4. Pathophysiology (機轉深究)
5. Counterfactual Analysis (反事實)
6. System Analysis (多層次)
7. Literature Review (文獻連結)
8. Teaching Points (教學萃取)

---

### Phase 3.X: 動態圖表系統 📊

#### 3.X.1 因果 DAG (Directed Acyclic Graph)

**目標：** 從線性 5-Why 升級為多分支因果圖

| Tool | 說明 |
|------|------|
| `rc_add_causal_link` | 新增因果連結 (多對多) |
| `rc_set_link_strength` | 設定因果強度 (0-1) |
| `rc_find_all_root_causes` | 找出所有根因 (非單一) |
| `rc_calculate_contribution` | 計算各因素貢獻度 |

**因果關係類型：**
- `necessary` - 必要條件
- `sufficient` - 充分條件
- `contributing` - 促成因素
- `correlated` - 相關但非因果

#### 3.X.2 時序整合 (Timeline Integration)

| Tool | 說明 |
|------|------|
| `rc_add_timestamp` | 為節點添加時間戳 |
| `rc_build_timeline` | 自動生成時序圖 |
| `rc_validate_temporality` | 驗證時序因果 (因必須先於果) |
| `rc_identify_critical_window` | 識別關鍵時間窗口 |

#### 3.X.3 互動式輸出 (Interactive Export)

| Tool | 說明 |
|------|------|
| `rc_export_cytoscape` | 匯出 Cytoscape.js JSON |
| `rc_export_d3` | 匯出 D3.js 格式 |
| `rc_export_html_viewer` | 生成獨立 HTML 檢視器 |
| `rc_export_vscode_webview` | VS Code Webview 整合 |

**互動功能：**
- 節點可拖曳
- 點擊展開詳情
- 動態高亮因果路徑
- 時間軸播放

#### 3.X.4 動態分類系統 (Domain Cartridge)

**目標：** 不同領域使用不同分類框架

```yaml
# config/domains/anesthesia.yaml
domain: anesthesia
categories:
  - id: patient_factors
    subcategories: [anatomy, physiology, comorbidities]
  - id: airway
    subcategories: [assessment, equipment, technique]
  - id: hemodynamics
    subcategories: [monitoring, drugs, volume]
  - id: system
    subcategories: [communication, handoff, workload]
```

| Tool | 說明 |
|------|------|
| `rc_load_domain` | 載入領域卡匣 |
| `rc_list_domains` | 列出可用領域 |
| `rc_create_domain` | 創建自訂領域 |

---

### Phase 3.Y: 討論引導系統 (Guided Discussion)

**目標：** 強制 LLM 按框架展開，不能「秒解」

#### Completion Gates (完成門檻)

| Stage | Completion Criteria |
|-------|---------------------|
| DIFFERENTIAL | hypotheses ≥ 5 |
| EVALUATION | 每個假設都已評估 |
| MECHANISM | depth ≥ "fellow" level |
| COUNTERFACTUAL | scenarios ≥ 3 |
| LITERATURE | references ≥ 3 |
| SYSTEM | levels ≥ 3 (Individual/Team/Org) |

| Tool | 說明 |
|------|------|
| `rc_check_stage_complete` | 檢查階段是否完成 |
| `rc_get_missing_elements` | 取得缺少的元素 |
| `rc_force_expand` | 強制展開不足的部分 |

---

### Phase 3 Legacy: Deep RCA Framework v2.0 🧠

**已整合至上述 Academic RCA Framework**

- [x] 架構設計完成 (`docs/architecture/deep_rca_framework_v2.md`)
- [ ] ~~rc_enrich_with_literature~~ → `rc_search_literature`
- [ ] ~~rc_triangulate_evidence~~ → `rc_grade_evidence`
- [ ] ~~rc_barrier_analysis~~ → Phase 6 Swiss Cheese
- [ ] ~~rc_generate_report~~ → `rc_generate_case_report`

### Phase 3.X: VS Code 整合

- [ ] VS Code MCP Server 整合測試
- [ ] Copilot Chat 呼叫驗證
- [ ] 正式 pytest 測試套件

---

## 計劃中 📋

### Phase 4: 進階 Tools

- [ ] rc_execute_stage (階段流轉)
- [ ] rc_create_action (改善措施)
- [ ] rc_generate_report (報告生成)
- [ ] rc_check_hfacs_coverage (HFACS 覆蓋率檢查)

### Phase 5: 真實案例庫整合 🏥

**目標：** 對接權威醫療安全資料庫，讓 Agent 學習真實世界的 RCA 分析

#### 5.1 AHRQ WebM&M 整合

- [ ] Observer 層對接 AHRQ PSNet API
- [ ] 網址：[psnet.ahrq.gov/webmm](https://psnet.ahrq.gov/webmm)
- [ ] 價值：醫療 AI 的黃金題庫，每個案例附有專家完整評論
- [ ] 用途：
  - 作為 Agent 訓練的 Ground Truth (真值)
  - 案例輸入 → Agent 生成 RCA 圖 → 對比 AHRQ 專家評論
  - 自動化測試 Agent 分析品質

#### 5.2 ISMP 用藥錯誤資料庫整合

- [ ] Observer 層對接 ISMP 資料
- [ ] 網址：[ismp.org](https://www.ismp.org)
- [ ] 價值：專門收集用藥錯誤案例
- [ ] 用途：
  - 測試 Agent 對藥名混淆 (LASA) 的偵測能力
  - 測試劑量錯誤分析
  - 測試給藥途徑錯誤分析
  - 強化 Personnel/Material 類別的 HFACS 建議

#### 5.3 案例庫 Tools (規劃中)

- [ ] rc_fetch_webmm_case - 取得 WebM&M 案例
- [ ] rc_search_ismp - 搜尋 ISMP 用藥錯誤
- [ ] rc_compare_with_expert - 對比專家分析
- [ ] rc_benchmark_analysis - 分析品質評估

---

## 🔮 Cartridge 擴展計畫

### Phase 6: Prospective Cartridge (前瞻性預防模型) 🛡️

**適用情境：** 新流程上線前、導入新設備時、預防醫療疏失

#### 6.1 HFMEA (Healthcare Failure Mode and Effect Analysis)

從工業界 FMEA 改良，專門用於醫療流程風險評估

| 項目 | 說明 |
|------|------|
| **圖結構** | 流程圖 (Flowchart)，非網狀圖 |
| **節點類型** | `PROCESS_STEP` → `FAILURE_MODE` → `CAUSE` → `EFFECT` |
| **計算邏輯** | Hazard Scoring Matrix: `Severity × Probability` → Decision Tree |
| **與 RPN 差異** | 醫療版不算 Detection，直接用決策樹判斷是否介入 |

**規劃 Tools:**

- [ ] rc_init_hfmea - 初始化 HFMEA 分析
- [ ] rc_add_process_step - 新增流程步驟
- [ ] rc_add_failure_mode - 新增失效模式
- [ ] rc_calc_hazard_score - 計算危害分數
- [ ] rc_get_hfmea_matrix - 取得風險矩陣
- [ ] rc_export_hfmea - 匯出 HFMEA 報告

**Agent 任務範例：** *"列出『給藥流程』的所有步驟，並預測可能的失效模式。"*

#### 6.2 HVA (Hazard Vulnerability Analysis)

醫院防災、大量傷患機制分析

| 項目 | 說明 |
|------|------|
| **適用** | 停電、地震、疫情爆發等情境 |
| **計算邏輯** | `Risk = Probability × Impact - Mitigation` |

**規劃 Tools:**

- [ ] rc_init_hva - 初始化 HVA 分析
- [ ] rc_add_hazard - 新增危害事件
- [ ] rc_assess_vulnerability - 評估脆弱度
- [ ] rc_calc_risk_score - 計算風險值

#### 6.3 Bowtie Analysis (領結分析)

結合威脅分析和後果分析的視覺化模型

- [ ] rc_init_bowtie - 初始化領結圖
- [ ] rc_add_threat - 新增威脅
- [ ] rc_add_barrier - 新增防護屏障
- [ ] rc_add_consequence - 新增後果

---

### Phase 7: Systemic Cartridge (系統複雜性模型) 🔄

**適用情境：** 複雜系統交互作用（自動化設備、AI 輔助診療）

#### 7.1 STAMP/STPA (Systems-Theoretic Accident Model and Processes)

聚焦於「控制迴路」與「反饋缺失」，分析「所有人都遵守 SOP，但病人還是死了」的狀況

| 項目 | 說明 |
|------|------|
| **核心概念** | 事故源於「控制不當」而非單純部件故障 |
| **圖結構** | 控制結構圖 (Control Structure Diagram) |
| **節點類型** | `CONTROLLER` → `CONTROL_ACTION` → `CONTROLLED_PROCESS` → `FEEDBACK` |

**規劃 Tools:**

- [ ] rc_init_stamp - 初始化 STAMP 分析
- [ ] rc_add_controller - 新增控制器（人/系統）
- [ ] rc_add_control_action - 新增控制動作
- [ ] rc_identify_uca - 識別不安全控制行為 (Unsafe Control Action)
- [ ] rc_trace_feedback_loop - 追蹤反饋迴路
- [ ] rc_export_control_structure - 匯出控制結構圖

#### 7.2 FRAM (Functional Resonance Analysis Method)

**最先進的安全工程方法**（比 STAMP 更新）

| 項目 | 說明 |
|------|------|
| **核心概念** | 系統不是「故障」，而是功能的「變異 (Variability)」產生「共振 (Resonance)」|
| **圖結構** | 六角形功能節點 (Hexagon) |
| **節點六角** | `Input`, `Output`, `Precondition`, `Resource`, `Time`, `Control` |
| **分析重點** | 平常無害的小變異如何疊加成大災難 |

**規劃 Tools:**

- [ ] rc_init_fram - 初始化 FRAM 分析
- [ ] rc_add_function - 新增功能節點（六角形）
- [ ] rc_define_coupling - 定義功能耦合
- [ ] rc_assess_variability - 評估變異性
- [ ] rc_detect_resonance - 偵測共振模式
- [ ] rc_export_fram - 匯出 FRAM 圖

**Agent 任務範例：** *"分析 ICU 的『給藥-監測-警示』系統，找出可能產生共振的變異組合。"*

#### 7.3 AcciMap (事故地圖)

多層級系統事故分析

- [ ] rc_init_accimap - 初始化 AcciMap
- [ ] rc_add_system_level - 新增系統層級
- [ ] rc_trace_vertical_links - 追蹤垂直連結

---

### Phase 8: Cartridge 統一介面

**目標：** 讓 Agent 能在不同分析模型間無縫切換

- [ ] rc_list_cartridges - 列出可用的分析卡匣
- [ ] rc_switch_cartridge - 切換分析模式
- [ ] rc_get_cartridge_schema - 取得卡匣的圖結構定義
- [ ] rc_validate_graph - 驗證圖結構符合卡匣規範
- [ ] rc_convert_between_cartridges - 跨卡匣轉換（如 5-Whys → HFACS 層級）

```
┌─────────────────────────────────────────────────────────────┐
│                    Cartridge Registry                        │
├─────────────────────────────────────────────────────────────┤
│  ID          │ Type         │ Graph Topology │ Status       │
├──────────────┼──────────────┼────────────────┼──────────────┤
│  hfacs       │ Retrospective│ Hierarchical   │ ✅ Active    │
│  5whys       │ Retrospective│ Linear Chain   │ ✅ Active    │
│  fishbone    │ Retrospective│ Tree (6M)      │ ✅ Active    │
│  hfmea       │ Prospective  │ Flowchart      │ 📋 Planned   │
│  hva         │ Prospective  │ Matrix         │ 📋 Planned   │
│  bowtie      │ Prospective  │ Dual-Tree      │ 📋 Planned   │
│  stamp       │ Systemic     │ Control Loop   │ 📋 Planned   │
│  fram        │ Systemic     │ Hexagon Net    │ 📋 Planned   │
│  accimap     │ Systemic     │ Multi-Level    │ 📋 Planned   │
└─────────────────────────────────────────────────────────────┘
```

---

### Phase 9: 協作功能

- [ ] 多使用者支援
- [ ] 角色權限管理
- [ ] 審核流程

---

## 長期目標 🎯

- [ ] FHIR 整合
- [ ] HL7 v2 訊息解析
- [ ] 匿名化資料匯出
- [ ] 統計分析儀表板
- [ ] FDA MAUDE 資料庫整合 (醫療器材不良事件)
- [ ] WHO ICPS 完整整合
- [ ] 跨醫院案例比對（匿名化後的 Pattern Mining）
- [ ] AI 輔助 Cartridge 推薦（根據案例特徵自動建議最佳分析模型）
