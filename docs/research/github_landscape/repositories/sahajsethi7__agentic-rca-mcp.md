# `SahajSethi7/agentic-rca-mcp` 學習報告

> 本報告只做 upstream 文件與原始碼稽核，不代表該專案已通過臨床、安全或生產驗證。

## 查核資料

| 欄位 | 內容 |
|---|---|
| Upstream | [SahajSethi7/agentic-rca-mcp](https://github.com/SahajSethi7/agentic-rca-mcp) |
| 查核日期 | `2026-08-18` |
| 查核版本 | `main` / `e3a5c6a39cfccf920c68457a15b881f564c970be` |
| 專案角色 | 直接競品（通用 RCA MCP），不是 clinical reasoning system |
| 授權 | repository 未提供 LICENSE/COPYING；**無可推定的重用授權，待法務確認** |
| 本次驗證 | README、architecture/decisions/benchmark、Pydantic schemas、methods、orchestrator、validation、MCP/API、eval 與 tests；未安裝或實跑 |

## 一句話結論

它是最成熟的通用 RCA MCP 對照組，typed Fishbone/5-Why/Fault Tree、deterministic critique、sanitizer 與多入口共用 orchestrator 值得學；但無授權且 validator fail-soft，不能成為 clinical final assurance dependency。

## 它解決什麼問題

專案把 operational incident 送入 local/hosted LLM，產出 `RCAReport`、PDF、JSON、HTML，並透過 MCP、CLI、FastAPI、React UI 共用一條 pipeline。方法支援 3–7 步 Why、五類 Fishbone 與 bounded simplified Fault Tree。

它還包含 deterministic anti-blame/root-specificity/method-consistency critique、bounded revise loop、secret redaction、prompt-injection fencing、structured errors、read-only past-RCA memory、audit JSONL 與 golden-set eval。

## 核心流程與資料邊界

- 輸入是 problem statement、單一 context 字串、severity、system area 與 method；不是 source manifest/evidence ledger。
- Pydantic 嚴格驗證 final `RCAReport`，generation schema 暫時允許 extra fields 後再 promote/revalidate。
- deterministic critique 可觸發最多兩次 revise；最後再由 reviewer model回傳 confidence/notes。
- reviewer model failure 明確 **fail-soft**，保留 generator confidence/report；anti-blame 殘留只把 confidence cap 為 low。
- MCP pipeline 寫固定名稱 artifacts，audit 只存 problem SHA-256 的 16-hex prefix，不是 final artifact attestation。

## 最值得學習的設計

- [method-specific typed schemas](https://github.com/SahajSethi7/agentic-rca-mcp/blob/e3a5c6a39cfccf920c68457a15b881f564c970be/schemas.py) 驗 Fishbone selection/category membership 與 bounded Fault Tree shape。
- 所有 MCP/CLI/API 入口走共同 orchestrator/sanitizer chokepoint，降低旁路不一致。
- deterministic critique → bounded revise → visible validation notes 的成本與可觀測性取捨清楚。
- structured error envelope、output path restriction、secret-not-reaching-model/audit tests 值得移植安全模式。
- 過去 RCA match 明確標示 supporting evidence、非 ground truth；這個語意適合 RootCause retrieval adapter。

## 與 RootCause MCP 的關係

| 面向 | Upstream | RootCause MCP 的處理 |
|---|---|---|
| Evidence lineage | unstructured context、past RCA match與 evidence-needed；無 atomic source | exact clinical source observations、location/hash、manifest與 ledger IDs |
| DDx／推理 | 無 clinical DDx/must-not-miss/LR | evidence-linked DDx、tests、certainty 與 cognitive audit |
| RCA／causation | typed Why/Fishbone/Fault Tree、通用 root critique | Why/Fishbone/HFACS、root/evidence exact lineage、保守 causation status |
| Final conformance | Pydantic report；validator failure fail-soft且仍產 artifacts | every hard mutation fail-closed，unsafe finalization 100% blocked |
| Human review | second model稱 reviewer，沒有 qualified-human review state | named allowlisted qualified reviewer/time/hash/frozen snapshot |

## 採用建議

決策：**概念借鑑**；無 LICENSE 前不複製或加入 dependency。

1. 整合邊界：移植 deterministic method-consistency test ideas 與 error/sanitizer patterns；不讓 upstream 生成 clinical root cause。
2. Fail-closed：validator unavailable、root selection 不在 ledger、evidence source 缺失、human review 缺失時不得寫 finalized artifacts。
3. Contract tests：Fishbone selected cause membership、Why index/lineage、blame/vague root、secret/injection、provider failure、artifact collision/hash。
4. 授權風險：repo 無 license；past-RCA workbook/training-data provenance 也自述未驗證，不能複製資料或 code。

### 概念引用方式

- 在 ADR 引用固定 commit，描述 deterministic critique、多入口 chokepoint 與 typed alternate-method payload。
- 不複製 schema、prompts、fixtures、eval data 或 frontend；自行依 RootCause clinical contracts 重做。
- 若未來補 LICENSE，仍需分開審 dataset/workbook 與 model provider terms，並 pin release/commit/digest。

## 不應直接照搬的部分

- final validator fail-soft 與 RootCause 100% block unsafe finalization 的目標相反。
- generic Fishbone 五類不是 HFACS-MES，也不處理 clinical causal proof obligation。
- LLM reviewer 不是 qualified human；validation note 也不是 reviewer signature。
- 16-hex problem hash、固定 artifact filenames、untrusted memory match 都不能當 immutable case snapshot。

## 建議引用

### 軟體引用

```text
SahajSethi7. (2026). agentic-rca-mcp (commit e3a5c6a39cfccf920c68457a15b881f564c970be) [Computer software]. GitHub. https://github.com/SahajSethi7/agentic-rca-mcp
```

### BibTeX fallback

```bibtex
@software{sethi_agentic_rca_mcp_2026,
  author  = {SahajSethi7},
  title   = {agentic-rca-mcp},
  year    = {2026},
  url     = {https://github.com/SahajSethi7/agentic-rca-mcp},
  version = {e3a5c6a39cfccf920c68457a15b881f564c970be},
  note    = {Accessed 2026-08-18; no repository license found}
}
```

## 來源

- [README](https://github.com/SahajSethi7/agentic-rca-mcp/blob/e3a5c6a39cfccf920c68457a15b881f564c970be/README.md)
- [Architecture decisions](https://github.com/SahajSethi7/agentic-rca-mcp/blob/e3a5c6a39cfccf920c68457a15b881f564c970be/DECISIONS.md)
- [Final validation implementation](https://github.com/SahajSethi7/agentic-rca-mcp/blob/e3a5c6a39cfccf920c68457a15b881f564c970be/validation.py)
- [MCP shared pipeline](https://github.com/SahajSethi7/agentic-rca-mcp/blob/e3a5c6a39cfccf920c68457a15b881f564c970be/server.py)
- [Tests](https://github.com/SahajSethi7/agentic-rca-mcp/tree/e3a5c6a39cfccf920c68457a15b881f564c970be/tests)
- [Repository tree showing no LICENSE](https://github.com/SahajSethi7/agentic-rca-mcp/tree/e3a5c6a39cfccf920c68457a15b881f564c970be)

## 查核限制

本次為 source audit only。tree 中有 14 個 test files、約 124 個 test functions，但未重跑，也未啟動 Ollama/hosted provider、MCP、API、UI、memory、PDF 或 benchmark。
