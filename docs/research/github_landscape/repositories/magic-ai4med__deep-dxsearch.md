# `MAGIC-AI4Med/Deep-DxSearch` 學習報告

> 本檔只記錄 upstream 文件與原始碼稽核，不代表臨床、安全或生產驗證。

## 查核資料

| 欄位 | 內容 |
|---|---|
| Upstream | [MAGIC-AI4Med/Deep-DxSearch](https://github.com/MAGIC-AI4Med/Deep-DxSearch) |
| 查核日期 | `2026-08-18` |
| 查核版本 | 預設分支 `main`；commit `57c62afcecf64cb61a6154c5d42caf55f409e7b7` |
| 專案角色 | 相鄰方案／診斷 RAG 訓練與 benchmark |
| 授權 | `Apache-2.0`；已直接讀取根目錄 LICENSE |
| 本次驗證 | README、完整 tree、訓練資料格式、MCP client、tool schema、評估入口；未安裝、未下載模型或資料、未實跑 |

## 一句話結論

不能取代 RootCause MCP；適合借鑑「檢索動作與診斷排序共同訓練」及 top-k benchmark，但不是具證據帳本、RCA 與 finalization gate 的臨床 MCP server。

## 它解決什麼問題

Upstream 以臨床表徵為輸入，讓 LLM 在 `reason／lookup／match／search／diagnose` 五種動作間選擇，聯合最佳化檢索時機與推理路徑。
README 提供模型、疾病—表徵 corpus、病例檢索資料與多資料集 top-1／top-5 評估；訓練資料把疾病標籤放在 `reward_model.ground_truth`。
程式中的 `MCPBaseTool` 是訓練 rollout 使用的 MCP client abstraction，會呼叫外部工具；它不是可供 RootCause agent 接入的臨床 MCP server。

## 核心流程與資料邊界

輸入為 phenotype/case vignette 或 parquet 訓練列；retriever 服務查 PubMed、Wikipedia、textbook 及相似病例，LLM／RL policy 決定下一個動作與最終診斷。
資料邊界跨本機訓練環境、獨立 retriever、SGLang summarizer、模型 checkpoint 與外部資料集；README 亦列出受 DUA 管制的 MIMIC-IV-note 與未公開院內資料。
輸出重點是診斷答案與 benchmark accuracy；未見 atomic source span、直接 evidence-to-DDx linkage、Why/Fishbone/HFACS、保守 causation status 或 immutable final snapshot。
`mcp_search_tool.py` 將外部文字結果再以 regex 擷取，不能視為可驗證來源 lineage。

## 最值得學習的設計

- 將「是否檢索、查哪一類資料、何時停止」建模成顯式動作，適合形成 RootCause 的 agent-in-loop eval 情境。
- 同時測 common／rare disease 與 top-1／top-5，可轉成不洩漏答案的 top-3 DDx rubric；仍須另測 must-not-miss、fabrication 與 workflow completion。
- 訓練列分開 `input`、`ground_truth` 與 `extra_info`，提醒 eval runner 僅向 agent 暴露 input，gold 留在隔離 grader。
- 需重新實作資料 lineage、certainty、clinical reviewer 與 conformance gate，不應複製其整套 GPU／retrieval stack。

## 與 RootCause MCP 的關係

| 面向 | Upstream | RootCause MCP 的處理 |
|---|---|---|
| Evidence lineage | 檢索結果與 phenotype/case DB；無逐項來源雜湊帳本 | exact snippet、location、source hash 與 event precision |
| DDx／推理 | RL policy、五動作、診斷 top-k | 至少三個 active DDx、支持／反證與 test disposition |
| RCA／causation | 未見醫療事件 RCA | Why／Fishbone／HFACS 與保守 causation validator |
| Final conformance | benchmark answer；未見 typed final report | nested report schema、`conformance_checks[]`、不可變 snapshot |
| Human review | 未見具名 reviewer gate | 授權且具資格的人類 reviewer 才能 finalize |

## 採用建議

**決策：概念借鑑。** 不把 Deep-DxSearch 加為 runtime dependency；以獨立研究 benchmark 重現其 action taxonomy 與 top-k 指標。
整合邊界僅允許去識別 vignette 與隔離 corpus；不得把 RootCause 原始 PHI、session database 或 reviewer 資料送入其 retriever／模型服務。
若輸入含 gold label、來源 DUA 未確認、檢索結果沒有可定位來源，或模型只回 final diagnosis，必須 fail-closed 並標為 eval invalid／unverified。
最小 contract tests：gold 欄位不進 prompt、每次 clean data root、固定 seed/config、保存 action/tool trace、top-3 與 must-not-miss rubric、檢索失敗不偽裝成功。
Apache-2.0 允許整合，但模型權重、Hugging Face corpus、MIMIC 與院內資料各有獨立條款；README 也明說 evaluation/reproduction code 持續更新，維護與重現風險高。

### 概念引用方式

在 design doc 引用 pinned repository 與論文，不 vendoring `verl`、資料或模型；若後續重現，另立隔離 project、pin container/model/dataset revision 與 artifact digest，並把各資料授權列入 SBOM／data inventory。

## 不應直接照搬的部分

- 不把 benchmark 的 `ground_truth` 或疾病清單帶入 production agent prompt。
- 不把模型生成的 reasoning trace、regex 解析結果或相似病例當成 verified clinical evidence。
- 不將 top-k accuracy 等同安全性，也不以強化學習 reward 取代 must-not-miss 與 qualified-human review。

## 建議引用

### 軟體引用

```text
MAGIC-AI4Med. (2026). Deep-DxSearch (commit 57c62afcecf64cb61a6154c5d42caf55f409e7b7) [Computer software]. GitHub. https://github.com/MAGIC-AI4Med/Deep-DxSearch
```

### BibTeX fallback

```bibtex
@software{magic2026deepdxsearch, author={MAGIC-AI4Med}, title={Deep-DxSearch}, year={2026}, url={https://github.com/MAGIC-AI4Med/Deep-DxSearch}, version={57c62afcecf64cb61a6154c5d42caf55f409e7b7}, note={Accessed 2026-08-18}}
```

### 論文引用（與軟體分開）

Zheng, Q. et al. (2025). *End-to-End Agentic RAG System Training for Traceable Diagnostic Reasoning*. arXiv:2508.15746. [原始論文](https://arxiv.org/abs/2508.15746)。

## 來源

- [README（pinned）](https://github.com/MAGIC-AI4Med/Deep-DxSearch/blob/57c62afcecf64cb61a6154c5d42caf55f409e7b7/README.md)；[LICENSE](https://github.com/MAGIC-AI4Med/Deep-DxSearch/blob/57c62afcecf64cb61a6154c5d42caf55f409e7b7/LICENSE)
- [MCP base client](https://github.com/MAGIC-AI4Med/Deep-DxSearch/blob/57c62afcecf64cb61a6154c5d42caf55f409e7b7/DeepDxSearch/src/verl/tools/mcp_base_tool.py)；[MCP search parser](https://github.com/MAGIC-AI4Med/Deep-DxSearch/blob/57c62afcecf64cb61a6154c5d42caf55f409e7b7/DeepDxSearch/src/verl/tools/mcp_search_tool.py)
- [完整 repository tree](https://github.com/MAGIC-AI4Med/Deep-DxSearch/tree/57c62afcecf64cb61a6154c5d42caf55f409e7b7)；[trainer evaluation entry](https://github.com/MAGIC-AI4Med/Deep-DxSearch/blob/57c62afcecf64cb61a6154c5d42caf55f409e7b7/DeepDxSearch/src/verl/trainer/main_eval.py)

## 查核限制

本次只做公開 GitHub 文件與原始碼稽核；沒有安裝、GPU 訓練、模型 inference、資料下載或 benchmark 重跑。公開搜尋亦無法涵蓋私人版本、未索引專案或院內資料。
