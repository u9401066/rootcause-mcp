# `mmonfar/clinical-node` 學習報告

> 本報告只做 upstream 文件與原始碼稽核，不代表該專案已通過臨床、安全或生產驗證。

## 查核資料

| 欄位 | 內容 |
|---|---|
| Upstream | [mmonfar/clinical-node](https://github.com/mmonfar/clinical-node) |
| 查核日期 | `2026-08-18` |
| 查核版本 | `main` / `0834357a106e26cea02199e2bf0bbaebc0149e6f` |
| 專案角色 | 相鄰方案；multi-Agent virtual M&M committee prototype |
| 授權 | README 寫「MIT」，但 tree 無 LICENSE/COPYING；授權條文與授權人不完整，**待法務確認** |
| 本次驗證 | README、Streamlit app、clinical engine、PubMed client、state manager、72-hour refinement；無 schema/tests/CITATION，未安裝或實跑 |

## 一句話結論

它不能取代 RootCause MCP，但多角色 M&M debate、evidence ladder、critical-gap banner 與新證據 dissent workflow 是有用的 reporting/UX 參考。

## 它解決什麼問題

Clinical Intelligence Node 以 Researcher、MDT Roundtable、Auditor 三個 LLM 角色處理 clinical case，搜尋 PubMed、選 25+ specialties、產生 risk heatmap、information gaps、discussion transcript 與正式 M&M minutes。

當初始查詢結果過少時，Researcher 拆成 conflict、guideline、procedure 三個 evidence pillars；另有排程器每 72 小時重查 PubMed，以 LLM 判斷新文章是否推翻既有 minutes，並追加 dissenting opinion/needs-review。

## 核心流程與資料邊界

- free text 先由 LLM 轉成 SBAR；source 明確指示可從 context「infer missing fields」，這不符合 RootCause 的 no-invention boundary。
- SBAR 產 PubMed query，依 RCT/review/guideline → trial/observational → case report ladder檢索並摘取 abstracts。
- GPT roundtable 產 raw dict，Auditor 再生成 Markdown；無 Pydantic/JSON Schema admission。
- `cases.json` 可覆寫最新 committee output；minutes 以 timestamp block append，但沒有 content hash 或 reviewer signature。
- case text 會送 OpenAI、query/metadata 送 NCBI；README 明說無 authentication，不應公開部署。

## 最值得學習的設計

- multi-pillar evidence search 可避免罕見/衝突事件只靠一個過窄 query，並明示空 pillar 是 evidence gap。
- dynamic specialty panel 與 mandatory invitees 可轉成「哪些 clinical reviewer 必須出席」的 advisory planner。
- [append-only-style minutes](https://github.com/mmonfar/clinical-node/blob/0834357a106e26cea02199e2bf0bbaebc0149e6f/state_manager.py) 保留每次會議 block，比只覆寫一份 Markdown 更能看演變。
- [72-hour refinement](https://github.com/mmonfar/clinical-node/blob/0834357a106e26cea02199e2bf0bbaebc0149e6f/cron_refine.py) 用 dissent 而非靜默改寫舊結論，適合借為 stale literature alert。
- UI 把 critical information gaps 置頂，可提升 human handoff 的安全可見性。

## 與 RootCause MCP 的關係

| 面向 | Upstream | RootCause MCP 的處理 |
|---|---|---|
| Evidence lineage | PMID/URL、abstract 與 evidence tier；case facts 無 source location/hash | case source ledger 與 literature citation分層、exact lineage |
| DDx／推理 | MDT risk debate，不提供 formal DDx ledger/LR | active DDx、must-not-miss、support/refute/test disposition |
| RCA／causation | 稱 M&M 且列 systemic gaps，無 Fishbone/Why/HFACS | structured RCA methods 與 conservative causation audit |
| Final conformance | raw dict + LLM Markdown、可覆寫 cases JSON | typed report、recomputed checks、review/hash immutable snapshot |
| Human review | virtual specialists 是 models；needs-review 是 status flag | qualified human allowlist、identity/role/time 與 adjudication |

## 採用建議

決策：**概念借鑑**；不把 virtual committee 當 reviewer，也不複製無完整授權的 code。

1. 整合邊界：只借 evidence-pillar query planner 與 new-literature dissent notification；文獻不得改寫 case-specific verified evidence。
2. Fail-closed：SBAR inferred fact、無 PMID/full claim support、model-only contradiction、無 human review 時保持 unverified/preliminary。
3. Contract tests：empty pillar、duplicate PMID、retracted/new evidence、old snapshot preserved、dissent linkage、PHI-free query、reviewer-vs-agent identity。
4. 授權風險：README 的單字 MIT 不等於附完整授權條文；取得正式 LICENSE 前只引用概念。

### 概念引用方式

- 在 literature-refresh/M&M UX ADR 引用固定 commit 與特定 source file。
- 不複製 prompts、CSS、specialty list 或 code；以既有 PubMed MCP 與 RootCause schema獨立實作。
- 若上游補正式 license，重新 pin snapshot，於 NOTICE/SBOM 記錄，不以目前 README 聲明回溯授權。

## 不應直接照搬的部分

- SBAR parser 的「infer missing fields」可能製造病例事實，與 no-fabrication 原則直接衝突。
- LLM 依截短 abstract 判斷 contradiction 不是可靠 systematic evidence review。
- virtual HOD/MDT 不等於 qualified clinicians，不能滿足 final reviewer gate。
- append Markdown 仍可由 filesystem 改寫；「full audit trail」不是 tamper-evident assurance。

## 建議引用

### 軟體引用

```text
mmonfar. (2026). clinical-node (commit 0834357a106e26cea02199e2bf0bbaebc0149e6f) [Computer software]. GitHub. https://github.com/mmonfar/clinical-node
```

### BibTeX fallback

```bibtex
@software{mmonfar_clinical_node_2026,
  author  = {mmonfar},
  title   = {Clinical Intelligence Node},
  year    = {2026},
  url     = {https://github.com/mmonfar/clinical-node},
  version = {0834357a106e26cea02199e2bf0bbaebc0149e6f},
  note    = {Accessed 2026-08-18; README says MIT but no LICENSE file found}
}
```

## 來源

- [README](https://github.com/mmonfar/clinical-node/blob/0834357a106e26cea02199e2bf0bbaebc0149e6f/README.md)
- [Clinical engine](https://github.com/mmonfar/clinical-node/blob/0834357a106e26cea02199e2bf0bbaebc0149e6f/clinical_engine.py)
- [PubMed client](https://github.com/mmonfar/clinical-node/blob/0834357a106e26cea02199e2bf0bbaebc0149e6f/pubmed_client.py)
- [State manager](https://github.com/mmonfar/clinical-node/blob/0834357a106e26cea02199e2bf0bbaebc0149e6f/state_manager.py)
- [Repository tree showing no LICENSE/tests](https://github.com/mmonfar/clinical-node/tree/0834357a106e26cea02199e2bf0bbaebc0149e6f)

## 查核限制

本次為 source audit only。未找到 conventional tests 或 executable schemas；未重跑 OpenAI/Entrez、M&M minutes、scheduled refinement 或任何 clinical output，亦未驗證 README 的效能、安全或「JCI-grade」呈現語句。
