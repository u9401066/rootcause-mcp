"""Deterministic Markdown presenter for clinical reasoning reports."""

from __future__ import annotations

import logging
import os
from pathlib import Path, PureWindowsPath
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from rootcause_mcp.domain.value_objects.clinical_concept import ClinicalConcept
from rootcause_mcp.domain.value_objects.contract_report import ContractReport

if TYPE_CHECKING:
    from rootcause_mcp.domain.value_objects.report_sections import (
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


def _render_custom_template(
    report: ContractReport,
    detail_level: str,
    hypotheses: list[HypothesisRecord],
    evidence: list[EvidenceRecord],
    evidence_limit: int | None,
    template_path: str | Path,
    template_root: str | Path | None,
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
    top_prob = (
        _percent(_probability(conclusion_hypotheses[0]))
        if conclusion_hypotheses
        else "N/A"
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
    has_source_inventory_placeholder = "{{source_inventory_section}}" in template_text
    has_rca_analysis_placeholder = "{{rca_analysis_section}}" in template_text
    has_conformance_placeholder = "{{conformance_checks_section}}" in template_text
    placeholders: dict[str, str] = {
        "report_title": "Clinical Reasoning & Root Cause Report",
        "session_id": _cell(report.session_id),
        "report_id": _cell(report.report_id),
        "generated_at": report.generated_at.isoformat(),
        "report_status": "Final" if report.is_finalized else "Preliminary",
        "detail_level": detail_level,
        "executive_summary": "\n".join(
            _executive_summary(conclusion_hypotheses, evidence, report)
        ),
        "hypothesis_table": "\n".join(_hypothesis_table(hypotheses)),
        "top_diagnosis": top_diag,
        "top_probability": top_prob,
        "rule_out_summary": rule_out_summary,
        "must_not_miss_evaluated": (
            f"{must_not_miss_count} explicitly marked high-harm rule-out condition(s)"
        ),
        "evidence_table": "\n".join(_evidence_table(evidence, evidence_limit)),
        "source_inventory_section": source_inventory_section,
        "rca_analysis_section": rca_analysis_section,
        "conformance_checks_section": conformance_checks_section,
        "timeline_diagram": timeline_mermaid or "_No timeline diagram generated._",
        "timeline_table": timeline_table or "_No timeline table generated._",
        "cognitive_safety_section": "\n".join(_cognitive_safety(report.thinking_chain)),
        "automated_checks_section": "\n".join(_automated_findings(report)),
        "quality_metrics_section": "\n".join(_quality_metrics(report)),
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
    if not has_rca_analysis_placeholder:
        template_text = f"{template_text.rstrip()}\n\n{rca_analysis_section}\n"
    if not has_conformance_placeholder:
        template_text = f"{template_text.rstrip()}\n\n{conformance_checks_section}\n"
    return template_text.rstrip() + "\n"


def render_contract_report_markdown(
    report: ContractReport,
    detail_level: str = "standard",
    template_path: str | Path | None = None,
    template_root: str | Path | None = None,
) -> str:
    """Render a deterministic report, optionally from an allowlisted template."""
    if detail_level not in {"brief", "standard", "full"}:
        raise ValueError("detail_level must be brief, standard, or full")

    hypotheses = sorted(
        report.hypotheses,
        key=_probability,
        reverse=True,
    )
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
        )
        return custom_rendered

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
            *_evidence_table(evidence, evidence_limit),
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
        lines.extend(_reasoning_audit(report.reasoning_chain, detail_level))
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


def _executive_summary(
    conclusion_hypotheses: list[HypothesisRecord],
    evidence: list[EvidenceRecord],
    report: ContractReport,
) -> list[str]:
    if not conclusion_hypotheses:
        leading = (
            "No active diagnosis hypothesis is eligible for the report conclusion."
            if report.hypotheses
            else "No diagnosis hypothesis has been recorded."
        )
    else:
        first = conclusion_hypotheses[0]
        diagnosis = first.get("diagnosis", {})
        display = _cell(diagnosis.get("display", "Unknown diagnosis"))
        leading = (
            f"Leading recorded hypothesis: **{display}** "
            f"({_percent(_probability(first))}, "
            f"status `{_cell(first.get('status', 'UNKNOWN'))}`)."
        )
    verified = sum(bool(item.get("verified")) for item in evidence)
    gaps = _unique_thinking_values(report.thinking_chain, "uncertainty_factors")
    return [
        leading,
        "",
        (
            f"The artifact contains **{_count_phrase(len(evidence), 'evidence record')}** "
            f"({verified} independently verified), "
            f"**{_count_phrase(len(report.hypotheses), 'hypothesis', 'hypotheses')}**, "
            f"and **{_count_phrase(len(gaps), 'recorded uncertainty factor')}**."
        ),
    ]


def _hypothesis_table(hypotheses: list[HypothesisRecord]) -> list[str]:
    lines = [
        "| Rank | Diagnosis | Code | Status | Prior | Posterior | Supports | Contradicts |",
        "| ---: | --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    if not hypotheses:
        lines.append("| - | No hypotheses recorded | - | - | - | - | - | - |")
        return lines
    for rank, hypothesis in enumerate(hypotheses, 1):
        diagnosis_display, code = _diagnosis_cells(hypothesis)
        lines.append(
            "| "
            + " | ".join(
                [
                    str(rank),
                    diagnosis_display,
                    _cell(code),
                    _cell(hypothesis.get("status", "UNKNOWN")),
                    _percent(_safe_float(hypothesis.get("prior_probability"))),
                    _percent(_probability(hypothesis)),
                    str(len(hypothesis.get("supporting_evidence_ids", []))),
                    str(len(hypothesis.get("contradicting_evidence_ids", []))),
                ]
            )
            + " |"
        )
    return lines


def _diagnosis_cells(hypothesis: HypothesisRecord) -> tuple[str, str]:
    diagnosis = hypothesis.get("diagnosis")
    if not isinstance(diagnosis, dict):
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
) -> list[str]:
    lines = [
        "| Evidence | Finding | Type / Quality | Source | Links | Verified |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    selected = evidence[:limit] if limit is not None else evidence
    if not selected:
        lines.append("| - | No evidence recorded | - | - | - | - |")
        return lines
    for item in selected:
        quality = item.get("quality", {})
        source = item.get("source", {})
        links = (
            f"+{len(item.get('supports_hypothesis_ids', []))} / "
            f"-{len(item.get('contradicts_hypothesis_ids', []))}"
        )
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
                    "Yes" if item.get("verified") else "No",
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
    lines = [scope_note, ""]
    lines.extend(
        [
            "| Document | Kind | Media type | SHA-256 | Evidence | Verified | Coverage status |",
            "| --- | --- | --- | --- | ---: | ---: | --- |",
        ]
    )
    if not report.source_inventory:
        lines.append("| - | - | - | - | 0 | 0 | registered_evidence_only |")
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
        if isinstance(report.fishbone, dict)
        else []
    )
    fishbone_rows = [
        (category, cause)
        for category in categories
        if isinstance(category, dict)
        for cause in category.get("causes", [])
        if isinstance(cause, dict)
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
        report.why_tree.get("nodes", []) if isinstance(report.why_tree, dict) else []
    )
    if nodes:
        lines.extend(
            [
                "| Why | Question | Answer | Root cause | Evidence links |",
                "| ---: | --- | --- | --- | ---: |",
            ]
        )
        for node in nodes:
            if not isinstance(node, dict):
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
            root_confidence = _percent(_safe_float(root_cause.get("confidence")))
            causation_result = _cell(
                root_cause.get("causation_result") or "NOT_AUDITED"
            )
            disposition = _cell(root_cause.get("disposition") or "PROPOSED")
            lines.append(
                f"- `{_cell(root_cause.get('id', 'unknown'))}` "
                f"{_cell(root_cause.get('answer', ''), 300)} "
                f"(confidence {root_confidence}; "
                f"evidence {len(root_cause.get('evidence', []))}; "
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
                "| Audit | Cause ID | Proposed relationship | Result | Scope | Clinical causality | Confidence |",
                "| --- | --- | --- | --- | --- | --- | ---: |",
            ]
        )
        for verification in report.causation_verifications:
            cause_event = verification.get("cause_event", {})
            effect_event = verification.get("effect_event", {})
            verification_confidence: object = verification.get("confidence", {})
            confidence_value = (
                verification_confidence.get("value")
                if isinstance(verification_confidence, dict)
                else verification_confidence
            )
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
                        _percent(_safe_float(confidence_value)),
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
                "| Cause | HFACS code | Confidence | Source |",
                "| --- | --- | ---: | --- |",
            ]
        )
        for classification in report.hfacs_classifications:
            lines.append(
                "| "
                + " | ".join(
                    [
                        _cell(classification.get("cause", ""), 240),
                        _cell(classification.get("hfacs_code", "unknown")),
                        _percent(_safe_float(classification.get("confidence"))),
                        _cell(classification.get("source", "unknown")),
                    ]
                )
                + " |"
            )

    lines.extend(["", "### Gap and Conflict Detection", ""])
    gap = report.gap_analysis
    if not isinstance(gap, dict):
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
            if not isinstance(conflict, dict):
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
                f"- Average reasoning confidence: {_percent(reasoning.avg_confidence)}",
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
            f"{unverified} evidence record(s) have not been independently verified."
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
        if isinstance(graph_warnings, list):
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
) -> list[str]:
    if not reasoning_chain:
        return ["- No reasoning steps were included."]
    lines = [
        "| Step | Type | Action | Confidence |",
        "| ---: | --- | --- | ---: |",
    ]
    for step in reasoning_chain:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(step.get("sequence_number", "-")),
                    _cell(step.get("step_type", "UNKNOWN")),
                    _cell(step.get("content", ""), 180),
                    _percent(_safe_float(step.get("confidence"))),
                ]
            )
            + " |"
        )
        if detail_level == "full":
            lines.append(
                f"\n**Step {step.get('sequence_number', '-')} rationale:** "
                f"{_cell(step.get('rationale', ''), 500)}"
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
                f"- Confidence: {_percent(_safe_float(step.get('confidence')))}",
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
        if isinstance(raw_values, list):
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
    if isinstance(raw_id, dict):
        return str(raw_id.get("value", "unknown"))
    return str(raw_id)


def _probability(hypothesis: HypothesisRecord) -> float:
    return _safe_float(hypothesis.get("current_probability")) or 0.0


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
