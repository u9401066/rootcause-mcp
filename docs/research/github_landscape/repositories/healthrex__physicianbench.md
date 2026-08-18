# `HealthRex/PhysicianBench` 學習報告

> 本檔只記錄固定版本的文件與原始碼稽核，不代表 PhysicianBench 已通過臨床、安全或生產驗證。

## 查核資料

| 欄位 | 內容 |
|---|---|
| Upstream | [HealthRex/PhysicianBench](https://github.com/HealthRex/PhysicianBench) |
| 查核日期 | `2026-08-18` |
| 查核版本 | 預設分支 `main`，commit `c7efa8fd5b1e4744ada50668efe4b7e84023cbb0` |
| 專案角色 | 長程 FHIR 臨床 agent benchmark |
| 授權 | Apache-2.0；已直接讀取該 commit 的 `LICENSE` |
| 本次驗證 | 查 README、完整 tree、100 個 task layout、runner、taxonomy、代表性 checkpoint tests 與 `pyproject.toml`；**未取得 Redivis image、未安裝、未實跑** |

## 一句話結論

它是最接近「真實長程 EHR agent eval」的相鄰 benchmark，可借鏡 fresh environment、checkpoint 與 artifact layout，但不取代 RootCause 的 evidence/DDx/RCA report contract。

## 它解決什麼問題

PhysicianBench 公開 100 個長程醫師任務、670 個 sub-checkpoints、21 個專科，使用 FHIR API 存取真實病人紀錄；任務要求跨 encounters 擷取資料、推理、執行臨床動作並輸出文件。

每一 task 有 instruction、`task.toml` 與 pytest verifier。Runner 為每 task 啟動新的 FHIR container、執行 agent、跑 verifier、移除 container，保存 trajectory、workspace、eval logs 與 metadata；支援 `n_runs`、max steps 與 resume。

代表性 verifier 同時檢查 tool trajectory、FHIR mutation、輸出檔與 LLM judge rubric；因此 checkpoint 標籤與 deterministic／LLM-judged 性質必須逐項保存，不能只看整體 pass。

## 核心流程與資料邊界

受限 FHIR Docker image 由 Stanford Redivis 提供，模型憑證可指向多種外部 API。Repository 的 Apache-2.0 不授予病歷 image 的使用或外送權；實跑前必須以 Redivis 條款、IRB／DUA 與部署環境重新確認。

新鮮 container 可隔離 mutation，但 jobs artifact 本身仍可能含病歷與完整 trajectory；需加密、去識別、存取控制、retention 與 hash manifest。

## 最值得學習的設計

- 每 task 啟動／銷毀 fresh FHIR container，降低跨 run state contamination。
- 以多個 checkpoint 拆解資料擷取、推理、order 與 documentation，可定位 agent 失敗階段。
- Code、trajectory 與 LLM judge 混合 grader 可覆蓋臨床任務，但必須分別標示 certainty。
- `n_runs`、resume、max-step 與 per-run jobs artifacts 適合 RootCause agent-in-loop matrix。
- Taxonomy 與 pytest task convention 值得概念借鑑；臨床 gold 仍需兩名盲評 reviewer 裁決。

## 與 RootCause MCP 的關係

| 面向 | Upstream | RootCause MCP 的處理 |
|---|---|---|
| Evidence lineage | trajectory 可證明查過哪些 FHIR tool；未定義 source-span hash | atomic snippet/location/hash/time 與 source manifest |
| DDx／推理 | task rubric 可要求 assessment，不是統一 DDx ledger | 至少三個 DDx、must-not-miss 與 evidence/test disposition |
| RCA／causation | 無 Fishbone／Why／HFACS／root audit | 保守 causation status 與 cross-object lineage |
| Final conformance | 670 checkpoints 與 outputs，無統一 final schema/hash | typed report、checks、reviewer/time、immutable snapshot |
| Human review | gold 由 benchmark 建置，執行結果可含 LLM judge | release 時兩名臨床 reviewer 盲評並裁決 |

## 採用建議

**決策：概念借鑑。** 優先採用 fresh FHIR environment、checkpoint taxonomy 與 per-run artifact layout；資料允許且資源足夠時，再做獨立 adapter POC。

1. 整合邊界：不把 FHIR image 或 corpus帶入 RootCause repo；adapter 只收 agent command、run IDs 與去識別結果。
2. Fail-closed：資料授權／模型外送未核准、container 非乾淨、grader 類型不明、LLM judge error、PHI leak 或 artifact/hash 缺漏皆算失敗。
3. Contract tests：fresh-state mutation、checkpoint disposition、judge/model/version 記錄、repeat isolation、timeout 與所有 artifacts 的 SHA-256。
4. 風險：Apache-2.0 僅涵蓋 code；受限 EHR image、外部模型、成本及混合 grader 影響可重現性，`pyproject` 名稱亦顯示 `healthagentbench`，整合時要避免套件辨識混淆。

### 概念引用方式

- 以論文／固定 commit 引用 benchmark 設計；若實作 adapter，pin image digest、task commit、model/judge ID 與 dependency lock。
- 病歷 image 與 benchmark 論文、repository software 分開列入 DUA inventory、SBOM 與研究紀錄。

## 不應直接照搬的部分

- 不把 test docstring 標為 deterministic 就忽略其內部 LLM judge 呼叫。
- 不因 container 每次重建就假設 jobs／trace 不含敏感資料。
- 不把 order 正確或 checkpoint pass 外推為完整 DDx、root cause 或臨床因果證明。

## 建議引用

### 軟體引用

```text
HealthRex. (2026). PhysicianBench (commit c7efa8fd5b1e4744ada50668efe4b7e84023cbb0) [Computer software]. GitHub. https://github.com/HealthRex/PhysicianBench
```

### BibTeX fallback

```bibtex
@software{healthrex_physicianbench_2026,
  author={{HealthRex}}, title={PhysicianBench}, year={2026},
  url={https://github.com/HealthRex/PhysicianBench},
  version={c7efa8fd5b1e4744ada50668efe4b7e84023cbb0}, note={Accessed 2026-08-18}
}
```

論文引用（與軟體分開，依 upstream BibTeX）：

```bibtex
@article{physicianbench2026,
  title={PhysicianBench: Evaluating LLM Agents on Physician Tasks in Real-World EHR Environments},
  author={Ruoqi Liu and Imran Q. Mohiuddin and Austin J. Schoeffler and Kavita Renduchintala and Ashwin Nayak and Prasantha L. Vemu and Shivam C. Vedak and Kameron C. Black and John L. Havlik and Isaac Ogunmola and Stephen P. Ma and Roopa Dhatt and Jonathan H. Chen},
  year={2026}, eprint={2605.02240}, archivePrefix={arXiv}, url={https://arxiv.org/abs/2605.02240}
}
```

## 來源

- [README](https://github.com/HealthRex/PhysicianBench/blob/c7efa8fd5b1e4744ada50668efe4b7e84023cbb0/README.md)／[LICENSE](https://github.com/HealthRex/PhysicianBench/blob/c7efa8fd5b1e4744ada50668efe4b7e84023cbb0/LICENSE)／[pyproject](https://github.com/HealthRex/PhysicianBench/blob/c7efa8fd5b1e4744ada50668efe4b7e84023cbb0/pyproject.toml)
- [runner](https://github.com/HealthRex/PhysicianBench/blob/c7efa8fd5b1e4744ada50668efe4b7e84023cbb0/scripts/run_task.py)／[代表性 checkpoint tests](https://github.com/HealthRex/PhysicianBench/blob/c7efa8fd5b1e4744ada50668efe4b7e84023cbb0/tasks/v1/aortic_aneurysm_cad/tests/test_outputs.py)
- [tasks tree](https://github.com/HealthRex/PhysicianBench/tree/c7efa8fd5b1e4744ada50668efe4b7e84023cbb0/tasks/v1)／[論文](https://arxiv.org/abs/2605.02240)

## 查核限制

本次未取得受限 FHIR image、未核對 DUA、未啟動 Docker／模型 API、未跑 100 tasks 或驗證官方分數；只涵蓋公開固定 commit，私人及未索引實作不在範圍。
