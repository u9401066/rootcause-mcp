# `IVUL-KAUST/MedCTA` 學習報告

> 本檔只記錄固定版本的文件與原始碼稽核，不代表 MedCTA 已通過臨床、安全或生產驗證。

## 查核資料

| 欄位 | 內容 |
|---|---|
| Upstream | [IVUL-KAUST/MedCTA](https://github.com/IVUL-KAUST/MedCTA) |
| 查核日期 | `2026-08-18` |
| 查核版本 | 預設分支 `main`，commit `eb7d1dc0adc6da4c31d9c5ebef3a8059a620022c` |
| 專案角色 | 多模態 clinical tool-agent benchmark |
| 授權 | Apache-2.0；已直接讀取該 commit 的 `LICENSE.txt` |
| 本次驗證 | 查 README、完整 tree、OpenCompass config、`clinical_accuracy.py`、`goal_accuracy.py`、vendored AgentLego/OpenCompass tests；無獨立正式 schema 或 MedCTA-specific tests；**未下載 dataset、未安裝、未實跑** |

## 一句話結論

它的 tool-route／trajectory 分解指標值得借鏡，但目前 scorer 主要是硬編設定的 LLM judge，且大量 vendored framework 不能當成 MedCTA 自身測試成熟度；只做概念引用。

## 它解決什麼問題

MedCTA 提供 107 個 clinician-verified、多模態、step-implicit tasks，五種工具（OCR、ImageDescription、RegionAttributeDescription、GoogleSearch、Calculator），README 報告 18 models、1,926 rollouts 與 321 小時人工標註。

Task 抽象為 `(X,Q,U,π,A)`：多模態 context、query、隱藏充分 tool subset、reference trajectory 與 final outcome。指標分成 InstAcc／ToolAcc／ArgAcc／SummAcc、clinical faithfulness／context integration／semantic completeness，以及 goal accuracy。

## 核心流程與資料邊界

資料另由 Hugging Face 下載，OpenCompass 配合 AgentLego／LMDeploy 執行 agent 與工具，再以 gold trajectory／answer 評分。GoogleSearch 與外部模型是資料外送面，醫療影像與 OCR 內容須先確認資料權利及去識別。

`clinical_accuracy.py`／`goal_accuracy.py` 以 GPT-5.4 Responses API 做語意評分，路徑、輸出目錄或 key 設定留空／硬編；goal prompt 甚至允許「包含 gold 即滿分」的寬鬆規則，不能當 RootCause 的 deterministic safety gate。

## 最值得學習的設計

- 同時評估 tool selection、argument、intermediate summary 與 final goal，能定位 trajectory 失敗。
- 隱藏 sufficient tool subset 與 reference trajectory 可測 planning，而非把步驟提示給 agent。
- Autonomous 與 gold-route 對照能量化 tool routing 瓶頸。
- RootCause 可重做 deterministic tool/event completeness 指標，再由臨床 reviewer 評主觀 reasoning；不複製上游 LLM judge prompt。

## 與 RootCause MCP 的關係

| 面向 | Upstream | RootCause MCP 的處理 |
|---|---|---|
| Evidence lineage | 評 tool observation 是否被使用，未綁 source-span hash | 每筆 evidence 的 snippet/location/source hash/lineage |
| DDx／推理 | clinical faithfulness/completeness 分數，無 DDx object contract | 三個 DDx、must-not-miss、支持／反證／planned test |
| RCA／causation | 無 Fishbone／Why／HFACS 或 causal status | 保守 RCA ledger 與 cross-object invariants |
| Final conformance | goal accuracy LLM score | deterministic nested schema、checks 與 immutable hash |
| Human review | clinician-verified tasks；runtime scorer 是模型 | 兩名臨床 reviewer 盲評與裁決 |

## 採用建議

**決策：概念借鑑。** 採用 process-vs-outcome metric taxonomy，於 RootCause 自行實作不含 gold 洩漏的 deterministic scorers。

1. 整合邊界：只引用 metric 定義與論文；不 vendor `agentlego/`、`opencompass/` 或上游 evaluator scripts。
2. Fail-closed：tool trace 缺漏、gold route 可見、外部搜尋未核准、judge error／版本不明或 PHI 外送時不得算合格。
3. Contract tests：錯 tool、錯 argument、少 observation、premature stop、final 對但 evidence 不支持、judge 與 deterministic label 分離。
4. 風險：repo code 為 Apache-2.0，但 dataset／影像仍需另查授權；大量 vendored code、硬編設定、未見 MedCTA-specific tests 與 LLM scorer 漂移增加維護風險。

### 概念引用方式

- 以固定 commit 與 arXiv 論文引用 metric／task model；不建立 runtime dependency。
- 若未來執行，另 pin dataset revision、tool image、model/judge ID、prompt hash 與 OpenCompass/AgentLego versions。

## 不應直接照搬的部分

- 不把 vendored framework tests 誤報成 benchmark conformance tests。
- 不使用「答案含 gold 即滿分」取代 fabricated evidence、must-not-miss 與 forbidden-claim scorers。
- 不讓 GoogleSearch 或 judge API 接收可識別病歷／影像。

## 建議引用

### 軟體引用

```text
IVUL-KAUST. (2026). MedCTA (commit eb7d1dc0adc6da4c31d9c5ebef3a8059a620022c) [Computer software]. GitHub. https://github.com/IVUL-KAUST/MedCTA
```

### BibTeX fallback

```bibtex
@software{ivul_medcta_2026,
  author={{IVUL-KAUST}}, title={MedCTA}, year={2026},
  url={https://github.com/IVUL-KAUST/MedCTA},
  version={eb7d1dc0adc6da4c31d9c5ebef3a8059a620022c}, note={Accessed 2026-08-18}
}
```

論文引用（與軟體分開，依 upstream BibTeX）：

```bibtex
@misc{medcta,
  title={MedCTA: A Benchmark for Clinical Tool Agents},
  author={Tajamul Ashraf and Hyewon Jeong and Fida Mohammad Thoker and Bernard Ghanem},
  year={2026}, eprint={2606.11702}, archivePrefix={arXiv}, primaryClass={cs.CV},
  url={https://arxiv.org/abs/2606.11702}
}
```

## 來源

- [README](https://github.com/IVUL-KAUST/MedCTA/blob/eb7d1dc0adc6da4c31d9c5ebef3a8059a620022c/README.md)／[LICENSE.txt](https://github.com/IVUL-KAUST/MedCTA/blob/eb7d1dc0adc6da4c31d9c5ebef3a8059a620022c/LICENSE.txt)
- [`clinical_accuracy.py`](https://github.com/IVUL-KAUST/MedCTA/blob/eb7d1dc0adc6da4c31d9c5ebef3a8059a620022c/clinical_accuracy.py)／[`goal_accuracy.py`](https://github.com/IVUL-KAUST/MedCTA/blob/eb7d1dc0adc6da4c31d9c5ebef3a8059a620022c/goal_accuracy.py)
- [OpenCompass config](https://github.com/IVUL-KAUST/MedCTA/blob/eb7d1dc0adc6da4c31d9c5ebef3a8059a620022c/opencompass/configs/eval_medcta_bench.py)／[論文](https://arxiv.org/abs/2606.11702)

## 查核限制

本次未下載 Hugging Face dataset、未執行工具／模型／scorer，也未獨立重現 leaderboard；只查公開固定 commit，私人、未索引或 dataset-side revisions 不在範圍。
