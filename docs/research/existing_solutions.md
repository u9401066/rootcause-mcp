# 現有方案研究：醫學推理、臨床 RCA 與 Agent 基礎設施

> **查核日期**：2026-08-18
> **方法**：公開 GitHub repository／topic／code 搜尋，再核對高相關專案的 README、tree、schema、tests、LICENSE 與 citation metadata。
> **完整資料**：[26 份逐 repo 學習與引用報告](github_landscape/README.md)

## Executive summary

RootCause MCP 確實與既有專案重疊，但重疊主要發生在可重用的基礎能力：DDx workflow、FHIR/EHR access、raw document extraction、Fishbone／5-Why templates、Agent runtime、trace、benchmark 與統計因果推論。

本次沒有找到單一公開 repo 同時具備下列完整組合：

1. 多來源 exact snippet、source location、whole-file/span hash lineage。
2. DDx、must-not-miss、direct applied LR 與 planned-test disposition。
3. Fishbone、Why、HFACS 與 root/audit/evidence exact lineage。
4. 明示不等於臨床因果證明的 conservative causation audit。
5. Server-side recomputed typed conformance checks。
6. Named qualified reviewer、final timestamp、recomputable hash 與 deep immutable snapshot。

這個搜尋結果不能證明絕對唯一，也不構成專利新穎性或臨床效度證明。私人、未索引或未公開專案不在搜尋範圍內。

## 產品定位

> RootCause MCP 不是另一個自行診斷的 medical Agent，也不是 EHR、FHIR gateway 或 raw-record parser；它是位於 extractor／EHR tools 與 reasoning Agent 之後的 evidence-grounded clinical reasoning + medical RCA assurance layer。

應保留的核心是病例層 ledger、跨 DDx/RCA 的 exact lineage、保守因果語意、不可偽造的 final conformance 與 qualified-human handoff。

不應繼續自行擴張的部分包括：

- PDF/image/OCR extraction；
- FHIR transport、SMART auth 與通用 CRUD；
- 通用 Agent container／parallel runner；
- 通用 trace interchange 與 trajectory viewer；
- population-level causal inference 演算法；
- 已有正式資料治理的外部 clinical benchmark。

## 最接近的方案

| 類別 | 代表方案 | 判定 |
|---|---|---|
| 多來源臨床推理 | [`jonio87/mastra-asklepios`](github_landscape/repositories/jonio87__mastra-asklepios.md) | 最接近整體架構；已有 MCP、W3C PROV、DDx、HITL 與 report hash，但缺 direct LR、clinical RCA、保守因果與 hard final conformance |
| 臨床安全 Agent | [`Francis1998/medagent-core`](github_landscape/repositories/francis1998__medagent-core.md) | 有 FHIR intake、FOR/AGAINST evidence、audit/hash、安全 gate；不是 MCP，且沒有 RCA/root lineage |
| 可稽核 DDx Skill | [`makidav/clinical-assistant`](github_landscape/repositories/makidav__clinical-assistant.md) | 可借鑑 anti-anchoring、evidence appraisal 與 planned tests；不是 deterministic runtime ledger |
| 直接 MCP DDx | [`bshepp/clinical-decision-support-agent`](github_landscape/repositories/bshepp__clinical-decision-support-agent.md) | 能跑完整 DDx/RAG pipeline，但沒有 source manifest、持久 lineage 與 final gate |
| Healthcare RCA | [`RCA-Assistant-for-Healthcare-Events`](github_landscape/repositories/akhilapugazhendhi98__rca-assistant-for-healthcare-events.md) | 可學 5-Why facilitation 與 actionability rubric；沒有 DDx/provenance/MCP assurance |
| Generic RCA MCP | [`SahajSethi7/agentic-rca-mcp`](github_landscape/repositories/sahajsethi7__agentic-rca-mcp.md) | 可學 bounded workflow、deterministic critique 與 artifact export；缺 clinical ledger，且授權需先確認 |
| Iterative DDx research | [`nec-research/meddxagent`](github_landscape/repositories/nec-research__meddxagent.md) | 可學 modular iterative DDx 與 benchmark；非商業研究授權，不可視為 Apache 元件 |

## 優先整合而非重寫

