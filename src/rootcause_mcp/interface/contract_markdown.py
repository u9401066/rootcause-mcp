"""Deterministic Markdown presenter for clinical reasoning reports."""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping, Sequence
from pathlib import Path, PureWindowsPath
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from rootcause_mcp.domain.value_objects.clinical_concept import ClinicalConcept
from rootcause_mcp.domain.value_objects.contract_report import ContractReport

if TYPE_CHECKING:
    from rootcause_mcp.domain.value_objects.report_sections import (
        DifferentialBreadthCellRecord,
        EvidenceRecord,
        HypothesisRecord,
        ReasoningStepRecord,
        ThinkingStepRecord,
    )

_STRENGTH_RANK = {"STRONG": 3, "MODERATE": 2, "WEAK": 1, "ANECDOTAL": 0}
logger = logging.getLogger(__name__)


def _default_template_root() -> Path:
    """Return the configured template allowlist root."""
    configured = os.environ.get("ROOTCAUSE_CONFIG_DIR")
    if configured:
        return Path(configured).expanduser().resolve() / "templates"
    return Path(__file__).resolve().parents[3] / "config" / "templates"


def _resolve_template_path(
    template_path: str | Path,
    template_root: str | Path | None = None,
) -> Path:
    """Resolve one relative Markdown template inside the allowlisted root."""
    raw_path = str(template_path).strip()
    requested = Path(raw_path)
    windows_requested = PureWindowsPath(raw_path)
    if not raw_path or "\x00" in raw_path:
        raise ValueError("template_file must name a relative Markdown template")
    if requested.is_absolute() or windows_requested.is_absolute():
        raise ValueError(
            "template_file must be relative to the configured templates directory"
        )
    if ".." in requested.parts or ".." in windows_requested.parts:
        raise ValueError("template_file cannot contain parent-directory traversal")

    parts = requested.parts
    if parts[:2] == ("config", "templates"):
        relative_path = Path(*parts[2:])
    elif parts[:1] == ("templates",):
        relative_path = Path(*parts[1:])
    else:
        relative_path = requested
    if not relative_path.parts or relative_path == Path():
        raise ValueError("template_file must name a Markdown file")
    if relative_path.suffix.lower() != ".md":
        raise ValueError("template_file must use the .md extension")

    allowed_root = Path(template_root or _default_template_root()).resolve()
    if not allowed_root.is_dir():
        raise ValueError("configured templates directory is unavailable")
    try:
        resolved = (allowed_root / relative_path).resolve(strict=True)
        resolved.relative_to(allowed_root)
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise ValueError(
            "template_file must resolve to an existing file inside the configured templates directory"
        ) from exc
    if not resolved.is_file():
        raise ValueError("template_file must resolve to a regular Markdown file")
    return resolved


def _timeline_artifacts(report: ContractReport) -> tuple[str, str]:
    """Render timeline artifacts, omitting only malformed persisted evidence."""
    if report.timeline is not None:
        return str(report.timeline.get("mermaid", "")), str(
            report.timeline.get("table", "")
        )

    from rootcause_mcp.domain.entities.evidence import Evidence
    from rootcause_mcp.interface.mermaid import build_timeline

    try:
        evidence = [Evidence.model_validate(item) for item in report.evidence]
    except ValidationError:
        logger.warning(
            "Chronological timeline omitted because persisted evidence failed "
            "Evidence schema validation"
        )
        return "", ""

    timeline = build_timeline(evidence)
    return str(timeline["mermaid"]), str(timeline["table"])


def _render_custom_template(  # noqa: PLR0912, PLR0915
    report: ContractReport,
    detail_level: str,
    hypotheses: list[HypothesisRecord],
    evidence: list[EvidenceRecord],
    evidence_limit: int | None,
    template_path: str | Path,
    template_root: str | Path | None,
    locale: str,
) -> str:
    """Render report using an allowlisted external Markdown template file."""
    tpl_path = _resolve_template_path(template_path, template_root)

    try:
        template_text = tpl_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ValueError("template_file could not be read as UTF-8 Markdown") from exc
    conclusion_hypotheses = report.ranked_conclusion_hypotheses()
    top_diag = (
        conclusion_hypotheses[0].get("diagnosis", {}).get("display", "Unknown")
        if conclusion_hypotheses
        else "None"
    )
    top_certainty = (
        _cell(conclusion_hypotheses[0].get("certainty", "UNKNOWN"))
        if conclusion_hypotheses
        else "UNKNOWN"
    )
    refuted = [
        h.get("diagnosis", {}).get("display", "Unknown")
        for h in hypotheses
        if str(h.get("status", "")).upper() in {"EXCLUDED", "RULED_OUT"}
        or len(h.get("contradicting_evidence_ids", [])) > 0
    ]
    rule_out_summary = ", ".join(refuted) if refuted else "None explicitly refuted"
    must_not_miss_count = sum(bool(h.get("must_not_miss")) for h in hypotheses)

    reasoning_mermaid = ""
    if detail_level in {"standard", "full"} and report.reasoning_chain:
        from rootcause_mcp.domain.entities.reasoning_step import (
            ReasoningChain,
            ReasoningStep,
        )
        from rootcause_mcp.interface.mermaid import (
            render_reasoning_chain_mermaid,
        )

        reasoning_steps = []
        for item in report.reasoning_chain:
            payload = dict(item)
            if isinstance(payload.get("id"), str):
                payload["id"] = {"value": payload["id"]}
            reasoning_steps.append(ReasoningStep.model_validate(payload))
        chain = ReasoningChain(
            session_id=report.session_id,
            steps=reasoning_steps,
        )
        reasoning_mermaid = render_reasoning_chain_mermaid(chain)

    evidence_mermaid = ""
    if report.evidence_graph and report.evidence_graph.get("mermaid"):
        evidence_mermaid = str(report.evidence_graph["mermaid"])

    timeline_mermaid, timeline_table = (
        _timeline_artifacts(report) if evidence else ("", "")
    )

    source_inventory_section = "\n".join(
        ["## Registered Source Inventory", "", *_source_inventory(report)]
    )
    rca_analysis_section = "\n".join(
        ["## Root Cause Analysis", "", *_root_cause_analysis(report)]
    )
    conformance_checks_section = "\n".join(
        ["## Deterministic Conformance Checks", "", *_conformance_checks(report)]
    )
    if locale == "zh-TW":
        evidence_by_id = {_entity_id(item): item for item in evidence}
        hypothesis_discussion_section = (
            "\n".join(
                line
                for index, hypothesis in enumerate(hypotheses, 1)
                for line in _zh_tw_hypothesis_discussion(
                    index,
                    hypothesis,
                    evidence_by_id,
                )
            )
            or "- 尚未記錄候選 diagnosis。"
        )
        differential_breadth_audit_section = "\n".join(
            ["## DDx breadth audit", "", *_zh_tw_breadth_audits(report)]
        )
    else:
        hypothesis_discussion_section = "\n".join(_hypothesis_table(hypotheses))
        differential_breadth_audit_section = "\n".join(
            [
                "## Differential Diagnosis Breadth Audit",
                "",
                *_english_breadth_audits(report),
            ]
        )
    has_source_inventory_placeholder = "{{source_inventory_section}}" in template_text
    has_rca_analysis_placeholder = "{{rca_analysis_section}}" in template_text
    has_conformance_placeholder = "{{conformance_checks_section}}" in template_text
    has_breadth_placeholder = "{{differential_breadth_audit_section}}" in template_text
    has_hypothesis_discussion_placeholder = (
        "{{hypothesis_discussion_section}}" in template_text
    )
    placeholders: dict[str, str] = {
        "report_title": (
            "Clinical Reasoning 與 Root Cause 分析報告"
            if locale == "zh-TW"
            else "Clinical Reasoning & Root Cause Report"
        ),
        "session_id": _cell(report.session_id),
        "report_id": _cell(report.report_id),
        "generated_at": report.generated_at.isoformat(),
        "report_status": "Final" if report.is_finalized else "Preliminary",
        "detail_level": detail_level,
        "executive_summary": "\n".join(
            _executive_summary(conclusion_hypotheses, evidence, report)
        ),
        "hypothesis_table": "\n".join(_hypothesis_table(hypotheses)),
        "hypothesis_discussion_section": hypothesis_discussion_section,
        "top_diagnosis": top_diag,
        "top_probability": (
            "Not presented; use qualitative certainty and evidence disposition"
        ),
        "top_certainty": top_certainty,
        "rule_out_summary": rule_out_summary,
        "must_not_miss_evaluated": (
            f"{must_not_miss_count} explicitly marked high-harm rule-out condition(s)"
        ),
        "evidence_table": "\n".join(
            _evidence_table(evidence, evidence_limit, hypotheses)
        ),
        "source_inventory_section": source_inventory_section,
        "rca_analysis_section": rca_analysis_section,
        "conformance_checks_section": conformance_checks_section,
        "differential_breadth_audit_section": differential_breadth_audit_section,
        "timeline_diagram": timeline_mermaid or "_No timeline diagram generated._",
        "timeline_table": timeline_table or "_No timeline table generated._",
        "cognitive_safety_section": "\n".join(_cognitive_safety(report.thinking_chain)),
        "automated_checks_section": "\n".join(_automated_findings(report)),
        "quality_metrics_section": "\n".join(_quality_metrics(report)),
        "unresolved_safety_risks": "\n".join(
            _custom_unresolved_safety_risks(hypotheses)
        ),
        "planned_tests_and_data_requests": "\n".join(
            _custom_planned_tests_and_data_requests(hypotheses)
        ),
        "reasoning_chain_diagram": reasoning_mermaid
        or "_No diagram generated for brief mode._",
        "evidence_graph_diagram": evidence_mermaid or "_No evidence graph generated._",
        "generated_by": _cell(report.generated_by),
        "report_version": _cell(report.report_version),
        "total_evidence_count": str(len(report.evidence)),
        "verified_evidence_count": str(
            sum(bool(item.get("verified")) for item in evidence)
        ),
        "total_hypotheses_count": str(len(report.hypotheses)),
        "reasoning_steps_count": str(len(report.reasoning_chain)),
        "content_hash": report.content_hash or "PRELIMINARY",
    }

    for key, val in placeholders.items():
        template_text = template_text.replace(f"{{{{{key}}}}}", val)
    if not has_source_inventory_placeholder:
        template_text = (
            f"{template_text.rstrip()}\n\n---\n\n{source_inventory_section}\n"
        )
    if not has_breadth_placeholder:
        template_text = (
            f"{template_text.rstrip()}\n\n{differential_breadth_audit_section}\n"
        )
    if locale == "zh-TW" and not has_hypothesis_discussion_placeholder:
        template_text = (
            f"{template_text.rstrip()}\n\n## DDx：逐項推論與待驗證事項\n\n"
            f"{hypothesis_discussion_section}\n"
        )
    if not has_rca_analysis_placeholder:
        template_text = f"{template_text.rstrip()}\n\n{rca_analysis_section}\n"
    if not has_conformance_placeholder:
        template_text = f"{template_text.rstrip()}\n\n{conformance_checks_section}\n"
    return template_text.rstrip() + "\n"


