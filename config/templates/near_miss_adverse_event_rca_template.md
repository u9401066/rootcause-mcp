# 🏥 醫療不良事件 / 異常未遂 (Near Miss) 結構化根因分析報告 (RCA Report)

**專案/事件主題:** `{{report_title}}`  
**案例 ID:** `{{session_id}}` | **報告編號:** `{{report_id}}`  
**產出時間:** {{generated_at}} | **審查狀態:** {{report_status}}  
**報告層級:** `{{detail_level}}` | **引擎驗證:** Deterministic Non-Death / Near-Miss Zero-LLM Aggregation  

> ⚠️ **病人安全與醫療品質改善免責宣告 (Confidential Quality Improvement Document):**  
> 本報告為病人安全事件（含未遂事件 Near Miss、藥物不良事件 ADE、醫療器材警報事件、延遲診斷）之結構化根本原因分析 (RCA) 報告。  
> 目的在於「找出系統脆弱點與防線失效原因 (Barrier Failure)」，建立防呆與容錯防護網，非針對個別臨床人員之過失究責。

---

## 1. 事件概要與時序還原 (Event Chronology & Context)

{{executive_summary}}

### ⏱️ 事件發生與發現時序圖 (Mermaid Timeline)

{{timeline_diagram}}

### 📋 時序里程碑矩陣

{{timeline_table}}

---

## 2. 異常機轉鑑別與診斷分析 (Differential & Mechanism Evaluation)

### 🔍 異常機轉假說與貝氏後驗機率

{{hypothesis_table}}

### 📋 關鍵排除與確認分析 (Rule-In / Rule-Out Summary)

- **確認主要機轉/假說:** {{top_diagnosis}} (後驗機率: {{top_probability}})
- **主動排除之可能原因:** {{rule_out_summary}}
- **評估之高危潛在危害:** {{must_not_miss_evaluated}}

---

## 3. 瑞士乳酪防線與屏障分析 (Swiss Cheese Defense & Barrier Analysis)

| 防線層級 (Barrier Layer) | 原設計之安全防護機制 | 本次事件之失效模式 (Failure Mode) | 為何未能攔截？ (Latent Gap) |
| --- | --- | --- | --- |
| **開單/醫囑端 (Prescribing/Order)** | 系統自動檢核 / 劑量警示 / 適應症確認 | 醫囑過期未續開 / 藥物特殊代謝風險未評估 | 系統無強制彈窗或直接過期無交接提醒 |
| **調劑/傳遞端 (Dispensing/Transmission)** | 藥師雙重覆核 / 報告即時傳真推播 | 傳真至護理站後未落實閉環簽收 (Closed-loop) | 無專人跟催未讀異常報告 (Critical Alert) |
| **給藥/執行端 (Administration/Nursing)** | 三讀五對 / 給藥條碼掃描 / 標籤辨識 | 針劑抽錯 (Syringe Swap) / 劑量設定錯誤 | 標籤顏色相近、急迫情境未落實雙人覆核 |
| **監測/警報端 (Monitoring & Alarm)** | 生理監視器自動警報 / 趨勢圖警示 | 警報被靜音或被視為假警報 (Alarm Fatigue) | 閾值設定過寬、同仁產生習慣性忽略 |
| **攔截/挽救端 (Rescue & Interception)** | 臨床惡化即時識別 / 團隊呼叫 (Code/RRT) | 成功識別並及時給予解毒/調整處置 | 依賴個人經驗，缺乏標準化危機處置卡 |

---

## 4. 實體證據矩陣與資料血緣 (Evidence Matrix & Physical Grounding)

{{evidence_table}}

---

## 5. 後設認知安全與 HFACS-MES 系統歸因 (Cognitive & System Audit)

### 🧠 認知偏誤審查 (Cognitive Bias Review)

{{cognitive_safety_section}}

### 🛡️ HFACS-MES 組織與環境層級歸因 (Latent Organizational Factors)

- **操作層面 (Unsafe Acts):** 慣性依賴口頭交班、未確認原始檢驗/波形數值。
- **前提條件 (Preconditions):** 跨科溝通落差、人力配置緊張、工作環境噪音與干擾。
- **督導與流程 (Supervision & Process):** 缺少異常檢驗值通報追蹤系統 (Critical Lab Tracking)。
- **組織與環境 (Organization & Environment):** 儀器人機介面 (HMI) 警報邏輯設計不良、缺乏防呆硬體。

---

## 6. 自動化結構與品質檢核 (Automated Quality Checks)

{{automated_checks_section}}

{{quality_metrics_section}}

---

## 7. 視覺化推理與因果網絡 (Visual Reasoning Diagrams)

### 📊 推理決策審計流 (Mermaid Reasoning Flow)

{{reasoning_chain_diagram}}

### 🕸️ 證據-假說支持/反對圖譜 (Mermaid Evidence Graph)

{{evidence_graph_diagram}}

---

## 8. 系統性防呆對策與持續改善行動計畫 (Poka-Yoke & Action Plan)

### 🛡️ 防呆與工程控制改善 (Engineering / Poka-Yoke Controls)

- [ ] **強制閉環通報 (Closed-Loop Alert):** 關鍵異常報告（Critical Value）若 30 分鐘內未被開單醫師確認，自動升級通知值班主管。
- [ ] **電子防呆鎖定 (System Lockout):** 針對高危險藥物與停藥醫囑，系統強制要求填寫復藥日期或交班註記。
- [ ] **器材防呆設計:** 醫療儀器參數警報與生理回饋連動，避免單純依賴聲音警報。

### 📋 病安委員會追蹤與主管簽核

- **分析專案負責人:** ___________________________  **日期:** ______________
- **單位護理長/科主任:** _______________________  **日期:** ______________
- **院級病人安全委員會主管:** ___________________  **日期:** ______________

---

## 9. 密碼學存證與稽核紀錄 (Audit Trail & SHA-256 Digest)

- **執行 Agent:** `{{generated_by}}`
- **報告規格版本:** `{{report_version}}`
- **實體證據筆數:** {{total_evidence_count}} 筆 ({{verified_evidence_count}} 筆完成原始檔案 Hash 驗證)
- **假說總數:** {{total_hypotheses_count}} 個
- **推論步數:** {{reasoning_steps_count}} 步
- **內容 SHA-256 指紋:** `{{content_hash}}`
