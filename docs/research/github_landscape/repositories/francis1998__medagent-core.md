# `Francis1998/medagent-core` 學習報告

> 本報告只做 upstream 文件與原始碼稽核，不代表該專案已通過臨床、安全或生產驗證。

## 查核資料

| 欄位 | 內容 |
|---|---|
| Upstream | [Francis1998/medagent-core](https://github.com/Francis1998/medagent-core) |
| 查核日期 | `2026-08-18` |
| 查核版本 | `main` / `63e01c69ef3a9148f5c3ad03f103aa6c869afa64` |
| 專案角色 | 相鄰方案；FHIR clinical reasoning 與 deterministic medication-safety prototype |
| 授權 | [Apache License 2.0](https://github.com/Francis1998/medagent-core/blob/63e01c69ef3a9148f5c3ad03f103aa6c869afa64/LICENSE)；GitHub API 顯示 `NOASSERTION`，但 LICENSE 本文是 Apache-2.0 |
| 本次驗證 | README、ARCHITECTURE、SAFETY、Pydantic models、state machine、audit、Bayesian scorer、API 與 tests；未安裝或實跑 |

## 一句話結論

它不能取代 RootCause MCP，但 immutable typed models、明確 state machine、deterministic safety checks 與 confidence escalation 很適合當安全設計參考。

## 它解決什麼問題

medagent-core 將 FHIR patient context 轉成 entities 與 retrieved evidence，再產生 ranked hypotheses、藥物/過敏/器官功能等安全警示，最後依 confidence 與 contradiction 決定 `OUTPUT` 或 `ESCALATE`。

專案把許多 medication hazards 做成 deterministic checkers，並將一次 agent run 的 hypothesis、confidence、model 與 timing 寫入 SQL audit table。文件明確定位為 research prototype，不是診斷或處方系統。

## 核心流程與資料邊界

- 輸入為 FHIR-compatible patient context 加 free-text query；parser 在 LLM boundary 前 hash/redact 部分識別資訊。
- 狀態為 `INTAKE → ENTITY_EXTRACTION → KNOWLEDGE_RETRIEVAL → REASONING → SAFETY_CHECK → OUTPUT/ESCALATE`。
- LLM 產生 hypothesis 與 FOR/AGAINST evidence；Pydantic 驗證 shape，deterministic code 重排與做 safety checks。
- 所謂 Bayesian score 把 `strength` 轉為 odds 更新；它不是來源支援的 direct LR，也未記錄 LR citation。
- API 非同步寫 audit；human review 是 escalation instruction，沒有 reviewer identity 或完成 review 的 lifecycle。

## 最值得學習的設計

- [frozen Pydantic models](https://github.com/Francis1998/medagent-core/blob/63e01c69ef3a9148f5c3ad03f103aa6c869afa64/src/medagent/models.py) 降低 clinical object 被原地改寫的風險。
- [explicit state machine](https://github.com/Francis1998/medagent-core/blob/63e01c69ef3a9148f5c3ad03f103aa6c869afa64/src/medagent/agent/state_machine.py) 限定 transition，讓 low confidence/no hypothesis/contradiction 可進 `ESCALATE`。
- deterministic medication safety checker 與「advisory、不可自動改藥」邊界，適合做 optional pre-final safety sidecar。
- [audit table](https://github.com/Francis1998/medagent-core/blob/63e01c69ef3a9148f5c3ad03f103aa6c869afa64/src/medagent/agent/audit.py) 把 run metadata 與 structured hypothesis 分欄保存，利於 operation metrics。
- 若移植設計，應保留 RootCause 的 evidence/source ID 與 hash；不要沿用 upstream 的簡化 `inputs_hash`。

## 與 RootCause MCP 的關係

| 面向 | Upstream | RootCause MCP 的處理 |
|---|---|---|
| Evidence lineage | evidence 有 source doc ID/label；`inputs_hash` 只 hash patient-ID hash + query | exact snippet、location、source/span hash 與完整 manifest |
| DDx／推理 | FOR/AGAINST hypotheses、Bayesian-inspired score、confidence gate | direct LR ledger、三個 DDx、must-not-miss 與 planned-test disposition |
| RCA／causation | 無 Fishbone、Why、HFACS 或 causation audit | clinical DDx 後接 patient-safety RCA 與保守 causation review |
| Final conformance | Pydantic shape 與 terminal state，未見 immutable final contract | nested conformance、server recomputation、reviewer/time/hash snapshot |
| Human review | `ESCALATE` 回傳 human-review 指示 | authorized reviewer 必須具名簽核才可 finalized |

## 採用建議

決策：**概念借鑑**；若需要 medication safety，才以獨立 sidecar/adapter pilot。

1. 整合邊界：只送最小必要、去識別的 meds/allergies/labs；回傳 advisory findings，不讓它寫 RootCause case ledger。
2. Fail-closed：來源缺失、checker version 未 pin、critical finding 未 disposition、sidecar failure 時阻擋「已完成 safety review」聲稱。
3. Contract tests：FHIR field mapping、unit/negation preservation、PHI egress、critical interaction、false-positive fixture、timeout/error envelope。
4. 授權風險：Apache-2.0 可整合，但臨床規則內容與外部 knowledge sources 仍需各自更新及驗證。

### 概念引用方式

- 優先透過 versioned HTTP/CLI adapter 或 optional dependency，不複製整包 checker code。
- 若形成依賴，pin release/commit 與 container digest，於 `NOTICE`、SBOM、dependency inventory 記錄 Apache-2.0。
- 若只借 state-machine/frozen-model 概念，在 ADR 引用固定 commit；不要暗示 upstream 驗證 RootCause clinical claims。

## 不應直接照搬的部分

- `inputs_hash` 未涵蓋 clinical notes、medications、labs 與完整 FHIR bundle，不能當 case snapshot integrity hash。
- `strength` 是 model-produced 0–1 分數；把它當 likelihood ratio 會造成錯誤的量化確定性。
- escalation 不是 qualified-human review 的證據，也不等於禁止產出 final artifact。
- SAFETY 文件與 audit source 對 raw FHIR persistence 的描述需進一步對照部署路徑，不應據此宣稱 PHI 合規。

## 建議引用

### 軟體引用

```text
Francis1998. (2026). medagent-core (commit 63e01c69ef3a9148f5c3ad03f103aa6c869afa64) [Computer software]. GitHub. https://github.com/Francis1998/medagent-core
```

### BibTeX fallback

```bibtex
@software{francis1998_medagent_core_2026,
  author  = {Francis1998},
  title   = {medagent-core},
  year    = {2026},
  url     = {https://github.com/Francis1998/medagent-core},
  version = {63e01c69ef3a9148f5c3ad03f103aa6c869afa64},
  note    = {Accessed 2026-08-18}
}
```

## 來源

- [README](https://github.com/Francis1998/medagent-core/blob/63e01c69ef3a9148f5c3ad03f103aa6c869afa64/README.md)
- [Architecture](https://github.com/Francis1998/medagent-core/blob/63e01c69ef3a9148f5c3ad03f103aa6c869afa64/ARCHITECTURE.md)
- [Safety policy](https://github.com/Francis1998/medagent-core/blob/63e01c69ef3a9148f5c3ad03f103aa6c869afa64/SAFETY.md)
- [Bayesian-inspired scorer](https://github.com/Francis1998/medagent-core/blob/63e01c69ef3a9148f5c3ad03f103aa6c869afa64/src/medagent/reasoning/bayesian.py)
- [Unit-test tree](https://github.com/Francis1998/medagent-core/tree/63e01c69ef3a9148f5c3ad03f103aa6c869afa64/tests/unit)

## 查核限制

本次為 source audit only。tree 中有 84 個 `test_*.py`、約 761 個 test functions，但未在本機重跑，也未驗證外部模型、FHIR payload、knowledge base 或 clinical accuracy。
