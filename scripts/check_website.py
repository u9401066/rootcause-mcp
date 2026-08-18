#!/usr/bin/env python3
"""Fail-closed conformance checks for the static GitHub Pages artifact."""

from __future__ import annotations

import argparse
import os
import re
import sys
import xml.etree.ElementTree as ET  # nosec B405
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

SITE_ORIGIN = "https://u9401066.github.io"
SITE_BASE_PATH = "/rootcause-mcp/"
SITE_BASE_URL = f"{SITE_ORIGIN}{SITE_BASE_PATH}"

EXPECTED_FILES = frozenset(
    {
        PurePosixPath("index.html"),
        PurePosixPath("en/index.html"),
        PurePosixPath("404.html"),
        PurePosixPath("assets/styles.css"),
        PurePosixPath("assets/site.js"),
        PurePosixPath("favicon.svg"),
        PurePosixPath("robots.txt"),
        PurePosixPath("sitemap.xml"),
        PurePosixPath(".nojekyll"),
    }
)
ALLOWED_SUFFIXES = frozenset({".html", ".css", ".js", ".svg", ".png", ".webp", ".ico"})
SPECIAL_TEXT_FILES = frozenset(
    {PurePosixPath("robots.txt"), PurePosixPath("sitemap.xml")}
)
FORBIDDEN_RAW_SUFFIXES = frozenset(
    {
        ".csv",
        ".db",
        ".dcm",
        ".dicom",
        ".doc",
        ".docx",
        ".hl7",
        ".jsonl",
        ".msg",
        ".pdf",
        ".sqlite",
        ".sqlite3",
        ".tsv",
        ".xls",
        ".xlsx",
    }
)
FORBIDDEN_PATH_PARTS = frozenset(
    {
        "backup",
        "case_rawdata",
        "checkpoint",
        "checkpoints",
        "data",
        "data_source",
        "docs",
        "ehr_export",
        "emr_export",
        "examples",
        "exports",
        "patient_record",
    }
)
ANALYTICS_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"google-analytics\.com",
        r"googletagmanager\.com",
        r"\bgtag\s*\(",
        r"\bdataLayer\b",
        r"plausible\.io/js/",
        r"\bposthog\.init\s*\(",
        r"\bmixpanel\.init\s*\(",
        r"clarity\.ms/tag/",
        r"\bhotjar\b",
        r"umami(?:\.is)?/script",
    )
)
FORBIDDEN_CLAIMS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"自動(?:地)?找出(?:真正|真實)的?根因",
        r"零\s*(?:幻覺|hallucination)",
        r"(?:保證合規|(?:法規)?合規(?:性)?保證)",
        r"已證明因果",
        r"100\s*%\s*確診",
        r"automatically (?:finds|identifies) the (?:true|actual) root cause",
        r"zero[- ]hallucination",
        r"guarantee(?:d|s)? (?:regulatory )?compliance",
        r"guarantees? of (?:regulatory )?compliance",
        r"causality is proven",
        r"100\s*% diagnostic accuracy",
    )
)

CSS_URL_PATTERN = re.compile(r"url\(\s*(['\"]?)(.*?)\1\s*\)", re.IGNORECASE)
CSS_IMPORT_PATTERN = re.compile(r"@import\s+(?:url\()?\s*(['\"])(.*?)\1", re.IGNORECASE)


@dataclass(frozen=True, order=True)
class Violation:
    """One deterministic website conformance failure."""

    path: str
    line: int
    message: str

    def __str__(self) -> str:
        location = f"{self.path}:{self.line}" if self.line else self.path
        return f"{location}: {self.message}"


@dataclass(frozen=True)
class Reference:
    """A URL-bearing HTML or CSS attribute."""

    source: PurePosixPath
    line: int
    kind: str
    url: str
    is_resource: bool


