# `bshepp/clinical-decision-support-agent` 學習報告

> 本報告只做 upstream 文件與原始碼稽核，不代表該專案已通過臨床、安全或生產驗證。

## 查核資料

| 欄位 | 內容 |
|---|---|
| Upstream | [bshepp/clinical-decision-support-agent](https://github.com/bshepp/clinical-decision-support-agent) |
| 查核日期 | `2026-08-18` |
| 查核版本 | `master` / `8f07b6b59eaf2444b9b5cb89432c26aa8a58246d` |
| 專案角色 | 直接競品；MCP clinical decision-support pipeline |
| 授權 | [Apache License 2.0](https://github.com/bshepp/clinical-decision-support-agent/blob/8f07b6b59eaf2444b9b5cb89432c26aa8a58246d/LICENSE) |
| 本次驗證 | README、architecture、Pydantic schemas、orchestrator、MCP、FHIR/CDS Hooks adapters、validation scripts/results；未安裝或實跑 |

## 一句話結論

它證明「MCP 可串起 free-text/FHIR → DDx → drug/guideline/conflict → typed report」，但沒有可持久續接的 evidence/RCA ledger，且自身 50-case top-3 結果也說明 smoke completion 不能代表 clinical conformance。

## 它解決什麼問題

專案提供六步 pipeline：patient parsing、clinical reasoning、drug interaction、guideline retrieval、conflict detection 與 report synthesis，並可轉成 CDS Hooks cards。MCP 同時提供 blocking full-run、submit/poll/result 與單步工具。

其 Pydantic schemas 將 patient profile、ranked diagnosis、recommendations、conflicts 與 final report typed 化；FHIR adapter 接收 Bundle/resource，RAG corpus 提供 clinical guideline search。

## 核心流程與資料邊界

- 輸入可為 free-text 或 FHIR；LLM 解析 patient profile 並產生 differential、reasoning、workup 與 synthesis。
- deterministic code 驗證 Pydantic shape、做部分 drug/conflict formatting；diagnosis 數量與 evidence quality 多靠 prompt。
- MCP async case store 在 process memory，TTL 為 600 秒；到期或重啟後無法續接。
- report 可輸出 JSON/CDS Hooks，但沒有原始 snippet location/hash、case manifest 或 qualified-review state。
- upstream 自報 50-case MedQA run pipeline success 94%、top-3 38%；本次未重現，且 MedQA 含非診斷題。

## 最值得學習的設計

- [blocking 與 submit/poll MCP surface](https://github.com/bshepp/clinical-decision-support-agent/blob/8f07b6b59eaf2444b9b5cb89432c26aa8a58246d/src/backend/app/mcp_server.py) 可作長任務 UX 參考。
- [typed nested schemas](https://github.com/bshepp/clinical-decision-support-agent/blob/8f07b6b59eaf2444b9b5cb89432c26aa8a58246d/src/backend/app/models/schemas.py) 涵蓋各 pipeline step，而非只驗 top-level envelope。
- [CDS Hooks adapter](https://github.com/bshepp/clinical-decision-support-agent/blob/8f07b6b59eaf2444b9b5cb89432c26aa8a58246d/src/backend/app/tools/cds_hooks.py) 將 differential、warning、conflict、recommendation 拆成不同 cards。
- validation runner 有 seed、checkpoint/resume 與不同資料集 adapter；可學 lifecycle，但 scorer 需換成 RootCause private gold rubric。
- 公開低準確率而非只報成功案例，是值得保留的工程誠實模式。

## 與 RootCause MCP 的關係

| 面向 | Upstream | RootCause MCP 的處理 |
|---|---|---|
| Evidence lineage | report 中有 supporting strings/guideline sources，無 case source identity/hash | exact snippet/location/hash、source manifest 與 ledger IDs |
| DDx／推理 | prompt 要求約五個 DDx、qualitative likelihood 與 support/argue-against | schema 強制三個 active DDx、direct LR、must-not-miss 與 tests |
| RCA／causation | guideline conflict，不含 incident RCA 或 causation | Fishbone/Why/HFACS、root lineage、conservative causation audit |
| Final conformance | nested Pydantic report，無 admission hash/final lifecycle | nested report + machine checks + fail-closed finalization |
| Human review | disclaimer/caveat；無 reviewer record | allowlisted reviewer、time、hash、immutable snapshot |

## 採用建議

決策：**概念借鑑**；CDS Hooks 可做獨立 export adapter，不接管 RootCause reasoning state。

1. 整合邊界：借 submit/poll job contract 與 CDS Hooks rendering；case truth 仍只寫 RootCause ledger。
2. Fail-closed：MCP success text 不等於 workflow complete；缺 persisted session、lineage、reviewer 或 recomputed checks 時禁止 finalized。
3. Contract tests：timeout/poll/idempotency、TTL/restart、FHIR unit/negation、nested invalid DDx、CDS Hooks card provenance、error-looking payload。
4. 授權風險：Apache-2.0 可重用，但 bundled guideline corpus、模型與資料集可能有各自條款，需獨立盤點。

### 概念引用方式

- 優先以 protocol adapter 實作 CDS Hooks，不直接嵌入 upstream whole pipeline。
- 若採用程式碼，pin commit/image digest，保留 Apache-2.0 LICENSE，並於 NOTICE/SBOM 記錄來源與修改。
- validation 數據引用時同時標明模型、日期、50-case sample 與 upstream self-reported 性質。

## 不應直接照搬的部分

- in-memory 10-minute store 不適合多次 agent handoff、稽核或 superseding-session replay。
- `supporting_evidence: list[str]` 沒有 source ID/location，不能提升為 verified evidence。
- qualitative `likelihood` 與 fuzzy normalization 不是 LR 或 calibrated probability。
- keyword case tests、MedQA matching 與 report self-consistency 不能取代 must-not-miss、PHI、lineage、forbidden-claim evaluation。

## 建議引用

### 軟體引用

```text
bshepp. (2026). clinical-decision-support-agent (commit 8f07b6b59eaf2444b9b5cb89432c26aa8a58246d) [Computer software]. GitHub. https://github.com/bshepp/clinical-decision-support-agent
```

### BibTeX fallback

```bibtex
@software{bshepp_clinical_decision_support_agent_2026,
  author  = {bshepp},
  title   = {clinical-decision-support-agent},
  year    = {2026},
  url     = {https://github.com/bshepp/clinical-decision-support-agent},
  version = {8f07b6b59eaf2444b9b5cb89432c26aa8a58246d},
  note    = {Accessed 2026-08-18}
}
```

## 來源

- [README](https://github.com/bshepp/clinical-decision-support-agent/blob/8f07b6b59eaf2444b9b5cb89432c26aa8a58246d/README.md)
- [Architecture](https://github.com/bshepp/clinical-decision-support-agent/blob/8f07b6b59eaf2444b9b5cb89432c26aa8a58246d/docs/architecture.md)
- [Clinical reasoning tool](https://github.com/bshepp/clinical-decision-support-agent/blob/8f07b6b59eaf2444b9b5cb89432c26aa8a58246d/src/backend/app/tools/clinical_reasoning.py)
- [Test results, including 50-case run](https://github.com/bshepp/clinical-decision-support-agent/blob/8f07b6b59eaf2444b9b5cb89432c26aa8a58246d/docs/test_results.md)
- [Validation package](https://github.com/bshepp/clinical-decision-support-agent/tree/8f07b6b59eaf2444b9b5cb89432c26aa8a58246d/src/backend/validation)

## 查核限制

本次是 source audit only。tree 中六個 test/validation scripts 並非全是 unit tests；未重跑模型 endpoint、RAG corpus、FHIR/CDS Hooks integration 或任何 accuracy 結果。
