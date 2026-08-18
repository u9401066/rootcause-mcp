# {{report_title}}

**Case / Session:** `{{session_id}}`
**Report:** `{{report_id}}`
**狀態:** {{report_status}}

> 本報告以繁體中文敘述並保留 English medical terminology。它是回溯性
> clinical decision-support 與 audit artifact，不是 autonomous diagnosis、
> treatment recommendation 或 clinical causation proof。

## 事件的一句話表示

{{executive_summary}}

## Source-linked timeline

{{timeline_table}}

時間精度、timezone、來源衝突或無法確認的事件必須保留為 unknown。

## Differential diagnosis discussion

每個 candidate 必須呈現 Mechanism / role、Evidence for、Evidence against、
Unknown / alternative explanation、Discriminating test 與 Certainty。

{{hypothesis_discussion_section}}

### Must-not-miss

{{must_not_miss_evaluated}}

{{differential_breadth_audit_section}}

## Evidence ledger 與資訊缺口

{{evidence_table}}

{{source_inventory_section}}

{{cognitive_safety_section}}

{{automated_checks_section}}

## Medical root-process / system RCA

{{rca_analysis_section}}

> Causation validator 只保守檢查已提交的 temporality、mechanism 與 evidence
> obligations；即使 audit 通過，也不等於已證明單一病人的 clinical causality。

## 下一步可區辨資料

{{rule_out_summary}}

## Conformance 與 review state

{{conformance_checks_section}}

{{quality_metrics_section}}

**Content hash:** `{{content_hash}}`
