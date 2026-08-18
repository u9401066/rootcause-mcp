# `kubla/root-cause-health-history-synthesis` 學習報告

> 本報告只做 upstream 文件與原始碼稽核，不代表該專案已通過臨床、安全或生產驗證。

## 查核資料

| 欄位 | 內容 |
|---|---|
| Upstream | [kubla/root-cause-health-history-synthesis](https://github.com/kubla/root-cause-health-history-synthesis) |
| 查核日期 | `2026-08-18` |
| 查核版本 | `main` / `a7f55cb77e7cc9c2e69193f43a860e60533f92dc` |
| 專案角色 | 相鄰方案；可作 longitudinal-history 前處理／handoff adapter 的 Agent Skill |
| 授權 | [Apache License 2.0](https://github.com/kubla/root-cause-health-history-synthesis/blob/a7f55cb77e7cc9c2e69193f43a860e60533f92dc/LICENSE.txt) |
| 本次驗證 | README、SKILL、templates、JSON Schema、evidence/output/snapshot references 與 eval fixtures；未安裝、未執行 Agent 或 schema validator |

## 一句話結論

它不做 DDx 或病安 RCA，但 canonical live case、多 audience renderings、evidence capsules 與 snapshot lineage 很適合透過 adapter 當 RootCause 上游病史整理器。

## 它解決什麼問題

此 Skill 將跨多次對話的零散病史整理為 `CASE.md`、`PLAN.md`、`EVIDENCE.md`、`OUTPUT.md`，再發布 master history、clinician brief、AI brief、causal map 與 `case-object.json`。

它用 trunk-first timeline、symptom clusters、high-leverage questions 與 completion levels，避免無止境 intake。外部抽取結果以 evidence capsule 匯入，要求保留 provenance、confidence、contradiction 與 questions raised。

## 核心流程與資料邊界

- 輸入主要是 user narrative 與其他工具產出的 Markdown evidence capsules，不直接解析 raw records。
- Agent 依 Skill instructions 持續更新 live files；snapshot 時複製 artifacts、更新 manifest 與 parent/delta lineage。
- `case-object.schema.json` 有多層型別，但不少 nested object 只要求 label/name，未強制 exact source、ISO time、hash 或 certainty enum。
- 「immutable snapshot」是 policy/instruction，沒有 runtime write protection、content hash 或 reviewer signature。
- causal map 是 cautious hypotheses/history synthesis，不是統計或臨床 causation proof。

## 最值得學習的設計

- one canonical case、多 audience rendering，避免 clinician/AI outputs 漂成互相矛盾的兩份 truth。
- question leverage score 將 timeline、causal map、output value、uncertainty reduction 與 user burden顯式化。
- [evidence capsule contract](https://github.com/kubla/root-cause-health-history-synthesis/blob/a7f55cb77e7cc9c2e69193f43a860e60533f92dc/references/evidence-integration.md) 明確區分 sourced fact、inference、conflict 與 retired questions。
- [snapshot policy](https://github.com/kubla/root-cause-health-history-synthesis/blob/a7f55cb77e7cc9c2e69193f43a860e60533f92dc/references/snapshot-policy.md) 要求 parentage 與 delta note，適合 human-readable handoff。
- `case-object.json` 可作 adapter input，但必須逐 field 降級成 self-report/host synthesis，不能自動升格 verified evidence。

## 與 RootCause MCP 的關係

| 面向 | Upstream | RootCause MCP 的處理 |
|---|---|---|
| Evidence lineage | capsule title/source/period/confidence與 narrative provenance | atomic exact snippet/location/source+span hash與 manifest |
| DDx／推理 | symptom clusters與 cautious causal factors，無 formal DDx | ≥3 DDx、must-not-miss、direct LR、evidence/test disposition |
| RCA／causation | antecedent/trigger/mediator/perpetuator/protective map | Fishbone/Why/HFACS與 conservative causation audit |
| Final conformance | JSON Schema + instruction-based snapshot policy | nested runtime validation、machine checks、recomputable hash |
| Human review | clinician brief audience，無 reviewer schema | authorized reviewer/time/role、adjudication與 immutable final |

## 採用建議

決策：**adapter**，僅作 optional upstream input/handoff，不引入第二個 case authority。

1. 整合邊界：讀取 `case-object.json`/evidence capsules，映射為 `source_type=self_report_or_host_synthesis`，原始文件仍須另走 RootCause manifest。
2. Fail-closed：無 exact source 的 capsule不得標 verified；snapshot 無 hash、schema fail、兩份 rendering 不一致時保持 preliminary。
3. Contract tests：schema version、field mapping、contradiction preservation、parent lineage、unknown date precision、causal factor certainty downgrade、idempotent import。
4. 授權風險：Apache-2.0 可用；仍要區分 skill instructions、user case data與 downstream generated artifacts 的權利/PHI責任。

### 基礎套件的引用與依賴方式

- 以獨立 Agent Skill sidecar 或 protocol adapter 引用，不複製模板到 RootCause runtime package。
- pin 固定 commit；若日後有 release/tag，再 pin tag、lockfile與部署 artifact digest。
- 在 `NOTICE`、SBOM/dependency inventory 記錄名稱、commit、URL、Apache-2.0 與 adapter 版本。
- 本 repo 無 CITATION.cff/DOI；軟體用下列 fixed-commit fallback 引用，若另有論文應分開引用。

## 不應直接照搬的部分

- schema `$id` 使用 `example.com`，不能當正式、穩定的公共 contract URI。
- instruction-based immutability 未阻止 overwrite，也沒有 snapshot content manifest/hash。
- causal factor 的 `confidence` 是自由字串；不能映射成 RootCause causal audit PASS。
- 12 個 `evals.json` cases 是文字 checks，不是已執行、跨 Agent、臨床 reviewer evaluation。

## 建議引用

### 軟體引用

```text
kubla. (2026). Root Cause Health History Synthesis (commit a7f55cb77e7cc9c2e69193f43a860e60533f92dc) [Computer software]. GitHub. https://github.com/kubla/root-cause-health-history-synthesis
```

### BibTeX fallback

```bibtex
@software{kubla_root_cause_health_history_2026,
  author  = {kubla},
  title   = {Root Cause Health History Synthesis},
  year    = {2026},
  url     = {https://github.com/kubla/root-cause-health-history-synthesis},
  version = {a7f55cb77e7cc9c2e69193f43a860e60533f92dc},
  note    = {Accessed 2026-08-18}
}
```

## 來源

- [README](https://github.com/kubla/root-cause-health-history-synthesis/blob/a7f55cb77e7cc9c2e69193f43a860e60533f92dc/README.md)
- [SKILL.md](https://github.com/kubla/root-cause-health-history-synthesis/blob/a7f55cb77e7cc9c2e69193f43a860e60533f92dc/SKILL.md)
- [case-object JSON Schema](https://github.com/kubla/root-cause-health-history-synthesis/blob/a7f55cb77e7cc9c2e69193f43a860e60533f92dc/assets/case-object.schema.json)
- [Output contract](https://github.com/kubla/root-cause-health-history-synthesis/blob/a7f55cb77e7cc9c2e69193f43a860e60533f92dc/references/output-contract.md)
- [Eval fixtures](https://github.com/kubla/root-cause-health-history-synthesis/blob/a7f55cb77e7cc9c2e69193f43a860e60533f92dc/evals/evals.json)

## 查核限制

本次為 source audit only。未在任何 Agent runtime 安裝此 Skill、未建立 `.casework`、未生成 snapshot、未以 JSON Schema validator 驗產物，也未做 clinical reviewer evaluation。