@dataclass
class HTMLDocument:
    """The small DOM subset needed for static conformance checks."""

    path: PurePosixPath
    tags: Counter[str] = field(default_factory=Counter)
    ids: dict[str, int] = field(default_factory=dict)
    references: list[Reference] = field(default_factory=list)
    issues: list[Violation] = field(default_factory=list)
    meta_names: dict[str, list[tuple[str, int]]] = field(default_factory=dict)
    meta_properties: dict[str, list[tuple[str, int]]] = field(default_factory=dict)
    canonical_links: list[tuple[str, int]] = field(default_factory=list)
    stylesheet_targets: list[str] = field(default_factory=list)
    script_targets: list[str] = field(default_factory=list)
    icon_targets: list[str] = field(default_factory=list)
    base_targets: list[tuple[str, int]] = field(default_factory=list)
    html_lang: str = ""
    charset: str = ""
    title_parts: list[str] = field(default_factory=list)
    h1_parts: list[str] = field(default_factory=list)
    visible_parts: list[str] = field(default_factory=list)
    _inside_title: int = 0
    _inside_h1: int = 0
    _ignored_depth: int = 0

    @property
    def visible_text(self) -> str:
        return " ".join(" ".join(self.visible_parts).split())

    @property
    def title(self) -> str:
        return " ".join(" ".join(self.title_parts).split())

    @property
    def h1_text(self) -> str:
        return " ".join(" ".join(self.h1_parts).split())


class WebsiteHTMLParser(HTMLParser):
    """Extract deterministic structure without third-party parser dependencies."""

    def __init__(self, path: PurePosixPath) -> None:
        super().__init__(convert_charrefs=True)
        self.document = HTMLDocument(path=path)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.casefold()
        line, _ = self.getpos()
        values = {key.casefold(): value or "" for key, value in attrs}
        document = self.document
        document.tags[tag] += 1

        element_id = values.get("id", "").strip()
        if element_id:
            previous = document.ids.get(element_id)
            if previous is not None:
                document.issues.append(
                    Violation(
                        document.path.as_posix(),
                        line,
                        f"duplicate id {element_id!r} (first declared on line {previous})",
                    )
                )
            else:
                document.ids[element_id] = line

        if tag == "html":
            document.html_lang = values.get("lang", "").strip()
        elif tag == "title":
            document._inside_title += 1
        elif tag == "h1":
            document._inside_h1 += 1
        elif tag in {"script", "style", "template"}:
            document._ignored_depth += 1

        self._record_metadata(tag, values, line)
        self._record_references(tag, values, line)
        self._check_element_policy(tag, values, line)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.casefold()
        if tag == "title" and self.document._inside_title:
            self.document._inside_title -= 1
        elif tag == "h1" and self.document._inside_h1:
            self.document._inside_h1 -= 1
        elif tag in {"script", "style", "template"} and self.document._ignored_depth:
            self.document._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.document._inside_title:
            self.document.title_parts.append(data)
        if self.document._inside_h1:
            self.document.h1_parts.append(data)
        if not self.document._ignored_depth:
            self.document.visible_parts.append(data)

    def _record_metadata(self, tag: str, values: dict[str, str], line: int) -> None:
        document = self.document
        if tag == "meta":
            charset = values.get("charset", "").strip()
            if charset:
                document.charset = charset
            content = values.get("content", "").strip()
            name = values.get("name", "").strip().casefold()
            property_name = values.get("property", "").strip().casefold()
            if name:
                document.meta_names.setdefault(name, []).append((content, line))
            if property_name:
                document.meta_properties.setdefault(property_name, []).append(
                    (content, line)
                )
        if tag == "base":
            document.base_targets.append((values.get("href", "").strip(), line))
        if tag != "link":
            return
        rel_tokens = set(values.get("rel", "").casefold().split())
        href = values.get("href", "").strip()
        if "canonical" in rel_tokens:
            document.canonical_links.append((href, line))
        if "stylesheet" in rel_tokens:
            document.stylesheet_targets.append(href)
        if "icon" in rel_tokens:
            document.icon_targets.append(href)

    def _record_references(self, tag: str, values: dict[str, str], line: int) -> None:
        document = self.document
        resource_attributes = {
            "audio": ("src",),
            "embed": ("src",),
            "iframe": ("src",),
            "img": ("src",),
            "object": ("data",),
            "script": ("src",),
            "source": ("src",),
            "video": ("poster", "src"),
        }
        for attribute in resource_attributes.get(tag, ()):
            url = values.get(attribute, "").strip()
            if url:
                document.references.append(
                    Reference(document.path, line, f"{tag}[{attribute}]", url, True)
                )
                if tag == "script" and attribute == "src":
                    document.script_targets.append(url)

        if tag in {"a", "area"}:
            href = values.get("href", "").strip()
            if href:
                document.references.append(
                    Reference(document.path, line, f"{tag}[href]", href, False)
                )
        if tag == "link":
            href = values.get("href", "").strip()
            rel_tokens = set(values.get("rel", "").casefold().split())
            if href and "canonical" not in rel_tokens and "alternate" not in rel_tokens:
                document.references.append(
                    Reference(document.path, line, "link[href]", href, True)
                )

        srcset = values.get("srcset", "").strip()
        if srcset:
            for candidate in srcset.split(","):
                url = candidate.strip().split(maxsplit=1)[0]
                if url:
                    document.references.append(
                        Reference(document.path, line, f"{tag}[srcset]", url, True)
                    )

    def _check_element_policy(
        self, tag: str, values: dict[str, str], line: int
    ) -> None:
        document = self.document
        if tag in {"form", "input", "select", "textarea"}:
            document.issues.append(
                Violation(
                    document.path.as_posix(),
                    line,
                    f"{tag} is forbidden on this non-collecting documentation site",
                )
            )
        if (
            tag == "script"
            and not values.get("src", "").strip()
            and values.get("type", "").casefold() != "application/ld+json"
        ):
            document.issues.append(
                Violation(
                    document.path.as_posix(),
                    line,
                    "inline script is forbidden; use the local assets/site.js",
                )
            )
        if tag == "img" and "alt" not in values:
            document.issues.append(
                Violation(
                    document.path.as_posix(), line, "img requires an alt attribute"
                )
            )
        if tag == "a" and values.get("target", "").casefold() == "_blank":
            rel_tokens = set(values.get("rel", "").casefold().split())
            if not {"noopener", "noreferrer"} <= rel_tokens:
                document.issues.append(
                    Violation(
                        document.path.as_posix(),
                        line,
                        'target="_blank" requires rel="noopener noreferrer"',
                    )
                )


