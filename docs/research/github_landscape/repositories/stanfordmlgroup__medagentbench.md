# `stanfordmlgroup/MedAgentBench` 學習報告

> 本檔只記錄固定版本的文件與原始碼稽核，不代表 MedAgentBench 已通過臨床、安全或生產驗證。

## 查核資料

| 欄位 | 內容 |
|---|---|
| Upstream | [stanfordmlgroup/MedAgentBench](https://github.com/stanfordmlgroup/MedAgentBench) |
| 查核日期 | `2026-08-18` |
| 查核版本 | 預設分支 `main`，commit `99260117137b09f04837a8c18d18a1107efa55ae` |
| 專案角色 | FHIR／EHR agent benchmark |
| 授權 | MIT；已直接讀取該 commit 的 `LICENSE`（Copyright 2025 Stanford Machine Learning Group） |
| 本次驗證 | 查 README、完整 tree、`test_data_v1/v2`、task server、`eval.py`、requirements 與 LICENSE；repo 無獨立 schema/tests tree；**未下載 Docker／refsol、未實跑** |

## 一句話結論

它是 FHIR 操作型 agent benchmark 的早期參考，不是 RootCause 的多文件 DDx／RCA harness；只宜包成隔離的外部 benchmark adapter。

## 它解決什麼問題

MedAgentBench 建立虛擬 FHIR EHR，讓 agent 完成病人查詢、資料寫入、訂單與多步任務；公開 `test_data_v2.json` 以 `task1_1` 到 `task10_30` 組成 300 個 instance。

流程建立 Python 3.9 環境、啟動預先建好的 FHIR Docker、另從 Stanford Box 取得不在 repo 的 `refsol.py`，再啟動 task controller／workers 與 assigner，最後寫出 `overall.json`。

README 明示此 repo 為研究用途，可能不適合大規模 production。公開資料可見 task instruction、MRN／姓名等 benchmark identifiers，部分項目也有 `sol`；gold isolation 必須由外層 runner 加固。

## 核心流程與資料邊界

Agent 經 HTTP 與 task server／FHIR server 互動；`eval.py` 依 task ID 動態呼叫外部 `refsol` 函式，以 boolean 判斷結果。FHIR image、Box refsol、agent API 與 outputs 都不在單一可重算供應鏈內。

該 benchmark 評估 EHR 操作成功，不保存 RootCause 所需的每筆來源 snippet/hash、DDx ledger、RCA lineage 或 final review snapshot。

## 最值得學習的設計

- 用隔離 FHIR server 評估 read／write 行為，而非只做單輪醫療問答。
- Controller／worker／assigner 分層可平行執行大量 instance。
- task-specific reference function 可檢查 EHR 最終狀態，適合借鏡 mutation verifier。
- RootCause 應另做公開 input 與 private gold 的硬隔離，並固定 container／refsol digest。

## 與 RootCause MCP 的關係

| 面向 | Upstream | RootCause MCP 的處理 |
|---|---|---|
| Evidence lineage | FHIR state 與 task result，無 atomic source hash ledger | manifest、snippet、location、time、hash 與 certainty |
| DDx／推理 | 十類 EHR 操作，不要求至少三個 competing DDx | typed DDx、must-not-miss、support/disconfirm/test disposition |
| RCA／causation | 無 Fishbone／Why／HFACS／causation review | 保守 causal audit 與 root/evidence/Why 一致性 |
| Final conformance | boolean refsol／`overall.json` | nested report schema、machine checks、reviewer/time/hash |
| Human review | benchmark gold；無 final qualified-human gate | named authorized reviewer 與盲評 adjudication |

## 採用建議

**決策：adapter。** 把它留在獨立 benchmark image，評估 RootCause-enabled agent 的 FHIR tool discipline；不得成為 production clinical dependency。

1. 整合邊界：只轉譯 agent invocation、FHIR endpoint 與 outcome；RootCause 的六案例、gold rubric、trace manifest 另行保存。
2. Fail-closed：缺 `refsol` digest、Docker digest、clean FHIR reset、gold isolation、完整 trace 或 verifier exception 時，該 run 失敗。
3. Contract tests：每 run 新 container、write mutation 最終狀態、timeout、重複 run、public input 不含答案與 artifact hash 可重算。
4. 風險：MIT code 可借用，但外部 Box 檔、Docker `latest`、舊 Python／requirements 與無正式 schema/tests 都降低可重現性；資料與 image 權利需另查。

### 概念引用方式

- 以外部 benchmark adapter 引用；pin repo commit、FHIR image digest 與 refsol SHA-256，不 vendor corpus 或外部 reference solution。
- 軟體、NEJM AI 論文與任何資料／image 應分開引用並記錄授權。

## 不應直接照搬的部分

- 不使用浮動 Docker `latest` 或未記 digest 的外部 `refsol.py` 作 release gate。
- 不讓 agent 讀到 `sol`／grader，也不把 benchmark MRN／姓名帶進公開 trace。
- 不把 EHR mutation 成功等同臨床推理正確、因果成立或 final report 合規。

## 建議引用

### 軟體引用

```text
Stanford Machine Learning Group. (2025). MedAgentBench (commit 99260117137b09f04837a8c18d18a1107efa55ae) [Computer software]. GitHub. https://github.com/stanfordmlgroup/MedAgentBench
```

### BibTeX fallback

```bibtex
@software{stanford_medagentbench_2025,
  author={{Stanford Machine Learning Group}}, title={MedAgentBench}, year={2025},
  url={https://github.com/stanfordmlgroup/MedAgentBench},
  version={99260117137b09f04837a8c18d18a1107efa55ae}, note={Accessed 2026-08-18}
}
```

論文引用（與軟體分開）：

```bibtex
@article{jiang2025medagentbench,
  title={MedAgentBench: A Virtual EHR Environment to Benchmark Medical LLM Agents},
  author={Jiang, Yixing and Black, Kameron C and Geng, Gloria and Park, Danny and Zou, James and Ng, Andrew Y and Chen, Jonathan H},
  journal={NEJM AI}, pages={AIdbp2500144}, year={2025},
  doi={10.1056/AIdbp2500144}
}
```

## 來源

- [README](https://github.com/stanfordmlgroup/MedAgentBench/blob/99260117137b09f04837a8c18d18a1107efa55ae/README.md)／[LICENSE](https://github.com/stanfordmlgroup/MedAgentBench/blob/99260117137b09f04837a8c18d18a1107efa55ae/LICENSE)
- [`test_data_v2.json`](https://github.com/stanfordmlgroup/MedAgentBench/blob/99260117137b09f04837a8c18d18a1107efa55ae/data/medagentbench/test_data_v2.json)／[`eval.py`](https://github.com/stanfordmlgroup/MedAgentBench/blob/99260117137b09f04837a8c18d18a1107efa55ae/src/server/tasks/medagentbench/eval.py)
- [完整 tree](https://github.com/stanfordmlgroup/MedAgentBench/tree/99260117137b09f04837a8c18d18a1107efa55ae)／[NEJM AI 論文](https://doi.org/10.1056/AIdbp2500144)

## 查核限制

本次未下載外部 `refsol.py`／FHIR image、未確認 image 內容與資料權利、未啟動 server 或跑 300 instances；只涵蓋公開固定 commit，私人及未索引方案不在範圍。
