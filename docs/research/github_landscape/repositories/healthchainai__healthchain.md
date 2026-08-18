# `healthchainai/HealthChain` 學習報告

> 本檔只記錄 upstream 文件與原始碼稽核，不代表臨床、安全或生產驗證。

## 查核資料

| 欄位 | 內容 |
|---|---|
| Upstream | [healthchainai/HealthChain](https://github.com/healthchainai/HealthChain) |
| 查核日期 | `2026-08-18` |
| 查核版本 | 預設分支 `main`；commit `87fbd28c8ddb996a0d7509193ad761b512205852` |
| 專案角色 | 基礎套件／FHIR validation、agent tools 與 EHR gateway |
| 授權 | `Apache-2.0`；已直接讀取根目錄 LICENSE |
| 本次驗證 | README、完整 tree、CITATION、FHIR/agent tool schemas、`pyproject.toml`、FHIR validation、gateway/FHIR/tool tests；未安裝、未連 EHR、未實跑 |

## 一句話結論

不能取代 RootCause MCP；適合以 optional dependency 建立離線 FHIR Bundle adapter，或把 gateway 放在 read-only upstream boundary，但 FHIR validity 不等於病歷真實性或臨床推理正確。

## 它解決什麼問題

HealthChain 是 Python healthcare AI SDK，提供 typed FHIR resources、validation reports、terminology lookup、FHIR gateway、CDS/FHIR adapter 與 agent tools。
`FHIRToolkit` 將 build、validate、load bundle、read resources、resolve reference、lookup code 包成 framework-neutral tools，並可轉成 MCP 或 LangChain surface。
其 stateful bundle pattern 只驗證一次再供多次 read，適合大型 Bundle；gateway 則可連接多個 EHR FHIR source。

## 核心流程與資料邊界

建議 RootCause 僅在 host-controlled adapter 載入既有 Bundle；將每個 FHIR resource 轉成 atomic observation，保留 `resourceType/id/meta.versionId/meta.lastUpdated`、Bundle link 與原始 bytes hash。
`validate_resource` 檢查 Pydantic 結構、必填欄位與部分 primitive-code required bindings；原始碼明列不檢查 Coding/CodeableConcept bindings、FHIRPath invariants、profiles 或 reference integrity。
完整 profile conformance 仍需對指定 FHIR server/profile 執行 `$validate`；即使 valid，也不能證明來源完整、值正確、患者一致或診斷成立。
FHIRToolkit MCP 結果採 JSON content 且 `structured_output=False`，RootCause adapter 仍須自行套 typed ingestion contract。

## 最值得學習的設計

- errors-as-values 的 `ValidationReport`／`issues[]`，便於 agent 修正而不把 exception 誤判成功。
- stateful、一次驗證的 Bundle toolkit 可避免在 tool calls 間反覆搬運大型 JSON。
- terminology lookup 明示「從 catalog 選 code，不從模型記憶編造」，適合 RootCause code provenance guard。
- upstream tests 涵蓋 FHIR helpers/readers/validation、gateway sync/async 與 toolkit；本次僅稽核檔案，未執行。

## 與 RootCause MCP 的關係

| 面向 | Upstream | RootCause MCP 的處理 |
|---|---|---|
| Evidence lineage | FHIR ids/meta 與 optional gateway provenance tag | source manifest、raw hash、exact snippet/cell、event precision |
| DDx／推理 | FHIR-grounded Q&A／agent utilities；非 DDx ledger | competing DDx、LR links、支持／反證與 test disposition |
| RCA／causation | 無 clinical event RCA contract | Why／Fishbone／HFACS 與 conservative validator |
| Final conformance | FHIR resource validation report | nested case-report schema、machine checks、hash/final snapshot |
| Human review | 工具／gateway 不提供 RootCause reviewer gate | named authorized qualified-human review |

## 採用建議

**決策：adapter。** 新增可選的離線 FHIR adapter，依賴 `healthchain` 的 public FHIR load/validation API；live gateway 若評估採用則獨立部署、只給 read scope。
adapter 輸出需帶 FHIR source URL、tenant/patient context、resource id/version、retrieval time、pagination completeness、原始 hash 與 validation issues；FHIR 資料不可直接變成 causal claim。
patient/context 不一致、Bundle 分頁未取完、reference unresolved、profile 未知、validation error、寫入工具可見或來源 hash 缺漏時，必須 fail-closed 並保持 preliminary。
最小 contract tests：valid/invalid Bundle、duplicate/version conflict、contained/external reference、pagination、timezone precision、wrong patient、terminology miss、PHI logging 與 upstream timeout。
Apache-2.0 可支援 dependency；但 `fhir-resources`、MCP/LangChain extras、terminology data 與 EHR contracts 各需 SBOM/授權與相容性查核，README roadmap 不視為已完成 governance。

### 基礎套件的引用與依賴方式

建議建立 `fhir` optional extra，以 public API 引用 `healthchain`，在 lockfile pin 已驗證 release（CITATION 目前記錄 `0.14.4`）及 artifact hash；不要複製 FHIR models。NOTICE、SBOM 與 dependency inventory 記錄版本、URL、Apache-2.0，正式驗證另 pin commit／wheel digest。

## 不應直接照搬的部分

- 不開放 live EHR create/update/writeback 給 retrospective reasoning agent；預設 read-only、最小 scope。
- 不把 `valid=true`、code lookup 或 provenance tag 當來源真實性、患者一致性或 clinical correctness 證明。
- 不把 README 的 production/HIPAA 敘述取代本部署 threat model、audit 與 qualified review。

## 建議引用

### 軟體引用

```text
Jiang-Kells, J. (2024). HealthChain: A Python SDK for Clinical AI Integration (commit 87fbd28c8ddb996a0d7509193ad761b512205852) [Computer software]. GitHub. https://github.com/healthchainai/HealthChain
```

### BibTeX fallback

```bibtex
@software{jiangkells2024healthchain, author={Jiang-Kells, Jennifer}, title={HealthChain: A Python SDK for Clinical AI Integration}, year={2024}, url={https://github.com/healthchainai/HealthChain}, version={87fbd28c8ddb996a0d7509193ad761b512205852}, note={Accessed 2026-08-18}}
```

### 軟體封存 DOI（與 commit 引用分開）

README 的 Zenodo badge 指向 [10.5281/zenodo.20056729](https://doi.org/10.5281/zenodo.20056729)；`CITATION.cff` 的 preferred citation 本身未列論文 DOI，因此不宣稱有經同儕審查的臨床論文。

## 來源

- [README（pinned）](https://github.com/healthchainai/HealthChain/blob/87fbd28c8ddb996a0d7509193ad761b512205852/README.md)；[LICENSE](https://github.com/healthchainai/HealthChain/blob/87fbd28c8ddb996a0d7509193ad761b512205852/LICENSE)；[CITATION.cff](https://github.com/healthchainai/HealthChain/blob/87fbd28c8ddb996a0d7509193ad761b512205852/CITATION.cff)
- [FHIR validation scope](https://github.com/healthchainai/HealthChain/blob/87fbd28c8ddb996a0d7509193ad761b512205852/healthchain/fhir/validation.py)；[FHIRToolkit](https://github.com/healthchainai/HealthChain/blob/87fbd28c8ddb996a0d7509193ad761b512205852/healthchain/tools/toolkit.py)；[dependency extras](https://github.com/healthchainai/HealthChain/blob/87fbd28c8ddb996a0d7509193ad761b512205852/pyproject.toml)
- [toolkit tests](https://github.com/healthchainai/HealthChain/blob/87fbd28c8ddb996a0d7509193ad761b512205852/tests/tools/test_toolkit.py)；[FHIR validation tests](https://github.com/healthchainai/HealthChain/blob/87fbd28c8ddb996a0d7509193ad761b512205852/tests/fhir/test_validation.py)

## 查核限制

本次只做公開 GitHub 文件與原始碼稽核；沒有安裝 wheel、執行 tests、連線 FHIR/EHR、測 OAuth 或驗證任何 profile。公開搜尋亦無法涵蓋私人部署與未索引版本。
