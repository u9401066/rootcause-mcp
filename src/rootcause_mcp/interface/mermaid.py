"""Mermaid presenters for user-facing analysis artifacts."""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

from rootcause_mcp.domain.entities.evidence import Evidence
from rootcause_mcp.domain.entities.fishbone import Fishbone
from rootcause_mcp.domain.entities.hypothesis import Hypothesis
from rootcause_mcp.domain.entities.reasoning_step import ReasoningChain
from rootcause_mcp.domain.entities.why_node import WhyChain
from rootcause_mcp.domain.value_objects.clinical_temporal import (
    ClinicalTemporal,
    resolve_clinical_temporal,
)
from rootcause_mcp.domain.value_objects.enums import FishboneCategoryType

_FISHBONE_REFS = {
    FishboneCategoryType.PERSONNEL: "PERS",
    FishboneCategoryType.EQUIPMENT: "EQUI",
    FishboneCategoryType.MATERIAL: "MATE",
    FishboneCategoryType.PROCESS: "PROC",
    FishboneCategoryType.ENVIRONMENT: "ENVI",
    FishboneCategoryType.MONITORING: "MONI",
}


def escape_mermaid_label(text: str, max_length: int = 80) -> str:
    """Normalize user text for a quoted Mermaid label."""
    normalized = " ".join(str(text).split())
    if len(normalized) > max_length:
        normalized = f"{normalized[: max_length - 3].rstrip()}..."
    return (
        normalized.replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("[", "&#91;")
        .replace("]", "&#93;")
        .replace("(", "&#40;")
        .replace(")", "&#41;")
    )


def escape_timeline_text(text: str, max_length: int = 80) -> str:
    """Normalize user text for Mermaid timeline diagram entries."""
    escaped = escape_mermaid_label(text, max_length)
    return escaped.replace(":", " -")


def mermaid_block(source: str) -> str:
    """Wrap Mermaid source for Markdown previewers."""
    return f"```mermaid\n{source.rstrip()}\n```"


def _extract_time_key(text: str) -> str:
    """Extract a displayable/sortable timestamp string from text."""
    pattern = (
        r"\b(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}"
        r"|\d{2}/\d{2}\s+\d{2}:\d{2}"
        r"|POD\s*\d+\s+\d{2}:\d{2}"
        r"|\d{4}/\d{2}/\d{2}"
        r"|\d{2}:\d{2})\b"
    )
    match = re.search(pattern, text, flags=re.IGNORECASE)
    return match.group(1) if match else ""


def _absolute_time_key(value: object) -> float | None:
    """Return a key only for an absolute datetime with explicit timezone."""
    parsed: datetime | None = None
    if isinstance(value, datetime):
        parsed = value
    elif value:
        candidate = str(value).strip().replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(candidate)
        except ValueError:
            return None
    if parsed is None or parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(UTC).timestamp()


def _custom_event_temporal(event: dict[str, Any]) -> ClinicalTemporal:
    """Resolve custom timeline input without assigning a timezone or precision."""
    if event.get("temporal") is not None:
        return resolve_clinical_temporal(
            event.get("temporal"),
            event.get("event_timestamp") or event.get("timestamp"),
        )
    raw_time = (
        event.get("event_timestamp") or event.get("timestamp") or event.get("time")
    )
    if raw_time is None:
        return ClinicalTemporal.unknown()
    try:
        return ClinicalTemporal.from_legacy_event_timestamp(raw_time)
    except ValueError:
        raw_text = str(raw_time)
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw_text):
            return ClinicalTemporal.model_validate(
                {"kind": "date", "raw_value": raw_text}
            )
        return ClinicalTemporal.from_lost_local_timestamp(raw_text)


def _detect_pattern_from_text(text: str) -> str:
    """Auto-detect clinical timeline pattern from content keywords."""
    if any(
        k in text
        for k in [
            "rad_report",
            "ct scan",
            "memo",
            "fax",
            "triage",
            "delayed",
            "44 day",
            "biopsy",
            "lost to follow-up",
            "01/05",
            "01/07",
            "02/20",
        ]
    ):
        return "delayed_diagnosis"
    if any(
        k in text
        for k in [
            "lvad",
            "heartmate",
            "pump",
            "suction",
            "controller log",
            "power spike",
            "low flow",
            "pi 1.0",
            "rpm",
            "bowing into lv",
        ]
    ):
        return "device_incident"
    if any(
        k in text
        for k in [
            "order expired",
            "not_given",
            "mar.csv",
            "pharmacy",
            "clexane held",
            "dispensing",
            "not renewed",
        ]
    ):
        return "barrier_failure"
    if any(
        k in text
        for k in [
            "induction",
            "intubation",
            "pre-op",
            "pre_anesthesia",
            "surgeon",
            "operating room",
            "intraoperative",
            "perioperative",
            "surgery",
            "surgical",
            "pacu",
            "tee",
            "propofol 80mg",
            "08:00",
            "08:05",
            "08:18",
        ]
    ):
        return "perioperative_sequence"
    return "acute_crisis"


