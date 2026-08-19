# RootCause MCP

> 讓任何相容 MCP 的通用 AI Agent 執行醫學推理、鑑別診斷與臨床根因分析的 Harness。

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![MCP SDK 2.0](https://img.shields.io/badge/MCP_SDK-2.0-green.svg)](https://modelcontextprotocol.io/)
[![Tools](https://img.shields.io/badge/MCP_tools-46_discrete_%2F_8_condensed-purple.svg)](#工具目錄)
[![Status](https://img.shields.io/badge/status-engineering_alpha-orange.svg)](#mvp-狀態)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

[English](README.md) | **繁體中文**

## 核心目標

RootCause MCP 讓 Claude Code、Codex、Cline、OpenCode、OpenClaw、Z.ai Agent 等
通用 Agent 執行下列專門工作流：

1. 由宿主 Agent 盤點並擷取已去識別的臨床文件。
2. 登錄有來源定位與字面引文（raw snippet）的結構化證據、保留 source-faithful time，
   並追加經授權的來源／去識別／independence 審閱。
3. 先依 phenotype 與 time course 建立最大合理的 mechanism-based DDx，再用 direct
   明確選定 working lead；只有另一筆 verified `LITERATURE` record 能證明定量校準時，
   才可用 direct likelihood ratio 關聯 source-linked evidence。
4. 將 unknown 當作推理輸入，逐候選記錄 why considered、支持／反證／neutral
   evidence、discriminating test、qualitative certainty 與偏差。
5. 串接魚骨圖與 5-Why、逐項取得 authorized HFACS-MES disposition，再執行保守的
   因果 proof-obligation 稽核。
6. 產生 typed、機器可讀，且具有明確來源血緣與 deterministic conformance
   結果的報告。

**真正進行推理的是 Agent。** MCP Server 不會讀取模型隱藏狀態，也不會擷取私密的原始
chain-of-thought。它提供 schema、流程約束、計算、持久化與稽核記錄，保存 Agent
主動外顯的結構化推理理由。

醫師版產物可由 built-in Markdown renderer 產生繁體中文說明，但 diagnosis、test、drug、
device、procedure 等 canonical 名稱保留 English；原始引文、單位、ID、code、JSON/FHIR
values 與 custom template 語言都不做 machine translation。

> 本專案不是醫療器材，不可自主診斷或治療病人。臨床使用必須由合格人員審查，並配合
> 在地治理、隱私保護、來源文件核驗與機構安全控制。

## MVP 狀態

Deterministic final-report boundary 已實作：nested report sections 有 typed schema、
每份報告都帶有機器可讀的 `conformance_checks[]`，而來源、DDx、root lineage、
causation disposition、reviewer 或完整性不安全時，finalization 會被阻擋。Final
snapshot 同時保存 reviewer、含時區時間與可重算的 SHA-256，並遞迴拒絕 nested
mutation。

DDx breadth 不再只由數量推測：Agent 必須選 syndrome-appropriate framework、審查每個
canonical cell，並保存 PRIMARY breadth audit。`REVIEWED_INSUFFICIENT_DATA` 要保留 unknowns
與 typed discriminators；`NOT_ASSESSED` 會阻擋 finalization。這個 audit 證明有做系統性
coverage review，不證明臨床判斷正確。

Final conformance 會攜帶完整 append-only source-review ledger，並由它重算 final inventory
projection／independence lineage；同時檢查明確的 leading diagnosis selection、
source-calibrated LR links、source-faithful temporal semantics、逐 cause HFACS review、
guidance/readiness facts、gap counts，以及 Why/root/causation lineage。`date`、
`range`、`relative` 與 `unknown` time 可合法保留在 final artifact，但不可被暗中排序或拿來
證明 temporality。

**2.0.0a3（2026-08-19）**目前仍是 **engineering alpha**，不是已完成臨床驗證的
Agent MVP。公開六案例與
runner 只作 engineering reference。正式結果至少需要 3 個真實 Agent runtimes × 6
cases × 2 repeats、repo 外的 private case bundles、分離保護的 private holdout gold、
filesystem isolation、可信的 runtime/server MCP trace，以及每個 job 都由兩名
qualified clinical reviewers 盲評並裁決分歧。目前狀態是
`AGENT_EVAL_NOT_ESTABLISHED`。詳見
[MVP conformance 與 Agent 評估](docs/mvp_conformance_and_evaluation.md)。

## Harness 如何節省工作

通用 Agent 當然可以在一個超長 prompt 中讀完所有文件並撰寫報告，但每次都會重複消耗
context 來載入 tool schemas、重述既有事實、排版、計算機率、畫圖、跑完整性清單及撰寫
報告。RootCause MCP 把可重複部分移到 deterministic code，臨床判斷仍由 Agent 負責。

| 工作 | 只有 Agent | RootCause MCP 自動化 |
| --- | --- | --- |
| Tool context | 載入所有 schemas | `clinical` / `rca` profiles 只曝光相關工具 |
| Tool results | 重讀重複的 text 與 JSON | 完整 SDK 2.0 `structuredContent` 加精簡 text fallback |
| 定量證據連結 | 重算並重新敘述 | 只對 source-calibrated direct LR 做 compatibility arithmetic；否則保留 neutral qualitative link |
| 個案延續 | 重新注入先前對話 | aggregate 持久化與重啟還原 |
| 報告組裝 | 重寫 DD、證據、缺口、指標與圖 | deterministic `brief` / `standard` / `full` Markdown |
| 品質檢查 | 靠 Agent 記住清單 | 自動產生結構與可追溯性 warnings |

![Token-efficient medical reasoning](docs/architecture/token_efficient_reasoning.svg)

Tokenizer-independent regression fixtures 會比較 tool-profile schema bytes、重複的
text fallback 與 deterministic report generation；schema 改動會改變量測，因此應以
當次 CI artifacts 為準。這些 byte proxy 不是特定模型 tokenizer 的保證。Agent 仍須
閱讀來源 extracts、產生合理臨床假設、選擇可辯護的 evidence relationship，並由合格人員
審查最終產物。非中性 LR 必須連到另一筆 verified `LITERATURE` calibration record；
未校準的 prior/posterior 不得呈現為 clinical probability 或 certainty；
`LR=1.0` 只表示 neutral／quantitatively unknown，不計為支持或反證。

## 輕量 (Flash) 模型的自我校正多輪導引

輕量或速度優先的 Flash/mini 模型在複雜臨床個案常見的失敗模式是：**提早下結論 (premature diagnostic closure)、只提出單一假設、忽略否定性排除測試、漏掉不確定性與認知偏差審查**。

RootCause MCP 透過**確定性推理狀態機 (Reasoning State Machine)** 來約束與賦能：

- 每次核心工具呼叫均回傳結構化 `guidance` 評估個案狀態。
- **階段進程追蹤**：自動識別 `EVIDENCE_COLLECTION` → `DIFFERENTIAL_EXPANSION` → `BAYESIAN_EVALUATION` → `COGNITIVE_AUDIT` → `READY_FOR_SYNTHESIS`。
- **臨床完備檢查清單**：要求證據內容已核驗、candidate labels 已 typed、至少 3 個
  不重複診斷且涵蓋 2 個非 `UNKNOWN` mechanisms、適用的 must-not-miss、每個 active
  診斷的 evidence/test disposition，以及 leading／must-not-miss 的支持加反證或 typed
  rule-out plan，並完成不確定性與偏差審查。這些是 deterministic finalization floors，
  不是臨床廣度的目標或上限。
- **下一步 Prompt 指令**：在工具回傳中直接給出 `next_recommended_actions` 與蘇格拉底式臨床詰問 `push_questions`，讓 Flash 模型在多輪迴圈中自然步步推進直到完成。
- **主動稽核工具**：Agent 或外部 orchestrator 可呼叫
  `rc_audit_differential_breadth` 保存 framework every-cell coverage，並隨時呼叫
  `rc_audit_reasoning_state` 檢查報告生成前尚缺的要件。

## 確定性證據溯源與資料血緣 (Deterministic Provenance)

借鑑大型資料整合與 ETL 血緣架構（如 Airbyte 的 source/stream/lineage 驗證概念），RootCause MCP 建立確定性、無幻覺的證據溯源契約：

- **逐字引文與密碼學錨定**：每筆 Evidence 包含 `raw_snippet`（原始病歷字面引文）、檔案路徑、行號定位與 SHA-256 雜湊摘要。
- **確定性實體驗證**：`ProvenanceVerifier` 領域服務直接掃描磁碟上的原始病歷檔案（TXT、CSV、HL7、XML），比對字面引文並計算行號與雜湊，完全不使用神經網路或 LLM。
- **竄改與幻覺偵測**：若 Agent 捏造引文、來源不可用，或實際 bytes 不再符合 pinned manifest，伺服器會維持未驗證狀態並回傳 audit diagnostics。
- **Append-only 來源審閱**：pinned manifest 與 digest 永遠不變；extraction、
  de-identification 與 independent/derived lineage 只能透過
  `rc_adjudicate_source` 推進。每份 final source 都要有 allowlisted reviewer、時間、
  理由與 stable adjudication ID。
- **清晰架構邊界**：RootCause MCP 專注於推理契約與血緣檢查，不負責批次
  解析 raw PDF、DOCX、影像、掃描、試算表或 EHR export。

Host Agent 或經核准的 extractor 必須產生 citation-ready text/cells，並保留原文、
來源位置、hash、單位、否定詞、時間精度、OCR 修正與 extraction method。只可將
structured atomic findings 送進 RootCause MCP；binary 或 inaccessible source 不得宣稱
已由 MCP 驗證。

## 臨床協議資源、範本與麻醉專科 4-Tier 倒推因果

YAML 協議與次專科 playbook 會以有版本、non-normative 的 retrospective DDx resources
曝露，bundled agent
harness 也會要求 Agent 讀取；Markdown 範本則直接控制 deterministic renderer。
目前 readiness threshold 與 gap rules 仍由 Python 實作，**只修改 YAML 並不會自動改變
runtime gate**。這些 playbook 只提示回溯性 mechanism review，不提供 active-care
management、treatment/rescue instruction 或 patient-specific dose。

- **可編輯 SOP 與次專科手冊 (`config/protocols/`, `config/domains/`)**：
  - `anesthesia_mm_rca_protocol.yaml`：麻醉專科 4-Tier 倒推因果架構（Tier 0 終末心律 → Tier 1 ACLS 5H5T → Tier 2 術中三方觸發流 [病人初始狀況 vs 外科處置干擾 vs 麻醉用藥通氣] → Tier 3 系統潛在漏洞）。
  - `perioperative_shock.yaml` 與 `toxicology_sedation.yaml`：用於考慮 Dynamic LVOT
    Obstruction (SAM) 與 Propofol Infusion Syndrome (PRIS) 的 non-normative 回溯性 DDx
    prompts，不是 active-care protocol。
- **純文字可覆寫 Markdown 報告範本 (`config/templates/`)**：
  - `anesthesia_mm_rca_report_template.md`：麻醉部 M&M 併發症與死亡病例討會專用結構化報告。
  - `clinical_reasoning_report_template.md`：通用臨床決策輔助與病安行動計畫報告。

## 架構

```mermaid
graph TB
    A[通用 AI Agent] -->|MCP SDK 2.0| T[8 Facade 或 25 / 24 / 46 個離散工具]
    D[臨床文件] --> A

    subgraph Harness
        T --> S[ServerState / 個案 Aggregate]
        S --> O[ClinicalReasoningOrchestrator]
        O --> E[Evidence + Provenance + 雜湊]
        O --> H[Hypotheses + Bayesian Updates]
        O --> R[ReasoningChain]
        O --> G[Clinical Guidance Engine]
        S --> C[ThinkingChain：外顯理由記錄]
    end

    E --> DB[(SQLite / SQLModel)]
    H --> DB
    R --> DB
    C --> DB

    S --> CR[CONTRACT Report]
    CR --> J[JSON]
    CR --> F[FHIR-compatible DiagnosticReport]
    CR --> M[Deterministic Markdown]

    T --> RCA[Fishbone / 5-Why / HFACS-MES / 保守因果稽核]
```

![醫學推理 Harness 架構](docs/architecture/medical_reasoning_harness.svg)

DDD 依賴方向：

```text
Interface -> Application -> Domain <- Infrastructure
```

## 持久化範圍

SDK 2.0 Server 會將醫學推理 Aggregate 寫入 SQLite：

- 結構化 Evidence、字面引文與來源 metadata
- 鑑別診斷 Hypothesis 與 Bayesian update history
- Agent 明確提交的 ThinkingStep
- Orchestrator 自動建立的 ReasoningStep
- RCA Session、來源 manifest、Fishbone 與 Why Tree

Authentication、靜態加密、多租戶隔離、reviewer role 授權、資料庫 migration 與法規
部署控制，仍須由部署環境補齊，才能用於臨床 production。詳見
[PHI 與臨床資料政策](docs/PHI_DATA_POLICY.md)。

## 快速開始與自動化安裝

### 🚀 一鍵快速自動安裝

你可以透過一鍵腳本自動偵測 `uv`、同步虛擬環境、註冊客戶端 MCP harness 設定（Copilot 原生 `.mcp.json`、VS Code `.vscode/mcp.json`、Claude Desktop、Cline），並自動執行 production stdio 自檢：

**Windows PowerShell：**

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
```

**Linux / macOS / WSL：**

```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

> MCP command 會在實際的 Agent／extension host 執行。若 VS Code 使用 WSL、SSH、
> Dev Container 或其他 Remote host，必須在該 remote integrated terminal 內安裝
> `uv` 並執行 `scripts/setup.sh`；只在本機 Windows 執行 `setup.ps1` 不會替遠端安裝
> `uv`。完成後請執行 **Developer: Reload Window**。

**通用 Python CLI 安裝器：**

```powershell
uv run --locked python scripts/install.py --profile all --target all
uv run --locked python scripts/mcp_doctor.py --config all
```

### 🔬 合成案例 Scripted Regression

執行六個 bundled synthetic scenarios（SAM、PRIS、大量輸血高血鉀、術後 PE、LVAD
suction 與延遲診斷）。此腳本是開發 regression/demo，不取代 native manifest／finalization
驗收測試，也不代表臨床驗證：

```powershell
uv run python scripts/run_case_trial.py --case all
```

### Agent 評估 Scaffold

公開 corpus 的 dry-run 只檢查 runner／artifact mechanics，且刻意維持
`AGENT_EVAL_NOT_ESTABLISHED`：

```bash
eval_output="$(mktemp -d)"
uv run python scripts/run_agent_eval.py dry-run \
  --output-root "$eval_output" \
  --repeats 2
```

Formal run 必須使用 repo 外 private cases 與分離保護的 private gold，並先執行
fail-closed preflight：

```bash
uv run python scripts/run_agent_eval.py \
  --preflight \
  --matrix /secure/adapter-matrix.json \
  --corpus-file /secure/private-corpus/corpus.json \
  --gold-dir /secure/private-holdout \
  --attest-holdout-isolation \
  --authorize-provider-egress
```

正式執行前請閱讀[評估規範](docs/mvp_conformance_and_evaluation.md)。Egress
authorization 只適用於經核准、已去識別的 synthetic inputs，絕不授權真實病歷或
PHI。

### 🛠️ 手動安裝與啟動

```powershell
# 安裝 lockfile 定義的環境
uv sync --locked --all-extras

# 啟動 MCP SDK 2.0 stdio server
uv run --locked rootcause-mcp
```

Copilot CLI／Agent Host 直接讀取 repo 根目錄的 `.mcp.json`：

```json
{
  "mcpServers": {
    "rootcauseMcp": {
      "type": "local",
      "command": "uv",
      "args": ["run", "--locked", "rootcause-mcp"],
      "cwd": ".",
      "env": {
        "ROOTCAUSE_TOOL_PROFILE": "all",
        "ROOTCAUSE_RESPONSE_MODE": "compact"
      },
      "tools": ["*"]
    }
  }
}
```

VS Code editor 使用 `.vscode/mcp.json`，並將設定轉交給執行中的 Agent Host：

```json
{
  "servers": {
    "rootcauseMcp": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "run",
        "--locked",
        "--directory",
        "${workspaceFolder}",
        "rootcause-mcp"
      ],
      "cwd": "${workspaceFolder}",
      "env": {
        "ROOTCAUSE_TOOL_PROFILE": "all",
        "ROOTCAUSE_RESPONSE_MODE": "compact"
      }
    }
  }
}
```

兩份設定刻意使用相同 server key `rootcauseMcp`，避免 Agent Host 建立重複的 MCP
identity。共享設定只寫 PATH-resolved `uv`，不得寫入 `C:\...\uv.exe`、
`ROOTCAUSE_DATA_DIR` 或 `ROOTCAUSE_AUTHORIZED_REVIEWERS`；後兩者應由受控的 host
環境提供。其他產品的 MCP server 請放在 VS Code user／remote-user config，不要把
個人 executable 或資料路徑提交到這個 repo。

### Copilot Remote `spawn ... uv.EXE ENOENT`

這表示實際 execution host 找不到設定中的 executable；在 WSL／SSH／container 的
Remote extension host，常見原因是誤用了 Windows 本機的 absolute path。請在 VS
Code 的 remote terminal 執行：

```bash
uv --version
uv sync --locked --all-extras
uv run --locked python scripts/install.py --profile all --target all \
  --skip-tests --skip-trial
uv run --locked python scripts/mcp_doctor.py --config all
```

Doctor 應同時顯示兩份 config 與 stdio 的 `PASS`。接著執行 **Developer: Reload
Window**，再以 **MCP: List Servers** 重新啟動 `rootcauseMcp`；工具 catalog 更新時可
執行 **MCP: Reset Cached Tools**。格式依據：[VS Code MCP configuration
reference](https://code.visualstudio.com/docs/agents/reference/mcp-configuration) 與
[GitHub Copilot CLI MCP
configuration](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-mcp-servers)。

環境變數：

| 變數 | 用途 | 預設值 |
| --- | --- | --- |
| `ROOTCAUSE_DATA_DIR` | SQLite、checkpoint、learned rules 與匯出產物根目錄 | OS user-data 目錄 |
| `ROOTCAUSE_CONFIG_DIR` | 可選的 `hfacs/`、`domains/`、`protocols/`、`templates/` 設定覆寫 | 套件內 `rootcause_mcp/config` |
| `ROOTCAUSE_SOURCE_ROOTS` | exact plain-text provenance 可讀取根目錄（依 OS path separator 分隔） | 目前工作目錄 |
| `ROOTCAUSE_AUTHORIZED_REVIEWERS` | 可人工核驗、裁決 source／HFACS 或 finalize 的 operator-controlled reviewer 清單 | 空值（人工審閱／最終核准停用） |
| `ROOTCAUSE_TOOL_PROFILE` | 工具目錄：`condensed` (8 個 Facade 工具)、`clinical` (25)、`rca` (24) 或 `all` (46) | `all` |
| `ROOTCAUSE_RESPONSE_MODE` | `compact` structured fallback 或 `verbose` JSON text | `compact` |

## Agent 工作流

相容 Agent 可以使用細粒度 Discrete 工具工作流，或是超精簡的 8-Facade 工具工作流：

### 細粒度工具工作流 (Discrete Tool Workflow)

```text
rc_start_session(source_manifest={...})
  -> rc_add_evidence(source_document=..., raw_snippet=..., temporal={...})
  -> rc_adjudicate_source  # 每份 manifest source 的授權 append-only review
  -> rc_think_aloud / rc_identify_gaps / rc_challenge_assumption
  -> rc_propose_hypothesis(diagnosis=..., clinical_reasoning=..., planned_tests=[...])
  -> rc_audit_differential_breadth(audit={...})
  -> rc_link_evidence_to_hypothesis(evidence_id=..., hypothesis_id=...,
                                     likelihood_ratio=..., calibration_status=...,
                                     calibration_source_ref=...)
  -> rc_select_leading_hypothesis(reason=..., changed_by=...)
  -> rc_get_differential_diagnosis
  -> rc_audit_reasoning_state
  -> rc_detect_conflicts
  -> rc_create_checkpoint
  -> rc_init_fishbone / rc_add_cause / rc_confirm_classification
  -> rc_ask_why / rc_mark_root_cause
  -> rc_verify_causation  # 保守稽核，不是臨床因果證明
  -> rc_generate_contract_report(format="markdown", detail_level="standard",
                                  locale="zh-TW", audience="clinician", finalize=false)
```

### 超精簡 Facade 工具工作流 (8 Tools Profile)

```text
rc_rca(action="session_start")
  -> rc_evidence(action="add")
  -> rc_rca(action="session_adjudicate_source")
  -> rc_thinking(action="think" / "gap" / "challenge" / "reflect")
  -> rc_hypothesis(action="propose" / "audit_breadth" / "link" / "select_leading" / "rank")
  -> rc_audit(action="stage_guidance" / "detect_conflicts")
  -> rc_checkpoint(action="create")
  -> rc_diagram(action="timeline" / "validate")
  -> rc_report(action="preview")
```

`rc_propose_hypothesis`（或 `rc_hypothesis(action="propose")`）會記錄
`mechanism_category`、`diagnostic_role`、`reasoning_basis`、qualitative `certainty`、
臨床理由、替代診斷、candidate-specific unknowns 與 typed planned tests。應展開最大合理的
不同 mechanisms；三個診斷只是 finalization floor，不是推理目標或上限。這些是 Agent
主動撰寫的可稽核記錄，不是模型隱藏思考的 dump。

Built-in renderer 使用 `locale="zh-TW"` 與 `audience="clinician"` 時，會產生繁體中文
臨床討論，保留 English canonical medical names，並展開候選層級的 evidence／unknown／
test。Custom template 保留自身語言；JSON 與 FHIR data 不翻譯。

完整 payload 範例請見 [Agent 整合指南](docs/agent_integration_guide.md)。

## MCP SDK 2.0 進階功能

RootCause MCP 深度整合 MCP SDK 2.0 完整原生功能，提供極致的 Agent 體驗：

### 1. 🧰 工具濃縮與 Facade 架構 (8 Unified Facade Tools)

當設定 `ROOTCAUSE_TOOL_PROFILE=condensed` 時，伺服器把曝光面濃縮為 **8 個多型 Facade
工具**，降低 discovery/schema overhead。少數管理操作仍只有離散工具；bundled harness
提供精確對照，並要求沿用同一 session 交接到適當 profile，不得靜默略過：

- `rc_evidence`: 登錄、查詢或物理檢驗病歷引文血緣。
- `rc_hypothesis`: 提出候選、稽核 framework breadth、連結證據、明確選定 leading、檢視或排除假設。
- `rc_thinking`: 記錄外顯臨床理由、反思認知偏差、標記數據缺口或挑戰既有假設。
- `rc_audit`: 查詢多迴圈導引、稽核完備性清單、或偵測臨床矛盾與指引遺漏。
- `rc_report`: 產生確定性 Contract 報告或匯出稽核產物。
- `rc_diagram`: 渲染時序圖、稽核修復 Mermaid 語法、或匯出圖表。
- `rc_checkpoint`: 建立、檢視或還原具完整性檢查的案例狀態快照。
- `rc_rca`: 路由 session／來源審閱、6M 魚骨圖、5-Why 與 HFACS-MES 工作流。

### 2. 📚 MCP 靜態與動態資源 (Resources)

無須消耗 Tool Call 即可即時讀取專業臨床協議與案例狀態：

- **靜態協議與範本 URI**（2.0.0a3 快照共 19 個 resources）：
  - `clinical://contracts/case-input-manifest`: canonical 多來源交接 schema。
  - `clinical://contracts/case-analysis-report`: canonical 標準化輸出 schema。
  - `clinical://protocols/anesthesia-mm-rca-protocol`: 麻醉專科 4-Tier 倒推因果推理 SOP。
  - `clinical://protocols/clinical-reasoning-sop`: 臨床鑑別診斷標準作業流程。
  - `clinical://protocols/non-death-adverse-event-protocol`: Near-miss 與 adverse-event 屏障分析 protocol。
  - `clinical://protocols/timeline-patterns`: 保留來源時間精度的 temporal-pattern 定義。
  - `clinical://templates/anesthesia-mm-rca-report-template`: Markdown 報告範本。
  - `clinical://templates/clinical-reasoning-report-template`: 通用 clinical reasoning 報告範本。
  - `clinical://templates/clinician-ddx-discussion-zh-tw`: 醫師版繁體中文 DDx 討論範本。
  - `clinical://templates/near-miss-adverse-event-rca-template`: 瑞士乳酪與屏障失效範本。
  - `clinical://domains/*`: 9 個 non-normative retrospective DDx playbooks：
    `anaphylaxis-crisis`, `anesthesia-perioperative-arrest`,
    `delayed-diagnosis-systems`, `difficult-airway-crisis`,
    `local-anesthetic-toxicity`, `lvad-mechanical-crisis`, `pediatric-opioid`,
    `perioperative-shock`, `toxicology-sedation`。
- **動態案例資源範本 (Resource Templates)**（2.0.0a3 快照共 4 個）：
  - `clinical://sessions/{session_id}/report`: 即時渲染的案例報告。
  - `clinical://sessions/{session_id}/timeline`: 即時臨床事件時序圖。
  - `clinical://sessions/{session_id}/guidance`: 即時推理階段、檢查清單與蘇格拉底詰問。
  - `clinical://sessions/{session_id}/conflicts`: 即時診斷矛盾、藥物反常反應與指引遺漏報告。

### 3. 🎯 MCP 預設臨床 Prompts（5 個）

支援在 Claude Desktop、VS Code、Cline 等客戶端一鍵發起專業臨床調查：

- `anesthesia_mm_investigation`: 麻醉專科 4-Tier 倒推因果 M&M 調查。
- `perioperative_crisis_differential`: 圍術期危機 5H5T 鑑別診斷擴展。
- `near_miss_barrier_analysis`: 瑞士乳酪非死亡不良事件屏障分析。
- `delayed_diagnosis_investigation`: 診斷延遲軌跡與認知偏差調查。
- `clinician_ddx_discussion_zh_tw`: 通用醫師版繁中 DDx 討論，要求最大合理
  mechanism breadth、explicit unknown、source-linked 支持／反證／neutral evidence、
  discriminating tests 與 qualitative certainty。

### 4. 🧠 伺服器級系統指令 (Server Instructions & Meta-Prompt)

在 MCP 連線握手時自動注入系統級 Meta-Prompt，確保任何連接的 AI Agent 自動遵守嚴格證據溯源、4-Tier 倒推因果、否定性假設檢驗與認知透明度。

## 工具目錄

| 類別 | 數量 | 用途 |
| --- | ---: | --- |
| 認知透明度 | 5 | 外顯理由、反思、缺口、假設挑戰與 ThinkingChain |
| Evidence 與溯源 | 3 | 新增、查詢與字面引文物理驗證結構化證據 (SHA-256 雜湊) |
| 鑑別診斷 | 6 | 提出、稽核 framework breadth、連結證據、明確選定 leading、檢視與排除 Hypothesis |
| Reasoning Chain 與導引 | 3 | 查詢行動鏈、匯出圖表、以及稽核推理完備性 |
| 缺口分析與衝突偵測 | 1 | 偵測診斷矛盾、藥物反常惡化反應與指引監測遺漏 |
| 案例快照 Checkpointing | 3 | 建立、檢視與還原具完整性檢查的 JSON 狀態快照 |
| CONTRACT Report | 1 | 產生 preliminary 或 gated-final JSON、FHIR-compatible 或 deterministic Markdown 報告 |
| HFACS-MES 分類法 | 6 | 建議、確認、檢視、學習、重載與分類對照 |
| Session 管理 | 5 | 建立、追加來源審閱裁決、查詢、列出與封存 RCA Session (SQLite 持久化) |
| Fishbone (Ishikawa 6M) | 4 | 初始化、新增原因、檢視與匯出 |
| Why Tree (5-Why 分析) | 6 | 追問、檢視、跨鏈接、標記根因、匯出與教學案例 (SQLite 持久化) |
| 驗證與圖表工具 | 3 | 保守的反事實因果檢核、Mermaid 語法稽核器與時序圖渲染器 |
| **總計 (Discrete)** | **46** | 提供 46 個離散工具（臨床 Profile 25 個、RCA Profile 24 個、All 46 個，或 `condensed` Profile **8 個 Facade 工具**） |

## 圖表輸出

| 產物 | 機器可讀輸出 | 圖表輸出 |
| --- | --- | --- |
| Fishbone | JSON | Mermaid 6M Ishikawa 版型，包含主脊、原因與次因 |
| Why Tree | JSON | Mermaid 階層圖，包含根因與跨因果連結 |
| Reasoning Chain | JSON | Mermaid 有序稽核鏈，包含 evidence/hypothesis 參照 |
| Evidence Graph | CONTRACT JSON `nodes` / `edges` | 內嵌 Mermaid 支持／反對關係圖 |
| Event Timeline | JSON `events` / Markdown 表格 | 內嵌 Mermaid `timeline` 時序圖（臨床分期與時間標記） |

## 品質閘門

Repository 與 CI 定義下列 engineering gates：

```powershell
uv run pytest -W error::ResourceWarning
uv run ruff check .
uv run ruff format --check .
uv run mypy src --ignore-missing-imports
uv run bandit -c pyproject.toml -r src --severity-level low --confidence-level medium
uv run vulture src tests --min-confidence 80
uv export --frozen --no-dev --no-emit-project --no-hashes --quiet --output-file requirements-audit.txt
uvx --from "pip-audit==2.9.0" pip-audit --strict --requirement requirements-audit.txt
uv build
uvx --from "twine==6.2.0" twine check dist/*
```

測試數、coverage、安全掃描與 packaging 結果應以當次 CI 與 release artifacts 為
準。這些 engineering gates 驗證軟體行為，不代表 Agent 臨床表現或 clinical
validity 已建立。

## 專案結構

```text
src/rootcause_mcp/
├── domain/          # Entity、Value Object、Repository Contract、Domain Service
├── application/     # Case Aggregate、Orchestrator、進度引導
├── infrastructure/  # SQLModel Repository、安全匯出路徑
├── interface/       # MCP Tool Schema、Handler、以及 Presenters
└── server_v2.py     # 唯一 MCP SDK 2.0 入口
```

## 文件

- [繁中／英文文件網站](https://u9401066.github.io/rootcause-mcp/)
- [架構文件](ARCHITECTURE.md)
- [深度推理架構](docs/architecture/deep_reasoning_architecture.md)
- [MCP API 參考](docs/api.md)
- [Agent 整合指南](docs/agent_integration_guide.md)
- [MVP conformance 與 Agent 評估](docs/mvp_conformance_and_evaluation.md)
- [RootCause Agent Harness](.codex/skills/rootcause-clinical-reasoning-harness/SKILL.md)
- [PHI 與臨床資料政策](docs/PHI_DATA_POLICY.md)
- [公開方案研究](docs/research/existing_solutions.md)
- [GitHub landscape：逐 repo 學習與引用報告](docs/research/github_landscape/README.md)
- [Roadmap](ROADMAP.md)
- [Changelog](CHANGELOG.md)

## 研究與引用

設計參考公開的臨床推理、RCA、FHIR、provenance、因果推論與 Agent evaluation
研究及專案。[研究總覽](docs/research/existing_solutions.md)說明產品邊界；
[逐 repo 報告](docs/research/github_landscape/README.md)則記錄可學設計、基礎套件的
整合與引用方式，以及禁止直接重用的授權或資料使用限制。

## 授權

Apache License 2.0，詳見 [LICENSE](LICENSE)。
