# 臨床根因分析文獻回顧

> **更新日期**: 2026-01-15  
> **用途**: 為 rootcause-mcp 專案提供理論基礎和框架參考

---

## 目錄

1. [人因分析框架](#1-人因分析框架)
2. [病人安全分類系統](#2-病人安全分類系統)
3. [因果分析方法](#3-因果分析方法)
4. [重要機構與資源](#4-重要機構與資源)
5. [關鍵文獻清單](#5-關鍵文獻清單)
6. [框架選擇建議](#6-框架選擇建議)
7. [麻醉事件專題資源](#7-麻醉事件專題資源)

---

## 1. 人因分析框架

### 1.1 HFACS-MES (Human Factors Analysis and Classification System for Medical Errors)

**來源**: Jalali et al. 2024  
**PMID**: [38394116](https://pubmed.ncbi.nlm.nih.gov/38394116/)  
**PMC**: PMC10889608 (Open Access)  
**DOI**: 10.1371/journal.pone.0298606

#### 架構概述

HFACS-MES 是針對醫療錯誤改良的 HFACS 框架，包含 **5 層 25 個因素類別**：

```
┌─────────────────────────────────────────────────────────────────┐
│ Level 5: Extra-Organizational Issues (組織外部因素) [新增層]    │
│   ├─ EO-L: Legislation & Regulation (法規制度)                  │
│   └─ EO-N: National Deficiencies (國家層級缺陷)                 │
├─────────────────────────────────────────────────────────────────┤
│ Level 4: Organizational Factors (組織因素)                      │
│   ├─ OF-RM: Resource Management (資源管理)                      │
│   ├─ OF-OP: Organizational Processes (組織流程)                 │
│   ├─ OF-PSC: Patient Safety Culture (病人安全文化) [修改]       │
│   └─ OF-MOC: Management of Change (變革管理) [新增]             │
├─────────────────────────────────────────────────────────────────┤
│ Level 3: Unsafe Supervision (不安全督導)                        │
│   ├─ US-IS: Inadequate Supervision (監督不足)                   │
│   ├─ US-IP: Inadequate Planning (計畫不當)                      │
│   ├─ US-FK: Failure to Address Known Problem (未處理已知問題)   │
│   └─ US-SV: Supervisory Violations (督導違規)                   │
├─────────────────────────────────────────────────────────────────┤
│ Level 2: Preconditions for Unsafe Acts (不安全行為前提)         │
│   │                                                             │
│   ├─ Healthcare Providers (醫療提供者):                         │
│   │   ├─ PP-AMS: Adverse Mental State (不良心理狀態)            │
│   │   ├─ PP-APS: Adverse Physiological State (不良生理狀態)     │
│   │   ├─ PP-CPL: Chronic Performance Limitation (慢性能力限制)  │
│   │   └─ PP-PR: Personal Readiness (個人準備度)                 │
│   │                                                             │
│   ├─ Team & Coordination (團隊協調):                            │
│   │   ├─ TC-COM: Communication (溝通) [新獨立類別]              │
│   │   └─ TC-TD: Team Dynamics (團隊動力) [新獨立類別]           │
│   │                                                             │
│   └─ Environmental Factors (環境因素):                          │
│       ├─ EF-PE: Physical Environment (物理環境)                 │
│       ├─ EF-PMI: Person-Machine Interface (人機介面)            │
│       ├─ EF-TE: Task Elements (任務要素) [新增]                 │
│       └─ EF-PRF: Patient Related Factors (病人相關因素) [新增]  │
├─────────────────────────────────────────────────────────────────┤
│ Level 1: Unsafe Acts (不安全行為)                               │
│   │                                                             │
│   ├─ Errors (錯誤):                                             │
│   │   ├─ UA-DE: Decision Errors (決策錯誤)                      │
│   │   ├─ UA-SBE: Skill-Based Errors (技能錯誤)                  │
│   │   └─ UA-PE: Perceptual Errors (感知錯誤)                    │
│   │                                                             │
│   └─ Violations (違規):                                         │
│       ├─ UA-RV: Routine Violations (常規違規)                   │
│       ├─ UA-EV: Exceptional Violations (例外違規)               │
│       └─ UA-SV: Situational Violations (情境違規) [新增]        │
└─────────────────────────────────────────────────────────────────┘
```

#### 驗證的因果路徑 (OR = Odds Ratio)

| 上層因素 | 下層因素 | OR | 相關強度 |
|----------|----------|-----|----------|
| National Deficiencies | Management of Change | 7.33 | 強 |
| Legislation & Regulation | Patient Safety Culture | 6.94 | 強 |
| Legislation & Regulation | Organizational Processes | 2.53 | 中 |
| Management of Change | Inadequate Planning | 4.52 | 強 |
| Resource Management | Supervisory Violations | 2.90 | 中 |
| Patient Safety Culture | Failure to Address Known Problem | 2.62 | 中 |
| Inadequate Supervision | Communication | - | Φc=0.32 |
| Inadequate Planning | Patient Related Factors | - | Φc=0.32 |

#### 適用場景

- ✅ 醫療不良事件根因分析
- ✅ 系統性漏洞識別
- ✅ 跨層級因果關係分析
- ✅ 病人安全文化評估

---

### 1.2 HFACS-Healthcare

**來源**: Cohen et al. 2018  
**PMID**: [29562768](https://pubmed.ncbi.nlm.nih.gov/29562768/)  
**DOI**: 10.1177/1062860618764316

#### 架構概述

原始 HFACS 的醫療版本，**4 層約 20 個類別**，較 HFACS-MES 簡單。

#### 適用場景

- ✅ 手術室事件分析
- ✅ 程序相關不良事件
- ✅ 快速分類需求

---

### 1.3 原始 HFACS (航空版)

**來源**: Shappell & Wiegmann 2001  
**背景**: 源自美國海軍/海軍陸戰隊航空安全

#### 架構概述

4 層 19 個類別的原始框架，是所有 HFACS 變體的基礎。

---

### 1.4 Swiss Cheese Model

**來源**: Reason J. 1990. Human Error  
**概念**: 多層防護模型

```
事件 → [防護層1] → [防護層2] → [防護層3] → 不良結果
         ↓孔洞      ↓孔洞       ↓孔洞
       (失效)     (失效)      (失效)
```

#### 核心概念

- **Active Failures**: 直接導致事件的不安全行為
- **Latent Conditions**: 潛在的系統性缺陷
- **Defence Barriers**: 防護機制

---

## 2. 病人安全分類系統

### 2.1 WHO ICPS (International Classification for Patient Safety)

**來源**: World Health Organization 2009  
**參考文獻**: PMID [31437756](https://pubmed.ncbi.nlm.nih.gov/31437756/), [35796187](https://pubmed.ncbi.nlm.nih.gov/35796187/)

#### 10 個主要類別

| 類別 | 英文 | 說明 |
|------|------|------|
| 事件類型 | Incident Type | 發生了什麼 |
| 病人結果 | Patient Outcomes | 對病人的影響 |
| 病人特性 | Patient Characteristics | 病人相關因素 |
| 事件特性 | Incident Characteristics | 事件發生的情境 |
| 促成因素 | Contributing Factors | 導致事件的因素 |
| 偵測 | Detection | 如何發現事件 |
| 緩解因素 | Mitigating Factors | 減輕傷害的因素 |
| 改善行動 | Ameliorating Actions | 事後補救措施 |
| 降低風險行動 | Actions to Reduce Risk | 預防措施 |
| 組織結果 | Organizational Outcomes | 對組織的影響 |

#### 適用場景

- ✅ 標準化事件報告
- ✅ 跨機構資料比較
- ✅ 國際性研究

---

### 2.2 病人安全分類系統比較研究

**系統性回顧文獻**:

1. **Part 1 - 開發與評估方法**
   - PMID: [35878822](https://pubmed.ncbi.nlm.nih.gov/35878822/)
   - Taheri Moghadam et al. 2022
   - Journal of Biomedical Informatics

2. **Part 2 - 內容覆蓋比較**
   - PMID: [37984548](https://pubmed.ncbi.nlm.nih.gov/37984548/)
   - Taheri Moghadam et al. 2023
   - Journal of Biomedical Informatics

這兩篇論文系統性地比較了各種病人安全分類/本體系統的：
- 開發方法
- 評估方法
- 內容覆蓋範圍
- 適用性

---

## 3. 因果分析方法

### 3.1 Root Cause Analysis (RCA)

**標準流程**:
1. 事件識別與通報
2. 組成調查團隊
3. 資料收集
4. 因果分析 (5-Why, Fishbone 等)
5. 根因確認
6. 改善建議
7. 追蹤與評估

**參考**: VA NCPS RCA Guidelines

---

### 3.2 Fishbone Diagram (石川圖)

#### 醫療版 6M 分類

| 類別 | 英文 | 範例 |
|------|------|------|
| 人員 | Man/Manpower | 訓練不足、疲勞、溝通失誤 |
| 方法 | Method | SOP 不清、流程缺陷 |
| 機器 | Machine | 設備故障、維護不當 |
| 材料 | Material | 藥品過期、耗材品質 |
| 測量 | Measurement | 監測不足、指標錯誤 |
| 環境 | Milieu/Environment | 照明不足、噪音干擾 |

---

### 3.3 5-Why Analysis

**原則**: 連續追問「為什麼」直到找到根本原因

**範例**:
```
問題: 病人給錯藥
  Why 1: 護理師拿錯藥 → 藥品標籤相似
  Why 2: 為什麼標籤相似? → 兩種藥放在一起
  Why 3: 為什麼放一起? → 儲存空間不足
  Why 4: 為什麼空間不足? → 藥局擴建被擱置
  Why 5: 為什麼被擱置? → 預算優先順序問題
  
根因: 組織對藥局空間的資源配置不足
```

---

## 4. 重要機構與資源

### 4.1 國際組織

| 機構 | 網址 | 資源 |
|------|------|------|
| **WHO Patient Safety** | https://www.who.int/teams/integrated-health-services/patient-safety | ICPS, Global Action Plan |
| **WHO GPSA** | https://www.who.int/initiatives/patient-safety-flagship | Global Patient Safety Action Plan 2021-2030 |

### 4.2 美國

| 機構 | 網址 | 資源 |
|------|------|------|
| **AHRQ** | https://www.ahrq.gov/patient-safety/ | Patient Safety Network (PSNet) |
| **PSNet** | https://psnet.ahrq.gov/ | 病人安全文獻資料庫 |
| **The Joint Commission** | https://www.jointcommission.org/ | Sentinel Event, RCA 指引 |
| **IHI** | https://www.ihi.org/ | 品質改善方法論 |
| **ISMP** | https://www.ismp.org/ | 用藥安全 |
| **ECRI** | https://www.ecri.org/ | 醫療技術安全 |
| **Leapfrog Group** | https://www.leapfroggroup.org/ | 醫院安全評比 |

### 4.3 英國

| 機構 | 網址 | 資源 |
|------|------|------|
| **NHS England Patient Safety** | https://www.england.nhs.uk/patient-safety/ | PSIRF, Learn from Patient Safety Events |
| **Healthcare Safety Investigation Branch (HSIB)** | https://www.hssib.org.uk/ | 獨立調查報告 |
| **Clinical Human Factors Group** | https://chfg.org/ | 人因工程資源 |

### 4.4 澳洲

| 機構 | 網址 | 資源 |
|------|------|------|
| **ACSQHC** | https://www.safetyandquality.gov.au/ | 國家標準、指引 |

### 4.5 加拿大

| 機構 | 網址 | 資源 |
|------|------|------|
| **CPSI / Healthcare Excellence Canada** | https://www.healthcareexcellence.ca/ | 病人安全資源 |

### 4.6 台灣

| 機構 | 網址 | 資源 |
|------|------|------|
| **台灣病人安全通報系統 (TPR)** | https://www.patientsafety.mohw.gov.tw/ | 通報資料、年報 |
| **財團法人醫院評鑑暨醫療品質策進會 (JCQHC)** | https://www.jct.org.tw/ | 評鑑標準、RCA 訓練 |
| **台灣醫療品質協會 (THQA)** | https://www.thqa.org.tw/ | 品質改善資源 |

### 4.7 日本

| 機構 | 網址 | 資源 |
|------|------|------|
| **日本医療機能評価機構** | https://www.med-safe.jp/ | 醫療安全情報 |

---

## 5. 關鍵文獻清單

### 5.1 HFACS 相關

| PMID | 作者/年份 | 標題 | 重要性 |
|------|-----------|------|--------|
| [38394116](https://pubmed.ncbi.nlm.nih.gov/38394116/) | Jalali et al. 2024 | HFACS-MES framework | ⭐⭐⭐ 主要參考 |
| [29562768](https://pubmed.ncbi.nlm.nih.gov/29562768/) | Cohen et al. 2018 | HFACS-Healthcare surgery | ⭐⭐ |
| [39936321](https://pubmed.ncbi.nlm.nih.gov/39936321/) | Lee et al. 2025 | HFACS + RCA integration | ⭐⭐ 台灣醫學中心 |
| [40320337](https://pubmed.ncbi.nlm.nih.gov/40320337/) | Rashdan et al. 2025 | HF frameworks medication error review | ⭐⭐ 系統性回顧 |

### 5.2 病人安全分類

| PMID | 作者/年份 | 標題 | 重要性 |
|------|-----------|------|--------|
| [35878822](https://pubmed.ncbi.nlm.nih.gov/35878822/) | Taheri Moghadam et al. 2022 | PS classifications review Part 1 | ⭐⭐ 方法論 |
| [37984548](https://pubmed.ncbi.nlm.nih.gov/37984548/) | Taheri Moghadam et al. 2023 | PS classifications review Part 2 | ⭐⭐ 內容比較 |
| [31437756](https://pubmed.ncbi.nlm.nih.gov/31437756/) | Mitchell et al. 2020 | WHO ICPS application | ⭐ |

### 5.3 理論基礎

| 文獻 | 作者/年份 | 貢獻 |
|------|-----------|------|
| Human Error | Reason J. 1990 | Swiss Cheese Model |
| Causality | Pearl J. 2009 | 因果階梯理論 |
| To Err Is Human | IOM 1999 | 病人安全運動起點 |

---

## 6. 框架選擇建議

### 6.1 框架比較矩陣

| 特性 | HFACS-MES | HFACS-Healthcare | WHO ICPS | Fishbone 6M |
|------|-----------|------------------|----------|-------------|
| 層級數 | 5 | 4 | 10類別 | 6類別 |
| 因素數 | 25 | ~20 | ~50+ | 6 |
| 因果關係 | ✅ 明確 | ✅ 明確 | ❌ 分類為主 | ⚠️ 隱含 |
| 複雜度 | 高 | 中 | 中 | 低 |
| 學習曲線 | 陡 | 中 | 中 | 平緩 |
| 適用場景 | 深度分析 | 手術/程序 | 標準報告 | 快速分類 |

### 6.2 選擇流程建議

```
使用者需求
    │
    ├─ 快速分類 → Fishbone 6M
    │
    ├─ 標準化報告 → WHO ICPS
    │
    ├─ 手術/程序事件 → HFACS-Healthcare
    │
    └─ 深度系統分析 → HFACS-MES
```

### 6.3 對 rootcause-mcp 的建議

1. **預設框架**: Fishbone 6M (簡單易用)
2. **進階框架**: HFACS-MES (深度分析)
3. **標準化輸出**: 可對應到 WHO ICPS
4. **Agent 選擇**: 根據事件複雜度自動建議適合的框架

---

## 附錄 A: 縮寫對照表

| 縮寫 | 全稱 | 中文 |
|------|------|------|
| HFACS | Human Factors Analysis and Classification System | 人因分析分類系統 |
| HFACS-MES | HFACS for Medical Errors | 醫療錯誤人因分析系統 |
| RCA | Root Cause Analysis | 根因分析 |
| ICPS | International Classification for Patient Safety | 國際病人安全分類 |
| PSC | Patient Safety Culture | 病人安全文化 |
| MOC | Management of Change | 變革管理 |
| PRF | Patient Related Factors | 病人相關因素 |
| MAE | Medical Adverse Event | 醫療不良事件 |
| HCS | Healthcare System | 醫療照護系統 |
| HOF | Human and Organizational Factors | 人與組織因素 |

---

## 附錄 B: 更新紀錄

| 日期 | 更新內容 |
|------|----------|
| 2026-01-15 | 初版：整理 HFACS-MES, WHO ICPS, 機構資源 |
| 2026-01-15 | 新增：麻醉事件專題 (Section 7) - Closed Claims, NAP, NACOR, 藥物錯誤, 危機手冊 |

---

## 7. 麻醉事件專題資源

### 7.1 麻醉安全資料庫與通報系統

#### 7.1.1 美國 - ASA 相關資源

| 資源 | 說明 | 重要文獻 |
|------|------|----------|
| **Anesthesia Closed Claims Project** | ASA 主導的麻醉醫療糾紛索賠分析資料庫，自 1985 年開始收集 | PMID: [34019629](https://pubmed.ncbi.nlm.nih.gov/34019629/) |
| **National Anesthesia Clinical Outcomes Registry (NACOR)** | 由 Anesthesia Quality Institute (AQI) 管理的全國性臨床結果登錄系統 | PMID: [26579661](https://pubmed.ncbi.nlm.nih.gov/26579661/) |
| **Anesthesia Patient Safety Foundation (APSF)** | 麻醉病人安全基金會，提供安全指引與教育資源 | https://www.apsf.org/ |
| **AANA Foundation Closed Claims Database** | 護理麻醉師相關的醫療糾紛資料庫 | PMID: [31920200](https://pubmed.ncbi.nlm.nih.gov/31920200/), [31573491](https://pubmed.ncbi.nlm.nih.gov/31573491/) |

#### 7.1.2 英國 - National Audit Projects (NAPs)

英國皇家麻醉醫師學院 (Royal College of Anaesthetists) 主導的系列全國性審計專案：

| 專案 | 主題 | 重要文獻 |
|------|------|----------|
| **NAP4** | Major complications of airway management (呼吸道管理重大併發症) | 2011 報告 |
| **NAP5** | Accidental Awareness during General Anaesthesia (全麻術中清醒) | 2014 報告 |
| **NAP6** | Perioperative Anaphylaxis (圍術期過敏反應) | PMID: [29935567](https://pubmed.ncbi.nlm.nih.gov/29935567/) ⭐ |
| **NAP7** | Perioperative Cardiac Arrest (圍術期心跳停止) | 進行中 |

**NAP6 重點發現** (PMID: 29935567):
- 圍術期過敏發生率約 **1:10,000 次麻醉**
- 主要致敏原：Teicoplanin, Chlorhexidine, Antibiotics, NMBAs
- 收集 266 例 Grade 3-5 過敏反應

#### 7.1.3 其他國際資源

| 資源 | 國家 | 說明 |
|------|------|------|
| **WebAIRS** | 澳洲 | Australian Incident Monitoring System 網路版 |
| **SENSAR** | 西班牙 | Spanish Anaesthesia and Resuscitation Incident Reporting System |
| **SBAR** | 國際 | Situation-Background-Assessment-Recommendation 溝通工具 |

---

### 7.2 麻醉事件關鍵文獻

#### 7.2.1 Closed Claims 分析

| PMID | 作者/年份 | 主題 | 重要發現 |
|------|-----------|------|----------|
| [34019629](https://pubmed.ncbi.nlm.nih.gov/34019629/) | Warner et al. 2021 | 肺吸入分析 | 吸入性肺炎相關的索賠分析，識別高風險因素 |
| [31920200](https://pubmed.ncbi.nlm.nih.gov/31920200/) | Kremer et al. 2019 | 可預防索賠 | AANA 資料庫可預防事件分析 |
| [31573491](https://pubmed.ncbi.nlm.nih.gov/31573491/) | Golinski 2018 | AANA 索賠主題分析 | 識別反覆出現的模式 |
| [28098575](https://pubmed.ncbi.nlm.nih.gov/28098575/) | Davies & Stephens 2017 | 產科麻醉責任 | 產科麻醉相關索賠趨勢 |

#### 7.2.2 圍術期不良事件

| PMID | 作者/年份 | 主題 | 重要發現 |
|------|-----------|------|----------|
| [25390278](https://pubmed.ncbi.nlm.nih.gov/25390278/) | Nunnally et al. 2015 | 圍術期心跳停止 | NACOR 資料庫分析，發生率與風險因素 |
| [26492481](https://pubmed.ncbi.nlm.nih.gov/26492481/) | Whitlock et al. 2015 | 圍術期死亡率 | 2010-2014 NACOR 死亡率趨勢 |
| [32324655](https://pubmed.ncbi.nlm.nih.gov/32324655/) | Yeh et al. 2020 | 非手術室麻醉 | NORA 安全議題與索賠分析 |
| [30550426](https://pubmed.ncbi.nlm.nih.gov/30550426/) | Larach et al. 2019 | 惡性高熱 | Succinylcholine 使用與 Dantrolene 可及性 |

#### 7.2.3 藥物錯誤

| PMID | 作者/年份 | 主題 | 重要發現 |
|------|-----------|------|----------|
| [39352269](https://pubmed.ncbi.nlm.nih.gov/39352269/) | Sharpe et al. 2024 | 產科麻醉藥物錯誤 | 緩解策略與最佳實務 ⭐ |
| [31303712](https://pubmed.ncbi.nlm.nih.gov/31303712/) | Annie et al. 2019 | 印度麻醉藥物錯誤 | 問卷調查分析 |
| [36877159](https://pubmed.ncbi.nlm.nih.gov/36877159/) | Patel 2023 | Tranexamic Acid 誤注 | 22 例鞘內注射毒性回顧 |

#### 7.2.4 危機處理與認知輔助工具

| PMID | 作者/年份 | 主題 | 重要發現 |
|------|-----------|------|----------|
| [28079584](https://pubmed.ncbi.nlm.nih.gov/28079584/) | Clebone et al. 2017 | SPA 危機檢核表 | 小兒麻醉危機認知輔助工具開發 ⭐ |
| [27541721](https://pubmed.ncbi.nlm.nih.gov/27541721/) | Goldhaber-Fiebert et al. 2016 | Emergency Manual | Stanford 實施經驗與安全文化改變 ⭐ |
| [37003046](https://pubmed.ncbi.nlm.nih.gov/37003046/) | Goldhaber-Fiebert et al. 2023 | EM 6 年後追蹤 | 危機手冊長期使用與永續性 |
| [34939840](https://pubmed.ncbi.nlm.nih.gov/34939840/) | Hardie et al. 2022 | PPP 框架 | Patient-Procedure-People 術中危機識別 |
| [31403011](https://pubmed.ncbi.nlm.nih.gov/31403011/) | Huang et al. 2019 | 中國 EM 推廣 | 免費手冊分發對臨床使用的影響 |

#### 7.2.5 系統分析與事件通報

| PMID | 作者/年份 | 主題 | 重要發現 |
|------|-----------|------|----------|
| [34472039](https://pubmed.ncbi.nlm.nih.gov/34472039/) | Mullins et al. 2022 | 桌面系統分析 | 大學醫院麻醉科事件分析方法 ⭐ |
| [32568118](https://pubmed.ncbi.nlm.nih.gov/32568118/) | Röhsig et al. 2020 | Near-miss 分析 | 巴西大型醫院 5 年回顧性研究 |

---

### 7.3 麻醉事件常見類別

基於 Closed Claims 和通報系統資料，常見麻醉相關事件可分為：

#### 7.3.1 呼吸道相關 (Airway-related)
- 困難插管 / 插管失敗
- 意外拔管
- 吸入性肺炎
- 氣道阻塞
- 食道誤插

#### 7.3.2 藥物相關 (Medication-related)
- **LASA 錯誤**: Look-Alike Sound-Alike 藥物混淆
- **針筒交換 (Syringe Swap)**: 錯誤藥物注射
- **劑量錯誤**: 給藥過量或不足
- **過敏反應**: 未確認過敏史

#### 7.3.3 設備相關 (Equipment-related)
- 監測設備故障
- 麻醉機故障
- IV/Central line 相關併發症
- 電氣安全問題

#### 7.3.4 定位/神經相關 (Positioning/Neurological)
- 體位傷害
- 神經壓迫損傷
- 區域麻醉併發症 (如硬脊膜外血腫)

#### 7.3.5 心血管相關 (Cardiovascular)
- 術中心跳停止
- 嚴重低血壓
- 心律不整
- 空氣栓塞

#### 7.3.6 術後併發症 (Postoperative)
- 術後噁心嘔吐 (PONV)
- 殘餘神經肌肉阻斷
- 認知功能障礙 / 譫妄
- 非預期再插管

---

### 7.4 麻醉安全機構資源

| 機構 | 網址 | 主要資源 |
|------|------|----------|
| **APSF** (Anesthesia Patient Safety Foundation) | https://www.apsf.org/ | APSF Newsletter, 安全指引, 教育資源 |
| **AQI** (Anesthesia Quality Institute) | https://www.aqihq.org/ | NACOR, Morbidity & Mortality 報告 |
| **MHAUS** (Malignant Hyperthermia Association) | https://www.mhaus.org/ | MH 熱線, 治療指引 |
| **Stanford Emergency Manual Project** | https://emergencymanual.stanford.edu/ | 免費危機手冊下載 |
| **Society for Pediatric Anesthesia** | https://www.pedsanesthesia.org/ | 小兒危機檢核表 |
| **SOAP** (Society for Obstetric Anesthesia) | https://soap.org/ | 產科麻醉安全資源 |
| **Royal College of Anaesthetists** | https://rcoa.ac.uk/ | NAP 系列報告, 指引 |
| **Association of Anaesthetists** | https://anaesthetists.org/ | 安全警示, Quick Reference Handbook |

---

### 7.5 麻醉事件分類對應 HFACS-MES

將常見麻醉事件對應到 HFACS-MES 框架：

| 事件類型 | Level 1 不安全行為 | Level 2 前提條件 | Level 3 督導 | Level 4 組織 |
|----------|-------------------|-----------------|-------------|-------------|
| 藥物錯誤 (Syringe Swap) | UA-SBE 技能錯誤 | EF-PMI 人機介面, PP-AMS 不良心理狀態 | US-IP 計畫不當 | OF-OP 組織流程 |
| 困難插管失敗 | UA-DE 決策錯誤 | TC-COM 溝通, EF-TE 任務要素 | US-IS 監督不足 | OF-RM 資源管理 |
| 過敏反應未識別 | UA-PE 感知錯誤 | TC-TD 團隊動力, EF-PRF 病人因素 | US-FK 未處理已知問題 | OF-PSC 安全文化 |
| 設備故障 | - | EF-PE 物理環境, EF-PMI 人機介面 | US-IP 計畫不當 | OF-RM 資源管理 |
| 體位傷害 | UA-RV 常規違規 | PP-PR 個人準備度 | US-IS 監督不足 | OF-OP 組織流程 |

---

## 待補充項目

- [ ] 各機構網站詳細資源爬取
- [ ] 台灣 TPR 通報類別對照
- [ ] JCAHO Sentinel Event 類別
- [ ] NHS PSIRF 框架詳細說明
- [ ] 更多亞太地區資源
- [ ] 台灣麻醉醫學會安全資源
- [ ] ERAS 流程與麻醉安全的交集
- [ ] AI 在麻醉安全的應用 (PMID: 40067037)
