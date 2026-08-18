# `langcare/langcare-mcp-fhir` 學習報告

> 本檔只記錄 upstream 文件與原始碼稽核，不代表臨床、安全或生產驗證。

## 查核資料

| 欄位 | 內容 |
|---|---|
| Upstream | [langcare/langcare-mcp-fhir](https://github.com/langcare/langcare-mcp-fhir) |
| 查核日期 | `2026-08-18` |
| 查核版本 | 預設分支 `main`；commit `430598bb5a76619ef55fa34fb1fd90c65f3d4783` |
| 專案角色 | 基礎 sidecar／FHIR R4 MCP proxy |
| 授權 | `MIT`；已直接讀取 LICENSE，copyright 為 `2026 langcare` |
| 本次驗證 | README、完整 tree、Go module、MCP input-schema registration、FHIR tools/providers、security/audit files 與 test tree；未 build、未連 EHR、未實跑 |

## 一句話結論

不能取代 RootCause MCP；可候選為 FHIR read-only upstream sidecar，但原始 server 同時暴露 create/update，必須用獨立 adapter、read scopes 與網路政策從能力面移除寫入。

## 它解決什麼問題

LangCare 是 Go 實作的 stateless FHIR R4 MCP proxy，支援 stdio／Streamable HTTP 與 Epic、Cerner、OpenEMR、GCP、generic backend。
核心四工具為 `fhir_read`、`fhir_search`、`fhir_create`、`fhir_update`，針對任意 FHIR R4 resource type；另附 skills、managed agents、MCP Apps、CLI 與 voice-agent 相鄰資產。
README 描述兩層認證、TLS、PHI log scrubbing、audit、OAuth/SMART/mTLS 與 rate limiting；這些是 upstream 功能聲明，本次未驗證部署合規性。

## 核心流程與資料邊界

MCP server 以 official Go SDK 將 registry 中所有 tools 註冊，將 JSON tool result 包成 text content；backend 是既有 FHIR server，proxy 本身宣稱不持久化資料。
RootCause 應透過窄版 protocol adapter 只暴露 `fhir_read`／`fhir_search`，使用獨立 read-only SMART scope；不要讓 agent 直接連原始四工具 surface。
adapter 將 resource／Bundle 轉為 source manifest 與 findings，保留 base URL、tenant/patient context、resource `id`、`meta.versionId`、`meta.lastUpdated`、`fullUrl`、next link、query 與 retrieval time。
skills 與 MCP Apps 是 agent/UI 層，不提供 RootCause evidence ledger、DDx/RCA schema 或 deterministic finalization。

## 最值得學習的設計

- stateless proxy 與 provider abstraction，能把 EHR authentication 留在來源邊界，而非注入 reasoning server。
- 以四個 generic operations 覆蓋 resource types，surface 小且易做 allowlist；RootCause 只需其中兩個 read operations。
- server 將 tool execution error 設 `IsError: true`，可用於 adapter 的明確錯誤傳遞。
- repository 有 security/audit/provider source，但公開 `test/` tree 主要見 CLI 與 Epic token 測試；不可據 README 自述推定全面 conformance。

## 與 RootCause MCP 的關係

| 面向 | Upstream | RootCause MCP 的處理 |
|---|---|---|
| Evidence lineage | FHIR resource／Bundle response與 audit | source manifest、raw hash、版本、query、pagination 與 exact observation |
| DDx／推理 | optional clinical skills；非持久 DDx ledger | ≥3 DDx、evidence/test disposition、must-not-miss |
| RCA／causation | 無 Why／Fishbone／HFACS contract | conservative RCA/causation stages |
| Final conformance | generic MCP text JSON | typed final report、machine checks、review hash/snapshot |
| Human review | prompt guidance；無 RootCause reviewer authorization | named qualified-human reviewer gate |

## 採用建議

**決策：sidecar。** 以 pinned container/binary 獨立部署，在前方加 RootCause-owned read-only adapter；production MCP catalog 只註冊 `fhir_read` 與 `fhir_search`。
sidecar 使用最小 read scopes、單一 tenant/patient context、egress allowlist 與 PHI-safe logs；原始 `fhir_create`／`fhir_update` 不得對 analysis agent 可見，即使 backend 會拒絕也不夠。
患者不一致、分頁不完整、OperationOutcome、resource version 缺漏、寫工具出現在 catalog、audit/PHI policy 未載入或 source hash 無法建立時必須 fail-closed。
最小 contract tests：tool allowlist、OAuth read/write denial、patient binding、pagination、version conflict、Bundle lineage、OperationOutcome、timeout/retry、log PHI canary 與 concurrent sessions。
MIT 授權寬鬆；需 pin Go/npm/container artifact 與 transitive modules，保存 NOTICE/SBOM。上游 `go.mod` 使用 Go 1.25.5 與 MCP Go SDK 1.2.0，升級相容性需重驗。

### 基礎套件的引用與依賴方式

不連結或複製 Go 原始碼；使用獨立 sidecar 的 MCP protocol adapter，pin release/container digest 與 config schema。dependency inventory 記錄 binary/package、commit、Go module graph、MIT；adapter contract 只接受 read/search response 及 provenance metadata。

## 不應直接照搬的部分

- 不把 create/update、interactive chart edit 或文件寫回能力暴露給 retrospective reasoning agent。
- 不把 README 的 HIPAA-compliant／enterprise-grade 用語視為本環境認證或安全測試結果。
- 不把 clinical skills 的 prompt、FHIR code 或 resource presence 當已驗證 diagnosis/causation。

## 建議引用

### 軟體引用

```text
langcare. (2026). langcare-mcp-fhir (commit 430598bb5a76619ef55fa34fb1fd90c65f3d4783) [Computer software]. GitHub. https://github.com/langcare/langcare-mcp-fhir
```

### BibTeX fallback

```bibtex
@software{langcare2026mcphfir, author={langcare}, title={langcare-mcp-fhir}, year={2026}, url={https://github.com/langcare/langcare-mcp-fhir}, version={430598bb5a76619ef55fa34fb1fd90c65f3d4783}, note={Accessed 2026-08-18}}
```

Upstream 未在查核 tree 中提供 `CITATION.cff` 或正式論文 DOI；不另造 paper citation。

## 來源

- [README（pinned）](https://github.com/langcare/langcare-mcp-fhir/blob/430598bb5a76619ef55fa34fb1fd90c65f3d4783/README.md)；[LICENSE](https://github.com/langcare/langcare-mcp-fhir/blob/430598bb5a76619ef55fa34fb1fd90c65f3d4783/LICENSE)；[Security docs](https://github.com/langcare/langcare-mcp-fhir/blob/430598bb5a76619ef55fa34fb1fd90c65f3d4783/docs/SECURITY.md)
- [MCP registration](https://github.com/langcare/langcare-mcp-fhir/blob/430598bb5a76619ef55fa34fb1fd90c65f3d4783/internal/mcp/server.go)；[read tool](https://github.com/langcare/langcare-mcp-fhir/blob/430598bb5a76619ef55fa34fb1fd90c65f3d4783/internal/tools/fhir_read.go)；[search tool](https://github.com/langcare/langcare-mcp-fhir/blob/430598bb5a76619ef55fa34fb1fd90c65f3d4783/internal/tools/fhir_search.go)
- [Go dependency manifest](https://github.com/langcare/langcare-mcp-fhir/blob/430598bb5a76619ef55fa34fb1fd90c65f3d4783/go.mod)；[test tree](https://github.com/langcare/langcare-mcp-fhir/tree/430598bb5a76619ef55fa34fb1fd90c65f3d4783/test)

## 查核限制

本次只做公開 GitHub 文件與原始碼稽核；沒有 build binary、執行 tests、驗證 OAuth/TLS/PHI scrub、連線任何 FHIR backend 或做安全掃描。公開搜尋亦無法涵蓋私人部署與未索引版本。
