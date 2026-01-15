# Progress - RootCause MCP (Updated: 2026-01-16T02:25)

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
  - **18 個 MCP Tools 總計**
  - **核心哲學轉變**：從「填表式」轉為「推論式」RCA
  - 實作 Counterfactual Testing Framework (4 準則)
  - WhyTreeRepository + InMemoryWhyTreeRepository
  - 支援 Mermaid / Markdown / JSON 匯出
- ✅ **DDD 模組重構** (2026-01-15)
  - 將 2057 行 monolithic `server.py` 拆分為模組化結構
  - **interface/tools/** - 5 個 Tool 定義模組
  - **interface/handlers/** - 5 個 Handler 實作模組
  - **interface/server.py** - 精簡入口點 (~350 行)
  - **application/** - Session-aware 機制
- ✅ **6M-HFACS 對照工具** (2026-01-16)
  - rc_get_6m_hfacs_mapping (第 19 個 Tool)
  - MAPPING_6M_HFACS 完整對照表
- ✅ **Multi-Model RCA Framework 架構設計** (2026-01-16)
  - 三大分析模型類別定義
  - **領域卡匣 (Cartridge)** 概念
- ✅ **README i18n 更新** (2026-01-16)
- ✅ **Export 自動存檔功能** (2026-01-16)
- ✅ **AHRQ WebM&M 測試案例** (2026-01-16)
- ✅ **擬真化測試案例** (2026-01-16)
  - `examples/realistic_delayed_diagnosis/` - 5 個擬真 HIS 資料檔
  - 含噪音資料 (咖啡訂單、停車通知、冷氣抱怨等)
  - 完整 RCA 測試：9 原因/6 類別、5-Why depth 5、root cause 標記
- ✅ **Mermaid 語法修正** (2026-01-16)
  - Fishbone: `HEAD(["🐟 ..."]):::head` + classDef head
  - Why Tree: 移除雙括號 `[[" "]]`，改用 `[" "]`
  - 測試通過，VS Code Preview 可正常渲染
- ✅ **Deep RCA Framework v2.0 架構設計** (2026-01-16)
  - `docs/architecture/deep_rca_framework_v2.md` - 完整設計文件
  - **五層分析架構**：
    - Layer 1: Evidence Gathering (✅ 已完成)
    - Layer 2: Knowledge Enrichment (PubMed RAG, 案例匹配)
    - Layer 3: Multi-Model Analysis (Swiss Cheese, Bowtie, Systems Thinking)
    - Layer 4: Validation (三角驗證, 反事實測試, 專家共識)
    - Layer 5: Synthesis (屏障分析, 優先矩陣, 報告生成)
  - **10 個新工具規格**：
    - P0: rc_enrich_with_literature, rc_build_swiss_cheese, rc_triangulate_evidence, rc_barrier_analysis, rc_generate_report
    - P1: rc_match_similar_cases, rc_build_bowtie, rc_prioritize_actions
    - P2: rc_analyze_feedback_loops, rc_expert_review
  - **Phase 1-3 實作計畫** (共 6 週)
- ✅ **God Level RCA 案例完成** (2026-01-16)

### God Level RCA 案例 (⭐ 診斷陷阱教學)

- ✅ **Case 4: PRIS (Propofol Infusion Syndrome)** (`rc_sess_c7d0c7cc`)
  - 患者：32yo alcoholic, Status Epilepticus
  - 根本原因：品質框架「頻率導向」非「風險導向」
  - **Pathognomonic Signs**: 綠尿 + Milky blood (被忽略)
  - 診斷陷阱：酗酒背景造成診斷錨定效應
  - 所有症狀都有「合理」的替代解釋
  - 檔案：`examples/pris_status_epilepticus/` (6 files + ANALYSIS_RESULT.md)

- ✅ **Case 5: LVAD Suction Event** (`rc_sess_b20ab22a`)
  - 患者：58yo HeartMate 3 LVAD, Low Flow Alarm
  - 根本原因：專家集中模式，無分散式能力擴散機制
  - **三層診斷陷阱**：
    - Level 1: Hypovolemia (ER 誤診)
    - Level 2: Thrombosis (AI/Fellow 誤診)
    - Level 3: Suction Event (正確 - 專家級)
  - **關鍵線索**: PI=1.0 + IVS bowing INTO LV + RV dilated = RV Failure
  - 檔案：`examples/lvad_suction_event/` (6 files + ANALYSIS_RESULT.md)

- ✅ **Case 6: Dynamic LVOT Obstruction (SAM)** (`rc_sess_5c486e7c`)
  - 患者：72yo frail female, Hip fracture, GA induction crash
  - 根本原因：統計導向設計缺乏治療反應異常的重評機制
  - **三層診斷陷阱**：
    - Level 1: Hypovolemia / Light Anesthesia
    - Level 2: Massive PE / MI (給 Epi = 致命)
    - Level 3: Dynamic LVOT Obstruction (正確)
  - **Pathognomonic Signs**: Bisferiens pulse, Dagger-shaped Doppler, SAM
  - **關鍵規則**: "If Epi makes it WORSE, think OBSTRUCTION"
  - 檔案：`examples/dynamic_lvot_obstruction_sam/` (6 files + ANALYSIS_RESULT.md)

### 已完成 RCA Sessions (6 cases)

| Case | Session ID | Type | Root Cause |
|------|------------|------|------------|
| 1. UTI Misdiagnosis | rc_sess_cf93ffa4 | complication | 護理評估流程省略 |
| 2. Postoperative PE | rc_sess_da3c741c | death | 無 Caprini 評估整合 |
| 3. Hyperkalemia Missed | rc_sess_415940b8 | near_miss | 警報設計無緊急分級 |
| 4. PRIS ⭐ | rc_sess_c7d0c7cc | death | 頻率導向 vs 風險導向 |
| 5. LVAD Suction ⭐ | rc_sess_b20ab22a | complication | 專家集中無能力擴散 |
| 6. SAM/Dynamic LVOT ⭐ | rc_sess_5c486e7c | near_miss | 統計導向缺乏異常重評 |

## Doing

- 🔄 Review Deep RCA Framework v2.0 設計

## Next (Phase 3-4)

1. **Phase 1: 基礎深化** (2 週)
   - rc_enrich_with_literature (PubMed MCP 整合)
   - rc_triangulate_evidence (證據三角驗證)
   - rc_barrier_analysis (屏障建議)
   - rc_generate_report (MD 報告生成)

2. **Phase 2: 模型擴展** (2 週)
   - rc_build_swiss_cheese (Swiss Cheese 視覺化)
   - rc_build_bowtie (Bowtie 分析)
   - rc_prioritize_actions (行動優先矩陣)

3. **Phase 3: 智能增強** (2 週)
   - rc_match_similar_cases (案例匹配引擎)
   - rc_expert_review (多專家視角)

4. **進階 Tools (Phase 4)**
   - rc_execute_stage (階段流轉)
   - rc_create_action (改善措施)
   - rc_link_why_to_cause (連結 Why Tree 和 Fishbone)

## Blocked

- (無)

## Risk Notes

- 🔴 PHI/PII 資料治理待補充
- 🟠 PubMed MCP 整合複雜度待評估
- ✅ Mermaid 語法問題已解決
- ✅ DDD 模組重構完成，程式碼更易維護
- ✅ Deep RCA v2.0 架構設計完成
