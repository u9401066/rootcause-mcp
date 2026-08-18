"""Regression tests for the dependency-free static website conformance gate."""

from __future__ import annotations

import ast
import importlib
import json
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Protocol, cast

import pytest

from rootcause_mcp.domain.entities.hypothesis import PlannedDiagnosticTest
from rootcause_mcp.domain.value_objects.contract_report import ContractReport


class _Issue(Protocol):
    path: str
    message: str


class _Checker(Protocol):
    SITE_BASE_URL: str

    @staticmethod
    def check_website(_site_root: str | Path = Path("website")) -> list[_Issue]: ...

    @staticmethod
    def main(argv: list[str] | None = None) -> int: ...


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))
CHECKER = cast("_Checker", importlib.import_module("scripts.check_website"))
SITE_BASE_URL = CHECKER.SITE_BASE_URL
check_website = CHECKER.check_website
main = CHECKER.main


class _ReportExampleParser(HTMLParser):
    """Collect visible JSON text from the report-example ``pre`` element."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "pre" and values.get("id") == "report-example":
            self.depth = 1
        elif self.depth:
            self.depth += 1

    def handle_endtag(self, _tag: str) -> None:
        if self.depth:
            self.depth -= 1

    def handle_data(self, data: str) -> None:
        if self.depth:
            self.parts.append(data)


def _report_example(path: Path) -> dict[str, object]:
    parser = _ReportExampleParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return cast("dict[str, object]", json.loads("".join(parser.parts)))


def _p0_hard_mutation_case_count() -> int:
    """Read the authoritative parametrized mutation table without importing it."""
    path = REPOSITORY_ROOT / "tests" / "test_p0_final_report_conformance.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name != "test_every_negative_mutation_produces_a_hard_failure":
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            if getattr(decorator.func, "attr", None) != "parametrize":
                continue
            if len(decorator.args) < 2:
                continue
            parameter_names = ast.literal_eval(decorator.args[0])
            if tuple(parameter_names) != ("mutation", "expected_code"):
                continue
            rows = ast.literal_eval(decorator.args[1])
            return len(rows)
    raise AssertionError("P0 hard-mutation parametrization table was not found")


def _page(*, language: str, canonical: str, english: bool) -> str:
    if english:
        heading = "Auditable clinical reasoning, with humans accountable"
        content = """
        <p><strong>Engineering alpha.</strong> RootCause MCP is not a medical device.</p>
        <section id="responsibilities">
          <h2>Responsibility boundary</h2>
          <p>The Host Agent or approved extractor preserves source material.</p>
          <p>The reasoning Agent performs clinical reasoning.</p>
          <p>MCP enforces schema, provenance, calculations, and workflow gates.</p>
          <p>A qualified human reviewer performs clinical review.</p>
        </section>
        <section id="causation">
          <h2>Causation status</h2>
          <p>The conservative audit does not prove clinical causality.</p>
        </section>
        <section id="p0-conformance">
          <h2>P0 deterministic conformance</h2>
          <p>A typed nested report schema emits conformance_checks[].</p>
          <p>Root audit lineage keeps Root, Why, and evidence exact; REJECTED is omitted and INSUFFICIENT_DATA remains PROPOSED.</p>
          <p>Finalization records a recomputable hash and creates an immutable final snapshot.</p>
        </section>
        <section id="formal-evaluation">
          <h2>Formal evaluation</h2>
          <p>Formal evaluation with a repo-external private holdout is NOT_ESTABLISHED.</p>
        </section>
        """
        peer_link = "../#responsibilities"
        stylesheet = "../assets/styles.css"
        script = "../assets/site.js"
        favicon = "../favicon.svg"
    else:
        heading = "可稽核的臨床推理，由人類承擔判斷責任"
        content = """
        <p><strong>Engineering alpha。</strong>RootCause MCP 不是醫療器材。</p>
        <section id="responsibilities">
          <h2>責任邊界</h2>
          <p>宿主 Host Agent 或 approved extractor 保存來源材料。</p>
          <p>Reasoning Agent 負責醫學推理。</p>
          <p>MCP 負責 schema、溯源、計算與 workflow gates。</p>
          <p>合格 qualified human reviewer 負責臨床審查。</p>
        </section>
        <section id="causation">
          <h2>因果狀態</h2>
          <p>保守稽核不代表臨床因果已獲證明。</p>
        </section>
        <section id="p0-conformance">
          <h2>P0 deterministic conformance</h2>
          <p>Typed nested schema 會輸出 machine-readable conformance_checks[]。</p>
          <p>Root audit lineage 要求 Root、Why、evidence 一致；REJECTED 必須移除，INSUFFICIENT_DATA 只能是 PROPOSED。</p>
          <p>Finalization 記錄可重算 hash，並建立 immutable final snapshot。</p>
        </section>
        <section id="formal-evaluation">
          <h2>正式評估</h2>
          <p>使用 repo-external private holdout 的正式評估仍為 NOT_ESTABLISHED。</p>
        </section>
        """
        peer_link = "./en/#responsibilities"
        stylesheet = "./assets/styles.css"
        script = "./assets/site.js"
        favicon = "./favicon.svg"
    return f"""<!doctype html>
