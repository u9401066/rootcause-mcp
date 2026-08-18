# MVP Conformance and Agent Evaluation

> 規範狀態：engineering alpha。本文是 deterministic final-report conformance
> 與跨-Agent 評估的 canonical 說明；live MCP resources 仍是 payload schema 的
> authoritative source。

## 目前可以宣稱什麼

| 範圍 | 目前狀態 | 可接受的宣稱 |
| --- | --- | --- |
| Typed report 與 finalization gate | 已實作 deterministic conformance | 程式可拒絕不符合結構、血緣、DDx、RCA 與 reviewer gate 的 final snapshot |
| 公開六案例與 runner | Engineering reference/scaffold | 可驗證 corpus、adapter、artifact 與評分管線，不是 blinded clinical eval |
| 3 runtimes × 6 cases × 2 repeats | `AGENT_EVAL_NOT_ESTABLISHED` | 尚無使用 private case bundle 與 private gold 的合格 36-run 結果可宣稱 |
| 兩名臨床 reviewer 盲評與裁決 | `AGENT_EVAL_NOT_ESTABLISHED` | 尚未完成正式臨床表現審查 |
| 臨床有效性或 autonomous diagnosis | 未建立且不在目前產品宣稱內 | 不得宣稱醫療器材、臨床因果證明或自主診療能力 |

因此，目前產品名稱應使用 **engineering alpha**。Smoke、unit、integration、
schema conformance 或 dry-run 都不能單獨升格為「完整 Agent MVP 已驗證」。

## 系統責任邊界

推理來自 Agent 與 qualified human reviewer；MCP 本身沒有臨床思考能力。
RootCause MCP 提供的是 typed schema、持久化 ledger、確定性計算、workflow gate、
報告組裝與可重算的稽核結果。

RootCause MCP 也不是 raw-document ingestion engine。PDF、DOCX、影像、掃描、
試算表或 EHR export 必須先由 host agent 或經核准的 extractor 轉成 citation-ready
span/cell。Host 必須保留原文、位置、whole-file/source-span hash、單位、否定詞、
時間精度、OCR 修正與 extraction method；MCP 只接收逐筆 structured atomic evidence。
無法存取或逐字比對的來源必須維持 `UNVERIFIED`。

## Typed report contract

在開始或 finalization 前，Agent 必須讀取：

- `clinical://contracts/case-input-manifest`
- `clinical://contracts/case-analysis-report`

`case-analysis-report` 不只驗證 top-level envelope。穩定的 nested sections 已有
typed schema，包括 hypotheses、evidence/source lineage、source inventory、timeline、
reasoning/thinking chain、evidence graph、Fishbone、Why Tree、root causes、HFACS、
causation audits、gap/readiness 與 metrics。Top-level 未知欄位會被拒絕；nested
stable fields 會被型別檢查，同時保留可向前相容的 leaf extension 空間。

Preliminary report 可以明確保留缺口；final report 不可以用空值或 Agent 敘事繞過
hard gate。每份 report 都應保留機器可讀的 `conformance_checks[]`；final report 中
每一項 deterministic hard check 必須由 server 重算並通過：

```json
{
  "code": "ROOT_CAUSE_DISPOSITION_SAFE",
  "status": "PASS",
  "severity": "HARD",
  "message": "Rejected claims are absent and insufficient-data roots remain proposed.",
  "refs": ["#/root_causes"],
  "details": {}
}
```

Caller 自行塞入 `PASS` 不會取得 finalization；domain boundary 會重新評估完整 hard
code set，任何 hard `FAIL` 都會阻擋。

## Deterministic final gates

### Workflow、來源與必要章節

- `GUIDANCE_READY`
- `NO_UNRESOLVED_SAFETY_CONFLICTS`
- `MULTI_SOURCE_MANIFEST`
- `MANIFEST_DOCUMENTS_REVIEWED`
- `SOURCE_INDEPENDENCE_LINEAGE`
- `SOURCE_REVIEW_ADJUDICATION_AUTHORIZED`
- `EVIDENCE_SOURCES_DECLARED`
- `EVIDENCE_VERIFICATION_COMPLETE`
- `SOURCE_INVENTORY_COUNTS_RECOMPUTABLE`
- `TIMELINE_EVIDENCE_LINEAGE`
- `CAUSATION_TEMPORAL_LINEAGE`
- `FINAL_REPORT_SECTIONS_INCLUDED`
- `FISHBONE_PRESENT`
- `WHY_ROOT_PRESENT`

Final report 必須有至少兩份經 append-only event 裁決為 reviewed、de-identified 的
獨立 source roots；相同 SHA-256 bytes 或 derived copies 不得被灌水成多來源。每個 source
review event 都要有 allowlisted reviewer、server time 與 reason，所有 evidence 必須指回
manifest 且完成驗證，inventory counts 必須由 ledger 重算。Timeline、reasoning/thinking
chain、evidence graph 與 metrics 不得在 final 輸出中省略。

