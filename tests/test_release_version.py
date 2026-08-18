import re
import tomllib
from pathlib import Path

from rootcause_mcp import __version__
from rootcause_mcp.domain.value_objects.contract_report import ContractReport
from rootcause_mcp.interface.prompts import get_all_prompts
from rootcause_mcp.interface.resources import (
    get_resource_templates,
    get_static_resources,
)
from rootcause_mcp.interface.tools import get_all_tools
from rootcause_mcp.server_v2 import server


def test_public_release_versions_stay_aligned() -> None:
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    expected = project["project"]["version"]

    report = ContractReport(
        report_id="RPT-version-contract",
        session_id="rc_sess_version_contract",
        generated_by="version-test",
    )

    assert expected == "2.0.0a2"
    assert __version__ == expected
    assert server.version == expected
    assert report.report_version == expected


def test_server_advertises_clinical_responsibility_boundaries() -> None:
    instructions = server.instructions or ""
    assert "does not reason, diagnose, or prove clinical causality" in instructions
    assert "Traditional Chinese" in instructions
    assert "non-normative retrospective DDx prompts" in instructions


def test_release_snapshot_catalog_counts_and_domain_docs_stay_aligned() -> None:
    """Release-facing counts and README domain slugs must match live catalogs."""
    assert {
        profile: len(get_all_tools(profile))
        for profile in ("all", "clinical", "rca", "condensed")
    } == {"all": 46, "clinical": 25, "rca": 24, "condensed": 8}

    resources = get_static_resources()
    assert len(resources) == 19
    assert len(get_resource_templates()) == 4
    assert len(get_all_prompts()) == 5

    domain_prefix = "clinical://domains/"
    runtime_domain_slugs = {
        str(resource.uri).removeprefix(domain_prefix)
        for resource in resources
        if str(resource.uri).startswith(domain_prefix)
    }
    non_domain_uris = {
        str(resource.uri)
        for resource in resources
        if not str(resource.uri).startswith(domain_prefix)
    }
    assert len(runtime_domain_slugs) == 9

    for readme_path in (Path("README.md"), Path("README.zh-TW.md")):
        text = readme_path.read_text(encoding="utf-8")
        assert all(f"`{uri}`" in text for uri in non_domain_uris)
        domain_block = text.split("`clinical://domains/*`", maxsplit=1)[1].split(
            "\n-", maxsplit=1
        )[0]
        documented_slugs = set(
            re.findall(r"`([a-z0-9]+(?:-[a-z0-9]+)+)`", domain_block)
        )
        assert documented_slugs == runtime_domain_slugs
