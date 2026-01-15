# 案例：大量輸血後高血鉀心跳停止 (Massive Transfusion Hyperkalemia Arrest)

## 案例概述

高速車禍多發傷患者，接受大量輸血 (MTP) 後轉入 ICU。
凌晨 02:45 發生心跳停止，急救無效死亡。
屍檢發現 **K+ > 8.5 mmol/L**，非失血性死亡。

## 關鍵發現

| 時間 | 事件 | 關鍵訊息 |
|------|------|----------|
| 01:45 | 輸血 Unit #7 | 「older stock, exp 2 days」- 舊血高鉀 |
| 02:00 | 尿量 20ml/hr | 紅棕色尿 - AKI 徵兆 |
| 02:00-04:00 | LIS 系統停機 | K+ 檢體卡在 queue 中 |
| 02:12 | ECG Alarm | 「HI_T_WAVE」被忽略 |
| 02:30 | Wide QRS | 醫師診斷為低血容 → 給更多輸液 |
| 02:45 | Code Blue | Sine Wave → Asystole |

## 死因分析

**高血鉀心跳停止** (Hyperkalemic Cardiac Arrest)

來源：
1. 大量輸血 (舊血 K+ 高)
2. 急性腎損傷 (無法排出 K+)
3. 組織缺血再灌流 (細胞內 K+ 釋出)

錯失機會：
1. Lab 系統停機 → K+ 未檢驗
2. ECG 警報被忽略
3. 誤診為低血容 → 給更多輸液

## 使用方式

```bash
rc_start_session(case_type="death", case_title="MTP後高血鉀心跳停止")
```
