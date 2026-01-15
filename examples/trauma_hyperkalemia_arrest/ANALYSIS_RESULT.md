# RCA分析結果：MTP後高血鉀心跳停止

**Session ID:** `rc_sess_415940b8`  
**案例類型:** Death  
**分析日期:** 2026-01-16

---

## 📋 案例摘要

- **患者:** 32歲男性
- **事件:** 高速車禍(MVA)，肝臟撕裂傷，啟動大量輸血(MTP)
- **結果:** 02:45 PEA arrest → 死亡
- **法醫發現:** K+ > 8.5 mmol/L，**非失血致死**

### 瑞士乳酪模型 - 所有層都失效

```
Layer 1: 大量輸血舊血品 → ↑K+ 負荷
Layer 2: AKI/ATN → 無法排出 K+
Layer 3: Lab系統停機 → K+ 未檢驗
Layer 4: ECG警報被忽略 → High T-wave, Wide QRS IGNORED
Layer 5: 誤診為低血容 → 給更多液體而非治療高血鉀
```

---

## 🐟 魚骨圖 (Fishbone / Ishikawa)

```mermaid
flowchart LR

    %% === FISHBONE (ISHIKAWA) DIAGRAM ===
    %% Problem is the fish head on the right
    %% Categories branch up/down from spine

    %% Fish Head (Problem Statement)
    HEAD(["🐟 大量輸血後高血鉀心跳停止死亡。Lab系統停機導致K+未檢驗，ECG高血鉀警報(High T-wave..."]):::head

    %% Main Spine
    SPINE[ ]:::spine
    SPINE --> HEAD

    %% === UPPER BRANCHES (Personnel, Equipment, Material) ===
    PERS["Personnel"]:::category
    PERS --> SPINE
    PERS_0["護理師將ECG警報靜音，生理性警報(High T-wave, V-Ev..."]:::cause
    PERS_0 --> PERS
    PERS_1["醫師將血壓下降診斷為低血容/出血，未考慮高血鉀"]:::cause
    PERS_1 --> PERS

    EQUI["Equipment"]:::category
    EQUI --> SPINE
    EQUI_0["Lab系統(LIS)在凌晨高風險時段停機維護"]:::cause
    EQUI_0 --> EQUI
    EQUI_1["床邊監視器警報設計無法區分技術性與緊急生理性警報"]:::cause
    EQUI_1 --> EQUI

    MATE["Material"]:::category
    MATE --> SPINE
    MATE_0["使用接近到期的舊血品(高鉀含量)"]:::cause
    MATE_0 --> MATE

    %% === LOWER BRANCHES (Process, Environment, Monitoring) ===
    PROC["Process"]:::category
    PROC --> SPINE
    PROC_0["大量輸血流程(MTP)無強制電解質監測protocol"]:::cause
    PROC_0 --> PROC
    PROC_1["LIS停機計畫未考慮ICU高風險患者的STAT lab需求"]:::cause
    PROC_1 --> PROC

    ENVI["Environment"]:::category
    ENVI --> SPINE
    ENVI_0["凌晨時段人力配置減少，監測能力下降"]:::cause
    ENVI_0 --> ENVI

    MONI["Monitoring"]:::category
    MONI --> SPINE
    MONI_0["ECG監視器無自動辨識高血鉀波形並觸發警報升級"]:::cause
    MONI_0 --> MONI

    %% === STYLING ===
    classDef head fill:#e74c3c,stroke:#c0392b,stroke-width:3px,color:#fff,font-weight:bold
    classDef spine fill:#456,stroke:#234,stroke-width:4px,color:#fff
    classDef category fill:#f96,stroke:#c63,stroke-width:2px,color:#fff,font-weight:bold
    classDef cause fill:#9cf,stroke:#36a,stroke-width:1px
```

---

## 🔍 5-Why 分析樹

