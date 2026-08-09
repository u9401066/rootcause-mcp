# Progress (Updated: 2026-08-09)

## Done

- 完成開源專案調查（MEDDxAgent, ClinClaw, fastmcp, fhir.resources）
- 確認核心定位：醫學推理 + 鑑別診斷專用 MCP Harness
- 建立 feat/sdk-2-contract-level-dd 分支
- 升級 MCP SDK 1.27.0 → 2.0.0
- 實作 EvidenceQuality VO (Oxford CEBM 啟發)
- 實作 ClinicalConcept VO (SNOMED/ICD-10/RxNorm/LOINC)
- 實作 Evidence Entity (first-class, 含 provenance tracking)
- 實作 Hypothesis Entity (Bayesian DDx, LR updating)
- 新增 EvidenceId, HypothesisId, ReasoningStepId 強型別 ID

## Doing

- 重新定位：從通用 RCA 工具 → 醫學推理專用 Harness
- 設計 Agent-friendly API（簡化複雜度，隱藏醫學專業細節）
- 準備更新 README 加入 Mermaid/SVG 架構圖

## Next

- 實作 ReasoningStep entity (Chain of Thought)
- 遷移現有 19 個 MCP tools 到 SDK 2.0
- 設計新的 8 個 Evidence/DD/Reasoning tools
- 建立 Application Layer Orchestrator (Agent-friendly)
- 實作 CONTRACT-level report generator
- 整合 FHIR resources (選配)