@dataclass(frozen=True)
class PageExpectation:
    """Language and canonical URL expected for one public entry point."""

    languages: tuple[str, ...]
    canonical_url: str


PAGE_EXPECTATIONS = {
    PurePosixPath("index.html"): PageExpectation(
        languages=("zh-hant", "zh-tw"), canonical_url=SITE_BASE_URL
    ),
    PurePosixPath("en/index.html"): PageExpectation(
        languages=("en", "en-us", "en-gb"), canonical_url=f"{SITE_BASE_URL}en/"
    ),
}

REQUIRED_CONCEPTS: dict[str, tuple[tuple[str, ...], ...]] = {
    "engineering-alpha maturity": (("engineering alpha",),),
    "host/extractor responsibility": (
        ("host agent",),
        ("approved extractor",),
        ("宿主", "agent"),
        ("host", "extractor"),
        ("核准", "extractor"),
    ),
    "agent reasoning responsibility": (("agent", "reasoning"), ("agent", "推理")),
    "MCP deterministic controls": (
        ("mcp", "schema"),
        ("mcp", "provenance"),
        ("mcp", "結構"),
        ("mcp", "溯源"),
    ),
    "qualified human review": (
        ("qualified human reviewer",),
        ("qualified", "clinical review"),
        ("合格", "審查"),
        ("合格", "reviewer"),
    ),
    "medical-device limitation": (
        ("not a medical device",),
        ("不是醫療器材",),
        ("非醫療器材",),
    ),
    "causation-audit limitation": (
        ("does not prove", "clinical causality"),
        ("does not prove", "clinical causation"),
        ("does not establish", "clinical causality"),
        ("does not mean", "causation is established"),
        ("not", "clinical causal proof"),
        ("不代表", "臨床因果"),
        ("不能證明", "臨床因果"),
        ("不會證明", "臨床因果"),
        ("不是", "臨床因果證明"),
    ),
    "typed nested report conformance": (
        ("typed nested schema", "conformance_checks"),
        ("typed nested report schema", "conformance_checks"),
    ),
    "root audit lineage and safe disposition": (
        ("root", "why", "evidence", "rejected", "insufficient_data", "proposed"),
    ),
    "immutable recomputable final snapshot": (
        ("recomputable hash", "immutable final snapshot"),
        ("可重算 hash", "immutable final snapshot"),
    ),
    "formal private evaluation not established": (
        ("private holdout", "not_established"),
    ),
}


