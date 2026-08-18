# `The-Swarm-Corporation/Open-MAI-Dx-Orchestrator` 學習報告

> 本檔只記錄 upstream 文件與原始碼稽核，不代表臨床、安全或生產驗證。

## 查核資料

| 欄位 | 內容 |
|---|---|
| Upstream | [The-Swarm-Corporation/Open-MAI-Dx-Orchestrator](https://github.com/The-Swarm-Corporation/Open-MAI-Dx-Orchestrator) |
| 查核日期 | `2026-08-18` |
| 查核版本 | 預設分支 `main`；commit `2914af1a5196007450424c55b79635c747257fb6`（該分支最新 commit 日期為 2025-07-03） |
| 專案角色 | 相鄰方案／多 Agent 序列診斷 orchestrator |
| 授權 | `MIT`；已直接讀取 LICENSE，copyright 為 `2023 Eternal Reclaimer` |
| 本次驗證 | README、完整 tree、`main.py` 內 Pydantic action/hypothesis schemas、`pyproject.toml`、CI workflow 名稱；未安裝、未呼叫模型、未實跑 |

## 一句話結論

不能取代 RootCause MCP；八角色 panel 與成本約束可作 agent workflow 靈感，但目前是小型 LLM orchestrator，缺乏來源 lineage、RCA、deterministic final conformance 與臨床 reviewer gate。

## 它解決什麼問題

Upstream 實作 Microsoft Research「Sequential Diagnosis with Language Models」方法，讓虛擬醫師 panel 反覆提問、選檢查或做出診斷。
角色包括 Hypothesis、Test-Chooser、Challenger、Stewardship、Checklist、Consensus、Gatekeeper 與 Judge；支援 instant、question-only、budgeted、no-budget、ensemble 模式及檢查成本追蹤。
`CaseState` 保存 evidence 字串、DDx probability、已做檢查與累積成本；Pydantic 僅約束 panel action 與 hypothesis function-call arguments。

## 核心流程與資料邊界

呼叫端同時傳 `initial_case_info`、`full_case_details` 與 `ground_truth_diagnosis`；Gatekeeper 從完整病例揭露資訊，Judge 用 gold 評分最終答案。
因此此 API 適合模擬／評估，不應原樣作 production inference boundary；gold diagnosis 必須留在隔離 grader，不能進 agent context。
主要狀態在單一 Python process，模型由 Swarms framework 呼叫；輸出 dataclass 含 final diagnosis、ground truth、accuracy、cost、iterations 與 conversation history。
完整 tree 未見 `tests/`、報告 JSON Schema、MCP server、持久證據 ledger、RCA 或 immutable final snapshot；多個 workflow 檔名本身不能證明測試存在或通過。

## 最值得學習的設計

- 將 DDx 維護、選檢查、反方挑戰、成本 stewardship 與 quality checklist 分成角色，適合作為 cross-agent eval 的可觀察分工。
- `ask／test／diagnose` 三種 structured action 與 loop-stagnation detection，可借鑑到 harness 的 workflow telemetry。
- 預算與檢查價格可形成「資訊增益／資源消耗」測試，但不能取代 must-not-miss 安全優先序。
- 需重新實作 evidence IDs、source lineage、certainty、typed final artifact 與 reviewer authorization，不能只擴充 prompt。

## 與 RootCause MCP 的關係

| 面向 | Upstream | RootCause MCP 的處理 |
|---|---|---|
| Evidence lineage | turn-level自由文字 evidence log | atomic exact snippet、location、hash 與 source manifest |
| DDx／推理 | probability dict 與多角色 deliberation | ≥3 active DDx、evidence/test disposition、leading 與 must-not-miss gate |
| RCA／causation | 無 Fishbone／Why／HFACS | RCA ledger 與保守、可稽核 causation status |
| Final conformance | `DiagnosisResult` dataclass；無 nested report schema | machine-readable checks、hash、reviewer、時間與 immutable snapshot |
| Human review | Judge 是 LLM agent | named qualified-human reviewer，agent 不得代替 |

## 採用建議

**決策：概念借鑑。** 不加入 runtime dependency；僅把角色分工、stagnation 與成本 telemetry 翻成 RootCause 自有 schema／eval cases。
整合邊界是離線、去識別、答案隔離的 eval runner；若試作 adapter，production call surface 不得接受 `ground_truth_diagnosis`。
gold 泄漏、只產一個診斷、must-not-miss 無支持／反證／planned test、無來源 evidence ID 或 LLM Judge 自行核准時必須 fail-closed。
最小 contract tests：schema rejection、gold canary、三 DDx、每項 disposition、成本計算、stagnation、模型錯誤、trace 保存及 reviewer gate。
MIT 授權寬鬆，但 LICENSE copyright 與 repository organization／package author metadata不同，納入產品前仍應法務確認 attribution；依賴使用未 pin 的 `swarms="*"`、`pydantic="*"`，供應鏈與重現風險高。

### 概念引用方式

在 ADR／eval design 引用 pinned commit 與原始論文；不要複製 prompt 或把 `mai-dx` 加入 production lockfile。若另建 prototype，應 pin package 與 transitive dependencies，隔離 API keys，並將軟體與論文分別記入 NOTICE／研究引用。

## 不應直接照搬的部分

- 不讓 production agent 收到 ground truth，也不把 Judge 的 LLM score 當臨床 reviewer 裁決。
- 不用自由文字 conversation history 取代 evidence ledger 或 source hashes。
- 不把 panel consensus、confidence probability 或 paper reproduction 自述升格為臨床驗證。

## 建議引用

### 軟體引用

```text
The-Swarm-Corporation. (2025). Open-MAI-Dx-Orchestrator (commit 2914af1a5196007450424c55b79635c747257fb6) [Computer software]. GitHub. https://github.com/The-Swarm-Corporation/Open-MAI-Dx-Orchestrator
```

### BibTeX fallback

```bibtex
@software{swarm2025maidxo, author={{The-Swarm-Corporation}}, title={Open-MAI-Dx-Orchestrator}, year={2025}, url={https://github.com/The-Swarm-Corporation/Open-MAI-Dx-Orchestrator}, version={2914af1a5196007450424c55b79635c747257fb6}, note={Accessed 2026-08-18}}
```

### 論文引用（與軟體分開）

Nori, H. et al. (2025). *Sequential Diagnosis with Language Models*. arXiv:2506.22405. [原始論文](https://arxiv.org/abs/2506.22405)。

## 來源

- [README（pinned）](https://github.com/The-Swarm-Corporation/Open-MAI-Dx-Orchestrator/blob/2914af1a5196007450424c55b79635c747257fb6/README.md)；[LICENSE](https://github.com/The-Swarm-Corporation/Open-MAI-Dx-Orchestrator/blob/2914af1a5196007450424c55b79635c747257fb6/LICENSE)
- [`mai_dx/main.py`](https://github.com/The-Swarm-Corporation/Open-MAI-Dx-Orchestrator/blob/2914af1a5196007450424c55b79635c747257fb6/mai_dx/main.py)；[`pyproject.toml`](https://github.com/The-Swarm-Corporation/Open-MAI-Dx-Orchestrator/blob/2914af1a5196007450424c55b79635c747257fb6/pyproject.toml)
- [完整 repository tree](https://github.com/The-Swarm-Corporation/Open-MAI-Dx-Orchestrator/tree/2914af1a5196007450424c55b79635c747257fb6)；[GitHub Actions workflows](https://github.com/The-Swarm-Corporation/Open-MAI-Dx-Orchestrator/tree/2914af1a5196007450424c55b79635c747257fb6/.github/workflows)

## 查核限制

本次只做公開 GitHub 文件與原始碼稽核；沒有安裝 `mai-dx`、設定模型 API、跑病例或驗證論文結果。公開搜尋亦無法涵蓋私人版本或未索引專案。