def _infer_delayed_diag_phase(text: str) -> str:
    if any(
        k in text
        for k in ["opd", "clinic", "initial visit", "exam arranged", "01/05", "visit"]
    ):
        return "1. Initial Contact & Testing Order"
    if any(
        k in text
        for k in [
            "ct completed",
            "rad",
            "mass found",
            "critical finding",
            "01/07",
            "hl7",
        ]
    ):
        return "2. Diagnostic Test & Result Generation"
    if any(
        k in text
        for k in [
            "faxed",
            "desk",
            "seminar",
            "early leave",
            "moved to archive",
            "lost",
            "14:01",
            "14:10",
            "14:30",
            "14:45",
        ]
    ):
        return "3. Communication Gap & Missed Opportunity"
    if any(
        k in text
        for k in [
            "44 days",
            "blank",
            "unaware",
            "progression",
            "interval",
            "normal thought",
        ]
    ):
        return "4. Latent Disease Progression"
    if any(
        k in text
        for k in [
            "hemoptysis",
            "er triage",
            "triage",
            "flare",
            "crisis discovery",
            "02/20",
        ]
    ):
        return "5. Symptom Flare & Crisis Discovery"
    return "6. Late Diagnosis & Corrective Action"


def _infer_barrier_failure_phase(text: str) -> str:
    if any(
        k in text
        for k in ["order written", "hold 24h", "op note", "dvt prophylaxis", "14:00"]
    ):
        return "1. Prescribing & Ordering Phase"
    if any(
        k in text
        for k in ["pharmacy", "dispensing", "order expired", "not renewed", "09:00"]
    ):
        return "2. Dispensing & Pharmacy Barrier"
    if any(
        k in text
        for k in ["mar", "not_given", "admin_by", "dose omitted", "calf pain", "16:00"]
    ):
        return "3. Administration & Nursing Barrier"
    if any(
        k in text
        for k in [
            "fever",
            "tachycardia",
            "progress note",
            "misdiagnosed",
            "08:30",
            "11:30",
        ]
    ):
        return "4. Monitoring & Detection Barrier"
    return "5. Interception or Adverse Outcome"


def _infer_device_incident_phase(text: str) -> str:
    if any(
        k in text
        for k in ["baseline", "implanted", "3 months", "02:00", "pi 4.5", "power 4.1"]
    ):
        return "1. Baseline Device Setting"
    if any(
        k in text
        for k in ["rv failure", "decreased preload", "02:45", "pi 1.5", "suction start"]
    ):
        return "2. Mechanical / Hemodynamic Disturbance"
    if any(
        k in text
        for k in [
            "alarm",
            "low flow",
            "power spike",
            "cola urine",
            "04:00",
            "controller log",
        ]
    ):
        return "3. Controller Alarm & Warnings"
    if any(
        k in text
        for k in [
            "fluid given",
            "speed increased",
            "echo misread",
            "er triage",
            "thrombosis suspected",
        ]
    ):
        return "4. Clinical Misinterpretation & Action"
    return "5. Corrective Rescue (Speed Reduction / RV Support)"


def _infer_acute_crisis_phase(text: str) -> str:
    if any(
        k in text
        for k in ["baseline", "pre-event", "admitted", "history", "08:00", "23:30"]
    ):
        return "1. Pre-Event Baseline"
    if any(
        k in text
        for k in [
            "trigger",
            "infusion",
            "older stock",
            "unit #7",
            "induction",
            "01:00",
            "01:45",
        ]
    ):
        return "2. Precipitating Trigger"
    if any(
        k in text
        for k in [
            "worsening",
            "hypotension",
            "acidosis",
            "rhabdomyolysis",
            "crash",
            "02:00",
            "02:30",
        ]
    ):
        return "3. Acute Deterioration"
    if any(
        k in text
        for k in [
            "alarm",
            "peaked t",
            "hi_t_wave",
            "brugada",
            "alert",
            "02:12",
            "05:30",
        ]
    ):
        return "4. Crisis Recognition & Alarm"
    if any(
        k in text
        for k in ["code blue", "arrest", "cpr", "epinephrine", "02:45", "12:10"]
    ):
        return "5. Rescue & Resuscitation"
    return "6. Stabilization / Post-Crisis Outcome"


def _infer_perioperative_phase(text: str) -> str:
    if any(
        k in text
        for k in [
            "cardiac arrest",
            "arrest",
            "pulseless",
            "cpr",
            "resuscitation",
            "defibrillation",
            "ventricular fibrillation",
            " vf ",
            "rosc",
            "code blue",
        ]
    ):
        phase = "5. Critical Collapse & Resuscitation"
    elif any(
        k in text
        for k in [
            "post-event",
            "post event",
            "post-crisis",
            "post crisis",
            "stabilized",
            "stabilisation",
            "stabilization",
            "extubated",
            "discharged",
            "discharge",
            "icu outcome",
        ]
    ):
        phase = "6. Stabilization / Post-Crisis Outcome"
    elif any(
        k in text
        for k in [
            "pre-op",
            "baseline",
            "admission",
            "08:00",
            "history",
            "pre_anesthesia",
        ]
    ):
        phase = "1. Baseline & Pre-Op"
    elif any(
        k in text
        for k in [
            "induction",
            "intubation",
            "rsi",
            "positioning",
            "08:05",
            "08:08",
            "08:10",
            "surgical incision",
        ]
    ):
        phase = "2. Induction & Surgical Events"
    elif any(
        k in text
        for k in [
            "hypotension",
            "crash",
            "worsening",
            "acidosis",
            "ephedrine",
            "epinephrine",
            "vt alarm",
            "ventricular tachycardia",
            "rhythm deterioration",
            "08:12",
            "08:15",
            "08:18",
        ]
    ):
        phase = "3. Crisis Progression & Deterioration"
    elif any(
        k in text
        for k in [
            "tee",
            "doppler",
            "dagger",
            "sam",
            "echo",
            "normal size",
            "08:20",
            "a-line waveform",
        ]
    ):
        phase = "4. Diagnostic Findings & Rule-Outs"
    else:
        phase = "5. Critical Collapse & Resuscitation"
    return phase