def _custom_unresolved_safety_risks(
    hypotheses: list[HypothesisRecord],
) -> list[str]:
    risks = [
        hypothesis
        for hypothesis in hypotheses
        if hypothesis.get("must_not_miss")
        and str(hypothesis.get("status", "")).upper() not in {"EXCLUDED", "RULED_OUT"}
    ]
    if not risks:
        return ["- No unresolved must-not-miss diagnosis is recorded."]
    return [
        f"- **{_diagnosis_cells(hypothesis)[0]}** — status "
        f"`{_cell(hypothesis.get('status', 'UNKNOWN'))}`, certainty "
        f"`{_cell(hypothesis.get('certainty', 'UNKNOWN'))}`"
        for hypothesis in risks
    ]


def _custom_planned_tests_and_data_requests(
    hypotheses: list[HypothesisRecord],
) -> list[str]:
    lines: list[str] = []
    for hypothesis in hypotheses:
        diagnosis = _diagnosis_cells(hypothesis)[0]
        for test in hypothesis.get("planned_tests", []):
            if not isinstance(test, Mapping):
                continue
            lines.append(
                f"- **{diagnosis}:** {_cell(test.get('name', 'Unnamed test'), 300)} "
                f"(`{_cell(test.get('purpose', 'unknown'))}`, "
                f"`{_cell(test.get('status', 'unknown'))}`)"
            )
        for unknown in hypothesis.get("uncertainty_factors", []):
            lines.append(f"- **{diagnosis} unknown:** {_cell(unknown, 500)}")
    return lines or ["- No typed planned test or hypothesis-specific unknown recorded."]


def render_contract_report_markdown(
    report: ContractReport,
    detail_level: str = "standard",
    template_path: str | Path | None = None,
    template_root: str | Path | None = None,
    *,
    locale: str = "en",
    audience: str = "general",
) -> str:
    """Render a deterministic report, optionally from an allowlisted template."""
    if detail_level not in {"brief", "standard", "full"}:
        raise ValueError("detail_level must be brief, standard, or full")
    if locale not in {"en", "zh-TW"}:
        raise ValueError("locale must be en or zh-TW")
    if audience not in {"general", "clinician"}:
        raise ValueError("audience must be general or clinician")

    hypotheses = list(report.hypotheses)
    evidence = sorted(report.evidence, key=_evidence_sort_key, reverse=True)
    conclusion_hypotheses = report.ranked_conclusion_hypotheses()
    evidence_limit = 8 if detail_level == "brief" else None

    if template_path:
        custom_rendered = _render_custom_template(
            report=report,
            detail_level=detail_level,
            hypotheses=hypotheses,
            evidence=evidence,
            evidence_limit=evidence_limit,
            template_path=template_path,
            template_root=template_root,
            locale=locale,
        )
        return custom_rendered

    if locale == "zh-TW":
        return _render_zh_tw_report(
            report,
            hypotheses,
            evidence,
            evidence_limit,
            detail_level,
            audience,
        )

    return _render_english_report(
        report,
        hypotheses,
        evidence,
        conclusion_hypotheses,
        evidence_limit,
        detail_level,
    )


def _render_english_report(
    report: ContractReport,
    hypotheses: list[HypothesisRecord],
    evidence: list[EvidenceRecord],
    conclusion_hypotheses: list[HypothesisRecord],
    evidence_limit: int | None,
    detail_level: str,
) -> str:
    """Render the backward-compatible built-in English Markdown report."""
    lines = [
        "# Clinical Reasoning Report",
        "",
        f"**Session:** `{_cell(report.session_id)}`  ",
        f"**Report:** `{_cell(report.report_id)}`  ",
        f"**Generated:** {report.generated_at.isoformat()}  ",
        f"**Status:** {'Final' if report.is_finalized else 'Preliminary'}  ",
        f"**Detail level:** `{detail_level}`  ",
        "**Generation:** Deterministic from persisted structured data; no LLM call",
        "",
        "> Decision-support artifact only. A qualified clinician must verify source",
        "> records, coding, likelihood ratios, conclusions, and patient-specific action.",
        "",
        "## Executive Summary",
        "",
    ]
    lines.extend(_executive_summary(conclusion_hypotheses, evidence, report))
    lines.extend(
        [
            "",
            "## Ranked Differential Diagnosis",
            "",
            *_hypothesis_table(hypotheses),
            "",
            "## Evidence Matrix",
            "",
            *_evidence_table(evidence, evidence_limit, hypotheses),
            "",
            "## Registered Source Inventory",
            "",
            *_source_inventory(report),
            "",
            "## Root Cause Analysis",
            "",
            *_root_cause_analysis(report),
        ]
    )

    if detail_level in {"standard", "full"} and evidence:
        timeline_mermaid, timeline_table = _timeline_artifacts(report)
        if timeline_mermaid and timeline_table:
            lines.extend(["", "## Chronological Timeline", ""])
            lines.append(timeline_table)
            lines.extend(["", timeline_mermaid])

    lines.extend(["", "## Uncertainty and Cognitive Safety", ""])
    lines.extend(_cognitive_safety(report.thinking_chain))
    lines.extend(["", "## Automated Completeness Checks", ""])
    lines.extend(_automated_findings(report))
    lines.extend(["", "## Deterministic Conformance Checks", ""])
    lines.extend(_conformance_checks(report))
    lines.extend(["", "## Quality Metrics", ""])
    lines.extend(_quality_metrics(report))

    if detail_level in {"standard", "full"}:
        lines.extend(["", "## Reasoning Audit", ""])
        lines.extend(
            _reasoning_audit(report.reasoning_chain, detail_level, report.evidence)
        )
        if report.evidence_graph and report.evidence_graph.get("mermaid"):
            lines.extend(["", "## Evidence Graph", ""])
            lines.append(str(report.evidence_graph["mermaid"]))

    if detail_level == "full":
        lines.extend(["", "## Recorded Agent Rationale", ""])
        lines.extend(_thinking_audit(report.thinking_chain))

    lines.extend(["", "## Audit", ""])
    lines.append(f"- Generated by: `{_cell(report.generated_by)}`")
    lines.append(f"- Report version: `{_cell(report.report_version)}`")
    lines.append(f"- Evidence records: {len(report.evidence)}")
    lines.append(f"- Hypotheses: {len(report.hypotheses)}")
    lines.append(f"- Reasoning steps: {len(report.reasoning_chain)}")
    lines.append(f"- Agent-authored rationale records: {len(report.thinking_chain)}")
    if report.approved_by:
        lines.append(f"- Approved by: `{_cell(report.approved_by)}`")
    if report.finalized_at:
        lines.append(f"- Finalized at: `{report.finalized_at.isoformat()}`")
    if report.content_hash:
        lines.append(f"- Content SHA-256: `{report.content_hash}`")
    return "\n".join(lines).rstrip() + "\n"


