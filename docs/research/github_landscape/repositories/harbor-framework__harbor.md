# `harbor-framework/harbor` 學習報告

> 本檔只記錄固定版本的文件與原始碼稽核，不代表 Harbor 已通過臨床、安全或生產驗證。

## 查核資料

| 欄位 | 內容 |
|---|---|
| Upstream | [harbor-framework/harbor](https://github.com/harbor-framework/harbor) |
| 查核日期 | `2026-08-18` |
| 查核版本 | 預設分支 `main`，commit `f03db62fd2ed2ed1f79aefe024cfcbc68a0d759e`；`pyproject.toml`／`CITATION.cff` 標示 `v0.21.0` |
| 專案角色 | 基礎套件／agent benchmark 與 rollout 執行框架 |
| 授權 | Apache-2.0；已直接讀取該 commit 的 `LICENSE` |
| 本次驗證 | 查 README、完整 tree、ATIF RFC、ATIF→OTel adapter、`pyproject.toml`、`CITATION.cff` 與 tests tree；**未安裝、未實跑** |

## 一句話結論

Harbor 適合作為跨 Agent eval runner 與軌跡 protocol adapter，但 ATIF／OpenTelemetry 只解決交換與觀測，不等於 RootCause 的來源證據、artifact hash 或不可變 final snapshot 證明。

## 它解決什麼問題

Harbor 把 agent、task、container environment、verifier 與 trial lifecycle 分離，支援以一致介面執行不同 agent／model、平行產生 rollout，並保存 verifier reward 與工作產物。

其 Agent Trajectory Interchange Format（ATIF）以版本化 JSON 表示 system/user/agent 訊息、tool call、observation、時間、model、metrics 與 sub-agent trajectory；`harbor-atif2otel` 再把它轉成 OpenTelemetry／OpenInference 的 AGENT、LLM、TOOL spans。

資料邊界是「runner 看得到的互動與 container artifacts」。含病歷的 prompt、tool output 與 trace 仍可能帶 PHI；OTel exporter 送往外部 collector 前必須另做去識別、存取控制與 retention 設定。

## 核心流程與資料邊界

典型流程是 task/environment adapter 建立隔離環境，agent adapter 執行工作，Harbor 收集 trajectory 與 artifacts，verifier 計分，最後把 trial 結果寫入 jobs directory。

ATIF 是完整互動紀錄的交換格式；OTel 是查詢與可觀測性管線。兩者都不自動證明輸入病歷真實、trace 未遭受信任端竄改，亦不驗證臨床物件間的不變條件。

## 最值得學習的設計

- Agent／task／environment／verifier adapter 分層，可用同一 case matrix 比較多個 runtime。
- 每次 trial 的隔離環境、attempt 與 job artifact 目錄，適合落實乾淨 data root 與重複試跑。
- ATIF 的版本化 trajectory、tool call／observation 配對、sub-agent 與時間欄位，適合統一跨 Agent trace。
- ATIF→OTel 的 protocol conversion 可供 sidecar 搜尋、效能與錯誤分析；RootCause 應自己實作欄位對映，不複製 Harbor 核心碼。
- Verifier 與 agent 分離的測試邊界，可把 deterministic conformance 與主觀臨床 reviewer rubric 分開。

## 與 RootCause MCP 的關係

| 面向 | Upstream | RootCause MCP 的處理 |
|---|---|---|
| Evidence lineage | ATIF 記錄 agent 看見的訊息與 tool observation | 保留 exact snippet、source location、source/span hash、event time 與 extraction method |
| DDx／推理 | 可保存 trajectory，不定義三個 DDx、must-not-miss 或 LR ledger | 以 typed clinical objects 與 cross-object invariants 約束 |
| RCA／causation | 無臨床 Fishbone／Why／HFACS 或保守 causation 狀態 | 明確區分 proposed、insufficient data、rejected 與可稽核 root lineage |
| Final conformance | runner／verifier 輸出 reward 與 artifacts | final report schema、`conformance_checks[]`、可重算 hash 與 immutable snapshot |
| Human review | benchmark verifier 可自訂，但無內建 qualified-clinician finalization 規則 | reviewer allowlist、姓名／角色／時間與 unresolved safety gates |

## 採用建議

**決策：adapter。** 以獨立 eval 環境讓 Harbor 啟動 RootCause harness，輸出 ATIF；需要集中觀測時再由 sidecar 轉 OTel，避免把 Harbor 變成臨床 runtime 的必要依賴。

1. 整合邊界：只接 task setup、agent invocation、trajectory 與 artifact collection；RootCause session、schema validator、hash manifest 與 finalization gate 仍由本專案掌控。
2. Fail-closed：缺 case/run ID、tool request/response 配對、完整 artifact、hash 或 PHI redaction 狀態時，該 trial 不得列為合格；OTel export 成功不得被當成 artifact attestation。
3. Contract tests：固定 ATIF fixture 的雙向欄位對映、sub-agent 關聯、時間／錯誤保存、PHI redaction、artifact digest mismatch 與 interrupted trial。
4. 風險：Apache-2.0 可整合，但 Python `>=3.12`、快速演進的 adapter／ATIF 版本與大量 container dependency 都需 pin；README citation 仍顯示較舊版本，應以 CFF 與固定 commit 為準。

### 基礎套件的引用與依賴方式

- 優先採獨立 sidecar／protocol adapter；只有 eval profile 才加入 optional dependency，不 vendor 原始碼。
- pin release/tag 與 lockfile，正式驗證再 pin commit、container digest 與 ATIF schema 版本。
- 在 `NOTICE`、SBOM 或 dependency inventory 記錄名稱、版本、URL、Apache-2.0。
- ATIF／OTel trace 是觀測資料；RootCause 仍需對 source manifest、JSON、Markdown 與 final snapshot 自行計算 SHA-256。

## 不應直接照搬的部分

- 不把 reward=1、完整 ATIF 或 OTel span 誤稱為臨床正確、因果成立或產物已受可信 attestation。
- 不把可能含 PHI 的 prompt／tool output 無條件送入第三方 collector。
- 不以 Harbor verifier 取代 RootCause 的 nested report schema、cross-object invariants 與 qualified-human review。

## 建議引用

### 軟體引用

```text
Harbor Framework Team. (2026). Harbor: A framework for evaluating and optimizing agents and models in container environments (v0.21.0; commit f03db62fd2ed2ed1f79aefe024cfcbc68a0d759e) [Computer software]. Zenodo. https://doi.org/10.5281/zenodo.20953922
```

### BibTeX fallback

```bibtex
@software{harbor2026,
  author  = {{Harbor Framework Team}},
  title   = {Harbor: A framework for evaluating and optimizing agents and models in container environments},
  year    = {2026},
  doi     = {10.5281/zenodo.20953922},
  url     = {https://github.com/harbor-framework/harbor},
  version = {v0.21.0 / f03db62fd2ed2ed1f79aefe024cfcbc68a0d759e},
  note    = {Accessed 2026-08-18}
}
```

## 來源

- [README（固定 commit）](https://github.com/harbor-framework/harbor/blob/f03db62fd2ed2ed1f79aefe024cfcbc68a0d759e/README.md)
- [LICENSE](https://github.com/harbor-framework/harbor/blob/f03db62fd2ed2ed1f79aefe024cfcbc68a0d759e/LICENSE)／[CITATION.cff](https://github.com/harbor-framework/harbor/blob/f03db62fd2ed2ed1f79aefe024cfcbc68a0d759e/CITATION.cff)／[pyproject.toml](https://github.com/harbor-framework/harbor/blob/f03db62fd2ed2ed1f79aefe024cfcbc68a0d759e/pyproject.toml)
- [ATIF RFC](https://github.com/harbor-framework/harbor/blob/f03db62fd2ed2ed1f79aefe024cfcbc68a0d759e/rfcs/0001-trajectory-format.md)／[ATIF→OTel adapter](https://github.com/harbor-framework/harbor/blob/f03db62fd2ed2ed1f79aefe024cfcbc68a0d759e/packages/harbor-atif2otel/README.md)
- [tests tree](https://github.com/harbor-framework/harbor/tree/f03db62fd2ed2ed1f79aefe024cfcbc68a0d759e/tests)

## 查核限制

本次只做公開 GitHub 固定 commit 的文件、schema/RFC、adapter 與測試樹稽核，未安裝、未執行 Harbor、未驗證 container image 或外部 collector；私人與未索引實作不在涵蓋範圍。