def _read_text(path: Path, relative_path: PurePosixPath) -> tuple[str, list[Violation]]:
    try:
        return path.read_text(encoding="utf-8"), []
    except (OSError, UnicodeError) as error:
        return "", [
            Violation(relative_path.as_posix(), 0, f"cannot read as UTF-8: {error}")
        ]


def _scan_tree(site_root: Path) -> tuple[list[PurePosixPath], list[Violation]]:
    files: list[PurePosixPath] = []
    issues: list[Violation] = []
    for current_root, directory_names, file_names in os.walk(
        site_root, followlinks=False
    ):
        current = Path(current_root)
        for name in sorted((*directory_names, *file_names)):
            path = current / name
            relative = PurePosixPath(path.relative_to(site_root).as_posix())
            if path.is_symlink():
                issues.append(
                    Violation(relative.as_posix(), 0, "symbolic links are forbidden")
                )
        for file_name in sorted(file_names):
            path = current / file_name
            if path.is_symlink():
                continue
            files.append(PurePosixPath(path.relative_to(site_root).as_posix()))
    return files, issues


def _validate_artifacts(site_root: Path, files: list[PurePosixPath]) -> list[Violation]:
    issues: list[Violation] = []
    missing = sorted(EXPECTED_FILES - set(files))
    issues.extend(
        Violation(path.as_posix(), 0, "required website file is missing")
        for path in missing
    )

    for relative in files:
        lowered_parts = {part.casefold() for part in relative.parts}
        suffix = relative.suffix.casefold()
        if suffix in FORBIDDEN_RAW_SUFFIXES or lowered_parts & FORBIDDEN_PATH_PARTS:
            issues.append(
                Violation(
                    relative.as_posix(), 0, "database/raw-case artifact is forbidden"
                )
            )
        if relative == PurePosixPath(".nojekyll"):
            continue
        if relative in SPECIAL_TEXT_FILES:
            continue
        if suffix not in ALLOWED_SUFFIXES:
            issues.append(
                Violation(
                    relative.as_posix(),
                    0,
                    f"file type {suffix or '<none>'} is not allowlisted",
                )
            )
        if any(part.startswith(".") for part in relative.parts):
            issues.append(
                Violation(
                    relative.as_posix(), 0, "hidden website artifacts are forbidden"
                )
            )
        if not (site_root / relative).is_file():
            issues.append(
                Violation(relative.as_posix(), 0, "artifact is not a regular file")
            )
    return issues


def _parse_html_documents(
    site_root: Path, files: list[PurePosixPath]
) -> tuple[dict[PurePosixPath, HTMLDocument], list[Violation]]:
    documents: dict[PurePosixPath, HTMLDocument] = {}
    issues: list[Violation] = []
    for relative in files:
        if relative.suffix.casefold() != ".html":
            continue
        text, read_issues = _read_text(site_root / relative, relative)
        issues.extend(read_issues)
        if read_issues:
            continue
        parser = WebsiteHTMLParser(relative)
        try:
            parser.feed(text)
            parser.close()
        except (
            Exception
        ) as error:  # HTMLParser subclasses can reject malformed callbacks.
            issues.append(
                Violation(relative.as_posix(), 0, f"cannot parse HTML: {error}")
            )
            continue
        documents[relative] = parser.document
        issues.extend(parser.document.issues)
    return documents, issues