def _render_zh_tw_report(
    report: ContractReport,
    hypotheses: list[HypothesisRecord],
    evidence: list[EvidenceRecord],
    evidence_limit: int | None,
    detail_level: str,
    audience: str,
) -> str:
    """Render a clinician-oriented Traditional Chinese report without translation.

    Persisted medical strings are intentionally left untouched.  The renderer
    translates only its fixed explanatory copy, so Diagnosis, procedure, drug,
    test, ECG/VF/ROSC/LR/DDx, and other source terminology retain their recorded
    English form and meaning.
    """
    conclusion_hypotheses = report.ranked_conclusion_hypotheses()
    provenance_checked = sum(bool(item.get("verified")) for item in evidence)
    uncertainties = _unique_thinking_values(
        report.thinking_chain, "uncertainty_factors"
    )
    status = "Final" if report.is_finalized else "Preliminary"
    target = "clinician" if audience == "clinician" else "general"
    lines = [
        "# Clinical Reasoning 與 Root Cause 分析報告",
        "",
        f"**Session：** `{_cell(report.session_id)}`  ",
        f"**Report：** `{_cell(report.report_id)}`  ",
        f"**產生時間：** {report.generated_at.isoformat()}  ",
        f"**狀態：** {status}  ",
        f"**Audience：** `{target}`  ",
        f"**Detail level：** `{detail_level}`  ",
        "**產生方式：** 由 persisted structured data deterministic rendering；無 LLM call",
        "",
        "> 本報告是回溯性 clinical decision-support，不是自主診斷、治療建議或",
        "> clinical causality proof。所有 source、DDx、LR、結論與個案處置，仍須由",
        "> qualified clinician 對照原始病歷與 waveform 後審查。",
        "",
        "## 臨床摘要",
        "",
    ]
    if conclusion_hypotheses:
        diagnosis = conclusion_hypotheses[0].get("diagnosis", {})
        display = _cell(diagnosis.get("display", "Unknown diagnosis"))
        lines.append(
            f"目前經 audited mutation 明確選定的 working leading DDx 為 **{display}**；"
            "這代表目前的明確工作選擇，"
            "不是確診，也不是已校準的 clinical probability ranking。"
        )
    elif hypotheses:
        lines.append(
            "尚未透過 audited mutation 選定 explicit leading DDx；既有候選仍保留於 "
            "ledger，不能從順序或未校準數值推定 leading diagnosis。"
        )
    else:
        lines.append("尚未記錄 DDx，不能進行 diagnostic closure。")
    lines.extend(
        [
            "",
            (
                f"目前共有 **{len(evidence)} 筆 evidence**、**{len(hypotheses)} 個 DDx**、"
                f"**{len(uncertainties)} 個明確 unknown/uncertainty**；其中 "
                f"**{provenance_checked} 筆**在 registered-source boundary 有成功的 "
                "provenance check。"
            ),
            "",
            (
                "上述 provenance check 只表示 registered text/source boundary 的 match "
                "或授權確認；不表示來源彼此獨立，也不自動驗證上游 PPTX/PDF/image、"
                "原始 EHR、臨床解讀或診斷真實性。"
            ),
            "",
            "DDx 的目的，是在未知仍多時保留最大範圍的合理推論，再用可追溯 evidence "
            "與 discriminating tests 逐步支持、削弱或排除，而不是過早收斂成單一答案。",
            "",
            "## DDx：逐項推論與待驗證事項",
            "",
        ]
    )
    if hypotheses:
        evidence_by_id = {_entity_id(item): item for item in evidence}
        for index, hypothesis in enumerate(hypotheses, 1):
            lines.extend(
                _zh_tw_hypothesis_discussion(index, hypothesis, evidence_by_id)
            )
    else:
        lines.append("- 尚未記錄候選 diagnosis。")

    lines.extend(["", "## DDx breadth audit", ""])
    lines.extend(_zh_tw_breadth_audits(report))
    lines.extend(["", "## Evidence ledger", ""])
    lines.extend(_zh_tw_evidence_table(evidence, evidence_limit))
    lines.extend(["", "## Registered source 與 extraction 邊界", ""])
    lines.extend(_zh_tw_source_inventory(report))

    lines.extend(_zh_tw_analysis_sections(report, detail_level))
    lines.extend(_zh_tw_audit_metadata(report))
    return "\n".join(lines).rstrip() + "\n"


def _zh_tw_breadth_audits(report: ContractReport) -> list[str]:
    """Render systematic framework coverage separately from the diagnosis list."""
    if not report.differential_breadth_audits:
        return [
            "- 尚未記錄 typed breadth audit；目前的 DDx 數量不能證明已完成系統性擴展。"
        ]
    lines: list[str] = []
    for audit in report.differential_breadth_audits:
        cells = [item for item in audit.get("cells", []) if isinstance(item, Mapping)]
        status_counts: dict[str, int] = {}
        for cell in cells:
            status = str(cell.get("status", "UNKNOWN"))
            status_counts[status] = status_counts.get(status, 0) + 1
        complete = not any(str(cell.get("status")) == "NOT_ASSESSED" for cell in cells)
        framework = _cell(
            audit.get("framework_name") or audit.get("framework", "UNKNOWN")
        )
        lines.extend(
            [
                f"### {framework}（`{_cell(audit.get('role', 'UNKNOWN'))}`）",
                "",
                f"- Audit：`{_cell(audit.get('audit_id', 'unknown'))}`",
                f"- Coverage status：{'COMPLETE' if complete else 'INCOMPLETE'}",
                f"- Framework rationale：{_cell(audit.get('framework_rationale', '未記錄'), 900)}",
                "- Cell summary："
                + ", ".join(
                    f"`{status}` {count}"
                    for status, count in sorted(status_counts.items())
                ),
                f"- Stop rationale：{_cell(audit.get('stop_rationale', '未記錄'), 900)}",
                "",
                "| Cell | Status | Linked hypotheses / mechanism | Rationale |",
                "| --- | --- | --- | --- |",
            ]
        )
        for cell in cells:
            links = (
                ", ".join(
                    [
                        *(str(item) for item in cell.get("hypothesis_ids", [])),
                        *(str(item) for item in cell.get("mechanism_categories", [])),
                    ]
                )
                or "-"
            )
            lines.append(
                "| "
                + " | ".join(
                    [
                        f"`{_cell(cell.get('cell_id', 'unknown'))}`",
                        f"`{_cell(cell.get('status', 'UNKNOWN'))}`",
                        _cell(links, 260),
                        _cell(cell.get("rationale", "未記錄"), 500),
                    ]
                )
                + " |"
            )
        lines.extend(_zh_tw_breadth_unknowns_and_tests(cells))
        lines.append("")
    return lines


def _zh_tw_breadth_unknowns_and_tests(
    cells: list[DifferentialBreadthCellRecord],
) -> list[str]:
    outstanding = [
        cell
        for cell in cells
        if str(cell.get("status")) in {"REVIEWED_INSUFFICIENT_DATA", "NOT_ASSESSED"}
    ]
    if not outstanding:
        return ["", "**未評估／INSUFFICIENT_DATA cells：** 無。"]
    lines = ["", "**未評估／INSUFFICIENT_DATA cells 與 discriminators：**"]
    for cell in outstanding:
        cell_id = _cell(cell.get("cell_id", "unknown"))
        status = _cell(cell.get("status", "UNKNOWN"))
        unknowns = cell.get("unknowns", [])
        lines.append(f"- `{cell_id}` — `{status}`")
        lines.extend(f"  - Unknown：{_cell(item, 700)}" for item in unknowns)
        discriminators = cell.get("planned_discriminators", [])
        if not discriminators:
            lines.append("  - Planned discriminator：未記錄")
        for discriminator in discriminators:
            if not isinstance(discriminator, Mapping):
                continue
            lines.extend(
                [
                    f"  - Planned discriminator：**{_cell(discriminator.get('name', 'Unnamed'), 300)}** "
                    f"(`{_cell(discriminator.get('kind', 'unknown'))}`, "
                    f"`{_cell(discriminator.get('status', 'unknown'))}`)",
                    "    - 若支持："
                    + _cell(
                        discriminator.get("expected_supporting_result", "未記錄"),
                        700,
                    ),
                    "    - 若反證："
                    + _cell(
                        discriminator.get("expected_refuting_result", "未記錄"),
                        700,
                    ),
                ]
            )
    return lines


def _english_breadth_audits(report: ContractReport) -> list[str]:
    """Render typed framework coverage without equating unknown with exclusion."""
    if not report.differential_breadth_audits:
        return [
            "- No typed breadth audit is recorded; the diagnosis count alone does "
            "not demonstrate systematic expansion."
        ]
    lines: list[str] = []
    for audit in report.differential_breadth_audits:
        cells = [item for item in audit.get("cells", []) if isinstance(item, Mapping)]
        status_counts: dict[str, int] = {}
        for cell in cells:
            status = str(cell.get("status", "UNKNOWN"))
            status_counts[status] = status_counts.get(status, 0) + 1
        complete = not any(str(cell.get("status")) == "NOT_ASSESSED" for cell in cells)
        framework = _cell(
            audit.get("framework_name") or audit.get("framework", "UNKNOWN")
        )
        lines.extend(
            [
                f"### {framework} (`{_cell(audit.get('role', 'UNKNOWN'))}`)",
                "",
                f"- Audit: `{_cell(audit.get('audit_id', 'unknown'))}`",
                f"- Coverage status: {'COMPLETE' if complete else 'INCOMPLETE'}",
                "- Framework rationale: "
                + _cell(audit.get("framework_rationale", "not recorded"), 900),
                "- Cell summary: "
                + ", ".join(
                    f"`{status}` {count}"
                    for status, count in sorted(status_counts.items())
                ),
                "- Stop rationale: "
                + _cell(audit.get("stop_rationale", "not recorded"), 900),
                "",
                "| Cell | Status | Linked hypotheses / mechanism | Rationale |",
                "| --- | --- | --- | --- |",
            ]
        )
        for cell in cells:
            links = (
                ", ".join(
                    [
                        *(str(item) for item in cell.get("hypothesis_ids", [])),
                        *(str(item) for item in cell.get("mechanism_categories", [])),
                    ]
                )
                or "-"
            )
            lines.append(
                "| "
                + " | ".join(
                    [
                        f"`{_cell(cell.get('cell_id', 'unknown'))}`",
                        f"`{_cell(cell.get('status', 'UNKNOWN'))}`",
                        _cell(links, 260),
                        _cell(cell.get("rationale", "not recorded"), 500),
                    ]
                )
                + " |"
            )
        lines.extend(_english_breadth_unknowns_and_tests(cells))
        lines.append("")
    return lines


def _english_breadth_unknowns_and_tests(
    cells: list[DifferentialBreadthCellRecord],
) -> list[str]:
    outstanding = [
        cell
        for cell in cells
        if str(cell.get("status")) in {"REVIEWED_INSUFFICIENT_DATA", "NOT_ASSESSED"}
    ]
    if not outstanding:
        return ["", "**Unassessed / insufficient-data cells:** None."]
    lines = ["", "**Unassessed / insufficient-data cells and discriminators:**"]
    for cell in outstanding:
        lines.append(
            f"- `{_cell(cell.get('cell_id', 'unknown'))}` — "
            f"`{_cell(cell.get('status', 'UNKNOWN'))}`"
        )
        lines.extend(
            f"  - Unknown: {_cell(item, 700)}" for item in cell.get("unknowns", [])
        )
        discriminators = cell.get("planned_discriminators", [])
        if not discriminators:
            lines.append("  - Planned discriminator: not recorded")
        for discriminator in discriminators:
            if not isinstance(discriminator, Mapping):
                continue
            lines.extend(
                [
                    f"  - Planned discriminator: **{_cell(discriminator.get('name', 'Unnamed'), 300)}** "
                    f"(`{_cell(discriminator.get('kind', 'unknown'))}`, "
                    f"`{_cell(discriminator.get('status', 'unknown'))}`)",
                    "    - Supporting result: "
                    + _cell(
                        discriminator.get("expected_supporting_result", "not recorded"),
                        700,
                    ),
                    "    - Refuting result: "
                    + _cell(
                        discriminator.get("expected_refuting_result", "not recorded"),
                        700,
                    ),
                ]
            )
    return lines