| 能力 | 建議 upstream | RootCause 邊界 |
|---|---|---|
| Raw document extraction | [`DIGIT-X-Lab/MOSAICX`](github_landscape/repositories/digit-x-lab__mosaicx.md) | Sidecar/adapter；只有 exact physical match 可升格 verified，fuzzy match 保持 unverified |
| Typed FHIR | [`healthchainai/HealthChain`](github_landscape/repositories/healthchainai__healthchain.md) | Optional adapter；不把 FHIR transport 與病例推理混成同一 aggregate |
| FHIR MCP upstream | [`langcare/langcare-mcp-fhir`](github_landscape/repositories/langcare__langcare-mcp-fhir.md)、[`wso2/fhir-mcp-server`](github_landscape/repositories/wso2__fhir-mcp-server.md) | 臨床分析預設 read-only scope；EHR write 不屬於 RCA workflow |
| Formal Agent eval | [`harbor-framework/harbor`](github_landscape/repositories/harbor-framework__harbor.md) | 讓 Harbor 負責 runtime/container/parallel lifecycle，RootCause 保留 clinical scorer、private gold、artifact hash 與 reviewer adjudication |
| OTel trace evaluation | [`agentevals-dev/agentevals`](github_landscape/repositories/agentevals-dev__agentevals.md) | 獨立 optional pilot；不得把 Agent 自報 trace 當 trusted server trace |
| Statistical causality | [`py-why/dowhy`](github_landscape/repositories/py-why__dowhy.md)、[`StatsPAI`](github_landscape/repositories/brycewang-stanford__statspai.md) | 只附加具研究設計與假設限制的 population-level analysis；不取代單病例 conservative audit |
| Verification envelope | [`QWED-AI/qwed-verification`](github_landscape/repositories/qwed-ai__qwed-verification.md) | 可借 proof/evidence/admission 分層；RootCause cross-object clinical invariants 仍由 domain evaluator 重算 |

## 外部效度與 Agent evaluation

現有六案例與 scripted smoke 只能建立 engineering regression，不足以建立跨 Agent 臨床效度。可用的外部參考包括：

- [`microsoft/HealthAgentBench`](github_landscape/repositories/microsoft__healthagentbench.md)：多 runtime、task-specific verifier 與 Harbor lifecycle。
- [`stanfordmlgroup/MedAgentBench`](github_landscape/repositories/stanfordmlgroup__medagentbench.md)：FHIR EHR retrieval/action tasks。
- [`HealthRex/PhysicianBench`](github_landscape/repositories/healthrex__physicianbench.md)：long-horizon、fresh-container physician tasks。
- [`IVUL-KAUST/MedCTA`](github_landscape/repositories/ivul-kaust__medcta.md)：tool choice、argument validity、evidence faithfulness。
- [`som-shahlab/medalign`](github_landscape/repositories/som-shahlab__medalign.md)：longitudinal multi-document synthesis；受 DUA 與資料外送規則限制。
- [`MAGIC-AI4Med/MedSP1000`](github_landscape/repositories/magic-ai4med__medsp1000.md)：frozen rubric、interactive trajectory 與 clinician scoring。

這些 benchmark 不會替 RootCause 驗證 Fishbone/Why/HFACS/root lineage；需經 adapter 加入 RootCause 自己的 gold DDx、must-not-miss、critical evidence、allowed RCA、forbidden claims 與 blinded reviewer adjudication。

## 授權與引用更正

舊版研究文件把 `nec-research/meddxagent` 誤寫為 Apache-2.0。其上游 LICENSE 是 academic/non-profit noncommercial research-only；應只依授權作研究評估，不直接併入可商業散布的 Apache-2.0 程式碼。

本研究庫採以下規則：

1. GitHub 公開可讀不等於可複製；無 LICENSE 時只學概念，不搬 code/content。
2. 軟體、論文、資料集、模型／權重分開引用。
3. 基礎套件優先以 optional dependency、protocol adapter 或 sidecar 使用。
4. Release/tag、commit、artifact digest 與 lockfile用於重現；NOTICE/SBOM 記錄名稱、版本、URL 與 license。
5. 個別專案的依賴與 citation 範例，以[逐 repo 報告索引](github_landscape/README.md)為準。

## 維護

這是一份有日期的 landscape snapshot。重新查核時應更新個別報告的 commit 與 upstream 條款，而不是保留「唯一」、「production-ready」或「已驗證」等無法由目前證據支持的絕對宣稱。
