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
- 實作 ReasoningStep Entity (Chain of Thought)
- 建立 docs/research/existing_solutions.md 研究文件
- 建立 server_v2.py (SDK 2.0 callback API)
- Merge feat/sdk-2-contract-level-dd → master
- 實作 ClinicalReasoningOrchestrator (Agent-friendly API)
- 新增 10 個 MCP Tools (Evidence/DD/Reasoning/CONTRACT)
- 修復 SDK 2.0 inputSchema → input_schema 參數名

## Doing

- 實作 CONTRACT Report Generator
- 更新 README.zh-TW.md（對齊英文版）
- 修復測試（test_mcp_tools.py 遷移到 server_v2）

## Next

- 實作 ContractReport value object
- 整合 FHIR resources (選配)
- 建立完整的 end-to-end 測試
- 發布 v2.0.0-alpha release