def _zh_tw_analysis_sections(
    report: ContractReport,
    detail_level: str,
) -> list[str]:
    """Render optional and shared analysis sections for the zh-TW artifact."""
    lines: list[str] = []
    if detail_level in {"standard", "full"} and report.timeline:
        lines.extend(["", "## Canonical timeline", "", *_zh_tw_timeline(report)])
    lines.extend(
        [
            "",
            "## Unknowns、missing data 與 cognitive safety",
            "",
            *_zh_tw_cognitive_safety(report.thinking_chain),
            "",
            "## Root Cause Analysis（RCA）",
            "",
            *_zh_tw_root_cause_analysis(report),
            "",
            "## Deterministic conformance checks",
            "",
            *_zh_tw_conformance_checks(report),
        ]
    )
    if detail_level in {"standard", "full"}:
        lines.extend(
            [
                "",
                "## Reasoning audit",
                "",
                *_zh_tw_reasoning_audit(
                    report.reasoning_chain, detail_level, report.evidence
                ),
            ]
        )
    if detail_level == "full":
        lines.extend(
            [
                "",
                "## Agent 已記錄的 rationale",
                "",
                *_thinking_audit(report.thinking_chain),
            ]
        )
    return lines


def _zh_tw_audit_metadata(report: ContractReport) -> list[str]:
    lines = [
        "",
        "## Audit metadata",
        "",
        f"- Generated by：`{_cell(report.generated_by)}`",
        f"- Report version：`{_cell(report.report_version)}`",
        f"- Evidence records：{len(report.evidence)}",
        f"- DDx：{len(report.hypotheses)}",
        f"- Reasoning steps：{len(report.reasoning_chain)}",
        f"- Agent-authored rationale records：{len(report.thinking_chain)}",
    ]
    if report.approved_by:
        lines.append(f"- Approved by：`{_cell(report.approved_by)}`")
    else:
        lines.append("- Human review：尚未有 authorized qualified reviewer 核准")
    if report.finalized_at:
        lines.append(f"- Finalized at：`{report.finalized_at.isoformat()}`")
    if report.content_hash:
        lines.append(f"- Content SHA-256：`{report.content_hash}`")
    return lines


def _zh_tw_hypothesis_discussion(
    index: int,
    hypothesis: HypothesisRecord,
    evidence_by_id: dict[str, EvidenceRecord],
) -> list[str]:
    """Explain one DDx using only recorded rationale, evidence, and tests."""
    display, code = _diagnosis_cells(hypothesis)
    status = _cell(hypothesis.get("status", "UNKNOWN"))
    must_not_miss = "；must-not-miss" if hypothesis.get("must_not_miss") else ""
    relationships = _hypothesis_lr_relationships(hypothesis)
    supporting = relationships["supporting"]
    contradicting = relationships["contradicting"]
    neutral = relationships["neutral"]
    lines = [
        f"### DDx {index}：{display}",
        "",
        f"- Code：`{_cell(code)}`",
        f"- 狀態：`{status}`{must_not_miss}",
        (
            f"- Mechanism / role / reasoning basis："
            f"`{_cell(hypothesis.get('mechanism_category', 'UNKNOWN'))}` / "
            f"`{_cell(hypothesis.get('diagnostic_role', 'UNKNOWN'))}` / "
            f"`{_cell(hypothesis.get('reasoning_basis', 'UNKNOWN'))}`"
        ),
        (
            f"- Certainty：recorded "
            f"`{_cell(hypothesis.get('certainty', 'UNKNOWN'))}`；evidence disposition："
            f"{_zh_tw_certainty(hypothesis, relationships)}"
        ),
        (
            "- 為何納入："
            + _cell(
                hypothesis.get("clinical_rationale")
                or "未記錄 hypothesis-specific rationale",
                1000,
            )
        ),
        "- Evidence for（僅 LR > 1 才列為 direction-changing support）：",
    ]
    lines.extend(
        _zh_tw_relationship_items(supporting, evidence_by_id)
        or ["  - 尚無已記錄的 LR > 1 evidence。"]
    )
    lines.append(
        "- Evidence against（僅 LR < 1 才列為 direction-changing refutation）："
    )
    lines.extend(
        _zh_tw_relationship_items(contradicting, evidence_by_id)
        or ["  - 尚無已記錄的 LR < 1 evidence。"]
    )
    lines.append("- Direction-neutral / qualitative evidence：")
    lines.extend(_zh_tw_relationship_items(neutral, evidence_by_id) or ["  - 無。"])

    unknowns = hypothesis.get("uncertainty_factors", [])
    lines.append("- Unknowns：")
    lines.extend(
        [f"  - {_cell(item, 800)}" for item in unknowns]
        if isinstance(unknowns, Sequence) and not isinstance(unknowns, str) and unknowns
        else ["  - 未明確記錄；需補做 uncertainty review。"]
    )
    inclusion = hypothesis.get("inclusion_criteria", [])
    exclusion = hypothesis.get("exclusion_criteria", [])
    lines.append("- 可增加可信度的預期 finding：")
    lines.extend(
        [f"  - {_cell(item, 800)}" for item in inclusion]
        if isinstance(inclusion, Sequence)
        and not isinstance(inclusion, str)
        and inclusion
        else ["  - 未記錄。"]
    )
    lines.append("- 可削弱／排除此 DDx 的預期 finding：")
    lines.extend(
        [f"  - {_cell(item, 800)}" for item in exclusion]
        if isinstance(exclusion, Sequence)
        and not isinstance(exclusion, str)
        and exclusion
        else ["  - 未記錄。"]
    )
    lines.extend(
        ["- Planned discriminating tests：", *_zh_tw_planned_tests(hypothesis)]
    )
    lines.append("")
    return lines


def _hypothesis_lr_relationships(
    hypothesis: HypothesisRecord,
) -> dict[str, list[dict[str, Any]]]:
    """Classify applied LRs without treating LR=1 as support or refutation."""
    relationships: dict[str, list[dict[str, Any]]] = {
        "supporting": [],
        "contradicting": [],
        "neutral": [],
    }
    seen: set[str] = set()
    for record in hypothesis.get("likelihood_ratios", []):
        if not isinstance(record, Mapping):
            continue
        evidence_id = str(record.get("evidence_id") or "unknown")
        seen.add(evidence_id)
        applied = _safe_float(record.get("applied_likelihood_ratio"))
        entry = {
            "evidence_id": evidence_id,
            "lr": applied,
            "rationale": record.get("rationale") or "No LR rationale recorded",
        }
        if applied is not None and applied > 1.0:
            relationships["supporting"].append(entry)
        elif applied is not None and applied < 1.0:
            relationships["contradicting"].append(entry)
        else:
            relationships["neutral"].append(entry)

    linked_ids = [
        *hypothesis.get("supporting_evidence_ids", []),
        *hypothesis.get("contradicting_evidence_ids", []),
    ]
    for evidence_id in linked_ids:
        normalized = str(evidence_id)
        if normalized in seen:
            continue
        seen.add(normalized)
        relationships["neutral"].append(
            {
                "evidence_id": normalized,
                "lr": None,
                "rationale": "Relationship recorded without an applied LR; direction is not quantified.",
            }
        )
    return relationships


def _evidence_relationship_counts(
    hypotheses: list[HypothesisRecord],
) -> dict[str, tuple[int, int, int]]:
    """Count support/refutation only when the direct applied LR changes odds."""
    counts: dict[str, list[int]] = {}
    for hypothesis in hypotheses:
        relationships = _hypothesis_lr_relationships(hypothesis)
        for index, key in enumerate(("supporting", "contradicting", "neutral")):
            for relationship in relationships[key]:
                evidence_id = str(relationship["evidence_id"])
                counts.setdefault(evidence_id, [0, 0, 0])[index] += 1
    return {
        evidence_id: (values[0], values[1], values[2])
        for evidence_id, values in counts.items()
    }


def _zh_tw_relationship_items(
    relationships: list[dict[str, Any]],
    evidence_by_id: dict[str, EvidenceRecord],
) -> list[str]:
    lines: list[str] = []
    for relationship in relationships:
        evidence_id = str(relationship["evidence_id"])
        evidence = evidence_by_id.get(evidence_id)
        finding = (
            _cell(evidence.get("content", ""), 500)
            if evidence is not None
            else "evidence record 不在本 report snapshot"
        )
        lr = _safe_float(relationship.get("lr"))
        lr_text = "LR 未記錄" if lr is None else f"applied LR {lr:g}"
        rationale = _cell(relationship.get("rationale", ""), 700)
        lines.append(
            f"  - `{_cell(evidence_id)}` — {finding}（{lr_text}；{rationale}）"
        )
    return lines


def _zh_tw_certainty(
    hypothesis: HypothesisRecord,
    relationships: dict[str, list[dict[str, Any]]],
) -> str:
    """Return a qualitative certainty label, never a model placeholder percent."""
    status = str(hypothesis.get("status", "")).upper()
    has_support = bool(relationships["supporting"])
    has_refutation = bool(relationships["contradicting"])
    if status in {"EXCLUDED", "RULED_OUT"}:
        certainty = "已記錄為 excluded；仍需 clinician 驗證排除依據"
    elif status == "CONFIRMED":
        certainty = "已記錄為 confirmed；仍需 clinician 驗證診斷依據"
    elif has_support and has_refutation:
        certainty = "mixed direction-changing evidence；尚未完成 clinical adjudication"
    elif has_support:
        certainty = "有 direction-changing support，但尚缺有效反證／排除"
    elif has_refutation:
        certainty = "有 direction-changing refutation，但尚未正式 excluded"
    elif relationships["neutral"]:
        certainty = "未校準／資料不足；既有 links 為 LR=1 或未量化 relationship"
    else:
        certainty = "資料不足；尚無 evidence/test disposition"
    return certainty