<html lang="{language}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Auditable multi-source clinical reasoning documentation.">
  <meta name="robots" content="index, follow">
  <meta property="og:title" content="RootCause MCP">
  <meta property="og:description" content="Auditable clinical reasoning harness">
  <meta property="og:type" content="website">
  <meta property="og:url" content="{canonical}">
  <link rel="canonical" href="{canonical}">
  <link rel="icon" href="{favicon}" type="image/svg+xml">
  <link rel="stylesheet" href="{stylesheet}">
  <title>RootCause MCP — auditable clinical reasoning</title>
  <script type="application/ld+json">{{"@type": "SoftwareSourceCode"}}</script>
</head>
<body>
  <header><nav aria-label="Primary"><a href="#main-content">Skip</a></nav></header>
  <main id="main-content"><h1>{heading}</h1>{content}<a href="{peer_link}">Language</a></main>
  <footer><p>Apache-2.0</p></footer>
  <script src="{script}" defer></script>
</body>
</html>
"""


def _write_valid_site(root: Path) -> None:
    (root / "assets").mkdir(parents=True)
    (root / "en").mkdir()
    (root / "index.html").write_text(
        _page(language="zh-Hant", canonical=SITE_BASE_URL, english=False),
        encoding="utf-8",
    )
    (root / "en" / "index.html").write_text(
        _page(
            language="en",
            canonical=f"{SITE_BASE_URL}en/",
            english=True,
        ),
        encoding="utf-8",
    )
    (root / "404.html").write_text(
        """<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex">
  <base href="/rootcause-mcp/">
  <link rel="icon" href="favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="assets/styles.css">
  <title>找不到頁面 — RootCause MCP</title>
</head>
<body>
  <header><a href="./">RootCause MCP</a></header>
  <main id="main-content"><h1>找不到頁面</h1><a href="./">回首頁</a></main>
  <footer>Engineering alpha · 非醫療器材</footer>
