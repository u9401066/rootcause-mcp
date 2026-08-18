# `akhilapugazhendhi98/RCA-Assistant-for-Healthcare-Events` 學習報告

> 本報告只做 upstream 文件與原始碼稽核，不代表該專案已通過臨床、安全或生產驗證。

## 查核資料

| 欄位 | 內容 |
|---|---|
| Upstream | [akhilapugazhendhi98/RCA-Assistant-for-Healthcare-Events](https://github.com/akhilapugazhendhi98/RCA-Assistant-for-Healthcare-Events) |
| 查核日期 | `2026-08-18` |
| 查核版本 | `main` / `7facacde362db0ca2328ce86b75bb3ca7ce08349` |
| 專案角色 | 相鄰方案；healthcare patient-safety RCA facilitator |
| 授權 | repository 未提供 LICENSE/COPYING；**無可推定的重用授權，待法務確認** |
| 本次驗證 | README、Streamlit app、四組 prompts、deterministic scope checker、12 synthetic scenarios、rubric/model judge/results；未安裝或實跑 |

## 一句話結論

它不能取代 RootCause MCP，但「stakeholder evidence → safety layer → guided Why → actionability/scope → human-editable report」是很清楚的病安 RCA UX 參考。

## 它解決什麼問題

Patient Safety RCA Navigator 協助 quality/patient-safety 團隊避免把事故歸因成「溝通失敗」「人為錯誤」等不可操作結論。六個畫面依序收集事件、stakeholder accounts、contributing factors、guided 5 Whys、action readiness 與 final report。

LLM 產生問題、layer mapping、Why 與 actionability；使用者可選取、排除、修改、重生、接受或 override。scope checker 先以 keyword 規則分類 `in_scope`、`needs_escalation`、`mixed`，再進模型評估。

## 核心流程與資料邊界

- 輸入是 incident description、category、stakeholder roles/answers；state 存在 Streamlit session。
- selected finding 保留一段 `evidence` 字串並逐步帶入 Why prompt，但無 source document、location 或 hash。
- Why chain 最多五步，可由模型提早提出 root cause，最後由使用者接受或自行改寫。
- output 是 downloadable report；沒有 typed report schema、persistent session、reviewer binding 或 artifact hash。
- 專案只使用 synthetic scenarios；真實案例會送 OpenAI 的 deployment/privacy 邊界未被此專案驗證。

## 最值得學習的設計

- stakeholder-specific question gathering 讓事件敘事不是只取單一角色，適合做 RCA intake facade。
- human 可逐項 include/exclude/override，使 LLM 建議保持「候選」而非自動 root cause。
- [deterministic scope checker](https://github.com/akhilapugazhendhi98/RCA-Assistant-for-Healthcare-Events/blob/7facacde362db0ca2328ce86b75bb3ca7ce08349/tools/scope_checker.py) 將 ownership/actionability 與 model judgment 分層。
- [synthetic cases](https://github.com/akhilapugazhendhi98/RCA-Assistant-for-Healthcare-Events/blob/7facacde362db0ca2328ce86b75bb3ca7ce08349/scenarios/test_scenarios.json) 同時列 strong、weak、baseline RCA，可轉成 forbidden vague/blame claims。
- actionability、scope、causal coherence、system focus 的 rubric 可補 RootCause RCA-specific quality score，但不能取代 hard invariants。

## 與 RootCause MCP 的關係

| 面向 | Upstream | RootCause MCP 的處理 |
|---|---|---|
| Evidence lineage | stakeholder answer 與 finding evidence 字串 | exact snippet/source/location/hash 加 evidence IDs |
| DDx／推理 | 不處理 clinical differential diagnosis | active DDx、must-not-miss、LR、test disposition |
| RCA／causation | guided Why、四 safety layers、actionability/scope | Fishbone/Why/HFACS、root ledger consistency、conservative causation status |
| Final conformance | downloadable report 與 disclaimer，無 typed admission | nested report schema、machine checks、unsafe mutation blocks |
| Human review | 全流程可 edit/accept/override，但無 reviewer identity | named authorized reviewer/time/hash/frozen final |

## 採用建議

決策：**概念借鑑**；因無 LICENSE，不複製 code、prompt、scenario text 或 UI assets。

1. 整合邊界：自行實作 stakeholder intake/actionability views，輸入輸出都映射既有 RootCause IDs。
2. Fail-closed：user accept 不能自動成 `VERIFIED`；evidence 不可定位、root 與 Why 不一致、scope unresolved 時保持 proposed。
3. Contract tests：weak/blame phrase、out-of-scope cause、manual override audit、Why/root exact link、excluded factor 不得進 final bucket。
4. 授權風險：無 repo-level license 即預設保留所有權；只能描述觀念並引用 URL，除非取得書面授權。

### 概念引用方式

- 在 UX/ADR 文件引用固定 commit，描述借鑑 stakeholder layering、guided Why 與 action-readiness workflow。
- 不複製其 prompts、synthetic scenario wording、screenshots 或 PDF。
- 若作者日後補 license，再重新做 license snapshot 與 provenance review，不回溯假設目前已獲授權。

## 不應直接照搬的部分

- keyword scope classification 只能作提示；不能把「local control」誤當 causal validity。
- model-as-judge 與五個代表案例的分數不是 blinded clinical validation。
- session-state final report 可繼續變更，沒有 recomputable hash 或 immutable snapshot。
- synthetic-only privacy 聲明不代表真實 PHI 可安全送入外部模型。

## 建議引用

### 軟體引用

```text
akhilapugazhendhi98. (2026). RCA-Assistant-for-Healthcare-Events (commit 7facacde362db0ca2328ce86b75bb3ca7ce08349) [Computer software]. GitHub. https://github.com/akhilapugazhendhi98/RCA-Assistant-for-Healthcare-Events
```

### BibTeX fallback

```bibtex
@software{akhilapugazhendhi98_rca_navigator_2026,
  author  = {akhilapugazhendhi98},
  title   = {RCA-Assistant-for-Healthcare-Events},
  year    = {2026},
  url     = {https://github.com/akhilapugazhendhi98/RCA-Assistant-for-Healthcare-Events},
  version = {7facacde362db0ca2328ce86b75bb3ca7ce08349},
  note    = {Accessed 2026-08-18; no repository license found}
}
```

## 來源

- [README](https://github.com/akhilapugazhendhi98/RCA-Assistant-for-Healthcare-Events/blob/7facacde362db0ca2328ce86b75bb3ca7ce08349/README.md)
- [Application workflow](https://github.com/akhilapugazhendhi98/RCA-Assistant-for-Healthcare-Events/blob/7facacde362db0ca2328ce86b75bb3ca7ce08349/app.py)
- [Guided Whys prompt](https://github.com/akhilapugazhendhi98/RCA-Assistant-for-Healthcare-Events/blob/7facacde362db0ca2328ce86b75bb3ca7ce08349/prompts/guided_whys.py)
- [Evaluation rubric/model judge/results](https://github.com/akhilapugazhendhi98/RCA-Assistant-for-Healthcare-Events/tree/7facacde362db0ca2328ce86b75bb3ca7ce08349/evaluation)
- [Repository tree showing no LICENSE](https://github.com/akhilapugazhendhi98/RCA-Assistant-for-Healthcare-Events/tree/7facacde362db0ca2328ce86b75bb3ca7ce08349)

## 查核限制

本次是 source audit only。未找到 conventional tests 或 executable schema validation；未重跑 12 synthetic scenarios、五案例 judge 評估、OpenAI calls 或 report export，也未做 clinical reviewer audit。
