# 案例 5: LVAD Suction Event (被誤診為 Hypovolemia/Thrombosis)

## 案例概述

- **患者**: 58歲男性 (CHEN, W.K.)
- **病史**: 擴張性心肌病變，HeartMate 3 LVAD 植入 3 個月
- **主訴**: Controller "Low Flow" 警報 + 可樂色尿液
- **結果**: 被誤診，錯誤處置導致惡化

## 「God Level」難度分析 - 三層陷阱

### Level 1 陷阱 (ER 醫師)
```
Low Flow Alarm → "缺水" → 給 Fluid
```
**錯誤**: 直覺性思考，沒有理解 LVAD 生理學

### Level 2 陷阱 (AI/一般推理)
```
Power Spike + LDH 3500 + Hemolysis → Pump Thrombosis → 需要 Thrombolysis
```
**錯誤**: 線性思考，只看到部分數據

### Level 3 正確答案 (專家級推理)
```
PI = 1.0 (極低) + LV collapse + RV failure → Suction Event → 需要 RV support
```

## 關鍵鑑別診斷

| 指標 | Pump Thrombosis | Suction Event ✓ |
|------|-----------------|-----------------|
| Power | 持續性升高 | **間歇性 spike** |
| PI | 正常或略低 | **極低 (1.0)** |
| Echo LV | 正常/擴張 | **Small, collapsed** |
| Echo RV | 可能正常 | **Dilated, failing** |
| IVC | 可能正常 | **Dilated, non-collapsible** |
| IVS | 正常 | **Bowing INTO LV** |

## 正確的因果圖譜

```
RV Failure 
    ↓
Reduced LV Preload (血液回不到左心)
    ↓
LV Collapse (IVS bowing into LV)
    ↓
Pump Suction (Wall Strike)
    ↓
Power Spike + Low PI + Hemolysis
```

## 被忽略的關鍵數據

### Controller Log 趨勢
```
02:00 - PI 4.5, Power 4.1W ← 正常
02:45 - PI 1.5, Power 6.5W ← 開始 Suction
04:00 - PI 1.0, Power 7.2W ← 嚴重 Suction (增速後更糟)
```

### Echo 的錯誤解讀
- ❌ "Small LV = Hypovolemia" 
- ✓ **Small LV + IVS bowing INTO LV + RV dilated = Suction Event**

## 正確處置

1. ❌ 不要再給 Fluid (會加重 RV overload)
2. ❌ 不要增加 Pump Speed (會加重 suction)
3. ❌ 不需要 Thrombolysis
4. ✅ **降低 Pump Speed**
5. ✅ **RV Support** (Inotropes: Milrinone/Dobutamine)
6. ✅ 考慮 Pulmonary Vasodilators (iNO, Sildenafil)
7. ✅ 嚴重時考慮 RVAD

## 資料來源

| 檔案 | 內容 |
|------|------|
| DATA_SOURCE_01 | ER 入院評估 |
| DATA_SOURCE_02 | 床邊 Echo 報告 |
| DATA_SOURCE_03 | LVAD Controller Log |
| DATA_SOURCE_04 | Lab 結果 |
| DATA_SOURCE_05 | 臨床更新 |