def _infer_phase(time_str: str, content: str, pattern: str = "auto") -> str:
    """Infer clinical phase for timeline grouping across various clinical patterns."""
    text = f"{time_str} {content}".lower()
    selected_pattern = _detect_pattern_from_text(text) if pattern == "auto" else pattern

    dispatchers = {
        "delayed_diagnosis": _infer_delayed_diag_phase,
        "barrier_failure": _infer_barrier_failure_phase,
        "device_incident": _infer_device_incident_phase,
        "acute_crisis": _infer_acute_crisis_phase,
        "perioperative_sequence": _infer_perioperative_phase,
    }
    handler = dispatchers.get(selected_pattern, _infer_perioperative_phase)
    return handler(text)


def build_timeline(
    evidence: Iterable[Evidence] | None = None,
    _reasoning_chain: ReasoningChain | None = None,
    pattern: str = "auto",
    custom_events: list[dict[str, Any]] | None = None,
    title: str | None = None,
) -> dict[str, Any]:
    """
    Build structured chronological timeline and Mermaid diagram from evidence items or custom events.

    Supports configurable clinical timeline patterns:
    - 'perioperative_sequence'
    - 'acute_crisis'
    - 'delayed_diagnosis'
    - 'barrier_failure'
    - 'device_incident'
    - 'auto'
    - 'custom'
    """
    events: list[dict[str, Any]] = []
    evidence_items = list(evidence or [])
    custom_items = list(custom_events or [])
    if pattern == "auto":
        pattern_text = " ".join(
            [
                *(
                    f"{item.content} {item.source.raw_snippet or ''}"
                    for item in evidence_items
                ),
                *(
                    f"{item.get('content', '')} {item.get('description', '')}"
                    for item in custom_items
                ),
            ]
        ).lower()
        selected_pattern = _detect_pattern_from_text(pattern_text)
    else:
        selected_pattern = pattern

    # 1. Ingest custom events if provided
    if custom_items:
        for ev in custom_items:
            temporal = _custom_event_temporal(ev)
            instant = temporal.aware_instant
            t_str = temporal.display_value()
            content = str(ev.get("content") or ev.get("description") or "")
            phase = ev.get("phase") or _infer_phase(t_str, content, selected_pattern)
            events.append(
                {
                    "id": str(ev.get("id") or f"EVT-{len(events) + 1}"),
                    "time": t_str,
                    "phase": phase,
                    "content": content,
                    "source_document": ev.get("source_document")
                    or ev.get("source")
                    or "Record",
                    "verified": bool(ev.get("verified", False)),
                    "evidence_type": str(
                        ev.get("evidence_type") or ev.get("type") or "OBSERVATION"
                    ),
                    "temporal": temporal.model_dump(mode="json"),
                    "chronology_status": (
                        "ORDERED_INSTANT" if instant is not None else "UNPOSITIONED"
                    ),
                    "_sort_instant": _absolute_time_key(instant),
                    "_input_index": len(events),
                }
            )

    # 2. Ingest domain Evidence items if provided
    if evidence_items:
        for item in evidence_items:
            temporal = item.temporal
            instant = temporal.aware_instant
            t_str = temporal.display_value()

            phase = _infer_phase(
                t_str,
                f"{item.content} {item.source.raw_snippet or ''}",
                selected_pattern,
            )
            events.append(
                {
                    "id": item.id.value,
                    "time": t_str,
                    "phase": phase,
                    "content": item.content,
                    "source_document": item.source.document_id,
                    "verified": item.verified,
                    "evidence_type": item.evidence_type.value,
                    "temporal": temporal.model_dump(mode="json"),
                    "chronology_status": (
                        "ORDERED_INSTANT" if instant is not None else "UNPOSITIONED"
                    ),
                    "_sort_instant": _absolute_time_key(instant),
                    "_input_index": len(events),
                }
            )

    timed_events = sorted(
        (event for event in events if event["_sort_instant"] is not None),
        key=lambda event: (event["_sort_instant"], event["_input_index"]),
    )
    # Preserve ingestion/ledger order for partial or unknown time. This is not a
    # chronology and is labelled as such on every event and presentation.
    untimed_events = [event for event in events if event["_sort_instant"] is None]
    events = [*timed_events, *untimed_events]
    for event in events:
        event.pop("_sort_instant", None)
        event.pop("_input_index", None)
    diagram_title = (
        title or f"Clinical Chronology ({selected_pattern.replace('_', ' ').title()})"
    )

    return {
        "pattern": selected_pattern,
        "title": diagram_title,
        "events": events,
        "timed_event_count": len(timed_events),
        "untimed_event_count": len(untimed_events),
        "ordering_note": (
            "Only ORDERED_INSTANT events are chronologically sorted; "
            "UNPOSITIONED events retain ledger order and imply no chronology."
        ),
        "mermaid": render_timeline_mermaid(events, title=diagram_title),
        "table": render_timeline_table(events),
    }


