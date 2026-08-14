"""Deterministic Markdown presenter for clinical reasoning reports."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import ValidationError

from rootcause_mcp.domain.value_objects.clinical_concept import ClinicalConcept
from rootcause_mcp.domain.value_objects.contract_report import ContractReport

_STRENGTH_RANK = {"STRONG": 3, "MODERATE": 2, "WEAK": 1, "ANECDOTAL": 0}


def _render_custom_template(
    report: ContractReport,
    detail_level: str,
    hypotheses: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    evidence_limit: int | None,
    template_path: str | Path,
) -> str | None:
    """Render report using an external Markdown template file if available."""
    tpl_path = Path(template_path)
    if not tpl_path.is_file():
        return None

    template_text = tpl_path.read_text(encoding="utf-8")
    top_diag = (
        hypotheses[0].get("diagnosis", {}).get("display", "Unknown")
        if hypotheses
        else "None"
    )
    top_prob = _percent(_probability(hypotheses[0])) if hypotheses else "N/A"
    refuted = [
        h.get("diagnosis", {}).get("display", "Unknown")
        for h in hypotheses
        if str(h.get("status", "")).upper() in {"EXCLUDED", "RULED_OUT"}
        or len(h.get("contradicting_evidence_ids", [])) > 0
    ]
    rule_out_summary = ", ".join(refuted) if refuted else "None explicitly refuted"

    reasoning_mermaid = ""
    if detail_level in {"standard", "full"} and report.reasoning_chain:
        from rootcause_mcp.domain.entities.reasoning_step import (
            ReasoningChain,
            ReasoningStep,
        )
        from rootcause_mcp.interface.mermaid import (
            render_reasoning_chain_mermaid,
        )

        chain = ReasoningChain(
            session_id=report.session_id,
            steps=[ReasoningStep.model_validate(s) for s in report.reasoning_chain],
        )
        reasoning_mermaid = render_reasoning_chain_mermaid(chain)

    evidence_mermaid = ""
    if report.evidence_graph and report.evidence_graph.get("mermaid"):
        evidence_mermaid = str(report.evidence_graph["mermaid"])

    timeline_mermaid = ""
    timeline_table = ""
    if evidence:
        from rootcause_mcp.domain.entities.evidence import Evidence
        from rootcause_mcp.interface.mermaid import build_timeline

        try:
            ev_entities = [Evidence.model_validate(e) for e in report.evidence]
            tl_res = build_timeline(ev_entities)
            timeline_mermaid = tl_res["mermaid"]
            timeline_table = tl_res["table"]
        except Exception:
            pass

    placeholders: dict[str, str] = {
        "report_title": "Clinical Reasoning & Root Cause Report",
        "session_id": _cell(report.session_id),
        "report_id": _cell(report.report_id),
        "generated_at": report.generated_at.isoformat(),
        "report_status": "Final" if report.is_finalized else "Preliminary",
        "detail_level": detail_level,
        "executive_summary": "\n".join(
            _executive_summary(hypotheses, evidence, report)
        ),
        "hypothesis_table": "\n".join(_hypothesis_table(hypotheses)),
        "top_diagnosis": top_diag,
        "top_probability": top_prob,
        "rule_out_summary": rule_out_summary,
        "must_not_miss_evaluated": f"{len(hypotheses)} emergency differential conditions modeled",
        "evidence_table": "\n".join(_evidence_table(evidence, evidence_limit)),
        "timeline_diagram": timeline_mermaid
        or "_No timeline diagram generated._",
        "timeline_table": timeline_table or "_No timeline table generated._",
        "cognitive_safety_section": "\n".join(
            _cognitive_safety(report.thinking_chain)
        ),
        "automated_checks_section": "\n".join(_automated_findings(report)),
        "quality_metrics_section": "\n".join(_quality_metrics(report)),
        "reasoning_chain_diagram": reasoning_mermaid
        or "_No diagram generated for brief mode._",
        "evidence_graph_diagram": evidence_mermaid
        or "_No evidence graph generated._",
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
    return template_text.rstrip() + "\n"


def render_contract_report_markdown(
    report: ContractReport,
    detail_level: str = "standard",
    template_path: str | Path | None = None,
) -> str:
    """Render a professional report without invoking an LLM, supporting custom template overrides."""
    if detail_level not in {"brief", "standard", "full"}:
        raise ValueError("detail_level must be brief, standard, or full")

    hypotheses = sorted(
        report.hypotheses,
        key=_probability,
        reverse=True,
    )
    evidence = sorted(report.evidence, key=_evidence_sort_key, reverse=True)
    evidence_limit = 8 if detail_level == "brief" else None

    if template_path:
        custom_rendered = _render_custom_template(
            report=report,
            detail_level=detail_level,
            hypotheses=hypotheses,
            evidence=evidence,
            evidence_limit=evidence_limit,
            template_path=template_path,
        )
        if custom_rendered is not None:
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
    lines.extend(_executive_summary(hypotheses, evidence, report))
    lines.extend(["", "## Ranked Differential Diagnosis", ""])
    lines.extend(_hypothesis_table(hypotheses))
    lines.extend(["", "## Evidence Matrix", ""])
    lines.extend(_evidence_table(evidence, evidence_limit))

    if detail_level in {"standard", "full"} and evidence:
        from rootcause_mcp.domain.entities.evidence import Evidence
        from rootcause_mcp.interface.mermaid import build_timeline

        try:
            ev_entities = [Evidence.model_validate(e) for e in report.evidence]
            tl_res = build_timeline(ev_entities)
            lines.extend(["", "## Chronological Timeline", ""])
            lines.append(tl_res["table"])
            lines.extend(["", tl_res["mermaid"]])
        except Exception:
            pass

    lines.extend(["", "## Uncertainty and Cognitive Safety", ""])
    lines.extend(_cognitive_safety(report.thinking_chain))
    lines.extend(["", "## Automated Completeness Checks", ""])
    lines.extend(_automated_findings(report))
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
    if report.content_hash:
        lines.append(f"- Content SHA-256: `{report.content_hash}`")
    return "\n".join(lines).rstrip() + "\n"


def _executive_summary(
    hypotheses: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    report: ContractReport,
) -> list[str]:
    if not hypotheses:
        leading = "No diagnosis hypothesis has been recorded."
    else:
        first = hypotheses[0]
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
            f"**{_count_phrase(len(hypotheses), 'hypothesis', 'hypotheses')}**, "
            f"and **{_count_phrase(len(gaps), 'recorded uncertainty factor')}**."
        ),
    ]


def _hypothesis_table(hypotheses: list[dict[str, Any]]) -> list[str]:
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


def _diagnosis_cells(hypothesis: dict[str, Any]) -> tuple[str, str]:
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
    evidence: list[dict[str, Any]],
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


def _cognitive_safety(thinking_chain: list[dict[str, Any]]) -> list[str]:
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
    if evidence is None and reasoning is None:
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
    return lines


def _automated_findings(report: ContractReport) -> list[str]:
    """Identify structural review gaps without making clinical judgments."""
    findings = [
        *_evidence_findings(report),
        *_hypothesis_findings(report),
        *_cognitive_findings(report),
        *_reasoning_findings(report),
        *_graph_findings(report),
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


def _reasoning_audit(
    reasoning_chain: list[dict[str, Any]],
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


def _thinking_audit(thinking_chain: list[dict[str, Any]]) -> list[str]:
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
    thinking_chain: list[dict[str, Any]],
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


def _evidence_sort_key(item: dict[str, Any]) -> tuple[int, int, int, str]:
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


def _entity_id(item: dict[str, Any]) -> str:
    raw_id = item.get("id", "unknown")
    if isinstance(raw_id, dict):
        return str(raw_id.get("value", "unknown"))
    return str(raw_id)


def _probability(hypothesis: dict[str, Any]) -> float:
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