def _zh_tw_planned_tests(hypothesis: HypothesisRecord) -> list[str]:
    tests = hypothesis.get("planned_tests", [])
    if not isinstance(tests, Sequence) or isinstance(tests, str) or not tests:
        return ["  - 未記錄 typed planned test。"]
    lines: list[str] = []
    for test in tests:
        if not isinstance(test, Mapping):
            continue
        lines.extend(
            [
                (
                    f"  - `{_cell(test.get('test_id', 'unknown'))}` "
                    f"**{_cell(test.get('name', 'Unnamed test'), 300)}** — "
                    f"purpose `{_cell(test.get('purpose', 'unknown'))}`, "
                    f"status `{_cell(test.get('status', 'unknown'))}`"
                ),
                (
                    "    - 若支持："
                    + _cell(test.get("expected_supporting_result", "未記錄"), 700)
                ),
                (
                    "    - 若反證："
                    + _cell(test.get("expected_refuting_result", "未記錄"), 700)
                ),
            ]
        )
    return lines or ["  - 未記錄 typed planned test。"]


def _zh_tw_provenance_label(item: EvidenceRecord) -> str:
    if not item.get("verified"):
        return "未完成"
    method = str(item.get("verification_method") or "RECORDED_VERIFIED")
    if method == "EXACT_SNIPPET_MATCH":
        return "registered source exact text match"
    if method.startswith("MANUAL_REVIEWER"):
        return "authorized manual confirmation"
    return f"已標記（{_cell(method)}）"


def _english_provenance_label(item: EvidenceRecord) -> str:
    """Describe provenance without implying independent-source verification."""
    if not item.get("verified"):
        return "Not completed"
    method = str(item.get("verification_method") or "RECORDED_VERIFIED")
    if method == "EXACT_SNIPPET_MATCH":
        return "Exact text match (registered source)"
    if method.startswith("MANUAL_REVIEWER"):
        return "Authorized manual confirmation"
    return f"Recorded true ({_cell(method)})"


def _zh_tw_evidence_table(
    evidence: list[EvidenceRecord],
    limit: int | None,
) -> list[str]:
    lines = [
        "| Evidence | Finding | Type / quality | Registered source | Provenance state |",
        "| --- | --- | --- | --- | --- |",
    ]
    selected = evidence[:limit] if limit is not None else evidence
    if not selected:
        lines.append("| - | 尚未記錄 evidence | - | - | - |")
        return lines
    for item in selected:
        quality = item.get("quality", {})
        source = item.get("source", {})
        source_text = source.get("document_id") or "未記錄"
        if source.get("location"):
            source_text = f"{source_text} @ {source['location']}"
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{_cell(_entity_id(item))}`",
                    _cell(item.get("content", ""), 240),
                    _cell(
                        f"{item.get('evidence_type', 'OTHER')} / "
                        f"{quality.get('strength', 'UNKNOWN')} "
                        f"{quality.get('reliability', '')}"
                    ),
                    _cell(source_text, 140),
                    _zh_tw_provenance_label(item),
                ]
            )
            + " |"
        )
    if limit is not None and len(evidence) > limit:
        lines.append(
            f"\n_Brief 僅顯示 {limit}/{len(evidence)} 筆；使用 `standard` 或 `full` 查看全部。_"
        )
    return lines


def _zh_tw_source_inventory(report: ContractReport) -> list[str]:
    statuses = {
        str(item.get("coverage_status", "")) for item in report.source_inventory
    }
    if "registered_evidence_only" in statuses or not report.source_inventory:
        note = (
            "_沒有 pinned input manifest；此處只涵蓋 evidence 已引用的 registered "
            "sources，不能解讀為完整原始資料清冊。_"
        )
    else:
        note = (
            "_清冊由 pinned input manifest 建立，再合併每份 document 的 evidence "
            "coverage。衍生 extracts 不等於彼此獨立的 clinical sources。_"
        )
    lines = [
        note,
        "",
        "| Document | Kind | Media type | SHA-256 | Independence | Group / parent | Evidence | Provenance-state true | Status |",
        "| --- | --- | --- | --- | --- | --- | ---: | ---: | --- |",
    ]
    if not report.source_inventory:
        lines.append(
            "| - | - | - | - | unknown | - | 0 | 0 | registered_evidence_only |"
        )
        return lines
    for item in report.source_inventory:
        lines.append(
            "| "
            + " | ".join(
                [
                    _cell(item.get("document") or "未記錄"),
                    _cell(item.get("source_kind") or "未記錄"),
                    _cell(item.get("media_type") or "未記錄"),
                    _cell(item.get("sha256") or "未記錄"),
                    _cell(item.get("independence_status") or "unknown"),
                    _cell(
                        f"{item.get('source_group_id') or '-'} / "
                        f"{item.get('parent_document_id') or '-'}"
                    ),
                    str(item.get("evidence_count", 0)),
                    str(item.get("verified_count", 0)),
                    _cell(item.get("coverage_status", "unknown")),
                ]
            )
            + " |"
        )
    return lines


def _zh_tw_timeline(report: ContractReport) -> list[str]:
    events = report.timeline.get("events", []) if report.timeline else []
    lines = [
        "| Source time expression | Temporal state | Clinical phase | Event / finding | Registered source | Provenance state |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    if not events:
        lines.append("| - | - | - | 沒有 timeline event | - | - |")
        return lines
    for event in events:
        temporal = event.get("temporal") or {}
        temporal_kind = _cell(temporal.get("kind") or "unknown")
        chronology = _cell(event.get("chronology_status") or "UNPOSITIONED")
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{_cell(event.get('time') or '-')}`",
                    f"`{temporal_kind}` / `{chronology}`",
                    _cell(event.get("phase") or "General"),
                    _cell(event.get("content") or "-", 360),
                    f"`{_cell(event.get('source_document') or 'Record')}`",
                    "registered-source check true"
                    if event.get("verified")
                    else "未完成",
                ]
            )
            + " |"
        )
    return lines


def _zh_tw_cognitive_safety(
    thinking_chain: list[ThinkingStepRecord],
) -> list[str]:
    uncertainties = _unique_thinking_values(thinking_chain, "uncertainty_factors")
    biases = _unique_thinking_values(thinking_chain, "potential_biases")
    assumptions = _unique_thinking_values(thinking_chain, "assumptions_made")
    gaps = [
        _cell(step.get("content", ""), 500)
        for step in thinking_chain
        if step.get("thinking_type") == "EVIDENCE_GAP_IDENTIFIED"
    ]
    lines = ["**Evidence gaps / unknowns**"]
    lines.extend(f"- {value}" for value in _unique([*gaps, *uncertainties]))
    if not gaps and not uncertainties:
        lines.append("- 未明確記錄；這是 completeness gap，不代表沒有 unknown。")
    lines.extend(["", "**Potential cognitive biases**"])
    lines.extend(f"- {value}" for value in biases)
    if not biases:
        lines.append("- 未明確記錄 bias review。")
    lines.extend(["", "**Assumptions**"])
    lines.extend(f"- {value}" for value in assumptions)
    if not assumptions:
        lines.append("- 未明確記錄 assumptions。")
    return lines


def _zh_tw_root_cause_analysis(report: ContractReport) -> list[str]:
    """Compose clinician-facing RCA sections from small deterministic presenters."""
    return [
        "_RCA 用來檢查可能的 system contribution 與 proof obligations；不是 clinical "
        "causality proof，也不能把 association 直接升格為 root cause。_",
        "",
        *_zh_tw_rca_session(report),
        "",
        "### Fishbone (Ishikawa)",
        "",
        *_zh_tw_fishbone(report),
        "",
        "### Why / proposed roots",
        "",
        *_zh_tw_proposed_roots(report),
        "",
        "### Conservative causation audit",
        "",
        *_zh_tw_causation_audits(report),
        "",
        "### HFACS classifications",
        "",
        *_zh_tw_hfacs(report),
        "",
        "### Gap / conflict detection",
        "",
        *_zh_tw_gaps(report),
    ]


def _zh_tw_rca_session(report: ContractReport) -> list[str]:
    if report.rca_session:
        lines = [
            f"- Case：{_cell(report.rca_session.get('case_title', '未記錄'), 400)}",
            f"- Problem statement：{_cell(report.rca_session.get('problem_statement') or '未記錄', 600)}",
            f"- Stage / status：`{_cell(report.rca_session.get('current_stage', 'unknown'))}` / `{_cell(report.rca_session.get('status', 'unknown'))}`",
        ]
        if report.rca_session.get("source_manifest_digest"):
            lines.append(
                f"- Source manifest：{report.rca_session.get('source_document_count', 0)} "
                f"document(s)，`{_cell(report.rca_session['source_manifest_digest'])}`"
            )
        return lines
    return ["- 沒有 persisted RCA session metadata。"]


def _zh_tw_fishbone(report: ContractReport) -> list[str]:
    categories = (
        report.fishbone.get("categories", [])
        if isinstance(report.fishbone, Mapping)
        else []
    )
    cause_rows = [
        (category, cause)
        for category in categories
        if isinstance(category, Mapping)
        for cause in category.get("causes", [])
        if isinstance(cause, Mapping)
    ]
    if not cause_rows:
        return ["- 沒有 persisted Fishbone cause。"]
    return [
        f"- **{_cell(category.get('category', 'unknown'))}**："
        f"{_cell(cause.get('description', ''), 700)} "
        f"(evidence links: {len(cause.get('evidence', []))}; "
        f"HFACS: `{_cell(cause.get('hfacs_code') or '-')}`)"
        for category, cause in cause_rows
    ]


def _zh_tw_proposed_roots(report: ContractReport) -> list[str]:
    if not report.root_causes:
        return ["- 沒有 persisted proposed root。"]
    return [
        (
            f"- `{_cell(root.get('id', 'unknown'))}` "
            f"{_cell(root.get('answer', ''), 700)}；audit "
            f"`{_cell(root.get('causation_result') or 'NOT_AUDITED')}`；"
            f"disposition `{_cell(root.get('disposition') or 'PROPOSED')}`。"
        )
        for root in report.root_causes
    ]


