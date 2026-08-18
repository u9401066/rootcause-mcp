# PHI 與臨床資料政策

本政策適用於 RootCause MCP 的原始資料、測試 fixture、prompt、log、SQLite
資料庫、WAL/SHM、checkpoint、匯出報告、CI artifact，以及 issue、PR 和 commit
歷史。此 repository 與一般 CI runner 均視為**非臨床資料安全區域**。

## 不得提交真實 PHI

- 不得把任何可識別真實病人的 PHI/PII 提交、貼上或上傳至 repository、issue、
  PR、CI、測試輸出或公開 artifact。姓名、病歷號、日期、影像 metadata、自由文字
  和罕見事件組合都可能成為識別資訊。
- Repository fixture 只能是完全合成資料。真實病人衍生資料即使經人工去識別，也
  不得當作 fixture 提交；如研究或臨床審查確實需要，必須留在機構核准的受控環境，
  並遵循當地法規、IRB/治理程序與資料使用協議。
- `.gitignore` 不是安全控制。資料一旦進入 commit、remote cache 或 CI log，即視為
  已揭露，不可用後續刪檔來宣稱復原。
- Agent 不得補造缺失病歷、時間、來源、檢驗值或 reviewer 身分；缺失內容必須標示
  `unknown`、限制或待人工確認。

## 合成 fixture 與 manifest

每組合成 fixture 必須有同目錄的 YAML 或 JSON manifest，且在送入
`rc_start_session.source_manifest` 前先以
`clinical://contracts/case-input-manifest` 的即時 schema 驗證。Manifest 至少包含：

- `fixture_policy.policy_version`、唯一 `fixture_id`、`synthetic: true`、用途、owner、
  產生方式、建立時間、reviewer，以及明確的 `retention_until` 或
  `retention: repository_lifetime`。
- `case_manifest.schema_version: "1.0"`，以及每一來源的穩定 `document_id`、
  `source_uri`、whole-file `sha256`、`media_type`、`source_kind`、`revision`、
  `captured_at`、parser 名稱/版本、處理 `status` 與 `de_identified: true`。
- 若來源省略時區，必須設定 IANA `default_timezone`；若無法決定，不可推測，應在
  fixture 限制中明列。
- `sha256` 必須由實際 fixture bytes 計算；同一 `document_id` 內容變更時必須更新
  digest 與 revision。Manifest 不可包含直接病人識別碼。

建議的外層結構如下；`case_manifest` 內容仍以即時 MCP resource schema 為準：

```yaml
fixture_policy:
  policy_version: "1.0"
  fixture_id: synthetic-airway-001
  synthetic: true
  purpose: integration-test
  owner: repository-maintainers
  generated_by: deterministic-fixture-generator
  created_at: "2026-08-17T00:00:00Z"
  reviewed_by: synthetic-data-reviewer
  retention: repository_lifetime
case_manifest:
  schema_version: "1.0"
  patient_key: SYNTHETIC-P001
  encounter_key: SYNTHETIC-E001
  default_timezone: Asia/Taipei
  documents:
    - document_id: SRC-001
      source_uri: fixtures/synthetic-airway-001/note.txt
      sha256: 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
      media_type: text/plain
      source_kind: progress_note
      revision: "1"
      captured_at: "2026-08-17T08:30:00+08:00"
      parser_name: fixture-author
      parser_version: "1"
      status: reviewed
      de_identified: true
```

## 儲存與權限

- 執行真實案例時，將 `ROOTCAUSE_DATA_DIR` 指向 repository 外、機構核准且加密的
  儲存空間。不得使用 repository 內的 `data/` 作為真實案例資料目錄。
- 採最小權限：資料夾僅允許案例團隊存取；在支援 POSIX 權限的主機上，目錄建議
  `0700`、檔案建議 `0600`。備份、同步、索引與遙測服務也必須納入權限範圍。
- `ROOTCAUSE_AUTHORIZED_REVIEWERS` 只放經核准的 reviewer 識別，透過受保護的環境
  設定注入，不得提交 `.env` 或把 allowlist 寫入 fixture。manual confirmation 只有
  `verified_by` 位於該 allowlist 時才有效。
- 未取得資料治理與使用者明確授權前，不得把臨床資料送往外部模型、搜尋服務、
  analytics、錯誤回報或其他第三方系統。

## 保留與刪除

- 合成 fixture 由 manifest owner 在 `retention_until` 到期時重新審查並刪除；使用
  `repository_lifetime` 時，則在測試或文件不再依賴它時移除。不得無 owner、無用途
  地永久保留。
- 真實案例的 runtime DB、WAL/SHM、checkpoint、export、log 與暫存檔，只保留到
  核准審查完成或機構 retention schedule 到期（取較早者）；CI 不得處理或保留
  真實案例資料。
- 刪除前先停止 MCP server 並確認精確的 `ROOTCAUSE_DATA_DIR`；再依核准程序清除
  DB/WAL/SHM、exports、checkpoints、logs、暫存、備份與同步副本，最後記錄並驗證
  刪除結果。SSD、雲端與版本控制未必能保證覆寫式 secure erase，應使用機構核准的
  cryptographic erasure 或供應商刪除流程。
- 若敏感資料曾進入 Git、PR、CI log 或 artifact，立即停止分享並依資安事件程序通報；
  限縮權限、撤銷外洩憑證、保存必要稽核證據，再由有權限的 maintainer 協調 remote
  artifact 清除及 history rewrite。不要自行假設本機刪檔已完成清除。

## Review checklist

- fixture 明確標為 synthetic，且無真實病人衍生內容。
- manifest 完整、hash 可重算，並通過即時 case-input schema。
- 時區、來源限制與缺失值均明列，沒有捏造或未標記推論。
- runtime 路徑、權限、外部傳輸與 retention 均已獲核准。
- 最終臨床產物仍須由 `ROOTCAUSE_AUTHORIZED_REVIEWERS` 中的人員審閱；工具輸出不可
  取代臨床判斷或病人照護決策。
