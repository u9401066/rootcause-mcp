# `py-why/dowhy` 學習報告

> 本檔只記錄 upstream 文件與原始碼稽核，不代表臨床、安全或生產驗證。

## 查核資料

| 欄位 | 內容 |
|---|---|
| Upstream | [py-why/dowhy](https://github.com/py-why/dowhy) |
| 查核日期 | `2026-08-18` |
| 查核版本 | 預設分支 `main`；commit `1d1efe77b092661252038baad72dc5d53e35ebfa` |
| 專案角色 | 基礎套件／統計因果推論與 graphical causal models |
| 授權 | `MIT`；已直接讀取 LICENSE，copyright 為 PyWhy contributors |
| 本次驗證 | README、完整 tree、pyproject、CausalModel/GCM typed APIs（無 case-report schema）、refuters、docs 與 unit tests；未安裝、未跑 notebook/test、未估計資料 |

## 一句話結論

不能取代 RootCause MCP，也不是單一病例的臨床因果證明工具；只適合作為有明確 cohort、estimand、DAG 與統計假設時的 optional analytical adapter。

## 它解決什麼問題

DoWhy 統一 causal question 的 model、identify、estimate、refute 四步，結合 graphical causal models、potential outcomes 與多種 estimator/refuter。
GCM surface另支援 causal mechanism、anomaly attribution、distribution-change attribution、intervention與 counterfactual；README 的 RCA 範例多為微服務、供應鏈與數值異常。
其 refutation／falsification API 檢查對特定擾動的 robustness；結果仍依賴 causal graph、交換性/overlap/SUTVA、測量與模型假設。

## 核心流程與資料邊界

輸入通常是多筆 tabular observations、treatment、outcome、causal graph 與 estimator；輸出 identified estimand、effect estimate、refutation 或 GCM attribution。
RootCause case evidence 不能直接湊成一列資料後執行 DoWhy；必須有合法取得、去識別、具 lineage 的研究 dataset 與事前定義的 estimand/DAG。
DoWhy 的「root cause analysis」是統計/圖模型 attribution，不等於醫療事件的 Why/Fishbone/HFACS，也不證明某暴露造成某患者結果。
統計輸出只能附在 preliminary report 的 analytical supplement，不能直接把 causation status 設為 established/verified。

## 最值得學習的設計

- `model → identify → estimate → refute` 將假設與估計步驟分離，可借鑑 RootCause causation audit 的可追溯 stage boundaries。
- identified estimand 與 untested assumptions 可顯示「此資料下不可識別」，比強行產生因果答案安全。
- placebo、random common cause、subset、unobserved-common-cause 等 refuters 可形成 cohort supplement 的 robustness checklist。
- tests 廣泛涵蓋 identifiers、estimators、refuters、GCM 與 independence tests；不代表特定臨床資料、DAG 或部署已驗證。

## 與 RootCause MCP 的關係

| 面向 | Upstream | RootCause MCP 的處理 |
|---|---|---|
| Evidence lineage | DataFrame/graph；非病歷 source ledger | manifest、exact source observations、hash 與 timestamp precision |
| DDx／推理 | 不做 clinical DDx | competing diagnoses與 evidence/test disposition |
| RCA／causation | population/statistical causal effect與 GCM attribution | conservative case/system audit；不得由統計 API自動定案 |
| Final conformance | Python result objects；非 case-report schema | typed final report、machine checks、review hash/snapshot |
| Human review | analyst interprets assumptions | statistician/clinician qualified review，加上 authorized final reviewer |

## 採用建議

**決策：adapter。** 建立 opt-in `causal-analysis` adapter，只接受 cohort/statistical supplement contract；預設 RootCause case workflow不載入 DoWhy。
contract 必填 dataset hash/schema、cohort definition、treatment/outcome、estimand、DAG版本、adjustment set、assumptions、estimator、seed、CI與 refuters；結果只寫入 supplement。
單病例、樣本不足、DAG由 LLM臨時生成、estimand/overlap缺漏、source lineage不全、identify失敗或 refuter重大異常時必須 fail-closed，不產生 clinical causal conclusion。
最小 contract tests：known synthetic DAG、non-identifiable graph、hidden confounding sensitivity、overlap failure、seed reproducibility、hash mismatch、missingness與「不可改寫 root causation status」。
MIT 授權可支援 optional dependency；需 pin release與 lockfile、記錄 NumPy/pandas/sklearn/graph依賴及 licenses，並由統計 reviewer確認版本與 method selection。

### 基礎套件的引用與依賴方式

以 optional dependency 加 host-owned adapter，不複製 estimator code；在 SBOM／NOTICE 記錄 `dowhy` 名稱、版本、URL、MIT，正式驗證 pin wheel/commit digest。大型或敏感 dataset 可改放隔離 sidecar，只回 typed supplement與 artifact hashes。

## 不應直接照搬的部分

- 不把 `estimate`、低 p-value、refuter 未拒絕或 anomaly attribution 稱為單病例臨床因果證明。
- 不讓 LLM從病例敘述自行補 DAG、confounders、counterfactual values 或 population data。
- 不把 statistical RCA名稱混同 RootCause 的保守醫療事件 RCA／human adjudication。

## 建議引用

### 軟體引用

```text
PyWhy contributors. (2026). DoWhy (commit 1d1efe77b092661252038baad72dc5d53e35ebfa) [Computer software]. GitHub. https://github.com/py-why/dowhy
```

### BibTeX fallback

```bibtex
@software{pywhy2026dowhy, author={{PyWhy contributors}}, title={DoWhy}, year={2026}, url={https://github.com/py-why/dowhy}, version={1d1efe77b092661252038baad72dc5d53e35ebfa}, note={Accessed 2026-08-18}}
```

### 論文引用（與軟體分開）

```bibtex
@article{dowhy, title={DoWhy: An End-to-End Library for Causal Inference}, author={Sharma, Amit and Kiciman, Emre}, journal={arXiv preprint arXiv:2011.04216}, year={2020}}
@article{JMLR:v25:22-1258, author={Blöbaum, Patrick and Götz, Peter and Budhathoki, Kailash and Mastakouri, Atalanti A. and Janzing, Dominik}, title={DoWhy-GCM: An Extension of DoWhy for Causal Inference in Graphical Causal Models}, journal={Journal of Machine Learning Research}, year={2024}, volume={25}, number={147}, pages={1--7}, url={https://jmlr.org/papers/v25/22-1258.html}}
```

## 來源

- [README（pinned）](https://github.com/py-why/dowhy/blob/1d1efe77b092661252038baad72dc5d53e35ebfa/README.rst)；[LICENSE](https://github.com/py-why/dowhy/blob/1d1efe77b092661252038baad72dc5d53e35ebfa/LICENSE)；[`pyproject.toml`](https://github.com/py-why/dowhy/blob/1d1efe77b092661252038baad72dc5d53e35ebfa/pyproject.toml)
- [`CausalModel`](https://github.com/py-why/dowhy/blob/1d1efe77b092661252038baad72dc5d53e35ebfa/dowhy/causal_model.py)；[GCM anomaly APIs](https://github.com/py-why/dowhy/blob/1d1efe77b092661252038baad72dc5d53e35ebfa/dowhy/gcm/anomaly.py)
- [identifier tests](https://github.com/py-why/dowhy/tree/1d1efe77b092661252038baad72dc5d53e35ebfa/tests/causal_identifiers)；[refuter tests](https://github.com/py-why/dowhy/tree/1d1efe77b092661252038baad72dc5d53e35ebfa/tests/causal_refuters)

## 查核限制

本次只做公開 GitHub 文件與原始碼稽核；沒有安裝 DoWhy、執行 tests/notebooks、重現論文或對任何臨床/cohort資料估計。公開搜尋亦無法涵蓋私人版本與未索引專案。