時間使用 typed `instant | date | range | relative | unknown`。只有 source 自帶 offset、
且與 Evidence ledger 完全一致的 `instant` 可排序或支持 causation temporality；其他合法
時間狀態保留為 unpositioned，不會被迫補成假的 timestamp。

### Root lineage 與 disposition

- `ROOT_EVIDENCE_LINEAGE`
- `ROOT_CAUSATION_AUDIT_LINEAGE`
- `ROOT_CAUSE_DISPOSITION_SAFE`

每個 Why root 的 stable ID、description 與 evidence ID set 必須與 root-cause bucket
及最新 persisted causation audit 一致。Cause/effect evidence 都必須存在於 evidence
ledger；audit 的 `verification_id` 必須非空且唯一。

`rc_verify_causation` 是保守的 proof-obligation audit，不是臨床因果證明工具。
Audit record 必須帶有：

```json
{
  "audit_scope": "CONSERVATIVE_CAUSATION_AUDIT",
  "clinical_causality_established": false
}
```

即使相容性 enum 回傳 `VERIFIED` 或 `VERIFIED_WITH_CAVEATS`，報告只能標示
`AUDIT_OBLIGATIONS_PASSED`，不得改寫為「已證明因果」。`REJECTED` 不得留在
`root_causes` bucket；`INSUFFICIENT_DATA` 若仍作為候選根因揭露，其 disposition
必須是 `PROPOSED`。

### Differential diagnosis safety

- `DIFFERENTIAL_MINIMUM_UNIQUE`
- `DIFFERENTIAL_TYPED_CLASSIFICATION`
- `DIFFERENTIAL_MECHANISM_BREADTH`
- `DIFFERENTIAL_BREADTH_AUDIT_COMPLETE`
- `LIKELIHOOD_RATIO_CALIBRATION_VALID`
- `ACTIVE_DIFFERENTIAL_DISPOSITION`
- `DIAGNOSTIC_CERTAINTY_SUPPORTED`
- `LEADING_DIAGNOSIS_CHALLENGED`
- `MUST_NOT_MISS_CHALLENGED`

Final report 至少包含三個經正規化後不重複的 diagnoses、兩個非 `UNKNOWN` mechanism，
並完成 syndrome-appropriate PRIMARY breadth audit。每個 active diagnosis
必須有真正的 ledger evidence disposition，並有 contradiction 或 typed pending
disconfirm/rule-out test。Leading diagnosis 必須由 persisted selection event 明確指定，
不能由 array order 或 uncalibrated numeric compatibility 決定。Leading 與每個
must-not-miss diagnosis 必須同時
有 genuine supporting evidence，以及 genuine contradiction 或符合下列契約的 planned
test：

```json
{
  "name": "Definitive diagnostic study",
  "purpose": "RULE_OUT",
  "expected_supporting_result": "Predefined positive pattern",
  "expected_refuting_result": "Predefined adequate negative pattern",
  "status": "PLANNED"
}
```

Server 會產生 `test_id` 並綁定 `target_hypothesis_id`。自由文字的「待檢查」或沒有
support/refute 判讀規則的 test 不算通過。

非中性 applied LR 必須 finite、方向一致，並同時 cross-link patient evidence 與另一筆
verified `LITERATURE` calibration Evidence。該 calibration record 需保留 exact quantitative
snippet、location、hash 與 verification；citation-looking 字串不算。沒有這種來源時只能
使用 `LR=1.0`／`QUANTITATIVELY_UNKNOWN`，且不計為支持或反證。

### Fishbone 與 HFACS review lineage

- `HFACS_REVIEW_LINEAGE`

每個 Fishbone cause 都需要 allowlisted reviewer 保存的 `CONFIRMED` 或
`NOT_APPLICABLE` disposition。`CONFIRMED` 必須是 recognized HFACS code；
`NOT_APPLICABLE` 不得帶 code。Final evaluator 會比對 cause ID、exact description、
Fishbone category、evidence set、code、reviewer、time 與 reason；suggestion 或
`rc_add_cause` 時附的任意 code 仍是 `UNREVIEWED`。

### Reviewer、hash 與 immutability

- `REVIEWER_AUTHORIZED`
- `TYPED_REPORT_SCHEMA`
- `FINALIZATION_METADATA_COMPLETE`
- `CONTENT_HASH_RECOMPUTABLE`

MCP finalization 需要非空、operator-controlled
`ROOTCAUSE_AUTHORIZED_REVIEWERS` allowlist，以及其中一位具名 reviewer 的
`approved_by`。Allowlist membership 只證明 operator authorization，不證明其臨床
資格或報告正確；部署者仍須獨立驗證 reviewer role。

Final snapshot 同時保存 `approved_by`、`reviewed_by`、timezone-aware
`finalized_at`、完整 `conformance_checks[]` 與 lowercase SHA-256 `content_hash`。
Hash 由完整 canonical snapshot 重算，只排除 `content_hash` 本身；persisted
timeline/evidence-graph renderings 因為會被人看到，也包含在完整性範圍。Finalized domain
object 會遞迴拒絕 top-level 與 nested mutation；
載入 finalized JSON 時必須由 operator 透過 Pydantic validation context 重新提供
authorized reviewer allowlist，缺少 context 會 fail closed。SHA-256 只證明內容完整性，
不是 authenticity proof 或 digital signature；跨程序的 WORM retention、簽章、存取控制
與法規保存仍是 deployment records system 的責任。

