# `som-shahlab/medalign` 學習報告

> 本檔只記錄固定版本的文件與資料存取規則稽核，不代表 MedAlign 已通過臨床、安全或生產驗證。

## 查核資料

| 欄位 | 內容 |
|---|---|
| Upstream | [som-shahlab/medalign](https://github.com/som-shahlab/medalign) |
| 查核日期 | `2026-08-18` |
| 查核版本 | 預設分支 `main`，commit `4a88e4744ea31b1fdea8b191fdc9e4dc05cf624e` |
| 專案角色 | 受控 longitudinal EHR instruction-following benchmark／資料集 |
| 授權 | Repository `LICENSE` 為 MIT（Copyright 2023 som-shahlab）；受控資料另受 MedAlign DUA，MIT 不覆蓋其資料使用限制 |
| 本次驗證 | 查 README、LICENSE 與完整 tree（sample EHR/XML、CSV、solicitation PDFs）；repo 無 runner、schema 或 tests；**未申請 Redivis、未取得資料、未實跑** |

## 一句話結論

MedAlign 是多文件／長期 EHR synthesis 的重要外部 benchmark，但嚴格 DUA 禁止未合規外送、訓練與重發；只能在核准環境概念引用或受控評估，不能納入一般跨 Agent cloud runner。

## 它解決什麼問題

README 記錄 983 個 clinician-curated instructions，對應 275 份 longitudinal EHR，含 303 個 reference responses；底層規模為 46,252 notes、128 note types 與約 3.6 million OMOP events。

它以臨床人員提出的真實 EHR instruction 測試 timeline understanding、clinical reasoning 與 multi-document synthesis，且明定為 test-only benchmark，不得用於 supervised training／fine-tuning。

## 核心流程與資料邊界

公開 repo 只有說明、樣本與 instruction taxonomy；完整資料需以機構信箱申請 Redivis、完成 HIPAA-compliant CITI training、說明用途、簽 DUA，並聲明 encrypted/access-controlled storage，cloud 必須 HIPAA compliant。

README 明確禁止把 MedAlign 資料傳給不符合 HIPAA 的商業 API（例示 ChatGPT、Claude、Gemini）、禁止重發或建立衍生資料集；衍生研究 artifacts 需事先核准並託管於 Redivis。這些限制高於一般 repo MIT 使用直覺。

## 最值得學習的設計

- Clinician-generated instruction taxonomy，而非由診斷名稱自動生成題目，降低答案提示。
- Longitudinal notes 加 OMOP event 的多來源邊界，貼近 RootCause 的 multi-record synthesis。
- Test-only 與 reference response 只覆蓋部分 instructions，提醒評估需處理無單一 gold 的情況。
- 存取、CITI、加密與外送條款可作 RootCause 敏感病例 eval 的治理清單；不能複製受控資料。

## 與 RootCause MCP 的關係

| 面向 | Upstream | RootCause MCP 的處理 |
|---|---|---|
| Evidence lineage | longitudinal EHR/OMOP 提供內容，公開 repo 未定義 per-span provenance | source manifest、snippet/location/hash/time/extraction method |
| DDx／推理 | instruction/reference response 評 synthesis，不強制 competing DDx | typed DDx、must-not-miss、support/disconfirm/test disposition |
| RCA／causation | 未提供 Fishbone／Why／HFACS 或 conservative causation | root/evidence/Why lineage 與 causation status |
| Final conformance | 無公開 runner/schema/tests | nested report schema、checks、hash 與 immutable final |
| Human review | instructions 由 clinicians 產生，不等於每次 output 雙人盲評 | 兩名 qualified reviewer 盲評與分歧裁決 |

## 採用建議

**決策：概念借鑑。** 現階段只引用 instruction taxonomy 與 longitudinal synthesis 設計；取得機構核准後，才在封閉 HIPAA/DUA-compliant 環境執行外部 benchmark。

1. 整合邊界：不把 MedAlign data、reference responses、derived artifacts 或 trace commit 到 RootCause repo／一般 CI；受控 runner 與研究環境完全分離。
2. Fail-closed：無有效 DUA/CITI、storage encryption、access control、API/region/BAA 核准或外送路徑不明時禁止執行。
3. Contract tests：輸入去識別、network egress deny、agent workspace 清除、trace/redaction、reference 隔離、artifact inventory 與刪除／retention 稽核。
4. 風險：code/doc 為 MIT，但 data DUA 具有訓練、外送、重發與衍生品限制；公開 repo 無可執行 evaluator，存取審查也會影響可重現性。

### 概念引用方式

- 只引用論文、taxonomy 與固定 commit；受控資料不得成為 package dependency 或測試 fixture。
- 研究紀錄需另列 DUA 版本、Redivis dataset revision、核准人員／環境與資料銷毀條件。

## 不應直接照搬的部分

- 不因 repository 為 MIT 就推論完整 EHR data 可自由複製、訓練、重發或商業 API 外送。
- 不把 clinician-curated instruction 等同 gold response 全覆蓋或 blinded output adjudication。
- 不將受控病例內容、檔名、trace、hash lookup text 或錯誤訊息送入公共 CI。

## 建議引用

### 軟體引用

```text
Stanford Shah Lab. (2024). MedAlign (commit 4a88e4744ea31b1fdea8b191fdc9e4dc05cf624e) [Dataset documentation and samples]. GitHub. https://github.com/som-shahlab/medalign
```

### BibTeX fallback

```bibtex
@software{shahlab_medalign_repo_2024,
  author={{Stanford Shah Lab}}, title={MedAlign}, year={2024},
  url={https://github.com/som-shahlab/medalign},
  version={4a88e4744ea31b1fdea8b191fdc9e4dc05cf624e}, note={Accessed 2026-08-18}
}
```

論文引用（與 repository 軟體／資料引用分開，依 upstream BibTeX）：

```bibtex
@inproceedings{DBLP:conf/aaai/FlemingLHJRTBGS24,
  author={Scott L. Fleming and Alejandro Lozano and William J. Haberkorn and Jenelle A. Jindal and Eduardo Reis and Rahul Thapa and Louis Blankemeier and Julian Z. Genkins and Ethan Steinberg and Ashwin Nayak and Birju S. Patel and Chia-Chun Chiang and Alison Callahan and Zepeng Huo and Sergios Gatidis and Scott J. Adams and Oluseyi Fayanju and Shreya J. Shah and Thomas Savage and Ethan Goh and Akshay S. Chaudhari and Nima Aghaeepour and Christopher D. Sharp and Michael A. Pfeffer and Percy Liang and Jonathan H. Chen and Keith E. Morse and Emma P. Brunskill and Jason A. Fries and Nigam H. Shah},
  title={MedAlign: A Clinician-Generated Dataset for Instruction Following with Electronic Medical Records},
  booktitle={Thirty-Eighth AAAI Conference on Artificial Intelligence}, year={2024},
  doi={10.1609/AAAI.V38I20.30205}, url={https://doi.org/10.1609/aaai.v38i20.30205}
}
```

## 來源

- [README／DUA 摘要](https://github.com/som-shahlab/medalign/blob/4a88e4744ea31b1fdea8b191fdc9e4dc05cf624e/README.md)／[LICENSE](https://github.com/som-shahlab/medalign/blob/4a88e4744ea31b1fdea8b191fdc9e4dc05cf624e/LICENSE)
- [公開 data samples tree](https://github.com/som-shahlab/medalign/tree/4a88e4744ea31b1fdea8b191fdc9e4dc05cf624e/data)／[Redivis 入口](https://redivis.com/datasets/48nr-frxd97exb)
- [AAAI 論文 DOI](https://doi.org/10.1609/aaai.v38i20.30205)

## 查核限制

本次未閱讀實際簽署版 DUA、未申請或存取完整資料，亦未驗證 reference responses／evaluation protocol；結論只涵蓋公開 README、樣本與授權，私人及未索引資料不在範圍。
