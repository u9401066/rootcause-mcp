# `wso2/fhir-mcp-server` 學習報告

> 本檔只記錄 upstream 文件與原始碼稽核，不代表臨床、安全或生產驗證。

## 查核資料

| 欄位 | 內容 |
|---|---|
| Upstream | [wso2/fhir-mcp-server](https://github.com/wso2/fhir-mcp-server) |
| 查核日期 | `2026-08-18` |
| 查核版本 | 預設分支 `main`；commit `796484417b9b04d7bf87ec2156c5fa5b593353f4` |
| 專案角色 | 基礎 sidecar／FHIR MCP proxy |
| 授權 | `Apache-2.0`；已直接讀取根目錄 LICENSE |
| 本次驗證 | README、完整 tree、tool input/output schemas、OAuth、FHIRPath filter、utils、pyproject、unit/integration/e2e tests；未安裝、未連 FHIR、未實跑 |

## 一句話結論

不能取代 RootCause MCP；可候選為 read-only FHIR sidecar，但原始 surface 含 create/update/delete，且 response filtering 可能移除 lineage 欄位，必須由 adapter 收窄能力並保存完整來源。

## 它解決什麼問題

WSO2 server 將 FHIR API 暴露為 MCP，支援 stdio、SSE、Streamable HTTP、SMART-on-FHIR/OAuth 與 FHIRPath response filtering。
工具包括 `get_capabilities`、`search`、`read`、`create`、`update`、`delete`、`get_user`；filter 用來減少回傳欄位與 payload。
package 為 Python `fhir-mcp-server` 0.10.0，直接 pin `mcp[cli]`、`aiohttp`、`fhirpy`、`fhirpathpy`；latest commit 修補 resource type validation。

## 核心流程與資料邊界

server 以 FHIR base URL 與 OAuth/access token 建 async client，MCP tool 直接對遠端 FHIR server 查詢或 mutation。
RootCause 前方 adapter 只應廣告 `get_capabilities`、`search`、`read`，配合 read-only token與 backend/network deny；不得只依賴 prompt 禁止 mutation。
FHIRPath filter 會保留部分 `id/resourceType`，但若未明示請求，`meta.versionId`、`meta.lastUpdated`、Bundle next link 或其他 lineage 可能消失；分析前需保存 unfiltered canonical response/hash。
FHIR validity、OAuth 成功與 resource type regex 均不證明 patient binding、clinical truth、source completeness 或 causal relation。

## 最值得學習的設計

- `get_capabilities` 先發現 search parameters／operations，較不易讓 agent猜測 FHIR 查詢。
- FHIRPath 最小化回傳資料可減少 PHI 暴露；RootCause 必須另保留不可篡改的完整來源或完整-response hash。
- errors 回為 FHIR `OperationOutcome`，可在 adapter 中統一轉成 fail-closed status，而非解析錯誤字串為成功。
- tests 分 unit、integration、e2e，e2e 明確涵蓋 create/update/delete；這也證實原始 surface 不適合直接交給 retrospective agent。

## 與 RootCause MCP 的關係

| 面向 | Upstream | RootCause MCP 的處理 |
|---|---|---|
| Evidence lineage | FHIR response/filter；非完整 case manifest | raw response hash、resource/version/query/pagination 與 exact findings |
| DDx／推理 | 資料存取／分析橋接；無 DDx ledger | competing DDx、LR links、support/disconfirm/test disposition |
| RCA／causation | 無 Why／Fishbone／HFACS | 保守 RCA 與 causation validation |
| Final conformance | MCP tool schema／FHIR payload | typed final report、machine checks、review hash/snapshot |
| Human review | OAuth user context；非 clinical reviewer gate | named authorized qualified-human review |

## 採用建議

**決策：sidecar。** 用獨立 container 執行 pinned artifact，另建 RootCause-owned adapter，只註冊 discovery/search/read；mutation tools 不得進 agent-visible catalog。
adapter 先保存完整 canonical response與 SHA-256，再做 FHIRPath/PHI minimization；每個 finding 帶 resource id/version、query、retrieval time、patient/tenant 與 pagination state。
write/delete tool 可見、authorization disabled、network token 可寫、OperationOutcome、patient mismatch、分頁/版本/完整-response hash 缺漏時一律 fail-closed。
最小 contract tests：tool allowlist、backend write denial、type injection、OAuth audience/scope、FHIRPath over/under-filter、pagination、wrong patient、version conflict、OperationOutcome 與 PHI-safe logs。
Apache-2.0 可支援 sidecar；應 pin 0.10.0 wheel/container與 digest、核對 transitive licenses/SBOM，且針對 latest security fix做 regression。README Docker 說明曾建議本機停用 authorization，production 絕不可沿用。

### 基礎套件的引用與依賴方式

建議 protocol sidecar 而非 import library；在 deployment lock pin image/wheel、commit與 dependency hashes，NOTICE/SBOM 記錄 WSO2、URL、Apache-2.0。adapter 對外維持自有 read-only contract，避免 upstream tool 增加時自動擴權。

## 不應直接照搬的部分

- 不將 create/update/delete 或 `FHIR_SERVER_DISABLE_AUTHORIZATION=True` 帶入任何 production clinical analysis環境。
- 不先 filter 再建立 provenance；縮減 payload 不能取代完整來源 hash與 Bundle lineage。
- 不把 OAuth user、FHIR OperationOutcome 或 server acceptance 當 clinical reviewer／clinical correctness。

## 建議引用

### 軟體引用

```text
WSO2. (2026). fhir-mcp-server (commit 796484417b9b04d7bf87ec2156c5fa5b593353f4) [Computer software]. GitHub. https://github.com/wso2/fhir-mcp-server
```

### BibTeX fallback

```bibtex
@software{wso22026fhirmcp, author={WSO2}, title={FHIR MCP Server}, year={2026}, url={https://github.com/wso2/fhir-mcp-server}, version={796484417b9b04d7bf87ec2156c5fa5b593353f4}, note={Accessed 2026-08-18}}
```

Upstream 未在查核 tree 中提供 `CITATION.cff` 或正式論文 DOI；不另造 paper citation。

## 來源

- [README（pinned）](https://github.com/wso2/fhir-mcp-server/blob/796484417b9b04d7bf87ec2156c5fa5b593353f4/README.md)；[LICENSE](https://github.com/wso2/fhir-mcp-server/blob/796484417b9b04d7bf87ec2156c5fa5b593353f4/LICENSE)；[`pyproject.toml`](https://github.com/wso2/fhir-mcp-server/blob/796484417b9b04d7bf87ec2156c5fa5b593353f4/pyproject.toml)
- [server tools](https://github.com/wso2/fhir-mcp-server/blob/796484417b9b04d7bf87ec2156c5fa5b593353f4/src/fhir_mcp_server/server.py)；[FHIRPath response filter](https://github.com/wso2/fhir-mcp-server/blob/796484417b9b04d7bf87ec2156c5fa5b593353f4/src/fhir_mcp_server/field_filter/response_filter.py)；[type validation](https://github.com/wso2/fhir-mcp-server/blob/796484417b9b04d7bf87ec2156c5fa5b593353f4/src/fhir_mcp_server/utils.py)
- [e2e tool tests](https://github.com/wso2/fhir-mcp-server/blob/796484417b9b04d7bf87ec2156c5fa5b593353f4/tests/e2e/test_tools.py)；[unit tests](https://github.com/wso2/fhir-mcp-server/tree/796484417b9b04d7bf87ec2156c5fa5b593353f4/tests/unit)

## 查核限制

本次只做公開 GitHub 文件與原始碼稽核；沒有安裝 package、執行其 100+ tests 自述、連線 HAPI/Epic、驗證 OAuth/FHIRPath 或安全掃描。公開搜尋亦無法涵蓋私人部署與未索引版本。
