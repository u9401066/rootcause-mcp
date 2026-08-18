# `<owner>/<repo>` 學習報告範本

> 本檔只定義研究報告格式，不代表任何 upstream 已通過臨床、安全或生產驗證。

## 查核資料

| 欄位 | 內容 |
|---|---|
| Upstream | `<GitHub URL>` |
| 查核日期 | `YYYY-MM-DD` |
| 查核版本 | 預設分支與 commit SHA；若只能查 release，記錄 tag |
| 專案角色 | 直接競品／相鄰方案／基礎套件／benchmark／資料集 |
| 授權 | SPDX 或上游 LICENSE 原文；不確定時明寫「待法務確認」 |
| 本次驗證 | README／tree／schema／tests／實跑範圍 |

## 一句話結論

說明它是否能取代 RootCause MCP、適合整合、或只適合學習概念。

## 它解決什麼問題

只寫由 upstream 程式碼或文件能支持的功能，不把 roadmap 當成已完成能力。

## 核心流程與資料邊界

說明輸入、狀態、主要處理、輸出，以及模型／deterministic code／人工審查的責任邊界。

## 最值得學習的設計

- 可移植的架構、schema、測試或安全模式。
- 為什麼適用於 RootCause MCP。
- 哪些部分需重新實作而非複製。

## 與 RootCause MCP 的關係

| 面向 | Upstream | RootCause MCP 的處理 |
|---|---|---|
| Evidence lineage |  |  |
| DDx／推理 |  |  |
| RCA／causation |  |  |
| Final conformance |  |  |
| Human review |  |  |

## 採用建議

使用 `採用／adapter／sidecar／概念借鑑／不採用` 其中一種明確決策，並說明：

1. 建議的整合邊界。
2. 必須 fail-closed 的條件。
3. 最小 contract tests。
4. 授權與維護風險。

### 基礎套件的引用與依賴方式

若屬基礎套件，至少記錄：

- 以 optional dependency、獨立 sidecar 或 protocol adapter 引用，避免複製原始碼。
- pin release/tag 與 lockfile；正式驗證再 pin commit／artifact digest。
- 在 `NOTICE`、SBOM 或 dependency inventory 記錄名稱、版本、URL、license。
- 論文與軟體要分開引用；優先採用 upstream `CITATION.cff`／DOI／Zenodo。

非基礎套件可將本節改為「概念引用方式」。

## 不應直接照搬的部分

- 無 LICENSE、非商業限制、資料 DUA、private corpus 或 roadmap-only 能力。
- LLM 自評、fuzzy provenance、未受信 trace 或把 audit 誤稱因果證明等風險。

## 建議引用

### 軟體引用

```text
<Author/Organization>. (<year>). <Repository name> (commit <SHA>) [Computer software]. GitHub. <URL>
```

### BibTeX fallback

```bibtex
@software{<key>,
  author  = {<author>},
  title   = {<title>},
  year    = {<year>},
  url     = {<url>},
  version = {<tag-or-commit>},
  note    = {Accessed YYYY-MM-DD}
}
```

若 upstream 提供正式論文／DOI，另列原始 BibTeX，不以 fallback 取代論文引用。

## 來源

- Upstream README
- LICENSE／CITATION／release
- 支持本文判斷的 schema、docs、tests 或 source files

## 查核限制

記錄是否只做文件／原始碼稽核、是否完成安裝或實跑，以及公開 GitHub 搜尋無法涵蓋私人或未索引專案。
