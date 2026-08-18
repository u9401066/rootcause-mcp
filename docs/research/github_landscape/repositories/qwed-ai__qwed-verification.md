# `QWED-AI/qwed-verification` 學習報告

> 本檔只記錄固定版本的文件與原始碼稽核，不代表 QWED 已通過臨床、安全或生產驗證。

## 查核資料

| 欄位 | 內容 |
|---|---|
| Upstream | [QWED-AI/qwed-verification](https://github.com/QWED-AI/qwed-verification) |
| 查核日期 | `2026-08-18` |
| 查核版本 | 預設分支 `main`，commit `4f0f4f05f2998889aed386e34f6a14e469d1ef2d`；`pyproject.toml` 為 `7.1.0` |
| 專案角色 | 基礎套件／deterministic verification 與 policy sidecar |
| 授權 | Apache-2.0；已直接讀取該 commit 的 `LICENSE` |
| 本次驗證 | 查 README、完整 tree、VC v1.0 spec/schema、ADR-001..005、pyproject、CITATION、Verification Context／attestation tests；**未安裝、未實跑** |

## 一句話結論

QWED 的 truth/admission 分離、fail-closed schema 與 content-bound `proof_ref` 值得做 sidecar POC，但它驗證形式化物件，不會驗證自然語言意圖，更不能取代 RootCause 的 clinical cross-object invariants。

## 它解決什麼問題

QWED 對 math、logic、SQL、code、schema、stats 等支援 domain 做 deterministic discharge，統一回傳 `DiagnosticResult`，再顯式轉成 Verification Context（VC）v1.0。

VC schema 把 object、interpretation、proof、evidence 與 decision 分層，truth verdict 為 `VERIFIED/UNVERIFIABLE/BLOCKED`，admission 為 `ADMIT/DENY`；unknown、timeout、error 不得升格 VERIFIED。

`proof_ref` 是對 canonical payload 的 `sha256:` commitment，確保被綁 evidence 的完整性／可重算；schema 自己明示它不是數學 proof。形式化來源 query 到 formal statement 的翻譯一律 `verified: false`。

## 核心流程與資料邊界

不受信 LLM 可把自然語言轉成 formal statement，SymPy／Z3／AST／SQLGlot 等 verifier 只對該 formal object discharge，接著 policy 依 admission 決定是否可執行。ADR-004 明示「正確證明錯問題」仍可能發生，需人確認 formalization。

ADR-005 又明示現階段是 self-attestation、root of trust 仍為 proposed/open question；多 replica 各自 ephemeral key 的 topology 甚至不受支援。簽章只驗 canonical bytes 相對於 configured key，不增加 proof strength 或建立獨立信任。

## 最值得學習的設計

- Truth verdict 與 safe-to-run admission 分離，避免「成功執行」或「證明不安全」被錯讀為允許。
- JSON Schema 以 conditional invariants 強制 VERIFIED 必有 hash、UNVERIFIABLE/BLOCKED 必須 DENY 且 hash 為 null。
- RFC 8785 canonical encoding、verifier/version/configuration 與 trusted dependencies 可支援重算。
- Formalization 明列在 trust boundary 外，是套用到臨床自然語言時必要的誠實限制。
- RootCause 可借其 Verification Context envelope；clinical object consistency 仍由本專案 typed validator 實作。

## 與 RootCause MCP 的關係

| 面向 | Upstream | RootCause MCP 的處理 |
|---|---|---|
| Evidence lineage | `proof_ref` 綁 formal statement/context evidence；不知原始病歷 source span | source manifest、snippet/location/hash/time 與跨物件引用 |
| DDx／推理 | 不驗證 diagnosis ranking、must-not-miss 或 evidence disposition | 至少三 DDx 與 supporting/disconfirming/planned test invariants |
| RCA／causation | solver 可驗形式規則，不證明臨床 causation | causation validator 僅保守稽核 root/Why/evidence consistency |
| Final conformance | VC v1 schema／admission，可承載單一形式化驗證 | 完整 nested clinical report、`conformance_checks[]`、final snapshot hash |
| Human review | formalization需人確認，未提供 qualified clinician workflow | reviewer allowlist、角色／時間、盲評與 adjudication |

## 採用建議

**決策：sidecar。** 先用 protocol adapter 把 RootCause deterministic check 的 formal object／evidence digest 映成 VC，QWED 只處理其原生支援 domain；finalization 最終權限留在 RootCause。

1. 整合邊界：獨立本機 sidecar，僅接去識別、最小化的 formal payload；不讓 QWED 翻譯 raw clinical narrative 或直接 mutation case store。
2. Fail-closed：formalization 未確認、verifier unsupported/unknown/error、VC schema/hash mismatch、root key 不可信或 admission 非 ADMIT 時禁止 finalization。
3. Contract tests：VERIFIED/hash、UNVERIFIABLE/DENY、tamper、wrong formalization、version/config drift、RootCause cross-object violation 即使 QWED ADMIT 仍必須被 RootCause 擋下。
4. 風險：Apache-2.0 可採，但 base package依賴廣、beta且 v7.0 有 breaking status semantics；self-attestation trust root 未完成。README DOI/version、`docs/CITATION.cff`（v1.0.1）與 pyproject v7.1.0 有 metadata drift，需 maintainer 確認。

### 基礎套件的引用與依賴方式

- 優先獨立 sidecar／protocol adapter；若只用 schema，可 vendor-free 讀取 pin 的 normative schema，不把整包 broad dependencies 加進 clinical runtime。
- pin release、lockfile、container digest、VC spec與 verifier versions；正式驗證再 pin commit／artifact digest。
- 在 `NOTICE`、SBOM／dependency inventory 記錄 QWED、Apache-2.0、版本、URL 與 transitive solvers。
- QWED `proof_ref` 不取代 RootCause 對 input manifest、JSON、Markdown、review metadata 與 final snapshot 的完整 hash。

## 不應直接照搬的部分

- 不把自然語言→formal statement 當已驗證，也不把 solver verdict 外推成 clinical truth／causation。
- 不把 self-signature 當獨立 attestation；未建立外部 trust anchor 前不得宣稱第三方可驗證。
- 不以 QWED schema verifier 取代 root ID/description/evidence、Why ledger、DDx/must-not-miss 與 immutable-final invariants。

## 建議引用

### 軟體引用

```text
Dass, Rahul. (2025). QWED Protocol: Deterministic Verification for Large Language Models (commit 4f0f4f05f2998889aed386e34f6a14e469d1ef2d) [Computer software]. Zenodo. https://doi.org/10.5281/zenodo.18075235
```

### BibTeX fallback

```bibtex
@software{dass_qwed_2025,
  author={Rahul Dass}, title={QWED Protocol: Deterministic Verification for Large Language Models},
  year={2025}, doi={10.5281/zenodo.18075235}, url={https://github.com/QWED-AI/qwed-verification},
  version={4f0f4f05f2998889aed386e34f6a14e469d1ef2d}, note={Accessed 2026-08-18}
}
```

此 DOI 來自固定 commit 的 `docs/CITATION.cff`，屬軟體／protocol archive；本次未查到可另列的 peer-reviewed benchmark paper。README 另顯示 `10.5281/zenodo.18111675`，與 CFF 不一致，引用前應向 upstream 確認。

## 來源

- [README](https://github.com/QWED-AI/qwed-verification/blob/4f0f4f05f2998889aed386e34f6a14e469d1ef2d/README.md)／[LICENSE](https://github.com/QWED-AI/qwed-verification/blob/4f0f4f05f2998889aed386e34f6a14e469d1ef2d/LICENSE)／[pyproject](https://github.com/QWED-AI/qwed-verification/blob/4f0f4f05f2998889aed386e34f6a14e469d1ef2d/pyproject.toml)
- [VC v1 schema](https://github.com/QWED-AI/qwed-verification/blob/4f0f4f05f2998889aed386e34f6a14e469d1ef2d/spec/v1.0/schemas/verification-context.schema.json)／[conformance tests](https://github.com/QWED-AI/qwed-verification/blob/4f0f4f05f2998889aed386e34f6a14e469d1ef2d/tests/test_verification_context_spec.py)
- [ADR-004 formalization boundary](https://github.com/QWED-AI/qwed-verification/blob/4f0f4f05f2998889aed386e34f6a14e469d1ef2d/docs/adr/ADR-004-formalization-boundary.md)／[ADR-005 root of trust](https://github.com/QWED-AI/qwed-verification/blob/4f0f4f05f2998889aed386e34f6a14e469d1ef2d/docs/adr/ADR-005-root-of-trust.md)／[CITATION](https://github.com/QWED-AI/qwed-verification/blob/4f0f4f05f2998889aed386e34f6a14e469d1ef2d/docs/CITATION.cff)

## 查核限制

本次未安裝 PyPI／Docker、未跑 test suite、未驗證 solver soundness、signing key lifecycle、multi-replica或臨床資料；結論只涵蓋公開固定 commit，私人與未索引部署不在範圍。