def _first_meta(
    values: dict[str, list[tuple[str, int]]], name: str
) -> tuple[str, int] | None:
    matches = values.get(name, [])
    return matches[0] if matches else None


def _validate_document_structure(document: HTMLDocument) -> list[Violation]:
    issues: list[Violation] = []
    path = document.path.as_posix()
    expectation = PAGE_EXPECTATIONS.get(document.path)

    if document.tags["h1"] != 1:
        issues.append(
            Violation(path, 0, f"expected exactly one h1, found {document.tags['h1']}")
        )
    elif not document.h1_text:
        issues.append(Violation(path, 0, "h1 must contain text"))
    if document.tags["main"] != 1:
        issues.append(
            Violation(
                path, 0, f"expected exactly one main, found {document.tags['main']}"
            )
        )
    required_landmarks = ["header", "footer"]
    if expectation:
        required_landmarks.append("nav")
    for landmark in required_landmarks:
        if document.tags[landmark] < 1:
            issues.append(Violation(path, 0, f"missing {landmark} landmark"))
    if not document.html_lang:
        issues.append(Violation(path, 0, "html requires a non-empty lang attribute"))
    elif expectation and document.html_lang.casefold() not in expectation.languages:
        allowed = ", ".join(expectation.languages)
        issues.append(Violation(path, 0, f"html lang must be one of: {allowed}"))
    return issues


def _validate_basic_metadata(document: HTMLDocument) -> list[Violation]:
    issues: list[Violation] = []
    path = document.path.as_posix()
    if document.charset.casefold().replace("_", "-") != "utf-8":
        issues.append(Violation(path, 0, "meta charset must be UTF-8"))
    if not document.title:
        issues.append(Violation(path, 0, "document requires a non-empty title"))
    viewport = _first_meta(document.meta_names, "viewport")
    if not viewport or "width=device-width" not in viewport[0].casefold():
        issues.append(
            Violation(path, 0, "viewport meta must include width=device-width")
        )
    if not document.stylesheet_targets:
        issues.append(Violation(path, 0, "page must load the local stylesheet"))
    if not document.icon_targets:
        issues.append(Violation(path, 0, "page must reference the local favicon"))
    return issues


def _validate_entry_metadata(
    document: HTMLDocument, expectation: PageExpectation
) -> list[Violation]:
    issues: list[Violation] = []
    path = document.path.as_posix()
    description = _first_meta(document.meta_names, "description")
    if not description or len(description[0].strip()) < 20:
        issues.append(
            Violation(path, 0, "meta description must contain at least 20 characters")
        )
    robots = _first_meta(document.meta_names, "robots")
    if robots and "noindex" in robots[0].casefold():
        issues.append(Violation(path, robots[1], "public entry page must be indexable"))
    for property_name in ("og:title", "og:description", "og:type", "og:url"):
        value = _first_meta(document.meta_properties, property_name)
        if not value or not value[0].strip():
            issues.append(
                Violation(path, 0, f"missing non-empty {property_name} metadata")
            )
    if len(document.canonical_links) != 1:
        issues.append(
            Violation(
                path,
                0,
                f"expected exactly one canonical link, found {len(document.canonical_links)}",
            )
        )
    elif document.canonical_links[0][0] != expectation.canonical_url:
        issues.append(
            Violation(
                path,
                document.canonical_links[0][1],
                f"canonical URL must be {expectation.canonical_url}",
            )
        )
    if not document.script_targets:
        issues.append(Violation(path, 0, "page must load the local site script"))
    return issues


def _validate_not_found_metadata(document: HTMLDocument) -> list[Violation]:
    issues: list[Violation] = []
    path = document.path.as_posix()
    robots = _first_meta(document.meta_names, "robots")
    if not robots or "noindex" not in robots[0].casefold():
        issues.append(Violation(path, 0, "404 page must declare noindex"))
    base_hrefs = [target for target, _ in document.base_targets]
    if base_hrefs != [SITE_BASE_PATH]:
        issues.append(
            Violation(path, 0, f"404 page base href must be {SITE_BASE_PATH}")
        )
    return issues


