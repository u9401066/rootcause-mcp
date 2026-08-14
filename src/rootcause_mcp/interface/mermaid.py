"""Mermaid presenters for user-facing analysis artifacts."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from rootcause_mcp.domain.entities.evidence import Evidence
from rootcause_mcp.domain.entities.fishbone import Fishbone
from rootcause_mcp.domain.entities.hypothesis import Hypothesis
from rootcause_mcp.domain.entities.reasoning_step import ReasoningChain
from rootcause_mcp.domain.entities.why_node import WhyChain
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


def mermaid_block(source: str) -> str:
    """Wrap Mermaid source for Markdown previewers."""
    return f"```mermaid\n{source.rstrip()}\n```"


def build_evidence_graph(
    evidence: Iterable[Evidence],
    hypotheses: Iterable[Hypothesis],
) -> dict[str, Any]:
    """Build deterministic graph data and Mermaid from aggregate relationships."""
    evidence_items = sorted(evidence, key=lambda item: item.id.value)
    hypothesis_items = sorted(hypotheses, key=lambda item: item.id.value)
    hypothesis_ids = {item.id.value for item in hypothesis_items}
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
                "supports",
            )
        for hypothesis_id in sorted(evidence_item.contradicts_hypothesis_ids):
            add_hypothesis_edge(
                evidence_item.id.value,
                hypothesis_id,
                "contradicts",
            )
        for cause_id in sorted(evidence_item.supports_cause_ids):
            edge_keys.add((evidence_item.id.value, cause_id, "supports_cause"))

    for hypothesis_item in hypothesis_items:
        nodes.append(
            {
                "id": hypothesis_item.id.value,
                "type": "hypothesis",
                "label": hypothesis_item.diagnosis.display,
                "status": hypothesis_item.status.value,
                "probability": hypothesis_item.current_probability,
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
            verified = "Verified" if node.get("verified") else "Unverified"
            lines.append(
                f'    {node_ref}["Evidence<br/>{label}<br/>{source} | {verified}"]:::evidence'
            )
        elif node_type == "hypothesis":
            probability = float(node.get("probability", 0.0))
            status = escape_mermaid_label(node.get("status", "UNKNOWN"), 20)
            lines.append(
                f'    {node_ref}(["Hypothesis<br/>{label}<br/>{probability:.0%} | {status}"]):::hypothesis'
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
        if step.confidence is not None:
            label_parts.append(f"Confidence: {step.confidence:.0%}")
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
