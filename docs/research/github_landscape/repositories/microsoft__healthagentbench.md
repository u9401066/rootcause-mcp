# `microsoft/HealthAgentBench` 學習報告

> 本檔只記錄固定版本的文件與原始碼稽核，不代表 HealthAgentBench 已通過臨床、安全或生產驗證。

## 查核資料

| 欄位 | 內容 |
|---|---|
| Upstream | [microsoft/HealthAgentBench](https://github.com/microsoft/HealthAgentBench) |
| 查核日期 | `2026-08-18` |
| 查核版本 | 預設分支 `main`，commit `ce89def2edf56f4a2ef068f37c8544bff944d5fc` |
| 專案角色 | 醫療 agent benchmark／相鄰方案 |
| 授權 | MIT；已直接讀取該 commit 的 `LICENSE`（Microsoft Corporation） |
| 本次驗證 | 查 README、完整 tree、54 個 task layout、代表性 verifier、`pyproject.toml` 與測試目錄；**未取得 gated data、未安裝、未實跑** |

## 一句話結論

它是可借鏡的跨 Agent 醫療 terminal benchmark 與 Harbor task corpus，不是多份 raw 病歷的 evidence-grounded DDx／RCA 產物引擎，宜以 benchmark adapter 方式外接。

## 它解決什麼問題

Upstream 提供 54 個 terminal-based health tasks、七類資料與任務：X-ray report correction、病理腫瘤區域、EHR→MEDS ETL、CT abnormality、clinical trial matching、EHR data quality 與 EHR event modelling。

每個 task 採 Harbor 的 `task.toml`、`instruction.md`、`environment/`、`tests/` 佈局；runner 可執行多次、保存完整 jobs artifacts，task-specific verifier 產生 binary reward 與額外 metrics。

部分資料來自 EHRSHOT、CT-RATE、MIMIC-IV／MIMIC-CXR，需個別申請或接受資料條款。X-ray 類別預設以 GPT-5.4 CheXprompt LLM judge 評分，故並非所有指標都 deterministic。

## 核心流程與資料邊界

Harbor 下載／掛載 task data，將 agent 放進 terminal environment，執行任務後以 tests 內的 verifier 比對輸出或隱藏 gold，再把 metrics 寫入 trial artifact。

README 明載 repo 不直接託管 labels，而是 run 時抓進 tests，並建議禁止 web search 避免洩漏。這是 benchmark isolation，不等於來源病歷 lineage；gated data、credentials、快取與輸出皆需視為敏感資料邊界。

## 最值得學習的設計

- 54 tasks 使用一致、可機讀的 task/environment/tests 結構，利於跨 runtime 重複評估。
- `n-attempts`、parallel jobs 與每 trial artifact 可直接對應 RootCause 的 3 runtimes × 6 cases × 2 repeats 矩陣。
- 隱藏 gold、停用網路與 timeout=fail 的規則，適合建立答案防洩漏 gate。
- verifier 同時輸出總 reward 與 task-specific metrics，適合把 workflow completion、recall、lineage 與 safety violation 分開。
- RootCause 可重新實作薄 Harbor task adapter，不應複製受資料條款約束的 corpus。

## 與 RootCause MCP 的關係

| 面向 | Upstream | RootCause MCP 的處理 |
|---|---|---|
| Evidence lineage | task data 與 agent artifacts 可追到 trial，但不定義 atomic source ledger | source manifest、exact snippet、location、hash、timestamp 與 certainty label |
| DDx／推理 | 任務橫跨分類、匹配、ETL；無統一 DDx schema | 至少三個 active DDx、must-not-miss、support／disconfirm／planned test |
| RCA／causation | 不提供 Fishbone／Why／HFACS 或 causal audit | 保守 causation validator 與 root/evidence/Why lineage invariants |
| Final conformance | verifier reward／metrics，非統一 clinical report | typed nested report、`conformance_checks[]`、immutable final hash |
| Human review | task gold／LLM judge，不等同兩名臨床 reviewer 盲評 | qualified reviewer metadata、盲評與分歧裁決 |

## 採用建議

**決策：adapter。** 只借用 Harbor task packaging 與 eval-runner 模式，將 RootCause 的六個無洩漏病例包成自有 tasks；HealthAgentBench 本身作外部泛化 benchmark。

1. 整合邊界：adapter 只負責 agent command、乾淨 data root、網路政策、trace／artifact 收集；臨床 gold rubric 與 conformance scorer 留在 RootCause。
2. Fail-closed：無 gated-data 授權、gold 與 agent workspace 未隔離、web 未禁用、verifier exception、timeout、PHI 外送或 artifact 缺漏均算失敗。
3. Contract tests：fixture task 的 gold 不可讀、同 case repeat 使用新 data root、每 run 均保存 trace/JSON/Markdown/hash，LLM judge 與 deterministic 指標標籤不可混淆。
4. 風險：MIT 軟體可借用；資料仍受各自 DUA／credential 約束。上游 pin `harbor==0.8.0` 與 Python `>=3.12`，和最新 Harbor 可能有相容性落差。

### 概念引用方式

- 以 benchmark task adapter 與外部 eval profile 引用，不把它加入 RootCause production dependency。
- pin 本報告 commit、Harbor 版本、task image digest 與每個 gated dataset 版本。
- 在研究報告分開引用 benchmark 論文與 repository software；資料集則依各資料提供者規定另行引用。

## 不應直接照搬的部分

- 不把 LLM judge 分數當 deterministic conformance，也不把 reward=1 當成臨床安全證明。
- 不下載、重發或把 MIMIC／EHRSHOT 等受限內容傳到未獲准的模型 API。
- 不沿用可能把 gold 拉進同一工作樹的流程而未加 OS/container 層隔離。

## 建議引用

### 軟體引用

```text
Microsoft. (2026). HealthAgentBench (commit ce89def2edf56f4a2ef068f37c8544bff944d5fc) [Computer software]. GitHub. https://github.com/microsoft/HealthAgentBench
```

### BibTeX fallback

```bibtex
@software{microsoft_healthagentbench_2026,
  author={{Microsoft}}, title={HealthAgentBench}, year={2026},
  url={https://github.com/microsoft/HealthAgentBench},
  version={ce89def2edf56f4a2ef068f37c8544bff944d5fc}, note={Accessed 2026-08-18}
}
```

論文引用（與軟體分開）：

```bibtex
@misc{liu2026healthagentbench,
  title={HealthAgentBench: A Unified Benchmark Suite of Realistic Agentic Healthcare Environments for Challenging Frontier AI Agents},
  author={Qianchu Liu and Sheng Zhang and Guanghui Qin and Jeya Maria Jose Valanarasu and Maximilian Rokuss and Mingyu Lu and Timothy Ossowski and Juan Manuel Zambrano Chaves and Cliff Wong and Peniel Argaw and Yashna Hasija and Mu Wei and Wen-wai Yim and Qin Liu and Zilin Jing and Jason Entenmann and Naoto Usuyama and Tristan Naumann and Hoifung Poon},
  year={2026}, eprint={2606.31179}, archivePrefix={arXiv},
  url={https://arxiv.org/abs/2606.31179}
}
```

## 來源

- [README（固定 commit）](https://github.com/microsoft/HealthAgentBench/blob/ce89def2edf56f4a2ef068f37c8544bff944d5fc/README.md)
- [LICENSE](https://github.com/microsoft/HealthAgentBench/blob/ce89def2edf56f4a2ef068f37c8544bff944d5fc/LICENSE)／[pyproject.toml](https://github.com/microsoft/HealthAgentBench/blob/ce89def2edf56f4a2ef068f37c8544bff944d5fc/pyproject.toml)
- [tasks tree](https://github.com/microsoft/HealthAgentBench/tree/ce89def2edf56f4a2ef068f37c8544bff944d5fc/tasks)／[代表性 verifier](https://github.com/microsoft/HealthAgentBench/blob/ce89def2edf56f4a2ef068f37c8544bff944d5fc/tasks/clinical_trial_matching_task_19/tests/verify.py)
- [HealthAgentBench 論文](https://arxiv.org/abs/2606.31179)

## 查核限制

本次未申請資料、未驗證 30GB 以上資產下載、credential／container、54-task 執行或官方分數；結論只涵蓋公開固定 commit 的 README、tree、設定與代表性 verifier，私人及未索引專案不在範圍。