def _validate_document_metadata(document: HTMLDocument) -> list[Violation]:
    issues = _validate_basic_metadata(document)
    expectation = PAGE_EXPECTATIONS.get(document.path)
    if expectation:
        issues.extend(_validate_entry_metadata(document, expectation))
    elif document.path == PurePosixPath("404.html"):
        issues.extend(_validate_not_found_metadata(document))
    return issues


def _validate_document_content(document: HTMLDocument) -> list[Violation]:
    issues: list[Violation] = []
    path = document.path.as_posix()

    text = document.visible_text.casefold()
    if document.path in PAGE_EXPECTATIONS:
        for concept, alternatives in REQUIRED_CONCEPTS.items():
            if not any(
                all(token.casefold() in text for token in tokens)
                for tokens in alternatives
            ):
                issues.append(
                    Violation(path, 0, f"missing required content contract: {concept}")
                )
    for pattern in FORBIDDEN_CLAIMS:
        match = pattern.search(document.visible_text)
        if match and not _is_negated_claim(document.visible_text, match):
            issues.append(Violation(path, 0, f"forbidden claim: {match.group(0)!r}"))
    return issues


def _is_negated_claim(text: str, match: re.Match[str]) -> bool:
    """Permit a risky phrase only inside an explicit non-claim disclaimer."""

    context = text[max(0, match.start() - 180) : match.end() + 80].casefold()
    markers = (
        "cannot be claimed",
        "cannot claim",
        "does not claim",
        "does not guarantee",
        "not built in",
        "not supported",
        "不得宣稱",
        "不能宣稱",
        "不保證",
        "無法保證",
    )
    return any(marker in context for marker in markers)


def _validate_document(document: HTMLDocument) -> list[Violation]:
    return [
        *_validate_document_structure(document),
        *_validate_document_metadata(document),
        *_validate_document_content(document),
    ]


def _classify_url(url: str) -> str:
    stripped = url.strip()
    if not stripped:
        return "empty"
    parsed = urlsplit(stripped)
    scheme = parsed.scheme.casefold()
    classification = "local"
    if stripped.startswith("//") or scheme in {"http", "https"}:
        classification = "external"
    elif scheme in {"mailto", "tel"}:
        classification = "contact"
    elif scheme == "data":
        classification = "data"
    elif scheme:
        classification = "unsafe"
    elif parsed.path.startswith("/"):
        classification = "root-relative"
    return classification


def _resolve_local_reference(
    site_root: Path, reference: Reference
) -> tuple[Path | None, str, list[Violation]]:
    issues: list[Violation] = []
    parsed = urlsplit(reference.url)
    decoded_path = unquote(parsed.path)
    if "\\" in decoded_path:
        issues.append(
            Violation(
                reference.source.as_posix(),
                reference.line,
                "local URL must use forward slashes",
            )
        )
        return None, unquote(parsed.fragment), issues

    source_path = site_root / reference.source
    candidate = source_path if not decoded_path else source_path.parent / decoded_path
    resolved = candidate.resolve()
    site_resolved = site_root.resolve()
    try:
        resolved.relative_to(site_resolved)
    except ValueError:
        issues.append(
            Violation(
                reference.source.as_posix(),
                reference.line,
                "local URL escapes the website root",
            )
        )
        return None, unquote(parsed.fragment), issues

    if decoded_path.endswith("/") or resolved.is_dir():
        resolved /= "index.html"
    return resolved, unquote(parsed.fragment), issues


def _validate_nonlocal_reference(
    reference: Reference, classification: str
) -> list[Violation]:
    issues: list[Violation] = []
    if classification == "external":
        parsed = urlsplit(reference.url)
        if parsed.scheme.casefold() == "http":
            issues.append(
                Violation(
                    reference.source.as_posix(),
                    reference.line,
                    "external links must use HTTPS",
                )
            )
        if reference.is_resource:
            issues.append(
                Violation(
                    reference.source.as_posix(),
                    reference.line,
                    f"external resource is forbidden in {reference.kind}",
                )
            )
    elif classification == "data" and reference.is_resource:
        issues.append(
            Violation(
                reference.source.as_posix(),
                reference.line,
                f"embedded data resource is forbidden in {reference.kind}",
            )
        )
    return issues