</body>
</html>
""",
        encoding="utf-8",
    )
    (root / "assets" / "styles.css").write_text(
        ":root { color-scheme: light dark; }\n", encoding="utf-8"
    )
    (root / "assets" / "site.js").write_text(
        'document.documentElement.classList.add("js");\n', encoding="utf-8"
    )
    (root / "favicon.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">'
        '<title>RootCause MCP</title><circle cx="8" cy="8" r="7"/></svg>\n',
        encoding="utf-8",
    )
    (root / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {SITE_BASE_URL}sitemap.xml\n",
        encoding="utf-8",
    )
    (root / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"<url><loc>{SITE_BASE_URL}</loc></url>"
        f"<url><loc>{SITE_BASE_URL}en/</loc></url>"
        "</urlset>\n",
        encoding="utf-8",
    )
    (root / ".nojekyll").touch()


def _messages(root: Path) -> list[str]:
    return [issue.message for issue in check_website(root)]


def test_valid_static_site_passes(tmp_path: Path) -> None:
    _write_valid_site(tmp_path)

    assert check_website(tmp_path) == []


def test_structure_language_and_seo_are_required(tmp_path: Path) -> None:
    _write_valid_site(tmp_path)
    page = tmp_path / "index.html"
    text = page.read_text(encoding="utf-8")
    text = (
        text.replace(' lang="zh-Hant"', "")
        .replace("<h1>", "<h2>")
        .replace("</h1>", "</h2>")
    )
    text = text.replace("<footer>", "<div>").replace("</footer>", "</div>")
    text = text.replace('<meta name="description"', '<meta name="summary"')
    text = text.replace('<link rel="canonical"', '<link rel="bookmark"')
    page.write_text(text, encoding="utf-8")

    messages = _messages(tmp_path)

    assert any("exactly one h1" in message for message in messages)
    assert "html requires a non-empty lang attribute" in messages
    assert "missing footer landmark" in messages
    assert any("meta description" in message for message in messages)
    assert any("canonical link" in message for message in messages)


def test_local_links_fragments_and_relative_assets_are_checked(tmp_path: Path) -> None:
    _write_valid_site(tmp_path)
    page = tmp_path / "index.html"
    text = page.read_text(encoding="utf-8")
    text = text.replace(
        '<a href="./en/#responsibilities">',
        '<a href="./en/#missing-fragment">',
    ).replace("./assets/styles.css", "/assets/styles.css")
    page.write_text(text, encoding="utf-8")

    messages = _messages(tmp_path)

    assert any("fragment #missing-fragment" in message for message in messages)
    assert any("must be relative for project Pages" in message for message in messages)


def test_artifact_allowlist_rejects_raw_data_and_symlinks(tmp_path: Path) -> None:
    _write_valid_site(tmp_path)
    (tmp_path / "patient_record.csv").write_text("patient,value\n", encoding="utf-8")
    for forbidden_directory in ("data", "docs", "examples"):
        directory = tmp_path / forbidden_directory
        directory.mkdir()
        (directory / "index.html").write_text("<!doctype html>", encoding="utf-8")
    link = tmp_path / "assets" / "linked.css"
    try:
        link.symlink_to(tmp_path / "assets" / "styles.css")
    except OSError:
        pytest.skip("symlinks are unavailable on this platform")

    issues = check_website(tmp_path)
    messages = [issue.message for issue in issues]

    assert "database/raw-case artifact is forbidden" in messages
    assert "symbolic links are forbidden" in messages
    for forbidden_directory in ("data", "docs", "examples"):
        assert any(
            issue.path == f"{forbidden_directory}/index.html"
            and issue.message == "database/raw-case artifact is forbidden"
            for issue in issues
        )


def test_external_resources_analytics_network_code_and_claims_fail(
    tmp_path: Path,
) -> None:
    _write_valid_site(tmp_path)
    page = tmp_path / "index.html"
    page.write_text(
        page.read_text(encoding="utf-8")
        .replace(
            "</head>",
            '<script src="https://example.com/tracker.js"></script>'
            '<link rel="stylesheet" href="https://fonts.example/font.css">'
            "<script>alert('unsafe inline script')</script>"
            "</head>",
        )
        .replace("</main>", "<p>本系統保證合規。</p></main>"),
        encoding="utf-8",
    )
    (tmp_path / "assets" / "site.js").write_text(
        'gtag("config", "tracking-id");\nfetch("https://example.com");\n',
        encoding="utf-8",
    )

    messages = _messages(tmp_path)

    assert sum("external resource is forbidden" in message for message in messages) >= 2
    assert any("analytics code is forbidden" in message for message in messages)
    assert any("network-capable JavaScript" in message for message in messages)
    assert any("inline script is forbidden" in message for message in messages)
    assert any("forbidden claim" in message for message in messages)


def test_required_responsibility_boundary_is_enforced(tmp_path: Path) -> None:
    _write_valid_site(tmp_path)
    page = tmp_path / "en" / "index.html"
    page.write_text(
        page.read_text(encoding="utf-8").replace(
            "A qualified human reviewer performs clinical review.", ""
        ),
        encoding="utf-8",
    )

    messages = _messages(tmp_path)

    assert any("qualified human review" in message for message in messages)


@pytest.mark.parametrize(
    ("relative_path", "required_text", "concept"),
    [
        (
            Path("index.html"),
            "Typed nested schema 會輸出 machine-readable conformance_checks[]。",
            "typed nested report conformance",
        ),
        (
            Path("en/index.html"),
            "A typed nested report schema emits conformance_checks[].",
            "typed nested report conformance",
        ),
        (
            Path("index.html"),
            "Root audit lineage 要求 Root、Why、evidence 一致；REJECTED 必須移除，INSUFFICIENT_DATA 只能是 PROPOSED。",
            "root audit lineage and safe disposition",
        ),
        (
            Path("en/index.html"),
            "Root audit lineage keeps Root, Why, and evidence exact; REJECTED is omitted and INSUFFICIENT_DATA remains PROPOSED.",
            "root audit lineage and safe disposition",
        ),
        (
            Path("index.html"),
            "Finalization 記錄可重算 hash，並建立 immutable final snapshot。",
            "immutable recomputable final snapshot",
        ),
        (
            Path("en/index.html"),
            "Finalization records a recomputable hash and creates an immutable final snapshot.",
            "immutable recomputable final snapshot",
        ),
        (
            Path("index.html"),
            "使用 repo-external private holdout 的正式評估仍為 NOT_ESTABLISHED。",
            "formal private evaluation not established",
        ),
        (
            Path("en/index.html"),
            "Formal evaluation with a repo-external private holdout is NOT_ESTABLISHED.",
            "formal private evaluation not established",
        ),
    ],
)
def test_p0_and_formal_evaluation_contracts_are_enforced_in_both_languages(
    tmp_path: Path,
    relative_path: Path,
    required_text: str,
    concept: str,
) -> None:
    _write_valid_site(tmp_path)
    page = tmp_path / relative_path
    page.write_text(
        page.read_text(encoding="utf-8").replace(required_text, ""),
        encoding="utf-8",
    )

    messages = _messages(tmp_path)

    assert any(concept in message for message in messages)


def test_cli_returns_nonzero_and_reports_violations(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_valid_site(tmp_path)
    (tmp_path / "robots.txt").write_text(
        "User-agent: *\nDisallow: /\n", encoding="utf-8"
    )

    assert main([str(tmp_path)]) == 1
    captured = capsys.readouterr()
    assert "Website conformance failed" in captured.err
    assert "robots.txt" in captured.err


def test_bilingual_report_examples_use_the_live_typed_contract() -> None:
    payloads = [
        _report_example(Path("website/index.html")),
        _report_example(Path("website/en/index.html")),
    ]

    assert payloads[0] == payloads[1]
    for payload in payloads:
        typed_input: dict[str, object] = {
            "report_id": "RPT-website-example",
            "session_id": "rc_sess_website_example",
            "generated_by": "website-example",
            **payload,
        }
        ContractReport.model_validate(typed_input)

        assert isinstance(payload["source_inventory"], list)
        hypotheses = cast("list[dict[str, object]]", payload["hypotheses"])
        assert len(hypotheses) == 3
        planned_tests = cast("list[dict[str, object]]", hypotheses[2]["planned_tests"])
        PlannedDiagnosticTest.model_validate(planned_tests[0])
        assert planned_tests[0]["test_id"] == "TST-001"

        roots = cast("list[dict[str, object]]", payload["root_causes"])
        assert roots[0]["causation_result"] == "INSUFFICIENT_DATA"
        assert roots[0]["disposition"] == "PROPOSED"

        audits = cast("list[dict[str, object]]", payload["causation_verifications"])
        assert audits[0]["audit_scope"] == "CONSERVATIVE_CAUSATION_AUDIT"
        assert audits[0]["clinical_causality_established"] is False

        checks = cast("list[dict[str, object]]", payload["conformance_checks"])
        assert checks[0]["code"] == "ROOT_CAUSATION_AUDIT_LINEAGE"
        assert payload["is_finalized"] is False
        assert payload["content_hash"] is None


def test_website_mutation_count_matches_authoritative_p0_table() -> None:
    """Keep the bilingual release snapshot synchronized with the P0 mutation table."""
    count = _p0_hard_mutation_case_count()
    english = Path("website/en/index.html").read_text(encoding="utf-8")
    traditional_chinese = Path("website/index.html").read_text(encoding="utf-8")

    assert count == 76
    assert f"{count}/{count} targeted hard-mutation regressions" in english
    assert f"{count}／{count} targeted hard-mutation regressions" in traditional_chinese


def test_repository_website_conforms() -> None:
    issues = check_website(Path("website"))

    assert issues == [], "\n".join(str(issue) for issue in issues)