def _zh_tw_causation_audits(report: ContractReport) -> list[str]:
    if not report.causation_verifications:
        return ["- 沒有 persisted causation audit。"]
    lines: list[str] = []
    for audit in report.causation_verifications:
        cause = audit.get("cause_event", {})
        effect = audit.get("effect_event", {})
        established = audit.get("clinical_causality_established") is True
        lines.extend(
            [
                f"- Audit `{_cell(audit.get('verification_id', 'unknown'))}`："
                f"{_cell(cause.get('description', ''), 500)} → "
                f"{_cell(effect.get('description', ''), 500)}",
                f"  - Result：`{_cell(audit.get('overall_result', 'unknown'))}`",
                f"  - Scope：`{_cell(audit.get('audit_scope', 'unknown'))}`",
                "  - Clinical causality：" + ("已建立" if established else "未建立"),
            ]
        )
    return lines


def _zh_tw_hfacs(report: ContractReport) -> list[str]:
    if not report.hfacs_classifications:
        return ["- 沒有 persisted HFACS classification。"]
    return [
        (
            f"- `{_cell(classification.get('hfacs_code', 'unknown'))}` — "
            f"{_cell(classification.get('cause', ''), 600)}；source "
            f"`{_cell(classification.get('source', 'unknown'))}`。"
        )
        for classification in report.hfacs_classifications
    ]


def _zh_tw_gaps(report: ContractReport) -> list[str]:
    gap = report.gap_analysis
    if not isinstance(gap, Mapping):
        return ["- 沒有 clinical gap analysis。"]
    lines = [
        f"- Conflicts：{gap.get('total_conflicts', 0)} total；"
        f"{gap.get('critical_count', 0)} critical；"
        f"{gap.get('high_count', 0)} high。",
        "- Safety invariants："
        + ("met" if gap.get("safety_invariants_met") else "not met"),
    ]
    for conflict in gap.get("conflicts", []):
        if not isinstance(conflict, Mapping):
            continue
        lines.append(
            f"- `{_cell(conflict.get('severity', 'unknown'))}` "
            f"{_cell(conflict.get('title', ''), 500)}；remedy："
            f"{_cell(conflict.get('actionable_remedy', ''), 500)}"
        )
    return lines


def _zh_tw_conformance_checks(report: ContractReport) -> list[str]:
    if not report.conformance_checks:
        return ["- 沒有 conformance checks；此 snapshot 不能視為 Final。"]
    lines = [
        "_以下只驗 structure、lineage 與 safety gates，不驗 clinical truth。_",
        "",
        "| Code | Status | Severity | Message | References |",
        "| --- | --- | --- | --- | --- |",
    ]
    for check in report.conformance_checks:
        refs = ", ".join(str(ref) for ref in check.refs) or "-"
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{_cell(check.code)}`",
                    f"`{_cell(check.status.value)}`",
                    f"`{_cell(check.severity.value)}`",
                    _cell(check.message, 360),
                    _cell(refs, 360),
                ]
            )
            + " |"
        )
    return lines


def _zh_tw_reasoning_audit(
    reasoning_chain: list[ReasoningStepRecord],
    detail_level: str,
    evidence: list[EvidenceRecord],
) -> list[str]:
    if not reasoning_chain:
        return ["- 沒有 reasoning steps。"]
    lines = [
        "| Step | Type | Action | Current evidence provenance |",
        "| ---: | --- | --- | --- |",
    ]
    for step in reasoning_chain:
        states = _current_reasoning_provenance(step, evidence)
        provenance = _reasoning_provenance_summary(states)
        lines.append(
            "| "
            + " | ".join(
                [
                    str(step.get("sequence_number", "-")),
                    _cell(step.get("step_type", "UNKNOWN")),
                    _cell(step.get("content", ""), 220),
                    provenance,
                ]
            )
            + " |"
        )
        if detail_level == "full":
            lines.append(
                f"\n**Step {step.get('sequence_number', '-')} rationale：** "
                f"{_cell(_reasoning_rationale(step), 700)}"
            )
    return lines


def _reasoning_provenance_summary(states: object) -> str:
    if not isinstance(states, Sequence) or isinstance(states, str) or not states:
        return "-"
    labels = []
    for state in states:
        if not isinstance(state, Mapping):
            continue
        evidence_id = _cell(state.get("evidence_id", "unknown"))
        if state.get("verified"):
            method = _cell(state.get("verification_method") or "RECORDED_VERIFIED")
            labels.append(f"{evidence_id}: true ({method})")
        else:
            labels.append(f"{evidence_id}: false")
    return _cell(", ".join(labels) or "-", 220)


def _current_reasoning_provenance(
    step: ReasoningStepRecord,
    evidence: list[EvidenceRecord],
) -> list[dict[str, Any]]:
    """Backfill current provenance for snapshots created before the typed field."""
    persisted_states = step.get("evidence_verification_states", [])
    if (
        isinstance(persisted_states, Sequence)
        and not isinstance(persisted_states, str)
        and persisted_states
    ):
        return [dict(item) for item in persisted_states if isinstance(item, Mapping)]
    evidence_by_id = {_entity_id(item): item for item in evidence}
    states = []
    for raw_id in step.get("evidence_ids", []):
        evidence_id = str(raw_id)
        item = evidence_by_id.get(evidence_id)
        if item is None:
            continue
        states.append(
            {
                "evidence_id": evidence_id,
                "verified": bool(item.get("verified")),
                "verification_method": item.get("verification_method"),
            }
        )
    return states


def _reasoning_rationale(step: ReasoningStepRecord) -> str:
    """Remove a stale ingestion-time verification suffix from report prose."""
    rationale = str(step.get("rationale", ""))
    if ", Verified:" in rationale:
        return rationale.split(", Verified:", 1)[0]
    return rationale


def _executive_summary(
    conclusion_hypotheses: list[HypothesisRecord],
    evidence: list[EvidenceRecord],
    report: ContractReport,
) -> list[str]:
    if not conclusion_hypotheses:
        leading = (
            "No explicit leading diagnosis has been selected through the audited "
            "DDx mutation; no lead is inferred from order or numeric compatibility."
            if report.hypotheses
            else "No diagnosis hypothesis has been recorded."
        )
    else:
        first = conclusion_hypotheses[0]
        diagnosis = first.get("diagnosis", {})
        display = _cell(diagnosis.get("display", "Unknown diagnosis"))
        certainty = _cell(first.get("certainty", "UNKNOWN"))
        leading = (
            f"Explicit audited leading diagnosis: **{display}** "
            f"(qualitative certainty `{certainty}`, "
            f"status `{_cell(first.get('status', 'UNKNOWN'))}`). "
            "This is a working ledger position, not a calibrated clinical probability."
        )
    verified = sum(bool(item.get("verified")) for item in evidence)
    gaps = _unique_thinking_values(report.thinking_chain, "uncertainty_factors")
    return [
        leading,
        "",
        (
            f"The artifact contains **{_count_phrase(len(evidence), 'evidence record')}** "
            f"({verified} with a successful registered-source provenance state), "
            f"**{_count_phrase(len(report.hypotheses), 'hypothesis', 'hypotheses')}**, "
            f"and **{_count_phrase(len(gaps), 'recorded uncertainty factor')}**."
        ),
        "",
        (
            "A successful provenance state does not establish source independence, "
            "upstream binary/EHR fidelity, clinical interpretation, or diagnostic truth."
        ),
    ]


def _hypothesis_table(hypotheses: list[HypothesisRecord]) -> list[str]:
    lines = [
        "_Order is a working ledger presentation, not a calibrated probability ranking._",
        "",
        "| Order | Diagnosis | Code | Mechanism | Role | Status | Qualitative certainty | LR>1 | LR<1 | Neutral / unquantified | Planned tests |",
        "| ---: | --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    if not hypotheses:
        lines.append(
            "| - | No hypotheses recorded | - | - | - | - | - | - | - | - | - |"
        )
        return lines
    for rank, hypothesis in enumerate(hypotheses, 1):
        diagnosis_display, code = _diagnosis_cells(hypothesis)
        relationships = _hypothesis_lr_relationships(hypothesis)
        lines.append(
            "| "
            + " | ".join(
                [
                    str(rank),
                    diagnosis_display,
                    _cell(code),
                    _cell(hypothesis.get("mechanism_category", "UNKNOWN")),
                    _cell(hypothesis.get("diagnostic_role", "UNKNOWN")),
                    _cell(hypothesis.get("status", "UNKNOWN")),
                    _cell(hypothesis.get("certainty", "UNKNOWN")),
                    str(len(relationships["supporting"])),
                    str(len(relationships["contradicting"])),
                    str(len(relationships["neutral"])),
                    str(len(hypothesis.get("planned_tests", []))),
                ]
            )
            + " |"
        )
    return lines


def _diagnosis_cells(hypothesis: HypothesisRecord) -> tuple[str, str]:
    diagnosis = hypothesis.get("diagnosis")
    if not isinstance(diagnosis, Mapping):
        return "Unknown diagnosis", "INVALID CODE: missing diagnosis"
    display = _cell(diagnosis.get("display", "Unknown"))
    try:
        concept = ClinicalConcept.model_validate(diagnosis)
    except ValidationError:
        raw_code = (
            f"{diagnosis.get('system', 'UNKNOWN')}:{diagnosis.get('code', 'unknown')}"
        )
        return display, _cell(f"INVALID CODE: {raw_code}")
    return display, _cell(f"{concept.system.value}:{concept.code}")


def _evidence_table(
    evidence: list[EvidenceRecord],
    limit: int | None,
    hypotheses: list[HypothesisRecord] | None = None,
) -> list[str]:
    relationship_counts = _evidence_relationship_counts(hypotheses or [])
    lines = [
        "| Evidence | Finding | Type / Quality | Source | Links | Provenance check |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    selected = evidence[:limit] if limit is not None else evidence
    if not selected:
        lines.append("| - | No evidence recorded | - | - | - | - |")
        return lines
    for item in selected:
        quality = item.get("quality", {})
        source = item.get("source", {})
        support, contradict, neutral = relationship_counts.get(
            _entity_id(item), (0, 0, 0)
        )
        links = f"LR>1 {support} / LR<1 {contradict} / neutral {neutral}"
        source_text = source.get("document_id") or "not recorded"
        if source.get("location"):
            source_text = f"{source_text} @ {source['location']}"
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{_cell(_entity_id(item))}`",
                    _cell(item.get("content", ""), 180),
                    _cell(
                        f"{item.get('evidence_type', 'OTHER')} / "
                        f"{quality.get('strength', 'UNKNOWN')} "
                        f"{quality.get('reliability', '')}"
                    ),
                    _cell(source_text, 100),
                    links,
                    _english_provenance_label(item),
                ]
            )
            + " |"
        )
    if limit is not None and len(evidence) > limit:
        lines.append(
            f"\n_Brief view shows {limit} of {len(evidence)} evidence records; "
            "use `standard` or `full` for the complete matrix._"
        )
    return lines