def _validate_local_reference(
    site_root: Path,
    documents: dict[PurePosixPath, HTMLDocument],
    reference: Reference,
) -> list[Violation]:
    issues: list[Violation] = []
    resolved, fragment, resolution_issues = _resolve_local_reference(
        site_root, reference
    )
    issues.extend(resolution_issues)
    if resolved is None:
        return issues
    if not resolved.is_file():
        issues.append(
            Violation(
                reference.source.as_posix(),
                reference.line,
                f"local target does not exist: {reference.url!r}",
            )
        )
        return issues
    if not fragment or resolved.suffix.casefold() != ".html":
        return issues
    target_relative = PurePosixPath(
        resolved.relative_to(site_root.resolve()).as_posix()
    )
    target_document = documents.get(target_relative)
    if target_document is None:
        issues.append(
            Violation(
                reference.source.as_posix(),
                reference.line,
                f"cannot inspect fragment target: {reference.url!r}",
            )
        )
    elif fragment not in target_document.ids:
        issues.append(
            Violation(
                reference.source.as_posix(),
                reference.line,
                f"fragment #{fragment} does not exist in {target_relative.as_posix()}",
            )
        )
    return issues


def _validate_reference(
    site_root: Path,
    documents: dict[PurePosixPath, HTMLDocument],
    reference: Reference,
) -> list[Violation]:
    simple_failures = {
        "empty": f"empty {reference.kind} URL",
        "unsafe": f"unsafe URL scheme in {reference.kind}",
        "root-relative": (
            f"{reference.kind} must be relative for project Pages, not root-relative"
        ),
    }
    classification = _classify_url(reference.url)
    if classification in simple_failures:
        return [
            Violation(
                reference.source.as_posix(),
                reference.line,
                simple_failures[classification],
            )
        ]
    if classification != "local":
        return _validate_nonlocal_reference(reference, classification)
    return _validate_local_reference(site_root, documents, reference)


def _validate_references(
    site_root: Path,
    documents: dict[PurePosixPath, HTMLDocument],
    references: list[Reference],
) -> list[Violation]:
    issues: list[Violation] = []
    for reference in references:
        issues.extend(_validate_reference(site_root, documents, reference))
    return issues


def _css_references(relative: PurePosixPath, text: str) -> list[Reference]:
    references: list[Reference] = []
    for pattern, kind in (
        (CSS_URL_PATTERN, "css url()"),
        (CSS_IMPORT_PATTERN, "css @import"),
    ):
        for match in pattern.finditer(text):
            url = match.group(2).strip()
            line = text.count("\n", 0, match.start()) + 1
            if url:
                references.append(Reference(relative, line, kind, url, True))
    return references


def _validate_text_assets(
    site_root: Path, files: list[PurePosixPath]
) -> tuple[list[Reference], list[Violation]]:
    references: list[Reference] = []
    issues: list[Violation] = []
    for relative in files:
        if relative.suffix.casefold() not in {".css", ".js", ".html"}:
            continue
        text, read_issues = _read_text(site_root / relative, relative)
        issues.extend(read_issues)
        if read_issues:
            continue
        for pattern in ANALYTICS_PATTERNS:
            match = pattern.search(text)
            if match:
                line = text.count("\n", 0, match.start()) + 1
                issues.append(
                    Violation(
                        relative.as_posix(),
                        line,
                        f"analytics code is forbidden: {match.group(0)!r}",
                    )
                )
        if relative.suffix.casefold() == ".css":
            references.extend(_css_references(relative, text))
        if relative.suffix.casefold() == ".js":
            for marker in ("fetch(", "xmlhttprequest", "sendbeacon(", "websocket("):
                index = text.casefold().find(marker)
                if index >= 0:
                    line = text.count("\n", 0, index) + 1
                    issues.append(
                        Violation(
                            relative.as_posix(),
                            line,
                            f"network-capable JavaScript is forbidden: {marker}",
                        )
                    )
    return references, issues


