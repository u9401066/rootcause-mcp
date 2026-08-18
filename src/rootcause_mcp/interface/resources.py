"""
MCP Resources Module for RootCause MCP (SDK 2.0).

Exposes clinical playbooks, SOP protocols, report templates, and dynamic session artifacts
as inspectable MCP resources and resource templates.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import TYPE_CHECKING

from mcp.types import (
    ReadResourceResult,
    Resource,
    ResourceTemplate,
    TextResourceContents,
)

if TYPE_CHECKING:
    from rootcause_mcp.application.server_state import ServerState
    from rootcause_mcp.interface.handlers.contract_handlers import ContractHandlers


def _get_config_root() -> Path:
    """Get the configuration root path."""
    env_config = os.environ.get("ROOTCAUSE_CONFIG_DIR")
    if env_config:
        return Path(env_config).resolve()
    return (Path(__file__).resolve().parent.parent.parent.parent / "config").resolve()


_RESOURCE_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _resolve_static_resource(
    config_root: Path,
    category: str,
    slug: str,
    suffix: str,
) -> Path | None:
    """Resolve an enumerated static resource without allowing URI traversal."""
    if not _RESOURCE_SLUG.fullmatch(slug):
        return None
    base = (config_root / category).resolve()
    target = (base / f"{slug.replace('-', '_')}{suffix}").resolve()
    if not target.is_relative_to(base) or not target.is_file():
        return None
    return target


def get_static_resources() -> list[Resource]:
    """Return all static clinical playbooks, protocols, and templates as MCP Resources."""
    config_root = _get_config_root()
    resources: list[Resource] = []

    resources.extend(
        [
            Resource(
                uri="clinical://contracts/case-input-manifest",
                name="Case Input Manifest JSON Schema",
                description="Versioned multi-source raw-record handoff contract",
                mime_type="application/schema+json",
            ),
            Resource(
                uri="clinical://contracts/case-analysis-report",
                name="Case Analysis Report JSON Schema",
                description="Canonical DDx and root-cause analysis output contract",
                mime_type="application/schema+json",
            ),
        ]
    )

    # 1. Protocols
    protocols_dir = config_root / "protocols"
    if protocols_dir.exists():
        for p in protocols_dir.glob("*.yaml"):
            slug = p.stem.replace("_", "-")
            resources.append(
                Resource(
                    uri=f"clinical://protocols/{slug}",
                    name=f"Clinical Protocol: {p.stem.replace('_', ' ').title()}",
                    description=f"Clinical standard operating procedure protocol for {p.stem}",
                    mime_type="application/yaml",
                    size=p.stat().st_size if p.is_file() else None,
                )
            )

    # 2. Domain Playbooks
    domains_dir = config_root / "domains"
    if domains_dir.exists():
        for p in domains_dir.glob("*.yaml"):
            slug = p.stem.replace("_", "-")
            resources.append(
                Resource(
                    uri=f"clinical://domains/{slug}",
                    name=f"Domain Playbook: {p.stem.replace('_', ' ').title()}",
                    description=(
                        "Non-normative retrospective DDx prompts for "
                        f"{p.stem}; no patient-specific management"
                    ),
                    mime_type="application/yaml",
                    size=p.stat().st_size if p.is_file() else None,
                )
            )

    # 3. Report Templates
    templates_dir = config_root / "templates"
    if templates_dir.exists():
        for p in templates_dir.glob("*.md"):
            slug = p.stem.replace("_", "-")
            resources.append(
                Resource(
                    uri=f"clinical://templates/{slug}",
                    name=f"Report Template: {p.stem.replace('_', ' ').title()}",
                    description=f"Deterministic Markdown report template for {p.stem}",
                    mime_type="text/markdown",
                    size=p.stat().st_size if p.is_file() else None,
                )
            )

    return resources


def get_resource_templates() -> list[ResourceTemplate]:
    """Return dynamic session resource templates for active clinical cases."""
    return [
        ResourceTemplate(
            uri_template="clinical://sessions/{session_id}/report",
            name="Session Clinical Reasoning Report",
            description="Current preliminary unified DDx and RCA preview from live session state",
            mime_type="text/markdown",
        ),
        ResourceTemplate(
            uri_template="clinical://sessions/{session_id}/timeline",
            name="Session Event Timeline",
            description="Dynamic chronological event timeline and Mermaid diagram for a session",
            mime_type="text/markdown",
        ),
        ResourceTemplate(
            uri_template="clinical://sessions/{session_id}/guidance",
            name="Session Reasoning Guidance",
            description="Active stage progression, readiness checklist, and next recommended actions",
            mime_type="application/json",
        ),
        ResourceTemplate(
            uri_template="clinical://sessions/{session_id}/conflicts",
            name="Session Conflict & Gap Analysis",
            description="Automated clinical contradiction and guideline monitoring omission audit",
            mime_type="application/json",
        ),
    ]


async def _read_unified_report_preview(
    uri: str,
    session_id: str,
    contract_handler: ContractHandlers,
) -> ReadResourceResult:
    """Render the current unified report without creating an export artifact."""
    preview = await contract_handler.handle_generate_contract_report(
        {
            "session_id": session_id,
            "format": "markdown",
            "detail_level": "standard",
            "locale": "zh-TW",
            "audience": "clinician",
            "finalize": False,
        },
        persist_export=False,
    )
    if preview.get("status") == "success":
        return ReadResourceResult(
            contents=[
                TextResourceContents(
                    uri=uri,
                    mime_type="text/markdown",
                    text=str(preview["content"]),
                )
            ]
        )
    message = preview.get("message", "Unified report preview failed")
    return ReadResourceResult(
        contents=[
            TextResourceContents(
                uri=uri,
                mime_type="text/plain",
                text=f"Report preview unavailable: {message}",
            )
        ]
    )


async def read_clinical_resource(
    uri: str,
    server_state: ServerState | None = None,
    contract_handler: ContractHandlers | None = None,
) -> ReadResourceResult:
    """
    Read a clinical resource by URI.

    Handles:
    - Static: `clinical://protocols/{slug}`, `clinical://domains/{slug}`, `clinical://templates/{slug}`
    - Dynamic: `clinical://sessions/{session_id}/{artifact}`
    """
    config_root = _get_config_root()
    clean_uri = uri.strip()

    if clean_uri == "clinical://contracts/case-input-manifest":
        import json

        from rootcause_mcp.domain.value_objects.case_manifest import CaseInputManifest

        return ReadResourceResult(
            contents=[
                TextResourceContents(
                    uri=clean_uri,
                    mime_type="application/schema+json",
                    text=json.dumps(CaseInputManifest.model_json_schema(), indent=2),
                )
            ]
        )

    if clean_uri == "clinical://contracts/case-analysis-report":
        import json

        from rootcause_mcp.domain.value_objects.contract_report import ContractReport

        return ReadResourceResult(
            contents=[
                TextResourceContents(
                    uri=clean_uri,
                    mime_type="application/schema+json",
                    text=json.dumps(ContractReport.model_json_schema(), indent=2),
                )
            ]
        )

    # 1. Handle Protocols
    if clean_uri.startswith("clinical://protocols/"):
        slug = clean_uri.removeprefix("clinical://protocols/")
        target = _resolve_static_resource(config_root, "protocols", slug, ".yaml")
        if target is not None:
            text = target.read_text(encoding="utf-8")
            return ReadResourceResult(
                contents=[
                    TextResourceContents(
                        uri=clean_uri,
                        mime_type="application/yaml",
                        text=text,
                    )
                ]
            )

    # 2. Handle Domains
    if clean_uri.startswith("clinical://domains/"):
        slug = clean_uri.removeprefix("clinical://domains/")
        target = _resolve_static_resource(config_root, "domains", slug, ".yaml")
        if target is not None:
            text = target.read_text(encoding="utf-8")
            return ReadResourceResult(
                contents=[
                    TextResourceContents(
                        uri=clean_uri,
                        mime_type="application/yaml",
                        text=text,
                    )
                ]
            )

    # 3. Handle Templates
    if clean_uri.startswith("clinical://templates/"):
        slug = clean_uri.removeprefix("clinical://templates/")
        target = _resolve_static_resource(config_root, "templates", slug, ".md")
        if target is not None:
            text = target.read_text(encoding="utf-8")
            return ReadResourceResult(
                contents=[
                    TextResourceContents(
                        uri=clean_uri,
                        mime_type="text/markdown",
                        text=text,
                    )
                ]
            )

    # 4. Handle Dynamic Sessions
    if clean_uri.startswith("clinical://sessions/") and server_state is not None:
        parts = clean_uri.replace("clinical://sessions/", "").split("/")
        if len(parts) == 2:
            session_id, artifact = parts[0], parts[1]
            if artifact == "report" and contract_handler is not None:
                return await _read_unified_report_preview(
                    clean_uri,
                    session_id,
                    contract_handler,
                )

            orch = await server_state.get_orchestrator(session_id)
            if orch is not None:
                if artifact == "guidance":
                    import json

                    guidance = orch.get_guidance()
                    return ReadResourceResult(
                        contents=[
                            TextResourceContents(
                                uri=clean_uri,
                                mime_type="application/json",
                                text=json.dumps(
                                    guidance.model_dump(mode="json"), indent=2
                                ),
                            )
                        ]
                    )
                elif artifact == "conflicts":
                    import json

                    from rootcause_mcp.domain.services.gap_analyzer import (
                        ClinicalGapAnalyzer,
                    )

                    gap_rep = ClinicalGapAnalyzer.analyze(
                        session_id=session_id,
                        evidence_store=orch.evidence_store,
                        hypothesis_store=orch.hypothesis_store,
                        thinking_chain=orch.thinking_chain,
                        reasoning_chain=orch.reasoning_chain,
                    )
                    return ReadResourceResult(
                        contents=[
                            TextResourceContents(
                                uri=clean_uri,
                                mime_type="application/json",
                                text=json.dumps(gap_rep.to_dict(), indent=2),
                            )
                        ]
                    )
                elif artifact == "timeline":
                    from rootcause_mcp.interface.mermaid import build_timeline

                    tl_data = build_timeline(orch.evidence_store.values())
                    content = f"{tl_data['table']}\n\n{tl_data['mermaid']}"
                    return ReadResourceResult(
                        contents=[
                            TextResourceContents(
                                uri=clean_uri,
                                mime_type="text/markdown",
                                text=content,
                            )
                        ]
                    )
                elif artifact == "report":
                    from rootcause_mcp.domain.value_objects.contract_report import (
                        ContractReport,
                    )
                    from rootcause_mcp.interface.contract_markdown import (
                        render_contract_report_markdown,
                    )
                    from rootcause_mcp.interface.mermaid import build_evidence_graph

                    working_hypotheses = list(orch.hypothesis_store.values())
                    rep = ContractReport.model_validate(
                        {
                            "report_id": f"RPT-{session_id}",
                            "session_id": session_id,
                            "generated_by": "resource_reader",
                            "leading_hypothesis_id": (orch.get_leading_hypothesis_id()),
                            "hypotheses": [
                                {
                                    **h.model_dump(mode="json"),
                                    "probability_semantics": (
                                        "UNCALIBRATED_COMPATIBILITY_ONLY"
                                    ),
                                    "clinical_probability_established": False,
                                }
                                for h in working_hypotheses
                            ],
                            "evidence": [
                                e.model_dump(mode="json")
                                for e in orch.evidence_store.values()
                            ],
                            "reasoning_chain": [
                                {
                                    **s.model_dump(mode="json"),
                                    "confidence_semantics": (
                                        "UNCALIBRATED_LEGACY_NOT_PRESENTED"
                                    ),
                                }
                                for s in orch.reasoning_chain.steps
                            ],
                            "thinking_chain": [
                                {
                                    **s.model_dump(mode="json"),
                                    "confidence_semantics": (
                                        "UNCALIBRATED_LEGACY_NOT_PRESENTED"
                                    ),
                                }
                                for s in orch.thinking_chain.steps
                            ],
                            "evidence_graph": build_evidence_graph(
                                orch.evidence_store.values(),
                                orch.hypothesis_store.values(),
                            ),
                        }
                    )
                    md_text = render_contract_report_markdown(
                        rep,
                        detail_level="standard",
                        locale="zh-TW",
                        audience="clinician",
                    )
                    md_text = (
                        "> 此為 limited clinical-only fallback：目前未提供 "
                        "ContractHandlers，因此省略 source manifest 與 RCA artifacts。\n\n"
                        f"{md_text}"
                    )
                    return ReadResourceResult(
                        contents=[
                            TextResourceContents(
                                uri=clean_uri,
                                mime_type="text/markdown",
                                text=md_text,
                            )
                        ]
                    )

    # Resource not found fallback
    return ReadResourceResult(
        contents=[
            TextResourceContents(
                uri=clean_uri,
                mime_type="text/plain",
                text=f"Resource not found: {clean_uri}",
            )
        ]
    )