def _source_inventory(report: ContractReport) -> list[str]:
    """Render provenance coverage without claiming undeclared raw-file ingest."""
    statuses = {
        str(item.get("coverage_status", "")) for item in report.source_inventory
    }
    if "registered_evidence_only" in statuses or not report.source_inventory:
        scope_note = (
            "_No input manifest was available. This inventory covers only source "
            "documents referenced by registered evidence (`registered_evidence_only`)._"
        )
    else:
        scope_note = (
            "_Inventory starts from the pinned input manifest and merges evidence "
            "registered for each document._"
        )
    lines = [
        scope_note,
        "",
        "| Document | Kind | Media type | SHA-256 | Independence | Group / parent | Evidence | Provenance-state true | Coverage status |",
        "| --- | --- | --- | --- | --- | --- | ---: | ---: | --- |",
    ]
    if not report.source_inventory:
        lines.append(
            "| - | - | - | - | unknown | - | 0 | 0 | registered_evidence_only |"
        )
        return lines
    for item in report.source_inventory:
        lines.append(
            "| "
            + " | ".join(
                [
                    _cell(item.get("document") or "not recorded"),
                    _cell(item.get("source_kind") or "not recorded"),
                    _cell(item.get("media_type") or "not recorded"),
                    _cell(item.get("sha256") or "not recorded"),
                    _cell(item.get("independence_status") or "unknown"),
                    _cell(
                        f"{item.get('source_group_id') or '-'} / "
                        f"{item.get('parent_document_id') or '-'}"
                    ),
                    str(item.get("evidence_count", 0)),
                    str(item.get("verified_count", 0)),
                    _cell(item.get("coverage_status", "unknown")),
                ]
            )
            + " |"
        )
    return lines


