# `makidav/clinical-assistant` 學習報告

> 本報告只做 upstream 文件與原始碼稽核，不代表該專案已通過臨床、安全或生產驗證。

## 查核資料

| 欄位 | 內容 |
|---|---|
| Upstream | [makidav/clinical-assistant](https://github.com/makidav/clinical-assistant) |
| 查核日期 | `2026-08-18` |
| 查核版本 | `main` / `0801291007a569aad1144d22c93059c9949e9c50` |
| 專案角色 | 相鄰方案；clinical reasoning Agent Skill 與 evaluation rubric |
| 授權 | [CC BY 4.0](https://github.com/makidav/clinical-assistant/blob/0801291007a569aad1144d22c93059c9949e9c50/LICENSE)；三個 ToolUniverse-derived scripts 另依 Apache-2.0 並記於 NOTICE |
| 本次驗證 | README、SKILL、references、CITATION.cff、NOTICE、structural validator 與 eval rubric；未安裝、未呼叫模型、未跑臨床案例 |

## 一句話結論

它不能取代持久化 MCP ledger，但 phenotype-first anti-anchoring、雙分支 LR test utility、citation/retraction gate 與 harm-first regression rubric 是最值得吸收的 reasoning policy。

## 它解決什麼問題

Clinical-Assistant 是單一 Agent Skill，透過 router 加八階段流程完成 intake、evidence search、GRADE/appraisal、13-perspective board、plan、report、QA 與 update。所有輸出都要求標為需 qualified review 的 draft。

它著重「可檢查而非流暢」：先由 phenotype 重建 differential、延後暴露既有診斷、檢查 citation resolution/retraction/claim fit，並用 pre-test probability、LR+、LR− 算兩個結果分支是否跨 decision threshold。

## 核心流程與資料邊界

- 輸入是去識別 case text、研究問題或 image；Skill 以文字規則指導 host Agent 與外部搜尋工具。
- workflow 與 safety gates 主要是 prompt instructions；scripts 做 citation、計算、skill 結構與 eval aggregation。
- 沒有 server-side case database、MCP mutation gate、source manifest 或 cross-object invariant。
- human review 留在 draft 標示與 eval reviewer 欄位，沒有授權 reviewer allowlist 或 signed final state。
- 評估建議使用 clinician 自有 de-identified closed cases，含 clean/anchored/red-herring/premature-closure arms。

## 最值得學習的設計

- phenotype-only research loop 與之後的 prior-label audit，可轉成 RootCause 的 anti-leak/anti-anchoring eval mutation。
- diagnostic test 必須計算陽性與陰性兩個 post-test 分支；兩邊都不改決策就不列入 workup。
- conclusion confidence 不得高於 evidence certainty，並要求寫出「什麼會改變判斷」。
- [eval rubric](https://github.com/makidav/clinical-assistant/blob/0801291007a569aad1144d22c93059c9949e9c50/eval/rubric.md) 把 serious/critical harm、fabricated citation 與 overconfidence 設成 stop-the-line，而非平均掉。
- [structural validator](https://github.com/makidav/clinical-assistant/blob/0801291007a569aad1144d22c93059c9949e9c50/scripts/validate_skill.py) 驗證 instruction bundle 的 cross-reference 與 safety invariant，值得鏡射到 harness assets。

## 與 RootCause MCP 的關係

| 面向 | Upstream | RootCause MCP 的處理 |
|---|---|---|
| Evidence lineage | citations、GRADE、claim-source/retraction policy；沒有 case source hash ledger | atomic source observations、locations、hashes、certainty 與 hypothesis links |
| DDx／推理 | phenotype-first DDx、must-not-miss prompts、Bayesian test branches | server-persisted DDx、direct applied LR、active/test dispositions |
| RCA／causation | 只稽核 citation causality inflation，無 clinical RCA methods | Fishbone、Why、HFACS 與 conservative causation audit |
| Final conformance | P7 prompt QA 與 skill linter，不是 report admission control | typed nested report 與 recomputed conformance checks |
| Human review | 所有產物標 DRAFT；rubric 有 reviewer 欄 | allowlisted reviewer/time/hash 與 immutable finalized snapshot |

## 採用建議

決策：**概念借鑑**，不要同時載入兩個會爭奪 case workflow 的 skills。

1. 整合邊界：把 anti-anchoring mutations、test-utility checks、citation/retraction disposition 與 harm rubric移入 RootCause eval/conformance；不匯入整套 prompt router。
2. Fail-closed：未標 citation status、LR 無來源/未知未用 1.0、must-not-miss 無 disposition、serious harm 或 fabricated evidence 時不得通過 release gate。
3. Contract tests：label withholding、anchored repeat、雙分支計算、decision-threshold no-op test、retracted citation、N3 evidence 洩入 plan。
4. 授權風險：CC BY 4.0 需要 attribution/change indication；bundled scripts 的 Apache-2.0 provenance 必須保留。

### 概念引用方式

- 優先在 RootCause ADR、eval rubric 與文件引用 upstream `CITATION.cff`，再獨立實作規則。
- 若複製/改寫 CC-BY 文字，清楚標出作者、來源、license、修改內容與固定 commit；Apache-derived scripts 另保留 NOTICE。
- upstream CFF 仍寫 version `6.8`，但 HEAD `SKILL.md` 是 `v6.9`；固定 commit 引用比引用該 version 欄更可靠。

## 不應直接照搬的部分

- prompt 中的 hard gate 仍受 host Agent 是否遵守限制，不能取代 server enforcement。
- specialty must-not-miss lists 自稱 screening prompts，不能直接當 gold differential 或醫療規則庫。
- LLM-applied GRADE/QUADAS 等是 reviewer aid，不是 automated verdict。
- CC BY 適用於 code/content 的組合需保留 attribution；不可只寫「open source」略過 NOTICE 的雙重來源。

## 建議引用

### 軟體引用

```text
Hernández Irisarri, D. (2026). Clinical-Assistant: a Virtual Clinical Team as a single Agent Skill (commit 0801291007a569aad1144d22c93059c9949e9c50) [Computer software]. GitHub. https://github.com/makidav/clinical-assistant
```

### BibTeX fallback

```bibtex
@software{hernandez_irisarri_clinical_assistant_2026,
  author  = {Hernández Irisarri, David},
  title   = {Clinical-Assistant: a Virtual Clinical Team as a single Agent Skill},
  year    = {2026},
  url     = {https://github.com/makidav/clinical-assistant},
  version = {0801291007a569aad1144d22c93059c9949e9c50},
  note    = {Accessed 2026-08-18}
}
```

## 來源

- [README](https://github.com/makidav/clinical-assistant/blob/0801291007a569aad1144d22c93059c9949e9c50/README.md)
- [Canonical SKILL.md](https://github.com/makidav/clinical-assistant/blob/0801291007a569aad1144d22c93059c9949e9c50/SKILL.md)
- [Evaluation protocol and rubric](https://github.com/makidav/clinical-assistant/tree/0801291007a569aad1144d22c93059c9949e9c50/eval)
- [CITATION.cff](https://github.com/makidav/clinical-assistant/blob/0801291007a569aad1144d22c93059c9949e9c50/CITATION.cff)
- [Third-party NOTICE](https://github.com/makidav/clinical-assistant/blob/0801291007a569aad1144d22c93059c9949e9c50/NOTICE.md)

## 查核限制

本次為 source audit only。未執行其 structural/citation self-tests，未安裝成 Agent Skill，也未驗證任何 case output；其工程 target 與 prompt completeness 不能解讀為 clinical performance。
