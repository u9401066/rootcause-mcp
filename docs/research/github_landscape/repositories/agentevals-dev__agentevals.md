# `agentevals-dev/agentevals` 學習報告

> 本檔只記錄固定版本的文件與原始碼稽核，不代表 agentevals 已通過臨床、安全或生產驗證。

## 查核資料

| 欄位 | 內容 |
|---|---|
| Upstream | [agentevals-dev/agentevals](https://github.com/agentevals-dev/agentevals) |
| 查核日期 | `2026-08-18` |
| 查核版本 | 預設分支 `main`，commit `5b4ad1863ffb14d07768a9f7fa879db9ddeef40d` |
| 專案角色 | 基礎套件／通用 agent trace evaluation sidecar |
| 授權 | Apache-2.0；已直接讀取該 commit 的 `LICENSE` |
| 本次驗證 | 查 README、完整 tree、eval-set format、OTel compatibility、`pyproject.toml`、MCP／CLI 與 tests tree；**未安裝、未實跑** |

## 一句話結論

可用作 OTel trace 的外部 eval sidecar，但專案明示 active development／可能 breaking，且與 `langchain-ai/agentevals` 使用相同 `agentevals` Python namespace，不能在同一環境並裝。

## 它解決什麼問題

此 repo 以 framework-agnostic OpenTelemetry traces 為輸入，支援 Jaeger JSON、OTLP、golden eval sets、自訂 evaluator、CLI／UI 與 MCP，目標是從真實 agent trace 進行 correctness evaluation。

Eval-set 格式沿用 Google ADK 概念，包含 eval set/case、conversation invocations、expected tool uses／responses 與 rubrics；OTel 文件涵蓋 GenAI semantic conventions、Google ADK、span attributes、logs 與舊 span events。

套件 distribution 名稱是 `agentevals-cli`，console script 與 import package 都是 `agentevals`，Python `>=3.11`。上游 README 明載仍在 active development，應預期 breaking changes。

## 核心流程與資料邊界

Collector／檔案 reader 匯入 OTel trace，正規化 conversation／tool events，再用 golden expected trajectory、rubric 或自訂 evaluator 計分，結果可由本機 UI／CLI／MCP 查閱。

它評估「收到的 trace」，不證明 trace 由可信 server 產生、不保證完整保存 artifact，也不建立臨床 evidence ledger；span/log 可能含 PHI，接收端、儲存端與 evaluator model 都是額外資料邊界。

## 最值得學習的設計

- OTel compatibility matrix 與多種 ingestion path，可降低 agent framework 綁定。
- Golden eval case 把 conversation、expected tool calls、responses 與 rubric 放在同一版本化物件。
- 自訂 evaluator／MCP／UI 分層，適合作為不影響 RootCause runtime 的獨立分析 sidecar。
- integration／e2e pytest markers 與 receiver tests 可借鏡；RootCause 應自己建立 clinical scorer，不複製 generic judge。
- 對 trace 欄位缺漏需採 fail-closed 正規化，而非把不可解析事件靜默略過。

## 與 RootCause MCP 的關係

| 面向 | Upstream | RootCause MCP 的處理 |
|---|---|---|
| Evidence lineage | OTel span/log 與 expected conversation，可追互動但不追原始病歷 span hash | source manifest、evidence ID、exact snippet、location 與 SHA-256 |
| DDx／推理 | generic rubric／trajectory，不定義 DDx clinical invariants | active DDx、must-not-miss、LR、support／disconfirm／planned test |
| RCA／causation | 無 Fishbone／Why／HFACS 或 conservative causal status | typed RCA objects、root/evidence/Why consistency 與 rejected/proposed 規則 |
| Final conformance | 可跑 evaluator，沒有 RootCause final report contract | nested schema、machine-readable checks、review metadata、immutable hash |
| Human review | rubric 可人工設計，未內建 qualified clinician adjudication | 兩名盲評 reviewer、分歧裁決與 authorized reviewer gate |

## 採用建議

**決策：sidecar。** 在隔離 container／virtualenv 讀取 RootCause 匯出的去識別 OTel trace，僅做通用 trajectory 與工具使用評估；臨床 conformance 由 RootCause 原生 evaluator 負責。

1. 整合邊界：RootCause 只輸出固定版本 trace adapter；agentevals 不得寫回 case store、決定 finalization 或持有未去識別原始病歷。
2. Fail-closed：缺 session/run/server/tool ID、request-response pairing、redaction 標記或 artifact digest 時，結果標 invalid；evaluator error 不可當 pass。
3. Contract tests：Harbor ATIF→OTel fixture、RootCause MCP tool span、nested/sub-agent trace、錯誤／timeout、敏感欄位移除與 deterministic evaluator 重跑一致性。
4. 風險：Apache-2.0 可採；active/breaking 與寬鬆 transitive dependency 需 lock。`langchain-ai/agentevals` 也安裝/import `agentevals`，同環境會 namespace／distribution 衝突。

### 基礎套件的引用與依賴方式

- 採獨立 sidecar 或 protocol adapter，不加入臨床 server 的 base dependencies，也不 vendor source。
- pin release/tag、lockfile 與 container digest；正式 conformance 再 pin commit 和 eval-set schema。
- 在 `NOTICE`、SBOM／dependency inventory 記錄 `agentevals-cli` 名稱、版本、repo URL 與 Apache-2.0。
- 若既有環境需要 [langchain-ai/agentevals](https://github.com/langchain-ai/agentevals)，兩者拆成不同 virtualenv/container；前者偏 message-list trajectory evaluator，本報告 repo 偏 OTel ingestion，RootCause 建議後者僅作 sidecar POC。

## 不應直接照搬的部分

- 不因 trace 符合 OTel 就視為受信、完整、無 PHI 或可重算的 artifact attestation。
- 不用 generic expected-tool rubric 取代 clinical cross-object invariants。
- 不在 RootCause runtime 同時安裝兩個 `agentevals` distribution，也不追蹤未 pin 的 `main`。

## 建議引用

### 軟體引用

```text
agentevals-dev. (2026). agentevals (commit 5b4ad1863ffb14d07768a9f7fa879db9ddeef40d) [Computer software]. GitHub. https://github.com/agentevals-dev/agentevals
```

### BibTeX fallback

```bibtex
@software{agentevals_dev_2026,
  author  = {{agentevals-dev}},
  title   = {agentevals},
  year    = {2026},
  url     = {https://github.com/agentevals-dev/agentevals},
  version = {5b4ad1863ffb14d07768a9f7fa879db9ddeef40d},
  note    = {Accessed 2026-08-18}
}
```

上游未提供正式 benchmark 論文／DOI；此軟體 fallback 不應被描述成論文引用。

## 來源

- [README（固定 commit）](https://github.com/agentevals-dev/agentevals/blob/5b4ad1863ffb14d07768a9f7fa879db9ddeef40d/README.md)
- [LICENSE](https://github.com/agentevals-dev/agentevals/blob/5b4ad1863ffb14d07768a9f7fa879db9ddeef40d/LICENSE)／[pyproject.toml](https://github.com/agentevals-dev/agentevals/blob/5b4ad1863ffb14d07768a9f7fa879db9ddeef40d/pyproject.toml)
- [eval-set format](https://github.com/agentevals-dev/agentevals/blob/5b4ad1863ffb14d07768a9f7fa879db9ddeef40d/docs/eval-set-format.md)／[OTel compatibility](https://github.com/agentevals-dev/agentevals/blob/5b4ad1863ffb14d07768a9f7fa879db9ddeef40d/docs/otel-compatibility.md)
- [tests tree](https://github.com/agentevals-dev/agentevals/tree/5b4ad1863ffb14d07768a9f7fa879db9ddeef40d/tests)／[同 namespace 的另一專案](https://github.com/langchain-ai/agentevals)

## 查核限制

本次只查公開固定 commit 的文件、格式、依賴與測試樹，未建立 collector、未匯入 RootCause／Harbor trace、未執行 evaluator；無法由公開搜尋涵蓋私人部署與未索引方案。