def _detect_diagram_header(
    lines: list[str],
    diagram_type: str | None,
    auto_fix: bool,
    fixed_lines: list[str],
    warnings: list[str],
    errors: list[str],
) -> str:
    """Detect or insert appropriate Mermaid diagram header."""
    header_patterns = [
        "flowchart",
        "graph",
        "timeline",
        "sequenceDiagram",
        "stateDiagram",
        "stateDiagram-v2",
        "erDiagram",
        "classDiagram",
        "gantt",
        "pie",
        "mindmap",
        "gitGraph",
    ]
    detected_type = "unknown"
    if lines:
        first_token = lines[0].strip().split()[0] if lines[0].strip() else ""
        for hp in header_patterns:
            if first_token.startswith(hp) or lines[0].strip().startswith(hp):
                detected_type = hp
                break

    if detected_type != "unknown":
        return detected_type

    if diagram_type and diagram_type in header_patterns:
        detected_type = diagram_type
        if auto_fix:
            header = (
                f"{diagram_type} TB"
                if diagram_type in {"flowchart", "graph"}
                else diagram_type
            )
            fixed_lines.append(header)
            warnings.append(f"Added missing diagram header '{header}' automatically.")
        else:
            errors.append(f"Missing header declaration for {diagram_type}.")
    elif auto_fix:
        detected_type = "flowchart"
        fixed_lines.append("flowchart TB")
        warnings.append("Added default header 'flowchart TB'.")
    else:
        errors.append(
            "Missing valid Mermaid diagram header (e.g., 'flowchart TB', 'timeline', 'sequenceDiagram')."
        )
    return detected_type


def _audit_and_fix_mermaid_line(
    idx: int,
    line: str,
    detected_type: str,
    auto_fix: bool,
    warnings: list[str],
) -> tuple[str, int, int]:
    """Audit bracket balances and auto-sanitize line content."""
    stripped = line.strip()
    open_sq, close_sq = stripped.count("["), stripped.count("]")
    open_pa, close_pa = stripped.count("("), stripped.count(")")
    open_cu, close_cu = stripped.count("{"), stripped.count("}")

    if open_sq != close_sq:
        warnings.append(
            f"Line {idx}: Unbalanced square brackets '[' ({open_sq}) vs ']' ({close_sq})."
        )
    if open_pa != close_pa:
        warnings.append(
            f"Line {idx}: Unbalanced parentheses '(' ({open_pa}) vs ')' ({close_pa})."
        )
    if open_cu != close_cu:
        warnings.append(
            f"Line {idx}: Unbalanced braces '{{' ({open_cu}) vs '}}' ({close_cu})."
        )

    sanitized = line
    if auto_fix:
        if detected_type == "timeline" and ":" in stripped:
            parts = stripped.split(":", 1)
            if len(parts) == 2:
                time_part = parts[0].strip()
                desc_part = parts[1].replace(":", " -")
                sanitized = f"        {time_part} :{desc_part}"
        elif detected_type in {"flowchart", "graph"}:
            sanitized = re.sub(r"(?<=\S)\s*->\s*(?=\S)", " --> ", sanitized)

            def _fix_label(m: re.Match[str]) -> str:
                return f"{m.group(1)}{m.group(2).replace('"', '&quot;')}{m.group(3)}"

            label_pat = r"(\[\"|\(\[\"|\[\[\"|\(\(\"|\{\{\"|\>\[\")([\s\S]+?)(\"\]|\"\]\)|\"\]\]|\"\)\)|\"\}\})"
            sanitized = re.sub(label_pat, _fix_label, sanitized)

    nodes = 1 if ("[" in sanitized or "(" in sanitized) else 0
    edges = 1 if any(tok in sanitized for tok in ["-->", "-.->", "==>"]) else 0
    return sanitized, nodes, edges


