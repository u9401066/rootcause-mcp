# `nec-research/meddxagent` 學習報告

> 本報告只做 upstream 文件與原始碼稽核，不代表該專案已通過臨床、安全或生產驗證。

## 查核資料

| 欄位 | 內容 |
|---|---|
| Upstream | [nec-research/meddxagent](https://github.com/nec-research/meddxagent) |
| 查核日期 | `2026-08-18` |
| 查核版本 | `main` / `b62a451a6a1fcc9a4f8b7fd3f338af2b29c7a323` |
| 專案角色 | benchmark／research framework；interactive differential diagnosis |
| 授權 | **自訂 academic/non-profit noncommercial research-only license**；不可轉授權、散布或提供第三方存取，衍生修改歸 Licensor；不是 Apache/MIT |
| 本次驗證 | README、LICENSE、driver/agent/benchmark/model tree、configs、metrics、scripts、examples；無 conventional tests/CITATION.cff，未安裝或實跑 |

## 一句話結論

它是很好的 iterative DDx 研究方法與外部 benchmark 參考，但因嚴格非商業授權與缺乏 clinical provenance/RCA，不能作 RootCause production dependency。

## 它解決什麼問題

MEDDxAgent 研究「病人資料不是一次完整給出」時的 interactive differential diagnosis。DDxDriver 可排列 history-taking simulator、patient agent、retrieval agent 與 diagnosis strategy，逐輪取得資訊並更新 ranked DDx。

benchmark 統一 DDxPlus、ICraftMD、RareBench 成 initial profile、complete profile、ground-truth pathology/DDx，並提供 strict exact matching 與 weak substring matching、intermediate/final metrics、seed/config/run logs。

## 核心流程與資料邊界

- benchmark 先 sample patient；Agent 依配置做 history questions、retrieval、diagnosis，一或多輪後輸出 final DDx/rationale。
- patient simulator 與 diagnosis/retrieval 都可使用 LLM；框架評估策略，不是 clinical record ingestion server。
- run artifacts 保存 config、dialogue、retrieval、intermediate DDx、final DDx 與 metrics。
- runner 在每個 patient log 開始即寫 ground-truth pathology；雖不表示 ground truth 進 prompt，但不符合 RootCause 對 trusted gold/agent trace隔離的要求。
- 沒有 source snippets/hash、MCP case session、must-not-miss gate、human final review或 RCA。

## 最值得學習的設計

- DDxDriver、history-taking、patient、RAG、diagnosis agents 都是可替換 module，方便做 component ablation。
- initial vs complete patient profile 能測量 iterative information acquisition，而不是只測一次性答案。
- intermediate metrics 可看正確診斷何時進入 candidate list，而非只看最後 top-1。
- config/seed/run-folder/log 結構可借作 experiment reproducibility；RootCause 應再加 clean data root、artifact hashes與 trusted trace。
- strict/weak matching 並列提醒 scorer semantics 會改變結果；RootCause 應使用 clinical gold rubric/adjudication而非 substring 即算成功。

## 與 RootCause MCP 的關係

| 面向 | Upstream | RootCause MCP 的處理 |
|---|---|---|
| Evidence lineage | patient profile/dialogue/retrieval logs，無 record source hash/location | exact multi-source case manifest、atomic evidence ledger |
| DDx／推理 | iterative modular DDx、rationale與多 benchmark | active DDx + must-not-miss + direct LR + support/refute/tests |
| RCA／causation | 無 incident RCA 或 causation review | Fishbone/Why/HFACS、root lineage與 conservative audit |
| Final conformance | metrics/results JSON，無 clinical report admission | typed nested final report與 fail-closed mutation checks |
| Human review | benchmark ground truth matching，無 reviewer workflow | two blinded clinical reviewers/adjudication、reviewer hash binding |

## 採用建議

決策：**不採用**為 runtime/code dependency；符合資格且經法務核准時，僅隔離作 noncommercial internal research benchmark。

1. 整合邊界：最多自建 output adapter 讀其 experiment result，或依論文重新實作 iterative DDx eval；不把 code/data包進 release。
2. Fail-closed：gold 不得出現在 prompt/filename/agent-readable trace；dataset license/DUA 未確認、trace 有 ground truth、case source不明時不計正式結果。
3. Contract tests：agent-vs-trusted trace isolation、seed/repeat、strict/top-k scorer、DDx normalization、failure denominator、artifact hash與 clean root。
4. 授權風險：只允許 academic/non-profit internal noncommercial research；禁止 distribution/sublicensing，衍生修改 ownership 條款需法務評估。

### 概念引用方式

- production 實作只引用論文的方法與觀察，獨立寫 code，不複製 upstream source/config/dataset。
- 合法研究使用時 pin commit、隔離環境與 access control，dependency inventory 明列 custom license，不得把 artifact 對第三方散布。
- DDxPlus、ICraftMD、RareBench 與 StreamBench-derived code 各有獨立來源/授權，必須逐項引用，不能由 MEDDxAgent license 一併推定。

## 不應直接照搬的部分

- 不能把此 repo 寫成 Apache-2.0；其 LICENSE 明確限制用途、轉移與衍生作品。
- ground truth 寫進 per-patient log 的做法會污染 agent-readable trace／盲評隔離。
- exact/substring diagnosis matching 不涵蓋 must-not-miss、fabrication、PHI、certainty與 harmful recommendation。
- benchmark simulator 結果不能當 multi-source real-record clinical validity。

## 建議引用

### 軟體引用

```text
NEC Laboratories Europe GmbH. (2025). MEDDxAgent (commit b62a451a6a1fcc9a4f8b7fd3f338af2b29c7a323) [Computer software]. GitHub. https://github.com/nec-research/meddxagent
```

### 論文引用（upstream 提供）

```bibtex
@article{rose2025meddxagent,
  title={MEDDxAgent: A Unified Modular Agent Framework for Explainable Automatic Differential Diagnosis},
  author={Rose, Daniel and Hung, Chia-Chien and Lepri, Marco and Alqassem, Israa and Gashteovski, Kiril and Lawrence, Carolin},
  journal={arXiv preprint arXiv:2502.19175},
  year={2025}
}
```

### BibTeX fallback

```bibtex
@software{nec_meddxagent_2025,
  author  = {{NEC Laboratories Europe GmbH}},
  title   = {MEDDxAgent},
  year    = {2025},
  url     = {https://github.com/nec-research/meddxagent},
  version = {b62a451a6a1fcc9a4f8b7fd3f338af2b29c7a323},
  note    = {Accessed 2026-08-18; noncommercial research-only license}
}
```

## 來源

- [README and upstream paper citation](https://github.com/nec-research/meddxagent/blob/b62a451a6a1fcc9a4f8b7fd3f338af2b29c7a323/README.md)
- [Custom LICENSE](https://github.com/nec-research/meddxagent/blob/b62a451a6a1fcc9a4f8b7fd3f338af2b29c7a323/LICENSE)
- [DDxDriver runner](https://github.com/nec-research/meddxagent/blob/b62a451a6a1fcc9a4f8b7fd3f338af2b29c7a323/ddxdriver/run_ddxdriver.py)
- [Modular agents and benchmarks](https://github.com/nec-research/meddxagent/tree/b62a451a6a1fcc9a4f8b7fd3f338af2b29c7a323/ddxdriver)
- [arXiv:2502.19175](https://arxiv.org/abs/2502.19175)

## 查核限制

本次為 source audit only。未建立 Azure/OpenAI/vLLM/Hugging Face 環境，未下載 DDxPlus，未重跑論文 experiments 或 metrics，亦未驗證各 dataset 的現行 license/DUA；論文效能聲稱只作 upstream 報告，不作本 repo 驗收結果。
