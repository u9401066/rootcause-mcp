# 案例 4: Propofol Infusion Syndrome (PRIS)

## 案例概述

- **患者**: 32歲男性 (WU, T.H.)
- **入院診斷**: 酒精戒斷癲癇重積狀態 + 吸入性肺炎
- **關鍵介入**: Propofol 持續輸注鎮靜 (60 ml/hr × 48h+)
- **結果**: 多重器官衰竭，被誤診為 Sepsis + Alcoholic Pancreatitis

## 「God Level」難度分析

### 診斷陷阱

每個 PRIS 症狀在酗酒患者身上都有「合理的替代解釋」：

| PRIS 症狀 | 被誤診為 |
|-----------|----------|
| 代謝性酸中毒 | Sepsis |
| 高 Lipase | Alcoholic Pancreatitis |
| 橫紋肌溶解 | Seizure-related |
| 心律不整 | Electrolyte imbalance |
| 綠色尿液 | 被忽略 |
| Milky blood | "Maybe hemolyzed?" |

### 被忽略的 Pathognomonic Signs

1. **綠色尿液** - Propofol 代謝產物
2. **Milky blood** - Propofol 脂質載體造成的高三酸甘油酯血症
3. **Triglycerides: -- (Not ordered)** - 沒人想到要驗！

### 劑量計算

```
Propofol 1%: 10 mg/ml
60 ml/hr = 600 mg/hr
Patient: 75 kg
Rate: 600 mg/hr ÷ 75 kg = 8 mg/kg/hr

PRIS Risk Threshold: > 4-5 mg/kg/hr for > 48 hours
This patient: 8 mg/kg/hr × 48+ hours = HIGH RISK
```

## 資料來源

| 檔案 | 內容 |
|------|------|
| DATA_SOURCE_01 | ER 轉入單 - Propofol 開始使用 |
| DATA_SOURCE_02 | ICU 24h Flowsheet - 劑量逐步增加 |
| DATA_SOURCE_03 | Lab 系列 - 惡化趨勢 |
| DATA_SOURCE_04 | 護理交班 - 綠尿/Milky blood |
| DATA_SOURCE_05 | ECG - Brugada-like pattern |

## 正確處置

1. ❌ 不是加抗生素
2. ❌ 不是當成 Pancreatitis 治療
3. ✅ **立即停止 Propofol**
4. ✅ 換成其他鎮靜劑 (Dexmedetomidine, Midazolam)
5. ✅ 支持性治療 (RRT if needed)