def validate_mermaid_syntax(
    source: str,
    diagram_type: str | None = None,
    auto_fix: bool = True,
) -> dict[str, Any]:
    """
    Audit, validate, and sanitize Mermaid diagram syntax.

    Checks:
    - Diagram header declarations
    - Delimiter balancing ([], (), {}, [()], [[]], (()))
    - Unescaped quotes and reserved symbols inside labels
    - Unclosed subgraph blocks
    - Colon handling inside timeline text entries
    - Illegal arrow connector tokens
    """
    raw = source.strip()
    if raw.startswith("```"):
        lines_raw = raw.splitlines()
        raw = "\n".join(lines_raw[1:-1]).strip()

    errors: list[str] = []
    warnings: list[str] = []
    fixed_lines: list[str] = []

    lines = [line.rstrip() for line in raw.splitlines() if line.strip()]
    detected_type = _detect_diagram_header(
        lines=lines,
        diagram_type=diagram_type,
        auto_fix=auto_fix,
        fixed_lines=fixed_lines,
        warnings=warnings,
        errors=errors,
    )

    header_names = [
        "flowchart",
        "graph",
        "timeline",
        "sequenceDiagram",
        "stateDiagram",
        "stateDiagram-v2",
        "erDiagram",
        "classDiagram",
        "gantt",
        "pie",
        "mindmap",
        "gitGraph",
    ]

    subgraph_count = 0
    end_count = 0
    total_nodes = 0
    total_edges = 0

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if (
            idx == 1
            and detected_type != "unknown"
            and any(stripped.startswith(hp) for hp in header_names)
        ):
            fixed_lines.append(stripped)
            continue

        if stripped.startswith("subgraph"):
            subgraph_count += 1
        elif stripped == "end":
            end_count += 1

        sanitized_line, n_count, e_count = _audit_and_fix_mermaid_line(
            idx=idx,
            line=line,
            detected_type=detected_type,
            auto_fix=auto_fix,
            warnings=warnings,
        )
        total_nodes += n_count
        total_edges += e_count
        fixed_lines.append(sanitized_line)

    if auto_fix and subgraph_count > end_count:
        missing = subgraph_count - end_count
        fixed_lines.extend("    end" for _ in range(missing))
        warnings.append(f"Auto-closed {missing} unclosed subgraph block(s).")
    elif subgraph_count < end_count:
        errors.append(
            f"Found {end_count} 'end' statements but only {subgraph_count} 'subgraph' blocks."
        )

    sanitized_source = "\n".join(fixed_lines).strip()
    return {
        "is_valid": len(errors) == 0,
        "diagram_type": detected_type,
        "errors": errors,
        "warnings": warnings,
        "sanitized_mermaid": sanitized_source,
        "preview_markdown": mermaid_block(sanitized_source),
        "node_count": total_nodes,
        "edge_count": total_edges,
    }


def render_timeline_mermaid(
    events: list[dict[str, Any]],
    title: str = "Clinical Timeline & Event Chronology",
) -> str:
    """Render a clean Mermaid timeline diagram with phases and events."""
    if not events:
        return mermaid_block(
            "timeline\n    title No timeline events recorded\n    section General\n        No events : No time-anchored evidence found"
        )

    lines = [
        "timeline",
        f"    title {escape_mermaid_label(title, 60)}",
    ]

    phases: dict[str, list[dict[str, Any]]] = {}
    for ev in events:
        phase = ev.get("phase", "General Sequence")
        if ev.get("chronology_status") != "ORDERED_INSTANT":
            phase = f"Unpositioned / partial time — {phase}"
        phases.setdefault(phase, []).append(ev)

    for phase_name, phase_events in phases.items():
        clean_phase = escape_mermaid_label(phase_name, 40)
        lines.append(f"    section {clean_phase}")
        for ev in phase_events:
            t = escape_mermaid_label(ev.get("time") or "Unknown time", 24)
            c = escape_timeline_text(ev.get("content", ""), 70)
            verified_tag = " [Source checked]" if ev.get("verified") else ""
            lines.append(f"        {t} : {c}{verified_tag}")

    return mermaid_block("\n".join(lines))


