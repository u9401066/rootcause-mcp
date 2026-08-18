# `DIGIT-X-Lab/MOSAICX` 學習報告

> 本檔只記錄 upstream 文件與原始碼稽核，不代表臨床、安全或生產驗證。

## 查核資料

| 欄位 | 內容 |
|---|---|
| Upstream | [DIGIT-X-Lab/MOSAICX](https://github.com/DIGIT-X-Lab/MOSAICX) |
| 查核日期 | `2026-08-18` |
| 查核版本 | 預設分支 `master`；commit `bb4a960b019f0d3098e1b1e159ee4e355c35ff23` |
| 專案角色 | 相鄰方案／文件 extraction 與去識別 sidecar |
| 授權 | `Apache-2.0`；已直接讀取根目錄 LICENSE |
| 本次驗證 | README、完整 tree、MCP docs/server、provenance models/resolver/source mapping、schemas 與相關 tests；未安裝、未啟動 OCR/LLM、未實跑 |

## 一句話結論

不能取代 RootCause MCP；可評估為本機文件 extraction sidecar，但其 fuzzy source mapping 絕不可自動升格為 `VERIFIED` evidence。

## 它解決什麼問題

MOSAICX 將 PDF、影像或文字醫療文件經 OCR／LLM 轉成 schema-driven JSON，另提供去識別、timeline summary、template、verification 與 document query。
MCP server 暴露十個工具；`extract_document` 接受完整文字，能回傳 extraction、metrics、completeness 與 `_source` mapping。
`SourceSpan`／`FieldEvidence` 建模 field path、excerpt、位置與 confidence；另一 resolver 明確區分 `exact`、`fuzzy`、`unresolved`。

## 核心流程與資料邊界

檔案解析、OCR、LLM extraction 與去識別在 MOSAICX 邊界；RootCause 只應接收去識別後的原文片段、來源 inventory、雜湊、抽取方法與解析狀態。
MCP 的 `extract_document` 直接收 `document_text`，並以合成來源路徑 `<mcp>` 建 `LoadedDocument`；它不會替 host 保存原始檔 URI、whole-file SHA-256 或 manifest。
`pipelines/provenance.py` 的 fuzzy 門檻為短 excerpt 0.90、長 excerpt 0.80；`source_mapping.py` 又會 fuzzy fallback，並可能只以 `grounded: true` 表示找到近似文字。
因此 fuzzy／case-insensitive／date-alternative／approximate offset 只能是 `UNVERIFIED` proposed extraction；只有可重算的 exact bytes/span match 才可進 RootCause verified evidence。

## 最值得學習的設計

- field-level `SourceSpan`、`FieldEvidence` 與 dotted field paths，可借鑑 adapter 的輸出 contract。
- `exact／fuzzy／unresolved` 三層 resolver 很適合做顯式 certainty，而不是二元「有 excerpt 即可信」。
- 本機 LLM／OCR 與 optional MCP extra 有利 PHI 邊界；仍需獨立驗證 log、cache、模型 endpoint 與 temp files。
- tests 涵蓋 provenance、source mapping、conformance、deidentifier、MCP verify/query 與 integration；本次只確認檔案存在，未執行。

## 與 RootCause MCP 的關係

| 面向 | Upstream | RootCause MCP 的處理 |
|---|---|---|
| Evidence lineage | field excerpt、offset／bbox、grounding resolution | 完整 source manifest、whole-source hash、exact snippet 與 certainty |
| DDx／推理 | extraction／summary；非 DDx ledger | ≥3 competing DDx、支持／反證與 planned test |
| RCA／causation | 無 Why／Fishbone／HFACS causation gate | 分離觀察、解讀、假設與保守 causal claim |
| Final conformance | extraction envelope／conformance modules | typed clinical report、machine checks 與 immutable snapshot |
| Human review | verification tools，不等於 qualified reviewer | fuzzy/OCR correction 與 final report 均需具名 reviewer |

## 採用建議

**決策：sidecar。** 以獨立本機 process/container 執行 `mosaicx[mcp]`，由窄版 adapter 將 extraction 輸出轉成 RootCause source manifest 與 atomic findings；不要 vendoring 原始碼。
adapter 必須另存原始來源 URI、SHA-256、parser/OCR/model version、page/line/char、時間精度、去識別狀態，且保留 upstream `resolution` 原值。
只允許 `resolution == "exact"` 且對 host 保管的 canonical text 重算成功時自動 verified；fuzzy、unresolved、缺來源 hash、OCR correction 未審或 `<mcp>` synthetic source 一律 fail-closed。
最小 contract tests：exact／duplicate／fuzzy／unresolved、跨頁 bbox、Unicode/whitespace、hash mismatch、PHI canary、source ID collision、sidecar timeout 與 malformed JSON。
Apache-2.0 可支援 sidecar；仍須 pin MOSAICX、OCR、模型與 container digest，在 NOTICE／SBOM 記錄，並另查模型權重及輸入資料條款。

### 基礎套件的引用與依賴方式

建議用獨立 sidecar，而非 RootCause Python dependency；prototype 可 pin `mosaicx[mcp]` release 並鎖完整 lockfile，正式驗證後再 pin commit／image digest。RootCause adapter 只依賴自有 JSON contract，不 import upstream internals。

## 不應直接照搬的部分

- 不把 README 的「validated」「HIPAA-conformant」描述視為本部署已合規；需獨立 threat model、BAA/政策與驗證。
- 不把 fuzzy `grounded: true`、LLM excerpt、confidence 或 verification 工具結果升格為 verified provenance。
- 不讓 extraction sidecar直接 finalize DDx、RCA 或 clinical causation。

## 建議引用

### 軟體引用

```text
DIGIT-X Lab. (2026). MOSAICX (commit bb4a960b019f0d3098e1b1e159ee4e355c35ff23) [Computer software]. GitHub. https://github.com/DIGIT-X-Lab/MOSAICX
```

### BibTeX fallback

```bibtex
@software{digitx2026mosaicx, author={{DIGIT-X Lab}}, title={MOSAICX}, year={2026}, url={https://github.com/DIGIT-X-Lab/MOSAICX}, version={bb4a960b019f0d3098e1b1e159ee4e355c35ff23}, note={Accessed 2026-08-18}}
```

### 軟體封存 DOI（與 commit 引用分開）

Upstream README 提供 Zenodo DOI [10.5281/zenodo.17601890](https://doi.org/10.5281/zenodo.17601890)；這是軟體封存引用，不是臨床效能或因果證明論文。

## 來源

- [README（pinned）](https://github.com/DIGIT-X-Lab/MOSAICX/blob/bb4a960b019f0d3098e1b1e159ee4e355c35ff23/README.md)；[LICENSE](https://github.com/DIGIT-X-Lab/MOSAICX/blob/bb4a960b019f0d3098e1b1e159ee4e355c35ff23/LICENSE)；[MCP docs](https://github.com/DIGIT-X-Lab/MOSAICX/blob/bb4a960b019f0d3098e1b1e159ee4e355c35ff23/docs/mcp-server.md)
- [provenance models](https://github.com/DIGIT-X-Lab/MOSAICX/blob/bb4a960b019f0d3098e1b1e159ee4e355c35ff23/mosaicx/provenance/models.py)；[exact/fuzzy resolver](https://github.com/DIGIT-X-Lab/MOSAICX/blob/bb4a960b019f0d3098e1b1e159ee4e355c35ff23/mosaicx/pipelines/provenance.py)；[source mapping](https://github.com/DIGIT-X-Lab/MOSAICX/blob/bb4a960b019f0d3098e1b1e159ee4e355c35ff23/mosaicx/source_mapping.py)
- [provenance tests](https://github.com/DIGIT-X-Lab/MOSAICX/blob/bb4a960b019f0d3098e1b1e159ee4e355c35ff23/tests/test_provenance.py)；[source mapping tests](https://github.com/DIGIT-X-Lab/MOSAICX/blob/bb4a960b019f0d3098e1b1e159ee4e355c35ff23/tests/test_source_mapping.py)

## 查核限制

本次只做公開 GitHub 文件與原始碼稽核；沒有安裝 package、啟動 Chandra/LLM、處理病歷、測 PHI 去識別或執行 tests。公開搜尋亦無法涵蓋私人部署與未索引版本。
