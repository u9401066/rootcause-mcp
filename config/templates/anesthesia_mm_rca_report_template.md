# 🏥 麻醉與圍術期重症事件 4-Tier 根因分析報告 (M&M Case Report)

**會議/報告主題:** `{{report_title}}`  
**案例 ID:** `{{session_id}}` | **報告編號:** `{{report_id}}`  
**產出時間:** {{generated_at}} | **審查狀態:** {{report_status}}  
**報告層級:** `{{detail_level}}` | **引擎驗證:** Deterministic 4-Tier Zero-LLM Aggregation  

> ⚠️ **麻醉科臨床品質與病安審查宣告 (Confidential Quality Improvement Document):**  
> 本報告為麻醉部圍術期併發症與死亡 (Morbidity & Mortality, M&M) 結構化根因分析 (RCA) 文件。  
> 目的在於從「終末休克/心跳停止」往前回溯「5H5T 急性機轉」、「術中觸發點（病人/外科/麻醉）」與「系統防護漏洞」，以建立預防再發機制，不代表單一醫療人員之法律過失認定。

---

## 1. 案例概要與時間軸 (Case Timeline & Clinical Event)

{{executive_summary}}

---

## 2. Tier 0 & Tier 1: 終末心律與 ACLS 5H5T 可逆機轉鑑別

### 🔍 5H5T 鑑別診斷與貝氏後驗機率 (Ranked 5H5T Differential)

{{hypothesis_table}}

### 📋 5H5T 排除與支持理由分析 (Rule-In / Rule-Out Audit)

- **主要診斷假說:** {{top_diagnosis}} (後驗機率: {{top_probability}})
- **關鍵排除機轉 (Rule-Out):** {{rule_out_summary}}
- **緊急致命假說檢視:** {{must_not_miss_evaluated}}

---

## 3. Tier 2: 術中事件回溯與三大觸發流分析 (Intraoperative Trigger Streams)

### 🩺 A. 病人初始狀況與術前評估 (Patient Baseline & Pre-op Misses)

- **術前漏網之魚/潛在體質:** 檢視是否有未被察覺的心肌肥厚 (HOCM/SAM substrate)、主動脈瓣狹窄、心律不整、低血容量或長期用藥影響。
- **ASA 分級與器官儲備力:** 評估脆弱度 (Frailty) 與對血壓波動之耐受度。

### 🔪 B. 外科手術處置與機械性干擾 (Surgical Events & Mechanical Insults)

- **手術操作事件:** 檢視是否有隱匿性大出血、骨水泥反應 (BCIS)、牽拉引發迷走神經反射、氣腹過高或下腔靜脈受壓。
- **手術-麻醉溝通時效:** 外科手術步驟變更時是否即時通知麻醉團隊。

### 💉 C. 麻醉處置、用藥與通氣管理 (Anesthesia Management & Pharmacology)

- **麻醉藥物與血管活性藥物作用:** 誘導藥物劑量、強心升壓劑選擇（是否在動態阻塞時誤用 Inotropes）、局麻藥用量 (LAST 鑑別)。
- **氣道與通氣監測:** ETT 位置、尖峰氣道壓 (PIP)、EtCO2 劇烈變化、動脈波形特徵 (Bisferiens / Spike and Dome)。

---

## 4. 實體證據矩陣與來源錨定 (Evidence Matrix & Physical Grounding)

{{evidence_table}}

---

## 5. Tier 3: 潛在系統性漏洞與認知安全審查 (Latent System Factors & Cognitive Audit)

### 🧠 認知偏誤與防護審查 (Cognitive Bias Audit)

{{cognitive_safety_section}}

### 🛡️ HFACS-MES 系統層級歸因 (Human Factors & System Gaps)

- **不安全行為 (Unsafe Acts):** 是否有未確認動脈波形特徵、未及早執行 POCUS/TEE 即給藥。
- **不安全前提 (Preconditions):** 外科-麻醉溝通斷層（如：「病人是不是太淺？」之定錨陷阱）、警報疲勞。
- **組織與環境 (Organizational/Environment):** 手術室內缺乏即時 TEE 設備支援流程、急救藥物推車配置問題。

---

## 6. 自動化結構與品質完整度檢核 (Automated Quality Checks)

{{automated_checks_section}}

{{quality_metrics_section}}

---

## 7. 視覺化推理與因果鏈圖 (Visual Reasoning & Causal Network)

### 📊 麻醉推理審計軌跡 (Mermaid Reasoning Flow)

{{reasoning_chain_diagram}}

### 🕸️ 證據-診斷支持/反駁網絡 (Mermaid Evidence Graph)

{{evidence_graph_diagram}}

---

## 8. 改善對策與科內預防再發行動計畫 (Action Plan & QI Measures)

### 🚫 圍術期高危禁忌警示 (Avoid Harm)

- [ ] 遭遇頑固性低血壓伴隨強心劑反常惡化時，立即停用 Beta-1 促效劑，改採擴容 + 純 Alpha-1 血管收縮劑 (Phenylephrine) + Esmolol。
- [ ] 高劑量 Propofol (>4.5 mg/kg/hr) 輸注超過 48 小時，強制常規檢驗三酸甘油酯 (Triglycerides) 與 CPK。

### 🎯 危機處理 SOP 與臨床指引修訂 (Protocol Revision)

- [ ] 制定「術中難治型休克與原因不明崩潰之 Bedside TEE/POCUS 快速掃描流程 (RUSH/Focus protocol)」。
- [ ] 更新手術室與恢復室危機檢查清單 (Crisis Checklists)。

### 📋 M&M 審查小組簽核 (Departmental Quality Committee Sign-off)

- **麻醉科報告醫師:** ___________________________  **日期:** ______________
- **麻醉品質委員會主席:** _______________________  **日期:** ______________
- **科主任核定:** _______________________________  **日期:** ______________

---

## 9. 密碼學存證與稽核紀錄 (Audit Trail & SHA-256 Digest)

- **執行 Agent / 模組:** `{{generated_by}}`
- **報告規格版本:** `{{report_version}}`
- **實體證據筆數:** {{total_evidence_count}} 筆 ({{verified_evidence_count}} 筆完成原始檔案 Hash 驗證)
- **鑑別診斷假說數:** {{total_hypotheses_count}} 個
- **推論步數:** {{reasoning_steps_count}} 步
- **內容 SHA-256 指紋:** `{{content_hash}}`