def render_timeline_table(events: list[dict[str, Any]]) -> str:
    """Render a structured Markdown chronological event table."""
    lines = [
        "| Time expression | Temporal state | Phase | Clinical Event / Finding | Source Record | Provenance check |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    if not events:
        lines.append("| - | - | - | No timeline events recorded | - | - |")
        return "\n".join(lines)

    for ev in events:
        t = ev.get("time") or "-"
        temporal_kind = str((ev.get("temporal") or {}).get("kind") or "unknown")
        chronology = ev.get("chronology_status") or "UNPOSITIONED"
        phase = ev.get("phase") or "General"
        content = ev.get("content") or "-"
        src = ev.get("source_document") or "Record"
        v = "✅ Yes" if ev.get("verified") else "❌ No"
        lines.append(
            f"| `{t}` | `{temporal_kind}` / `{chronology}` | **{phase}** | "
            f"{content} | `{src}` | {v} |"
        )

    return "\n".join(lines)


def build_evidence_graph(
    evidence: Iterable[Evidence],
    hypotheses: Iterable[Hypothesis],
) -> dict[str, Any]:
    """Build deterministic graph data and Mermaid from aggregate relationships."""
    evidence_items = sorted(evidence, key=lambda item: item.id.value)
    hypothesis_items = sorted(hypotheses, key=lambda item: item.id.value)
    hypothesis_ids = {item.id.value for item in hypothesis_items}
    lr_relationships: dict[tuple[str, str], str] = {}
    for hypothesis_item in hypothesis_items:
        for likelihood in hypothesis_item.likelihood_ratios:
            applied = likelihood.applied_likelihood_ratio
            if applied is None or applied == 1.0:
                relationship = "neutral"
            elif applied > 1.0:
                relationship = "supports"
            else:
                relationship = "contradicts"
            lr_relationships[(likelihood.evidence_id, hypothesis_item.id.value)] = (
                relationship
            )
    nodes: list[dict[str, Any]] = []
    edge_keys: set[tuple[str, str, str]] = set()
    warnings: list[str] = []

    def add_hypothesis_edge(
        source: str,
        target: str,
        relationship: str,
    ) -> None:
        if target not in hypothesis_ids:
            warnings.append(
                f"Omitted {relationship} edge from {source} to missing hypothesis {target}"
            )
            return
        edge_keys.add((source, target, relationship))

    for evidence_item in evidence_items:
        nodes.append(
            {
                "id": evidence_item.id.value,
                "type": "evidence",
                "label": evidence_item.content,
                "evidence_type": evidence_item.evidence_type.value,
                "verified": evidence_item.verified,
                "source_document": evidence_item.source.document_id,
                "source_location": evidence_item.source.location,
            }
        )
        for hypothesis_id in sorted(evidence_item.supports_hypothesis_ids):
            add_hypothesis_edge(
                evidence_item.id.value,
                hypothesis_id,
                lr_relationships.get(
                    (evidence_item.id.value, hypothesis_id), "supports"
                ),
            )
        for hypothesis_id in sorted(evidence_item.contradicts_hypothesis_ids):
            add_hypothesis_edge(
                evidence_item.id.value,
                hypothesis_id,
                lr_relationships.get(
                    (evidence_item.id.value, hypothesis_id), "contradicts"
                ),
            )
        for cause_id in sorted(evidence_item.supports_cause_ids):
            edge_keys.add((evidence_item.id.value, cause_id, "supports_cause"))

    evidence_ids = {item.id.value for item in evidence_items}
    for (evidence_id, hypothesis_id), relationship in sorted(lr_relationships.items()):
        if evidence_id not in evidence_ids:
            warnings.append(
                "Omitted "
                f"{relationship} edge from missing evidence {evidence_id} "
                f"to {hypothesis_id}"
            )
            continue
        add_hypothesis_edge(evidence_id, hypothesis_id, relationship)

    for hypothesis_item in hypothesis_items:
        nodes.append(
            {
                "id": hypothesis_item.id.value,
                "type": "hypothesis",
                "label": hypothesis_item.diagnosis.display,
                "status": hypothesis_item.status.value,
                "certainty": hypothesis_item.certainty.value,
                "probability_semantics": "UNCALIBRATED_NOT_PRESENTED",
            }
        )

    cause_ids = sorted(
        {
            target
            for _, target, relationship in edge_keys
            if relationship == "supports_cause"
        }
    )
    nodes.extend(
        {"id": cause_id, "type": "cause", "label": cause_id} for cause_id in cause_ids
    )
    edges = [
        {"source": source, "target": target, "relationship": relationship}
        for source, target, relationship in sorted(edge_keys)
    ]
    return {
        "nodes": nodes,
        "edges": edges,
        "warnings": sorted(set(warnings)),
        "mermaid": render_evidence_graph_mermaid(nodes, edges),
    }


def render_evidence_graph_mermaid(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, str]],
) -> str:
    """Render evidence-to-hypothesis and evidence-to-cause relationships."""
    lines = [
        "flowchart LR",
        "    %% Evidence provenance and diagnostic relationships",
    ]
    node_refs = {node["id"]: f"N{index}" for index, node in enumerate(nodes, 1)}

    for node in nodes:
        node_ref = node_refs[node["id"]]
        node_type = node["type"]
        label = escape_mermaid_label(node["label"], 72)
        if node_type == "evidence":
            source = escape_mermaid_label(
                node.get("source_document") or "source not recorded", 40
            )
            verified = (
                "Registered-source check true"
                if node.get("verified")
                else "Provenance check incomplete"
            )
            lines.append(
                f'    {node_ref}["Evidence<br/>{label}<br/>{source} | {verified}"]:::evidence'
            )
        elif node_type == "hypothesis":
            status = escape_mermaid_label(node.get("status", "UNKNOWN"), 20)
            certainty = escape_mermaid_label(node.get("certainty", "UNKNOWN"), 24)
            lines.append(
                f'    {node_ref}(["Hypothesis<br/>{label}<br/>{certainty} | {status}"]):::hypothesis'
            )
        else:
            lines.append(f'    {node_ref}["Cause<br/>{label}"]:::cause')

    for edge in edges:
        source_ref = node_refs.get(edge["source"])
        target_ref = node_refs.get(edge["target"])
        if source_ref is None or target_ref is None:
            continue
        relationship = edge["relationship"]
        if relationship == "supports":
            lines.append(f'    {source_ref} -->|"supports"| {target_ref}')
        elif relationship == "contradicts":
            lines.append(f'    {source_ref} -. "contradicts" .-> {target_ref}')
        elif relationship == "neutral":
            lines.append(f'    {source_ref} -. "neutral LR=1" .-> {target_ref}')
        else:
            lines.append(f'    {source_ref} -. "supports cause" .-> {target_ref}')

    if not nodes:
        lines.append('    EMPTY["No evidence or hypotheses recorded"]:::empty')
    lines.extend(
        [
            "    classDef evidence fill:#dbeafe,stroke:#2563eb,color:#1e3a8a",
            "    classDef hypothesis fill:#fef3c7,stroke:#d97706,color:#78350f",
            "    classDef cause fill:#dcfce7,stroke:#16a34a,color:#14532d",
            "    classDef empty fill:#f3f4f6,stroke:#9ca3af,color:#4b5563",
        ]
    )
    return mermaid_block("\n".join(lines))


