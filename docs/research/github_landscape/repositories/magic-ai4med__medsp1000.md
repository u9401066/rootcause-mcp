# `MAGIC-AI4Med/MedSP1000` 學習報告

> 本檔只記錄固定版本的文件與原始碼稽核，不代表 MedSP1000 已通過臨床、安全或生產驗證。

## 查核資料

| 欄位 | 內容 |
|---|---|
| Upstream | [MAGIC-AI4Med/MedSP1000](https://github.com/MAGIC-AI4Med/MedSP1000) |
| 查核日期 | `2026-08-18` |
| 查核版本 | 預設分支 `main`，commit `2806984cb331d6fedc2c0555e3c1c4a54171c77a` |
| 專案角色 | interactive standardized-patient clinical agent benchmark |
| 授權 | `LICENSE` 為 MIT 範本文字，但保留 `<YEAR>`／`<COPYRIGHT HOLDER>` placeholder；**待 maintainer／法務確認** |
| 本次驗證 | 查 README、完整 tree、1,638 份 rubric JSON、sample rubric、simulation/evaluation scripts、LICENSE、CITATION；未見正式 tests suite；**未下載 dataset、未安裝、未實跑** |

## 一句話結論

Frozen rubric、closed-loop state 與 per-run artifact 很值得學，但目前 repository 仍有 license/CITATION placeholder、缺文件／測試與 LLM evaluator 邊界；只作概念借鑑。

## 它解決什麼問題

MedSP1000 把 peer-reviewed MedEdPORTAL standardized-patient teaching material轉成 1,638 個 interactive cases、17 specialties 與 24,602 rubric items，依 ACGME 六項 competency 評分。

每次 encounter 由 clinician agent、patient agent、environment controller 與 evaluator agent 閉環互動。README 稱 12 位 clinicians 檢查 cases／trajectories且各自 double-scored，並報告 1,638 個 frozen rubric JSON 已隨 repo 發布。

## 核心流程與資料邊界

下載 Hugging Face scenario materials後建立 manifest，examinee 只見 clinician packet；patient script、environment state 與 evaluator material分角色保存。Runner 支援並行、resume、status marker、test-time-compute，輸出 transcript、agent logs 與 `final_evaluation_frozen_rubric.json`。

Frozen rubric 是版本化評分規則，不是 deterministic proof；最終逐項 true/false 仍由 evaluator agent判斷。Patient/environment 模型與 evaluator 共用外部 API 時，scenario 內容與 model drift 都是額外資料／重現性邊界。

## 最值得學習的設計

- Freeze-before-run rubric，避免看見模型答案後改規則。
- Clinician／patient／environment／evaluator packets 分離，降低角色間答案洩漏。
- 六 competency 與細項 disposition 比單一總分更可診斷。
- Idempotent status marker、resume、isolated test-time strategies 與 per-run artifacts 適合大型 eval。
- RootCause 可採 frozen gold rubric 與 blind adjudication流程，但 deterministic safety checks必須另寫。

## 與 RootCause MCP 的關係

| 面向 | Upstream | RootCause MCP 的處理 |
|---|---|---|
| Evidence lineage | scenario packets／transcript，sample rubric含本機路徑但無 source hash contract | manifest、snippet/location/hash/time 與 extraction method |
| DDx／推理 | rubric 可評 clinical actions，無固定 competing DDx schema | 三個 DDx、must-not-miss、evidence/test disposition |
| RCA／causation | 教學 encounter，不做 Fishbone／Why／HFACS | conservative RCA／causation ledger |
| Final conformance | frozen-rubric JSON，未見跨物件 final schema/hash | typed report、checks、review/time、immutable snapshot |
| Human review | upstream case/trajectory雙重評分是 dataset validation | 每個 RootCause output 仍需雙 reviewer 盲評／裁決 |

## 採用建議

**決策：概念借鑑。** 採 frozen rubric、角色隔離與 resumable artifact pattern；在授權與 evaluator contract 補齊前不建立 dependency。

1. 整合邊界：只引用 rubric/versioning 方法；不 vendor MedEdPORTAL／HF materials 或上游 simulation code。
2. Fail-closed：rubric version/hash、role packet isolation、judge/model/prompt、artifact、human adjudication或 license 任一不明即不作 release evidence。
3. Contract tests：rubric immutable、兩 reviewer 分歧、judge error、resume 不覆寫、每 run hash、gold 不進 examinee context。
4. 風險：MIT placeholder 法律品質不足；`CITATION.cff` 仍是 placeholder、README 連到不存在的 `docs/RUNNING.md` 且留有未完成表格提示，repo 無完整 tests suite；dataset/MedEdPORTAL 權利需另查。

### 概念引用方式

- 固定引用 commit 與 arXiv；若未來整合，先取得明確 LICENSE/CFF，再 pin dataset revision、rubric hash、model/judge/prompt 與 container digest。
- 論文、repository software、Hugging Face dataset、MedEdPORTAL source materials 分開記錄授權與引用。

## 不應直接照搬的部分

- 不把 evaluator-agent true/false 當 deterministic conformance 或臨床因果證明。
- 不把 upstream 12 clinicians 的 dataset validation 說成 RootCause 每次 run 的兩人盲評。
- 不使用含絕對本機 `scenario_dir` 的 rubric 原樣進入可攜 artifact。

## 建議引用

### 軟體引用

```text
MAGIC-AI4Med. (2026). MedSP1000 (commit 2806984cb331d6fedc2c0555e3c1c4a54171c77a) [Computer software]. GitHub. https://github.com/MAGIC-AI4Med/MedSP1000
```

### BibTeX fallback

```bibtex
@software{magic_medsp1000_2026,
  author={{MAGIC-AI4Med}}, title={MedSP1000}, year={2026},
  url={https://github.com/MAGIC-AI4Med/MedSP1000},
  version={2806984cb331d6fedc2c0555e3c1c4a54171c77a}, note={Accessed 2026-08-18}
}
```

論文引用（與軟體分開，依 README；arXiv 尚非 DOI）：

```bibtex
@misc{liang2026evaluatinglargelanguagemodels,
  title={Evaluating Large Language Models in Dynamic Clinical Decision-Making with Standardized Patient Cases},
  author={Cheng Liang and Pengcheng Qiu and Ya Zhang and Yanfeng Wang and Chaoyi Wu and Weidi Xie},
  year={2026}, eprint={2606.05112}, archivePrefix={arXiv}, primaryClass={cs.CL},
  url={https://arxiv.org/abs/2606.05112}
}
```

## 來源

- [README](https://github.com/MAGIC-AI4Med/MedSP1000/blob/2806984cb331d6fedc2c0555e3c1c4a54171c77a/README.md)／[LICENSE](https://github.com/MAGIC-AI4Med/MedSP1000/blob/2806984cb331d6fedc2c0555e3c1c4a54171c77a/LICENSE)／[CITATION.cff](https://github.com/MAGIC-AI4Med/MedSP1000/blob/2806984cb331d6fedc2c0555e3c1c4a54171c77a/CITATION.cff)
- [sample frozen rubric](https://github.com/MAGIC-AI4Med/MedSP1000/blob/2806984cb331d6fedc2c0555e3c1c4a54171c77a/rubrics/mededportal_10009_scenario1.json)／[simulation source](https://github.com/MAGIC-AI4Med/MedSP1000/tree/2806984cb331d6fedc2c0555e3c1c4a54171c77a/src/simulate)
- [論文](https://arxiv.org/abs/2606.05112)／[dataset](https://huggingface.co/datasets/byrLLCC/MedSP1000)

## 查核限制

本次未下載 HF/MedEdPORTAL 資料、未呼叫模型、未重現 1,638 runs 或人類評分；也未做法律判定，只指出直接讀到的 placeholder。公開 GitHub 無法涵蓋私人或未索引實作。
