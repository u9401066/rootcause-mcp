# 案例：術後肺栓塞死亡 (Post-operative PE Death)

## 案例概述

55歲女性接受左側全髖關節置換術 (THA)，術後第二天 (POD 2) 發生 Code Blue，
心跳停止類型為 PEA (Pulseless Electrical Activity)。

## 資料來源

| 檔案 | 內容 | 關鍵資訊 |
|------|------|----------|
| `DATA_SOURCE_01_OP_NOTE.txt` | 手術記錄 | DVT Prophylaxis: HOLD Clexane 24hrs |
| `DATA_SOURCE_02_NURSING_FLOWSHEET.csv` | 護理生命徵象 | POD1 16:00 calf pain, leg swelling |
| `DATA_SOURCE_03_PROGRESS_NOTE.txt` | 住院醫師病程記錄 | 診斷：Sepsis |
| `DATA_SOURCE_04_NURSING_OBSERVATION.txt` | 護理觀察紀錄 | Code Blue 過程 |
| `DATA_SOURCE_05_MAR.csv` | 給藥紀錄 | Clexane: NOT_GIVEN (Order Expired) |

## RCA 分析目標

1. 識別導致 Code Blue 的因果鏈
2. 評估 DVT 預防措施的執行狀況
3. 分析臨床判斷的認知因素
4. 提出系統性改善建議

## 關鍵時間軸

```
04/10 14:00  手術完成，Clexane HELD (引流出血)
04/11 09:00  Clexane 醫囑過期，未給藥
04/11 16:00  病人小腿疼痛、腿腫
04/12 08:00  發燒、低血壓、意識混亂
04/12 11:30  胸悶、呼吸困難
04/12 12:10  CODE BLUE - PEA arrest
```

## 使用方式

```bash
# 開始 RCA 分析
rc_start_session(case_type="death", case_title="術後肺栓塞死亡")
```