```mermaid
flowchart TB

    %% === 5-WHY ANALYSIS TREE ===
    %% Deeper levels show progression toward root cause

    PROBLEM["❓ 大量輸血後高血鉀心跳停止死亡"]:::problem

    %% --- Why Level 1 ---
    N58faf252("❓ 因為患者接受大量輸血(6+ units PRBC)後血鉀急遽上升，但K+檢驗無法執行(La..."):::why1
    PROBLEM -->|"Why 1<br/>📋 Autopsy: K+ > 8.5 mm..."| N58faf252

    %% --- Why Level 2 ---
    Nf4dcc8c6("❓ 因為: (1) Lab系統停機計畫只考慮IT維護便利性，未評估對重症患者的影響; (2) ..."):::why2
    N58faf252 -->|"Why 2<br/>📋 LIS Maintenance noti..."| Nf4dcc8c6

    %% --- Why Level 3 ---
    N1a2bdc57("❓ 因為醫院的病人安全治理架構是分散的、各自為政的: (1) IT部門有自己的維護排程，不需與..."):::why3
    Nf4dcc8c6 -->|"Why 3<br/>📋 醫院分工細致但silo化嚴重"| N1a2bdc57

    %% --- Why Level 4 ---
    N0b19aa45("❓ 因為醫院高層將病人安全視為各部門的「副業」而非核心任務，沒有專責的病人安全長(PSO)或跨..."):::why4
    N1a2bdc57 -->|"Why 4<br/>📋 無專責病人安全治理架構"| N0b19aa45

    %% --- Why Level 5 ---
    N52fc9155(["🎯 ROOT: 因為醫院評鑑標準和績效指標主要聚焦於財務績效和作業效率，病人安全僅是「合規項目」而非競爭優..."]):::rootcause
    N0b19aa45 -->|"Why 5<br/>📋 醫院評鑑標準缺少即時安全系統審查"| N52fc9155

    %% Analysis Depth: 5
    %% Root Causes Found: 1

    %% === STYLING ===
    %% Colors progress from red (surface) to green (root)
    classDef problem fill:#2196F3,stroke:#1565C0,stroke-width:3px,color:#fff,font-weight:bold
    classDef why1 fill:#FF5722,stroke:#E64A19,stroke-width:2px,color:#fff
    classDef why2 fill:#FF9800,stroke:#F57C00,stroke-width:2px,color:#fff
    classDef why3 fill:#FFC107,stroke:#FFA000,stroke-width:2px,color:#000
    classDef why4 fill:#8BC34A,stroke:#689F38,stroke-width:2px,color:#fff
    classDef why5 fill:#4CAF50,stroke:#388E3C,stroke-width:2px,color:#fff
    classDef rootcause fill:#9C27B0,stroke:#7B1FA2,stroke-width:4px,color:#fff,font-weight:bold
```

---

## 🎯 根本原因 (Root Cause)

> **因為醫院評鑑標準和績效指標主要聚焦於財務績效和作業效率，病人安全僅是「合規項目」而非競爭優勢或組織核心價值。醫院領導層的績效考核不包含病人安全指標(如Serious Safety Events、RCA完成率等)**

**信心度:** 92%

### HFACS 分類
- **Level 4:** Organizational Influences (組織影響)
- **Code:** OI-RP (Resource Management / Process)

---

## 💡 建議改善措施

### 立即 (0-30天)
1. **MTP Protocol 更新**
   - 加入強制電解質監測 (每2小時 K+/Ca2+/iCa)
   - 配置 POC i-STAT 作為備援

2. **警報管理**
   - HI_T_WAVE, Wide QRS 設為「不可忽略」警報
   - 連續3個生理警報觸發自動升級

3. **IT停機政策**
   - 任何影響STAT lab的停機需臨床主管簽核
   - ICU/急診必須有backup方案

### 中期 (30-90天)
4. **血庫政策**
   - MTP優先使用新鮮血品 (<7天)
   - 高風險患者(AKI)標註「避免舊血品」

5. **跨部門安全委員會**
   - 建立IT/工程/臨床的風險協調機制
   - 定期審查系統性風險

### 長期 (90-365天)
6. **領導層KPI**
   - 將病人安全指標納入高層績效考核
   - 設立專責病人安全長(PSO)

---

## 📁 相關檔案

- 原始資料: `examples/trauma_hyperkalemia_arrest/`
- 匯出報告: `data/exports/rc_sess_415940b8/`