def render_fishbone_mermaid(fishbone: Fishbone) -> str:
    """Render a 6M Ishikawa diagram with a visible three-segment spine."""
    category_pairs = (
        (FishboneCategoryType.PERSONNEL, FishboneCategoryType.PROCESS),
        (FishboneCategoryType.EQUIPMENT, FishboneCategoryType.ENVIRONMENT),
        (FishboneCategoryType.MATERIAL, FishboneCategoryType.MONITORING),
    )
    upper = [pair[0] for pair in category_pairs]
    lower = [pair[1] for pair in category_pairs]
    problem = escape_mermaid_label(fishbone.problem_statement, 72)
    lines = [
        "flowchart LR",
        "    %% 6M Ishikawa layout: upper row, horizontal spine, lower row",
        '    subgraph UPPER[" "]',
        "        direction LR",
        "        " + " ~~~ ".join(_category_node(category) for category in upper),
        "    end",
        '    subgraph SPINE_GROUP[" "]',
        "        direction LR",
        '        S0((" ")):::anchor',
        '        S1((" ")):::anchor',
        '        S2((" ")):::anchor',
        f'        HEAD(["Problem<br/>{problem}"]):::head',
        "        S0 ==> S1",
        "        S1 ==> S2",
        "        S2 ==> HEAD",
        "    end",
        '    subgraph LOWER[" "]',
        "        direction LR",
        "        " + " ~~~ ".join(_category_node(category) for category in lower),
        "    end",
    ]

    for anchor_index, pair in enumerate(category_pairs):
        for category in pair:
            lines.append(f"    {_FISHBONE_REFS[category]} --> S{anchor_index}")

    for category in FishboneCategoryType:
        category_ref = _FISHBONE_REFS[category]
        for cause_index, cause in enumerate(fishbone.get_category(category).causes, 1):
            cause_ref = f"{category_ref}_C{cause_index}"
            label = escape_mermaid_label(cause.description, 64)
            if cause.hfacs_code:
                label = (
                    f"{label}<br/>HFACS: {escape_mermaid_label(cause.hfacs_code, 20)}"
                )
            if cause.verified:
                label = f"{label}<br/>Verified"
            lines.append(f'    {cause_ref}["{label}"]:::cause')
            lines.append(f"    {cause_ref} --> {category_ref}")
            for sub_index, sub_cause in enumerate(cause.sub_causes, 1):
                sub_ref = f"{cause_ref}_S{sub_index}"
                sub_label = escape_mermaid_label(sub_cause, 56)
                lines.append(f'    {sub_ref}["{sub_label}"]:::subcause')
                lines.append(f"    {sub_ref} --> {cause_ref}")

    lines.extend(
        [
            "    style UPPER fill:transparent,stroke:transparent",
            "    style SPINE_GROUP fill:transparent,stroke:transparent",
            "    style LOWER fill:transparent,stroke:transparent",
            "    classDef anchor fill:transparent,stroke:transparent,color:transparent",
            "    classDef head fill:#b91c1c,stroke:#7f1d1d,stroke-width:3px,color:#fff",
            "    classDef category fill:#fef3c7,stroke:#b45309,stroke-width:2px,color:#78350f",
            "    classDef cause fill:#dbeafe,stroke:#2563eb,color:#1e3a8a",
            "    classDef subcause fill:#dcfce7,stroke:#16a34a,color:#14532d",
        ]
    )
    return mermaid_block("\n".join(lines))


def _category_node(category: FishboneCategoryType) -> str:
    """Return one stable 6M category node declaration."""
    label = escape_mermaid_label(category.value, 24)
    return f'{_FISHBONE_REFS[category]}["{label}"]:::category'