def _validate_robots(site_root: Path) -> list[Violation]:
    relative = PurePosixPath("robots.txt")
    text, issues = _read_text(site_root / relative, relative)
    if issues:
        return issues
    normalized_lines = {
        line.strip().casefold()
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    if "user-agent: *" not in normalized_lines:
        issues.append(
            Violation(relative.as_posix(), 0, "robots.txt must declare User-agent: *")
        )
    if "disallow: /" in normalized_lines:
        issues.append(
            Violation(
                relative.as_posix(), 0, "robots.txt must not disallow the entire site"
            )
        )
    expected_sitemap = f"sitemap: {SITE_BASE_URL}sitemap.xml".casefold()
    if expected_sitemap not in normalized_lines:
        issues.append(
            Violation(
                relative.as_posix(), 0, f"robots.txt must declare {expected_sitemap}"
            )
        )
    return issues


def _validate_sitemap(site_root: Path) -> list[Violation]:
    relative = PurePosixPath("sitemap.xml")
    text, issues = _read_text(site_root / relative, relative)
    if issues:
        return issues
    if len(text.encode("utf-8")) > 65_536:
        return [Violation(relative.as_posix(), 0, "sitemap exceeds 64 KiB")]
    folded = text.casefold()
    if "<!doctype" in folded or "<!entity" in folded:
        return [
            Violation(
                relative.as_posix(),
                0,
                "sitemap must not contain DTD or entity declarations",
            )
        ]
    try:
        # Input is repo-local, size-bounded above, and declarations are rejected.
        root = ET.fromstring(text)  # nosec B314
    except ET.ParseError as error:
        return [Violation(relative.as_posix(), 0, f"cannot parse sitemap XML: {error}")]

    locations = [
        (element.text or "").strip()
        for element in root.iter()
        if element.tag.rsplit("}", maxsplit=1)[-1] == "loc"
    ]
    expected = {SITE_BASE_URL, f"{SITE_BASE_URL}en/"}
    missing = sorted(expected - set(locations))
    if missing:
        issues.append(
            Violation(
                relative.as_posix(), 0, f"sitemap is missing URLs: {', '.join(missing)}"
            )
        )
    if len(locations) != len(set(locations)):
        issues.append(
            Violation(relative.as_posix(), 0, "sitemap contains duplicate URLs")
        )
    for location in locations:
        if not location.startswith(SITE_BASE_URL):
            issues.append(
                Violation(
                    relative.as_posix(),
                    0,
                    f"sitemap URL is outside the canonical site: {location!r}",
                )
            )
    return issues


def check_website(site_root: str | Path = Path("website")) -> list[Violation]:
    """Return all conformance violations for a static website directory."""

    root = Path(site_root)
    if not root.is_dir():
        return [Violation(root.as_posix(), 0, "website directory does not exist")]

    files, issues = _scan_tree(root)
    issues.extend(_validate_artifacts(root, files))
    documents, parse_issues = _parse_html_documents(root, files)
    issues.extend(parse_issues)
    for document in documents.values():
        issues.extend(_validate_document(document))

    css_references, text_issues = _validate_text_assets(root, files)
    issues.extend(text_issues)
    html_references = [
        reference
        for document in documents.values()
        for reference in document.references
    ]
    issues.extend(
        _validate_references(root, documents, [*html_references, *css_references])
    )

    if (root / "robots.txt").is_file():
        issues.extend(_validate_robots(root))
    if (root / "sitemap.xml").is_file():
        issues.extend(_validate_sitemap(root))
    return sorted(set(issues))


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point used by local checks and the Pages workflow."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "site_root",
        nargs="?",
        default="website",
        help="static website directory (default: website)",
    )
    arguments = parser.parse_args(argv)
    issues = check_website(arguments.site_root)
    if issues:
        print(
            f"Website conformance failed with {len(issues)} violation(s):",
            file=sys.stderr,
        )
        for issue in issues:
            print(f"- {issue}", file=sys.stderr)
        return 1
    print(f"Website conformance passed: {arguments.site_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