def _root_cause_analysis(  # noqa: PLR0912, PLR0915
    report: ContractReport,
) -> list[str]:
    """Render persisted RCA artifacts and deterministic gap/conflict findings."""
    lines: list[str] = ["### RCA Session", ""]
    if report.rca_session:
        session = report.rca_session
        lines.extend(
            [
                f"- Case: {_cell(session.get('case_title', 'not recorded'), 240)}",
                f"- Case type: `{_cell(session.get('case_type', 'unknown'))}`",
                f"- Stage / status: `{_cell(session.get('current_stage', 'unknown'))}` / "
                f"`{_cell(session.get('status', 'unknown'))}`",
                f"- Problem statement: {_cell(session.get('problem_statement') or 'not recorded', 400)}",
            ]
        )
        if session.get("source_manifest_digest"):
            lines.append(
                f"- Source manifest: {session.get('source_document_count', 0)} document(s), "
                f"`{_cell(session['source_manifest_digest'])}`"
            )
    else:
        lines.append("- No persisted RCA session metadata was available.")

    lines.extend(["", "### Fishbone (Ishikawa)", ""])
    categories = (
        report.fishbone.get("categories", [])
        if isinstance(report.fishbone, Mapping)
        else []
    )
    fishbone_rows = [
        (category, cause)
        for category in categories
        if isinstance(category, Mapping)
        for cause in category.get("causes", [])
        if isinstance(cause, Mapping)
    ]
    if not fishbone_rows:
        lines.append("- No persisted Fishbone causes were available.")
    else:
        lines.extend(
            [
                "| Category | Cause | Evidence links | Verified | HFACS |",
                "| --- | --- | ---: | --- | --- |",
            ]
        )
        for category, cause in fishbone_rows:
            lines.append(
                "| "
                + " | ".join(
                    [
                        _cell(category.get("category", "unknown")),
                        _cell(cause.get("description", ""), 240),
                        str(len(cause.get("evidence", []))),
                        "Yes" if cause.get("verified") else "No",
                        _cell(cause.get("hfacs_code") or "-"),
                    ]
                )
                + " |"
            )

    lines.extend(["", "### Why Tree and Root Causes", ""])
    nodes = (
        report.why_tree.get("nodes", []) if isinstance(report.why_tree, Mapping) else []
    )
    if nodes:
        lines.extend(
            [
                "| Why | Question | Answer | Root cause | Evidence links |",
                "| ---: | --- | --- | --- | ---: |",
            ]
        )
        for node in nodes:
            if not isinstance(node, Mapping):
                continue
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(node.get("level", "-")),
                        _cell(node.get("question", ""), 220),
                        _cell(node.get("answer", ""), 240),
                        "Yes" if node.get("is_root_cause") else "No",
                        str(len(node.get("evidence", []))),
                    ]
                )
                + " |"
            )
    else:
        lines.append("- No persisted Why tree was available.")
    if report.root_causes:
        lines.extend(["", "**Structured root-cause dispositions**"])
        for root_cause in report.root_causes:
            causation_result = _cell(
                root_cause.get("causation_result") or "NOT_AUDITED"
            )
            disposition = _cell(root_cause.get("disposition") or "PROPOSED")
            lines.append(
                f"- `{_cell(root_cause.get('id', 'unknown'))}` "
                f"{_cell(root_cause.get('answer', ''), 300)} "
                f"(evidence {len(root_cause.get('evidence', []))}; "
                f"audit `{causation_result}`; disposition `{disposition}`)"
            )

    lines.extend(["", "### Conservative Causation Audit", ""])
    lines.append(
        "_These records audit submitted proof obligations; they do not establish "
        "clinical causality._"
    )
    lines.append("")
    if not report.causation_verifications:
        lines.append("- No persisted conservative causation audit was available.")
    else:
        lines.extend(
            [
                "| Audit | Cause ID | Proposed relationship | Result | Scope | Clinical causality |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
        )
        for verification in report.causation_verifications:
            cause_event = verification.get("cause_event", {})
            effect_event = verification.get("effect_event", {})
            lines.append(
                "| "
                + " | ".join(
                    [
                        _cell(verification.get("verification_id", "unknown")),
                        _cell(cause_event.get("id") or "unlinked"),
                        _cell(
                            f"{cause_event.get('description', '')} -> "
                            f"{effect_event.get('description', '')}",
                            320,
                        ),
                        _cell(verification.get("overall_result", "unknown")),
                        _cell(verification.get("audit_scope", "unknown")),
                        (
                            "Established"
                            if verification.get("clinical_causality_established")
                            is True
                            else "Not established"
                        ),
                    ]
                )
                + " |"
            )

    lines.extend(["", "### HFACS Classifications", ""])
    if not report.hfacs_classifications:
        lines.append("- No persisted HFACS classification was available.")
    else:
        lines.extend(
            [
                "| Cause | HFACS code | Match semantics | Source |",
                "| --- | --- | --- | --- |",
            ]
        )
        for classification in report.hfacs_classifications:
            lines.append(
                "| "
                + " | ".join(
                    [
                        _cell(classification.get("cause", ""), 240),
                        _cell(classification.get("hfacs_code", "unknown")),
                        "heuristic_rule_match / not calibrated",
                        _cell(classification.get("source", "unknown")),
                    ]
                )
                + " |"
            )

    lines.extend(["", "### Gap and Conflict Detection", ""])
    gap = report.gap_analysis
    if not isinstance(gap, Mapping):
        lines.append("- No clinical gap analysis was available.")
        return lines
    lines.append(
        f"- Conflicts: {gap.get('total_conflicts', 0)} total; "
        f"{gap.get('critical_count', 0)} critical; {gap.get('high_count', 0)} high."
    )
    lines.append(
        "- Safety invariants met: "
        + ("Yes" if gap.get("safety_invariants_met") else "No")
    )
    conflicts = gap.get("conflicts", [])
    if conflicts:
        lines.extend(
            [
                "",
                "| Severity | Category | Conflict | Remedy |",
                "| --- | --- | --- | --- |",
            ]
        )
        for conflict in conflicts:
            if not isinstance(conflict, Mapping):
                continue
            lines.append(
                "| "
                + " | ".join(
                    [
                        _cell(conflict.get("severity", "unknown")),
                        _cell(conflict.get("category", "unknown")),
                        _cell(conflict.get("title", ""), 260),
                        _cell(conflict.get("actionable_remedy", ""), 300),
                    ]
                )
                + " |"
            )
    alerts = gap.get("guideline_alerts", [])
    if alerts:
        lines.extend(["", "**Guideline alerts**"])
        lines.extend(f"- {_cell(alert, 400)}" for alert in alerts)
    return lines


def _cognitive_safety(thinking_chain: list[ThinkingStepRecord]) -> list[str]:
    uncertainties = _unique_thinking_values(thinking_chain, "uncertainty_factors")
    biases = _unique_thinking_values(thinking_chain, "potential_biases")
    assumptions = _unique_thinking_values(thinking_chain, "assumptions_made")
    gaps = [
        _cell(step.get("content", ""), 240)
        for step in thinking_chain
        if step.get("thinking_type") == "EVIDENCE_GAP_IDENTIFIED"
    ]
    lines = ["**Evidence gaps / uncertainties**"]
    lines.extend(f"- {value}" for value in _unique([*gaps, *uncertainties]))
    if not gaps and not uncertainties:
        lines.append("- None explicitly recorded")
    lines.extend(["", "**Potential biases**"])
    lines.extend(f"- {value}" for value in biases)
    if not biases:
        lines.append("- None explicitly recorded")
    lines.extend(["", "**Assumptions**"])
    lines.extend(f"- {value}" for value in assumptions)
    if not assumptions:
        lines.append("- None explicitly recorded")
    return lines


def _quality_metrics(report: ContractReport) -> list[str]:
    evidence = report.evidence_metrics
    reasoning = report.reasoning_metrics
    readiness = report.report_readiness
    if evidence is None and reasoning is None and readiness is None:
        return ["- Quality metrics were omitted by request."]
    lines: list[str] = []
    if evidence is not None:
        lines.extend(
            [
                f"- Evidence verification rate: {_percent(evidence.verification_rate)}",
                f"- Strong / moderate / weak evidence: "
                f"{evidence.strong_evidence} / {evidence.moderate_evidence} / "
                f"{evidence.weak_evidence}",
            ]
        )
    if reasoning is not None:
        lines.extend(
            [
                "- Average reasoning confidence: not presented; legacy hypothesis "
                "steps may contain uncalibrated compatibility values",
                f"- Evidence-linked reasoning coverage: "
                f"{_percent(reasoning.evidence_coverage)}",
                f"- Hypothesis-linked reasoning coverage: "
                f"{_percent(reasoning.hypothesis_coverage)}",
                f"- Alternatives / biases / uncertainties: "
                f"{reasoning.alternatives_considered} / "
                f"{reasoning.biases_identified} / "
                f"{reasoning.uncertainties_acknowledged}",
            ]
        )
    if readiness is not None:
        lines.extend(
            [
                f"- Finalization readiness: "
                f"{'Ready' if readiness.get('is_ready_for_report') else 'Not ready'}",
                f"- Completeness score: "
                f"{_percent(_safe_float(readiness.get('completeness_score')))}",
            ]
        )
    return lines


def _automated_findings(report: ContractReport) -> list[str]:
    """Identify structural review gaps without making clinical judgments."""
    findings = [
        *_evidence_findings(report),
        *_hypothesis_findings(report),
        *_cognitive_findings(report),
        *_reasoning_findings(report),
        *_graph_findings(report),
        *_rca_findings(report),
        *_readiness_findings(report),
    ]
    lines = [
        "_These checks assess report structure and traceability, not diagnostic correctness._",
        "",
    ]
    if findings:
        lines.extend(f"- WARNING: {finding}" for finding in findings)
    else:
        lines.append("- No structural completeness warnings detected.")
    return lines


def _conformance_checks(report: ContractReport) -> list[str]:
    """Render the canonical machine-readable checks without changing them."""
    if not report.conformance_checks:
        return [
            "- No conformance checks are attached; this snapshot cannot be treated "
            "as final."
        ]
    lines = [
        "_These deterministic checks validate structure and lineage, not clinical "
        "truth._",
        "",
        "| Code | Status | Severity | Message | References |",
        "| --- | --- | --- | --- | --- |",
    ]
    for check in report.conformance_checks:
        refs = ", ".join(str(ref) for ref in check.refs) or "-"
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{_cell(check.code)}`",
                    f"`{_cell(check.status.value)}`",
                    f"`{_cell(check.severity.value)}`",
                    _cell(check.message, 320),
                    _cell(refs, 320),
                ]
            )
            + " |"
        )
    return lines


def _evidence_findings(report: ContractReport) -> list[str]:
    findings = [] if report.evidence else ["No evidence records have been registered."]
    missing_provenance = sum(
        not item.get("source", {}).get("document_id") for item in report.evidence
    )
    if missing_provenance:
        findings.append(
            f"{missing_provenance} evidence record(s) lack a source document."
        )

    unverified = sum(not item.get("verified") for item in report.evidence)
    if unverified:
        findings.append(
            f"{unverified} evidence record(s) have no successful registered-source "
            "provenance check."
        )
    return findings


def _hypothesis_findings(report: ContractReport) -> list[str]:
    findings: list[str] = []
    if not report.hypotheses:
        findings.append("No diagnosis hypotheses have been recorded.")
    elif len(report.hypotheses) < 3:
        findings.append(
            f"Fewer than 3 differential diagnoses evaluated ({len(report.hypotheses)}/3); "
            "risk of premature diagnostic closure."
        )

    unlinked_hypotheses = sum(
        not hypothesis.get("supporting_evidence_ids")
        and not hypothesis.get("contradicting_evidence_ids")
        for hypothesis in report.hypotheses
    )
    if unlinked_hypotheses:
        findings.append(
            f"{unlinked_hypotheses} hypothesis/hypotheses have no linked evidence."
        )
    return findings


def _cognitive_findings(report: ContractReport) -> list[str]:
    findings: list[str] = []
    uncertainties = _unique_thinking_values(
        report.thinking_chain, "uncertainty_factors"
    )
    if not uncertainties:
        findings.append("No uncertainty factors have been explicitly recorded.")
    if not _unique_thinking_values(report.thinking_chain, "potential_biases"):
        findings.append("No cognitive-bias review has been explicitly recorded.")
    return findings


def _rca_findings(report: ContractReport) -> list[str]:
    findings: list[str] = []
    if not report.root_causes:
        findings.append("No proposed root cause has been persisted.")
        return findings
    unaudited = sum(
        not root_cause.get("causation_verification_id")
        for root_cause in report.root_causes
    )
    if unaudited:
        findings.append(
            f"{unaudited} proposed root cause(s) lack a linked causation audit."
        )
    insufficient = sum(
        root_cause.get("disposition") != "AUDIT_OBLIGATIONS_PASSED"
        for root_cause in report.root_causes
        if root_cause.get("causation_verification_id")
    )
    if insufficient:
        findings.append(
            f"{insufficient} root-cause candidate(s) remain PROPOSED because the "
            "conservative audit obligations did not all pass."
        )
    return findings


def _reasoning_findings(report: ContractReport) -> list[str]:
    findings: list[str] = []
    if report.reasoning_metrics is not None:
        if report.reasoning_metrics.evidence_coverage < 0.5:
            findings.append("Fewer than half of reasoning steps reference evidence.")
        if report.reasoning_metrics.hypothesis_coverage < 0.5:
            findings.append("Fewer than half of reasoning steps reference hypotheses.")
    return findings


def _graph_findings(report: ContractReport) -> list[str]:
    findings: list[str] = []
    if report.evidence_graph:
        graph_warnings = report.evidence_graph.get("warnings", [])
        if isinstance(graph_warnings, Sequence) and not isinstance(graph_warnings, str):
            findings.extend(
                f"Evidence graph: {_cell(warning, 240)}" for warning in graph_warnings
            )
    return findings


def _readiness_findings(report: ContractReport) -> list[str]:
    readiness = report.report_readiness
    if not readiness or readiness.get("is_ready_for_report"):
        return []
    missing = readiness.get("missing_prerequisites", [])
    if not missing:
        return ["Clinical guidance has not reached final-report readiness."]
    return ["Finalization prerequisite: " + _cell(item, 300) for item in missing]


def _reasoning_audit(
    reasoning_chain: list[ReasoningStepRecord],
    detail_level: str,
    evidence: list[EvidenceRecord],
) -> list[str]:
    if not reasoning_chain:
        return ["- No reasoning steps were included."]
    lines = [
        "| Step | Type | Action | Current evidence provenance |",
        "| ---: | --- | --- | --- |",
    ]
    for step in reasoning_chain:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(step.get("sequence_number", "-")),
                    _cell(step.get("step_type", "UNKNOWN")),
                    _cell(step.get("content", ""), 180),
                    _reasoning_provenance_summary(
                        _current_reasoning_provenance(step, evidence)
                    ),
                ]
            )
            + " |"
        )
        if detail_level == "full":
            lines.append(
                f"\n**Step {step.get('sequence_number', '-')} rationale:** "
                f"{_cell(_reasoning_rationale(step), 500)}"
            )
    return lines


def _thinking_audit(thinking_chain: list[ThinkingStepRecord]) -> list[str]:
    if not thinking_chain:
        return ["- No agent-authored rationale records were included."]
    lines: list[str] = []
    for index, step in enumerate(thinking_chain, 1):
        lines.extend(
            [
                f"### Rationale {index}: {_cell(step.get('thinking_type', 'UNKNOWN'))}",
                "",
                _cell(step.get("content", ""), 500),
                "",
                f"- Recorded rationale: {_cell(step.get('internal_reasoning', ''), 800)}",
                "",
            ]
        )
    return lines


def _unique_thinking_values(
    thinking_chain: list[ThinkingStepRecord],
    field: str,
) -> list[str]:
    values: list[str] = []
    for step in thinking_chain:
        raw_values = step.get(field, [])
        if isinstance(raw_values, Sequence) and not isinstance(raw_values, str):
            values.extend(_cell(value, 240) for value in raw_values)
    return _unique(values)


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _evidence_sort_key(item: EvidenceRecord) -> tuple[int, int, int, str]:
    quality = item.get("quality", {})
    linked_count = len(item.get("supports_hypothesis_ids", [])) + len(
        item.get("contradicts_hypothesis_ids", [])
    )
    return (
        int(bool(item.get("verified"))),
        _STRENGTH_RANK.get(str(quality.get("strength", "")), -1),
        linked_count,
        _entity_id(item),
    )


def _entity_id(item: EvidenceRecord) -> str:
    raw_id = item.get("id", "unknown")
    if isinstance(raw_id, Mapping):
        return str(raw_id.get("value", "unknown"))
    return str(raw_id)


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _percent(value: float | None) -> str:
    return "-" if value is None else f"{value:.0%}"


def _count_phrase(count: int, singular: str, plural: str | None = None) -> str:
    noun = singular if count == 1 else (plural or f"{singular}s")
    return f"{count} {noun}"


def _cell(value: Any, max_length: int = 120) -> str:
    normalized = " ".join(str(value).split()).replace("|", "\\|")
    if len(normalized) > max_length:
        return f"{normalized[: max_length - 3].rstrip()}..."
    return normalized
