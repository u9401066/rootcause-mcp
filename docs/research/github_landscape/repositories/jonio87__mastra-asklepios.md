# `jonio87/mastra-asklepios` 學習報告

> 本報告只做 upstream 文件與原始碼稽核，不代表該專案已通過臨床、安全或生產驗證。

## 查核資料

| 欄位 | 內容 |
|---|---|
| Upstream | [jonio87/mastra-asklepios](https://github.com/jonio87/mastra-asklepios) |
| 查核日期 | `2026-08-18` |
| 查核版本 | `main` / `a4ed241e02af46b3879336bb0073ecd1cdd7fd65` |
| 專案角色 | 直接競品；罕見疾病研究與 clinical-document reasoning 平台 |
| 授權 | 有 MIT 文本，但 copyright 仍是 `{{YEAR}} {{AUTHOR}}` 模板 placeholder；採用前待法務確認 |
| 本次驗證 | 無 README；查了 system specs、tree、Zod schemas、MCP、workflows、processors 與 tests；未安裝、未連資料庫、未實跑模型或 MCP |

## 一句話結論

這是九案中架構最接近 RootCause MCP 的 upstream，W3C PROV、分層資料、變更傳播與 report version 很值得學，但它不能取代醫療 RCA、direct-LR ledger 或 fail-closed finalization。

## 它解決什麼問題

Asklepios 把罕見疾病的長期 diagnostic odyssey 拆成 document ingestion、phenotype mapping、biomedical research、hypothesis、interview、synthesis 與三種受眾報告。九個 Agent 共用病人 working memory，MCP 暴露 agent、workflow、state、validation 與 data-layer 工具。

其資料層採 Layer 0–5：原始文件、結構化 clinical data、research findings、hypotheses/evidence links、reports。原始文件 schema 保存 SHA-256、抽取工具、方法與信心；W3C PROV-aligned entity/activity/agent/relation 及 change signal 支援 stale-report/regeneration 判斷。

## 核心流程與資料邊界

- 輸入是外部先抽取的 clinical documents、patient data 與研究查詢；專案本身仍含 importer/parser，但本次未驗證 binary/OCR fidelity。
- 主要流程為 intake → phenotype HITL → research → hypothesis/evidence link → interview → synthesis HITL → report。
- Zod 與 storage code 約束結構；hypothesis ranking、synthesis、報告與部分 validation 仍由 LLM prompt 執行。
- report schema 記錄 `contentHash`、版本與 data integration 狀態；沒有 reviewer 身分、finalized timestamp 或不可變封存狀態。
- 系統文件要求 qualified professional review，但該要求不是 RootCause 式 server-side final gate。

## 最值得學習的設計

- [W3C PROV schema](https://github.com/jonio87/mastra-asklepios/blob/a4ed241e02af46b3879336bb0073ecd1cdd7fd65/src/schemas/provenance.ts) 將 entity、activity、agent、relation 與 change signal 分離，可轉成 RootCause 的 export adapter。
- [source-document schema](https://github.com/jonio87/mastra-asklepios/blob/a4ed241e02af46b3879336bb0073ecd1cdd7fd65/src/schemas/source-document.ts) 明列 whole-file hash、抽取方法、工具、confidence 與 FHIR/LOINC metadata。
- [report version schema](https://github.com/jonio87/mastra-asklepios/blob/a4ed241e02af46b3879336bb0073ecd1cdd7fd65/src/schemas/report-version.ts) 把新資料是否已整合進特定 report version 做成一級資料。
- cascade/change-signal 的思路可讓 source 更動使 downstream DDx/RCA/report 自動變 stale，而不是靜默沿用。
- 這些概念應依 RootCause contract 重做或透過 adapter 映射，不應假設兩邊的 evidence tier、ID 或 lifecycle 相同。

## 與 RootCause MCP 的關係

| 面向 | Upstream | RootCause MCP 的處理 |
|---|---|---|
| Evidence lineage | W3C PROV graph、source SHA、分層 entity 與 change propagation | atomic exact snippet/location/span hash，加 case manifest 與跨物件 lineage invariant |
| DDx／推理 | tier-weighted hypotheses、support/contradict links、HITL | 至少三個 active DDx、must-not-miss、direct applied LR 與 test disposition |
| RCA／causation | 未找到 Fishbone、5-Why、HFACS 或 causation audit | Fishbone／Why／HFACS，加保守 proof-obligation causation validator |
| Final conformance | Zod schemas、report content hash、regeneration status | typed nested report、machine `conformance_checks[]`、fail-closed recomputation |
| Human review | workflow suspend/resume 與文件性 professional-review 要求 | authorized reviewer、review time、可重算 hash、deep-immutable final snapshot |

## 採用建議

決策：**概念借鑑**，短期不把它加入 runtime dependency。

1. 整合邊界：新增單向 W3C PROV export 與 source-change invalidation 設計，不共用 upstream patient storage。
2. Fail-closed：無 exact source location/hash、PROV edge 找不到 RootCause ID、或變更後仍引用舊 snapshot 時拒絕 finalization。
3. Contract tests：entity/edge round-trip、cascade stale propagation、hash mismatch、循環/孤兒 edge、report regeneration lineage。
4. 授權風險：LICENSE 是標準 MIT 條文但授權人與年份 placeholder 未填；法務確認前不 vendoring 原始碼。

### 概念引用方式

- 在 architecture decision record 說明 W3C PROV/change-cascade 受 Asklepios 啟發，附固定 commit URL。
- 若日後獲授權並複製 schema 片段，保留完整 MIT 條文與 copyright notice，並在 `NOTICE`/SBOM 記錄 commit。
- 不把 upstream 的 clinical prompt、evidence tier 或 cross-patient memory 當成已驗證醫療規則。

## 不應直接照搬的部分

- MIT placeholder 未完成，不能把 GitHub 的 SPDX 偵測當成授權鏈已完備。
- cross-patient observational memory 可能混入 PHI、錯誤模式或跨個案 contamination，不適合直接接 RootCause case store。
- report hash 是版本追蹤欄位，不等於具 reviewer binding 的 immutable final snapshot。
- tier-weighted confidence 是 upstream 方法，並非 case-specific direct likelihood ratio。

## 建議引用

### 軟體引用

```text
jonio87. (2026). mastra-asklepios (commit a4ed241e02af46b3879336bb0073ecd1cdd7fd65) [Computer software]. GitHub. https://github.com/jonio87/mastra-asklepios
```

### BibTeX fallback

```bibtex
@software{jonio87_mastra_asklepios_2026,
  author  = {jonio87},
  title   = {mastra-asklepios},
  year    = {2026},
  url     = {https://github.com/jonio87/mastra-asklepios},
  version = {a4ed241e02af46b3879336bb0073ecd1cdd7fd65},
  note    = {Accessed 2026-08-18; LICENSE placeholders unresolved}
}
```

## 來源

- [System specifications](https://github.com/jonio87/mastra-asklepios/blob/a4ed241e02af46b3879336bb0073ecd1cdd7fd65/docs/system-specs.md)
- [Provenance schema and tests](https://github.com/jonio87/mastra-asklepios/tree/a4ed241e02af46b3879336bb0073ecd1cdd7fd65/src/schemas)
- [Diagnostic workflow](https://github.com/jonio87/mastra-asklepios/blob/a4ed241e02af46b3879336bb0073ecd1cdd7fd65/src/workflows/diagnostic-research.ts)
- [MCP implementation](https://github.com/jonio87/mastra-asklepios/tree/a4ed241e02af46b3879336bb0073ecd1cdd7fd65/src/mcp)
- [LICENSE with unresolved placeholders](https://github.com/jonio87/mastra-asklepios/blob/a4ed241e02af46b3879336bb0073ecd1cdd7fd65/LICENSE)

## 查核限制

本次是固定 commit 的 source audit only。未安裝依賴、未建立資料庫、未連外部 biomedical services，也未重跑其 77 個 test files；公開原始碼與 specs 的存在不證明臨床正確性、PHI 合規或 production readiness。
