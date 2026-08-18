"""Conformance checks for the dated per-repository research library."""

from __future__ import annotations

import re
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
LANDSCAPE_ROOT = REPOSITORY_ROOT / "docs" / "research" / "github_landscape"
REPORTS_ROOT = LANDSCAPE_ROOT / "repositories"
INDEX_PATH = LANDSCAPE_ROOT / "README.md"
REPORT_LINK_RE = re.compile(r"\]\((repositories/[^)#]+\.md)(?:#[^)]+)?\)")
LOCAL_LINK_RE = re.compile(r"\]\((?!https?://|mailto:|#)([^)#]+)(?:#[^)]+)?\)")
COMMIT_SHA_RE = re.compile(r"\b[0-9a-f]{40}\b")

REQUIRED_HEADINGS = (
    "## 查核資料",
    "## 一句話結論",
    "## 它解決什麼問題",
    "## 最值得學習的設計",
    "## 與 RootCause MCP 的關係",
    "## 採用建議",
    "## 建議引用",
    "## 來源",
    "## 查核限制",
)


def test_index_covers_each_repository_report_exactly_once() -> None:
    index = INDEX_PATH.read_text(encoding="utf-8")
    indexed = REPORT_LINK_RE.findall(index)
    reports = {f"repositories/{path.name}" for path in REPORTS_ROOT.glob("*.md")}

    assert len(indexed) == 26
    assert len(indexed) == len(set(indexed))
    assert set(indexed) == reports


def test_repository_reports_have_auditable_learning_sections() -> None:
    for path in sorted(REPORTS_ROOT.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        commit_match = COMMIT_SHA_RE.search(text)

        assert text.startswith("# "), path
        assert "https://github.com/" in text, path
        assert "2026-08-18" in text, path
        assert commit_match is not None, f"{path}: missing full commit SHA"
        assert (
            f"/{commit_match.group(0)}/" in text
            or f"/commit/{commit_match.group(0)}" in text
        ), f"{path}: source links are not pinned to the audited commit"
        assert "授權" in text, path
        assert "@software{" in text, f"{path}: missing software citation fallback"
        assert "### 基礎套件的引用與依賴方式" in text or "### 概念引用方式" in text, (
            f"{path}: missing adoption-specific citation guidance"
        )

        role_line = next(
            (line for line in text.splitlines() if line.startswith("| 專案角色 |")),
            "",
        )
        if "基礎" in role_line:
            assert "### 基礎套件的引用與依賴方式" in text, path
        for heading in REQUIRED_HEADINGS:
            assert heading in text, f"{path}: missing {heading}"


def test_local_markdown_links_resolve() -> None:
    markdown_files = [
        REPOSITORY_ROOT / "README.md",
        REPOSITORY_ROOT / "README.zh-TW.md",
        REPOSITORY_ROOT / "docs" / "research" / "existing_solutions.md",
        INDEX_PATH,
        *sorted(REPORTS_ROOT.glob("*.md")),
    ]

    for path in markdown_files:
        text = path.read_text(encoding="utf-8")
        for target in LOCAL_LINK_RE.findall(text):
            clean_target = target.strip().strip("<>")
            if not clean_target or "{" in clean_target:
                continue
            resolved = (path.parent / clean_target).resolve()
            assert resolved.exists(), f"{path}: broken local link {target}"


def test_meddxagent_license_is_not_misrepresented() -> None:
    report = (REPORTS_ROOT / "nec-research__meddxagent.md").read_text(encoding="utf-8")
    overview = (
        REPOSITORY_ROOT / "docs" / "research" / "existing_solutions.md"
    ).read_text(encoding="utf-8")

    assert "noncommercial" in report.lower() or "非商業" in report
    assert "非商業研究授權" in overview
    assert "MEDDxAgent (NEC Research)\n\n**連結**" not in overview
    assert "是目前**唯一**" not in overview
    assert "唯一同時整合" not in overview