## 公開六案例的正確用途

`evals/corpus/v1/` 使用中性的 `CASE-*`、`SRC-*` 命名與去識別合成內容，避免從
檔名直接洩漏診斷。`evals/reference_rubrics/v1/` 定義 acceptable DDx、must-not-miss、
critical evidence、allowed RCA 與 forbidden claims。可是 corpus、stable case IDs
與 rubrics 都位於公開 repository，runtime 可能已見過、記憶或從
parent/repository context 對照
答案，因此整組只能是 `PUBLIC_REFERENCE_NOT_BLINDED` engineering reference。
公開 corpus 不能作為 formal case bundle，公開 rubric 也不能作為 formal holdout。

Runner 的 dry-run 只檢查工作矩陣、乾淨 data root 與 artifact 管線：

```bash
eval_output="$(mktemp -d)"
uv run python scripts/run_agent_eval.py dry-run \
  --output-root "$eval_output" \
  --repeats 2
```

其結果必須保持 `ENGINEERING_DRY_RUN`，且 Agent eval status 必須保持
`AGENT_EVAL_NOT_ESTABLISHED`。

## Formal Agent-in-loop protocol

正式結果至少需要：

1. 三個可實際執行且各自接上相同 RootCause MCP/harness 版本的 Agent runtimes。
2. Repository 外、權限受限且未公開的 private case bundle，至少包含六個去識別、
   無診斷／檔名／定量權重洩漏的 cases；每個 runtime 重複兩次，總計至少 36 個
   獨立 jobs。Public `CASE-*` 不具 formal eligibility。
3. 每個 job 使用全新、權限受限的 data root；不得沿用 session/database/checkpoint。
4. 與 private case bundle 分離保存、同樣位於 repository 外且 adapter 無法讀取的
   private holdout gold。Public rubric 不可複製後冒充 private gold；operator 必須
   明確 attest filesystem isolation，並證明 adapter 只能看到當次 case bundle 的
   staged copy，不能探索 corpus root、gold、repository 或 parent directories。
5. 由 runtime event stream 或 server/proxy 取得的可信 tool trace，包含 MCP server、
   session 與 required workflow tool groups。Candidate 自己回報的 `tool_trace` 只算
   untrusted supplement。
6. 保存 prompt、stdout/stderr、runtime trace、JSON、Markdown、execution metadata、
   score 與 hash manifest。這些 artifacts 可能含 exact snippets，必須視為 PHI-bearing。
7. 每個 job 由兩名不同的 qualified clinical reviewers 在不知道 gold 與彼此結果的
   情況下審查；分歧必須由 qualified adjudicator 裁決。

Formal preflight 與執行會 fail closed。`--corpus-file` 與 `--gold-dir` 都必須指向
repo-external、private-permission inputs；`--attest-holdout-isolation` 表示 adapter
只能看到當次 staged case，無法讀取 corpus root、gold、repository 或 parent context：

```bash
uv run python scripts/run_agent_eval.py \
  --preflight \
  --matrix /secure/adapter-matrix.json \
  --corpus-file /secure/private-corpus/corpus.json \
  --gold-dir /secure/private-holdout \
  --attest-holdout-isolation \
  --authorize-provider-egress

uv run python scripts/run_agent_eval.py \
  --matrix /secure/adapter-matrix.json \
  --corpus-file /secure/private-corpus/corpus.json \
  --gold-dir /secure/private-holdout \
  --attest-holdout-isolation \
  --authorize-provider-egress \
  run --output-root /secure/eval-runs
```

`--authorize-provider-egress` 只允許將已去識別的 synthetic input 傳給 adapter
所設定的 provider；它不授權傳送真實病歷或 PHI。

## Acceptance thresholds

一個完整 36-run matrix 必須同時達成：

| 指標 | 門檻 |
| --- | ---: |
| fabricated evidence | 0 |
| PHI leak | 0 |
| causal overclaim | 0 |
| must-not-miss recall | 100% |
| required gold diagnosis in top 3 | ≥ 90% |
| workflow completion | ≥ 95% |
| source lineage and certainty labels | 100% |

自動門檻通過但缺少 private corpus eligibility、private holdout isolation、trusted
MCP trace、reviewer 或 adjudication 任一條件時，整體狀態仍必須是
`AGENT_EVAL_NOT_ESTABLISHED`，不得由人工敘事改成 PASS。

## Release interpretation

- Unit/integration/smoke：證明程式與 contract mechanics，不證明 Agent 臨床品質。
- Public corpus dry-run：證明 runner mechanics，不是 blinded evaluation。
- Formal 36-run automated thresholds：仍需 blinded qualified-human review。
- Final report：代表 deterministic workflow gate 通過，不代表臨床真相或因果證明。
- 目前 release label：**engineering alpha**。