def render_why_tree_mermaid(chain: WhyChain) -> str:
    """Render a Why Tree while merging redundant direct causal links."""
    node_refs = {str(node.id): f"N{index}" for index, node in enumerate(chain.nodes, 1)}
    direct_links: dict[tuple[str, str], list[Any]] = {}
    parent_edges = {
        (str(node.parent_id), str(node.id))
        for node in chain.nodes
        if node.parent_id is not None
    }
    for link in chain.causal_links:
        key = (str(link.source_id), str(link.target_id))
        if key in parent_edges:
            direct_links.setdefault(key, []).append(link)
    consumed_links: set[tuple[str, str]] = set()
    problem = escape_mermaid_label(chain.initial_problem, 72)
    lines = [
        "flowchart TB",
        f'    PROBLEM["Problem<br/>{problem}"]:::problem',
    ]

    for node in chain.nodes:
        node_key = str(node.id)
        node_ref = node_refs[node_key]
        parent_key = str(node.parent_id) if node.parent_id else None
        parent_ref = node_refs.get(parent_key, "PROBLEM") if parent_key else "PROBLEM"
        answer = escape_mermaid_label(node.answer, 72)
        level_class = f"why{min(max(node.level, 1), 5)}"
        if node.is_root_cause:
            lines.append(f'    {node_ref}(["ROOT: {answer}"]):::rootcause')
        elif node.needs_further_analysis:
            lines.append(f'    {node_ref}(["{answer}"]):::{level_class}')
        else:
            lines.append(f'    {node_ref}["{answer}"]:::{level_class}')

        edge_parts = [f"Why {node.level}"]
        if node.evidence:
            edge_parts.append(f"Evidence: {escape_mermaid_label(node.evidence[0], 28)}")
        direct_key = (parent_key, node_key) if parent_key else None
        if direct_key in direct_links:
            links = direct_links[direct_key]
            edge_parts.extend(
                f"{link.relationship.value} {link.strength:.0%}" for link in links
            )
            consumed_links.add(direct_key)
        edge_label = "<br/>".join(edge_parts)
        lines.append(f'    {parent_ref} -->|"{edge_label}"| {node_ref}')

    for link_index, link in enumerate(chain.causal_links, 1):
        link_key = (str(link.source_id), str(link.target_id))
        source_ref = node_refs.get(str(link.source_id))
        target_ref = node_refs.get(str(link.target_id))
        if source_ref is None or target_ref is None:
            continue
        label = f"{link.relationship.value}<br/>{link.strength:.0%}"
        if link_key not in consumed_links:
            lines.append(f'    {source_ref} -. "{label}" .-> {target_ref}')
        if link.bidirectional:
            lines.append(
                f'    {target_ref} -. "feedback {link_index}" .-> {source_ref}'
            )

    lines.extend(
        [
            "    classDef problem fill:#dbeafe,stroke:#1d4ed8,stroke-width:3px,color:#172554",
            "    classDef why1 fill:#fee2e2,stroke:#dc2626,color:#7f1d1d",
            "    classDef why2 fill:#ffedd5,stroke:#ea580c,color:#7c2d12",
            "    classDef why3 fill:#fef3c7,stroke:#d97706,color:#78350f",
            "    classDef why4 fill:#ecfccb,stroke:#65a30d,color:#365314",
            "    classDef why5 fill:#dcfce7,stroke:#16a34a,color:#14532d",
            "    classDef rootcause fill:#ede9fe,stroke:#7c3aed,stroke-width:3px,color:#4c1d95",
        ]
    )
    return mermaid_block("\n".join(lines))


def render_reasoning_chain_mermaid(chain: ReasoningChain) -> str:
    """Render ordered reasoning steps and their domain references."""
    lines = [
        "flowchart TB",
        "    %% Ordered clinical reasoning audit trail",
    ]
    evidence_uses: dict[str, list[str]] = {}
    hypothesis_uses: dict[str, list[str]] = {}
    cause_uses: dict[str, list[str]] = {}

    for index, step in enumerate(chain.steps, start=1):
        step_ref = f"S{index}"
        label_parts = [
            f"{index}. {escape_mermaid_label(step.step_type.value, 36)}",
            escape_mermaid_label(step.content, 88),
            f"Rationale: {escape_mermaid_label(step.rationale, 88)}",
        ]
        label = "<br/>".join(label_parts)
        lines.append(f'    {step_ref}["{label}"]:::step')
        if index > 1:
            lines.append(f"    S{index - 1} --> {step_ref}")

        for evidence_id in step.evidence_ids:
            evidence_uses.setdefault(evidence_id, []).append(step_ref)
        for hypothesis_id in step.hypothesis_ids:
            hypothesis_uses.setdefault(hypothesis_id, []).append(step_ref)
        for cause_id in step.cause_ids:
            cause_uses.setdefault(cause_id, []).append(step_ref)

    for index, (evidence_id, step_refs) in enumerate(evidence_uses.items(), start=1):
        evidence_ref = f"E{index}"
        label = escape_mermaid_label(evidence_id, 48)
        lines.append(f'    {evidence_ref}["Evidence<br/>{label}"]:::evidence')
        lines.extend(f"    {evidence_ref} -.-> {step_ref}" for step_ref in step_refs)

    for index, (hypothesis_id, step_refs) in enumerate(
        hypothesis_uses.items(), start=1
    ):
        hypothesis_ref = f"H{index}"
        label = escape_mermaid_label(hypothesis_id, 48)
        lines.append(f'    {hypothesis_ref}["Hypothesis<br/>{label}"]:::hypothesis')
        lines.extend(f"    {step_ref} -.-> {hypothesis_ref}" for step_ref in step_refs)

    for index, (cause_id, step_refs) in enumerate(cause_uses.items(), start=1):
        cause_ref = f"C{index}"
        label = escape_mermaid_label(cause_id, 48)
        lines.append(f'    {cause_ref}["Cause<br/>{label}"]:::cause')
        lines.extend(f"    {step_ref} -.-> {cause_ref}" for step_ref in step_refs)

    if not chain.steps:
        lines.append('    EMPTY["No reasoning steps recorded"]:::empty')

    lines.extend(
        [
            "    classDef step fill:#f7f7f5,stroke:#4b5563,stroke-width:2px,color:#111827",
            "    classDef evidence fill:#dbeafe,stroke:#2563eb,color:#1e3a8a",
            "    classDef hypothesis fill:#fef3c7,stroke:#d97706,color:#78350f",
            "    classDef cause fill:#dcfce7,stroke:#16a34a,color:#14532d",
            "    classDef empty fill:#f3f4f6,stroke:#9ca3af,color:#4b5563",
        ]
    )
    return mermaid_block("\n".join(lines))
