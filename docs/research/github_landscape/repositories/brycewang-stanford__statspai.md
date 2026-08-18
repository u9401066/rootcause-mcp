# `brycewang-stanford/StatsPAI` 學習報告

> 本檔只記錄 upstream 文件與原始碼稽核，不代表臨床、安全或生產驗證。

## 查核資料

| 欄位 | 內容 |
|---|---|
| Upstream | [brycewang-stanford/StatsPAI](https://github.com/brycewang-stanford/StatsPAI) |
| 查核日期 | `2026-08-18` |
| 查核版本 | 預設分支 `main`；commit `a98b6743cc797ddd9cc33de1772c3ea3e3f0c394` |
| 專案角色 | 基礎套件／agent-native econometrics與 causal inference MCP |
| 授權 | `MIT`；已直接讀取 LICENSE，copyright 為 `2025 Bryce Wang` |
| 本次驗證 | README、完整 tree、CITATION、result/tools schemas、MCP server/workflow docs、validation/parity/agent tests；未安裝、未跑 estimator/MCP/tests |

## 一句話結論

不能取代 RootCause MCP，也不是單病例臨床因果證明工具；可評估為隔離的 cohort/econometrics sidecar，其 validation tiers只描述數值/軟體證據，不代表 clinical validity。

## 它解決什麼問題

StatsPAI 提供 OLS、IV、fixed effects、DiD、RD、synthetic control、matching、DML等 applied econometrics APIs，並產生 summary、diagnostics、export與 agent-facing outputs。
其 registry 將 `certified／validated／api_stable／experimental` 與 parity evidence分層，並提供 machine-readable functions/tools/result schemas。
內建 stdio MCP server接受資料路徑、回 text JSON與新版 protocol的 `structuredContent`／`outputSchema`，並可用 result handles接續 audit/sensitivity/plot/citation。

## 核心流程與資料邊界

資料來源是 CSV、DTA、Parquet、Arrow等本地/遠端表格；MCP workflow為 detect design、preflight、fit、audit、sensitivity與 citation。
本機檔案 provenance可記 path、format、columns/sample、size、mtime、SHA-256；remote URL只移除 query token且不一定 hash bytes，因此 RootCause只應允許 host staging後的本機 immutable dataset。
`result.schema.json` 涵蓋 estimand/estimate/CI、diagnostics、violations與 next steps，但僅 `method` required 且允許 additional properties；不能當 RootCause typed final report schema。
validation/parity tier證明的是函式數值對照或 API狀態，不證明 causal assumptions、臨床適用性、單一病例因果或 reviewer adjudication。

## 最值得學習的設計

- 將 API stability 與 numerical validation evidence分開，避免把「可呼叫」誤稱「已驗證」。
- estimator schema描述 assumptions、preconditions、failure modes與 alternatives，可借鑑 RootCause planned-test disposition。
- MCP result handle減少大型 fitted object經 chat往返；本機檔案 SHA-256與 audit resource有利重現。
- committed parity、Monte Carlo、agent transcript與 citation audit tests提供多層品質模式；本次未執行，不能重述為本地通過。

## 與 RootCause MCP 的關係

| 面向 | Upstream | RootCause MCP 的處理 |
|---|---|---|
| Evidence lineage | dataset provenance與 result handle | clinical source manifest、atomic evidence、event precision |
| DDx／推理 | 不做 clinical DDx | ≥3 diagnoses、support/disconfirm/test disposition |
| RCA／causation | cohort econometrics estimates | conservative case/system RCA；統計 supplement不得自動定案 |
| Final conformance | permissive agent result schema | strict nested report、machine checks、hash與 immutable snapshot |
| Human review | audit_result checklist | statistician/clinician review加 authorized final reviewer |

## 採用建議

**決策：sidecar。** 僅對具 cohort design的案例啟用隔離 MCP sidecar；allowlist經審查的 estimator/audit/sensitivity tools，不暴露全部 1,000+ surface。
host 先將去識別 dataset寫入 read-only staging、計算 hash，再以窄 adapter傳 absolute `data_path`；結果進 analytical supplement，不能 mutation root/causation bucket。
單病例、remote URL、dataset hash缺漏、estimand/DAG/assumptions未定、validation tier低於政策門檻、diagnostic violation或 method citation缺漏時必須 fail-closed。
最小 contract tests：path traversal/symlink、remote URL denial、hash round-trip、allowlist、schema strict wrapper、seed、known DGP、diagnostic failure、result handle隔離與 causation-status non-mutation。
MIT 授權可支援 sidecar；surface與更新速度大，應 pin release/image digest、依 estimator鎖版本與 citation，納入 SBOM/NOTICE並由統計 reviewer管理升級。

### 基礎套件的引用與依賴方式

優先用獨立 `statspai-mcp` sidecar與 host protocol adapter，不 vendoring。pin `1.22.0`相容 artifact、lockfile與 container digest；inventory記錄 package、commit、MIT、Zenodo concept DOI。每個 estimator的 method paper另引用，不以 package DOI取代。

## 不應直接照搬的部分

- 不把 certified/validated、CI、p-value、audit_result或 sensitivity稱為單病例臨床因果證明。
- 不允許 remote URL、任意 local path或全部 estimator catalog直接交給 PHI-bearing agent。
- 不用 upstream permissive result schema取代 RootCause deterministic final conformance與 qualified review。

## 建議引用

### 軟體引用

```text
Wang, B., & Rozelle, S. (2026). StatsPAI: Validation-Tiered Causal Inference and Econometrics Workflows for Python (version 1.22.0; commit a98b6743cc797ddd9cc33de1772c3ea3e3f0c394) [Computer software]. Zenodo/GitHub. https://doi.org/10.5281/zenodo.19933900
```

### BibTeX fallback

```bibtex
@software{wang2026statspai, author={Wang, Biaoyue and Rozelle, Scott}, title={StatsPAI: Validation-Tiered Causal Inference and Econometrics Workflows for Python}, year={2026}, url={https://github.com/brycewang-stanford/StatsPAI}, version={a98b6743cc797ddd9cc33de1772c3ea3e3f0c394}, doi={10.5281/zenodo.19933900}, note={Accessed 2026-08-18}}
```

### DOI／論文狀態（與 commit 引用分開）

`CITATION.cff` 將 [10.5281/zenodo.19933900](https://doi.org/10.5281/zenodo.19933900) 明列為軟體的 Zenodo concept DOI。JOSS citation仍是註解且 DOI=`TBD`，所以本報告不宣稱論文已接受；使用個別 estimator時另引原始方法論文。

## 來源

- [README（pinned）](https://github.com/brycewang-stanford/StatsPAI/blob/a98b6743cc797ddd9cc33de1772c3ea3e3f0c394/README.md)；[LICENSE](https://github.com/brycewang-stanford/StatsPAI/blob/a98b6743cc797ddd9cc33de1772c3ea3e3f0c394/LICENSE)；[CITATION.cff](https://github.com/brycewang-stanford/StatsPAI/blob/a98b6743cc797ddd9cc33de1772c3ea3e3f0c394/CITATION.cff)
- [result schema](https://github.com/brycewang-stanford/StatsPAI/blob/a98b6743cc797ddd9cc33de1772c3ea3e3f0c394/schemas/result.schema.json)；[tool schemas](https://github.com/brycewang-stanford/StatsPAI/blob/a98b6743cc797ddd9cc33de1772c3ea3e3f0c394/schemas/tools.json)；[MCP server](https://github.com/brycewang-stanford/StatsPAI/blob/a98b6743cc797ddd9cc33de1772c3ea3e3f0c394/src/statspai/agent/mcp_server.py)
- [MCP workflow](https://github.com/brycewang-stanford/StatsPAI/blob/a98b6743cc797ddd9cc33de1772c3ea3e3f0c394/docs/guides/economist_mcp_workflow.md)；[agent eval tests](https://github.com/brycewang-stanford/StatsPAI/tree/a98b6743cc797ddd9cc33de1772c3ea3e3f0c394/tests/agent_eval)；[Monte Carlo tests](https://github.com/brycewang-stanford/StatsPAI/tree/a98b6743cc797ddd9cc33de1772c3ea3e3f0c394/tests/coverage_monte_carlo)

## 查核限制

本次只做公開 GitHub 文件與原始碼稽核；沒有安裝 StatsPAI、啟動 MCP、執行 tests、重現 parity/Monte Carlo或估計任何臨床資料。公開搜尋亦無法涵蓋私人版本與未索引專案。
