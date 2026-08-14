"""
Provenance Verifier Domain Service.

Provides deterministic, zero-hallucination verification of clinical evidence
against raw data files in the workspace or data directory.
"""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class ProvenanceMatch:
    """Result of deterministic provenance verification."""

    is_verified: bool
    match_type: str  # EXACT_SNIPPET_MATCH, NORMALIZED_SNIPPET_MATCH, LOCATION_MATCH, FILE_EXISTS, FILE_NOT_FOUND, SNIPPET_NOT_FOUND
    file_path: str | None = None
    line_numbers: tuple[int, ...] = ()
    snippet_hash: str | None = None
    matched_text: str | None = None
    diagnostics: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return {
            "is_verified": self.is_verified,
            "match_type": self.match_type,
            "file_path": self.file_path,
            "line_numbers": list(self.line_numbers),
            "snippet_hash": self.snippet_hash,
            "matched_text": self.matched_text,
            "diagnostics": self.diagnostics,
        }


class ProvenanceVerifier:
    """
    Deterministic Provenance Verifier.

    Verifies evidence by anchoring it to raw physical files (TXT, CSV, HL7, XML, Markdown)
    without relying on LLM interpretations.
    """

    def __init__(self, search_roots: list[Path] | None = None) -> None:
        self.search_roots = search_roots or self._default_search_roots()

    @staticmethod
    def _default_search_roots() -> list[Path]:
        roots = [Path.cwd()]
        data_dir = os.environ.get("ROOTCAUSE_DATA_DIR")
        if data_dir:
            roots.append(Path(data_dir).resolve())
        examples_dir = Path.cwd() / "examples"
        if examples_dir.exists():
            roots.append(examples_dir.resolve())
        return list(dict.fromkeys(roots))

    def resolve_file(self, document_id: str) -> Path | None:
        """
        Find the actual file on disk matching document_id.

        Supports:
        - Absolute paths
        - Paths relative to current directory
        - Search within search_roots
        - Filename-only recursive matching within examples/ or data/
        """
        if not document_id or not document_id.strip():
            return None

        clean_doc_id = document_id.strip().replace("\\", "/")
        candidate = Path(clean_doc_id)

        # 1. Direct absolute or relative path
        if candidate.is_file():
            return candidate.resolve()

        # 2. Check each search root
        for root in self.search_roots:
            p = (root / clean_doc_id).resolve()
            if p.is_file():
                return p

        # 3. If filename only, search recursively under search roots
        filename = candidate.name
        if filename:
            for root in self.search_roots:
                if not root.exists():
                    continue
                for match in root.rglob(filename):
                    if match.is_file():
                        return match.resolve()

        return None

    def verify_provenance(
        self,
        document_id: str | None,
        raw_snippet: str | None = None,
        location: str | None = None,
        content: str | None = None,
    ) -> ProvenanceMatch:
        """
        Deterministically verify that evidence matches a physical raw document.

        Args:
            document_id: Document file name or path
            raw_snippet: Exact verbatim quote from the file
            location: Human-readable location (e.g., "Line 14", "Section: Labs")
            content: Fallback content if raw_snippet not provided
        """
        if not document_id:
            return ProvenanceMatch(
                is_verified=False,
                match_type="NO_DOCUMENT_SPECIFIED",
                diagnostics="No source document ID was specified.",
            )

        resolved_path = self.resolve_file(document_id)
        if resolved_path is None:
            return ProvenanceMatch(
                is_verified=False,
                match_type="FILE_NOT_FOUND",
                diagnostics=f"Source document '{document_id}' could not be located on disk.",
            )

        file_text = self._read_file_text(resolved_path)
        if file_text is None:
            return ProvenanceMatch(
                is_verified=False,
                match_type="FILE_UNREADABLE",
                file_path=str(resolved_path),
                diagnostics=f"Could not read source document at {resolved_path}.",
            )

        snippet_to_match = raw_snippet or (
            content if content and len(content) < 300 else None
        )
        if snippet_to_match:
            return self._verify_snippet(resolved_path, file_text, snippet_to_match)

        return self._verify_location_or_file(resolved_path, file_text, location)

    def _verify_snippet(
        self,
        path: Path,
        file_text: str,
        snippet: str,
    ) -> ProvenanceMatch:
        # 1. Exact substring match
        match = self._match_snippet_in_text(file_text, snippet)
        if match is not None:
            line_numbers, matched_text = match
            digest = hashlib.sha256(matched_text.encode("utf-8")).hexdigest()
            return ProvenanceMatch(
                is_verified=True,
                match_type="EXACT_SNIPPET_MATCH",
                file_path=str(path),
                line_numbers=tuple(line_numbers),
                snippet_hash=f"sha256:{digest}",
                matched_text=matched_text,
                diagnostics=(
                    f"Verbatim quote verified at line(s) {line_numbers} in {path.name}"
                ),
            )

        # 2. Normalized whitespace match
        norm_match = self._match_normalized_snippet(file_text, snippet)
        if norm_match is not None:
            line_numbers, matched_text = norm_match
            digest = hashlib.sha256(matched_text.encode("utf-8")).hexdigest()
            return ProvenanceMatch(
                is_verified=True,
                match_type="NORMALIZED_SNIPPET_MATCH",
                file_path=str(path),
                line_numbers=tuple(line_numbers),
                snippet_hash=f"sha256:{digest}",
                matched_text=matched_text,
                diagnostics=(
                    f"Normalized quote verified at line(s) {line_numbers} in {path.name}"
                ),
            )

        return ProvenanceMatch(
            is_verified=False,
            match_type="SNIPPET_NOT_FOUND",
            file_path=str(path),
            diagnostics=f"Snippet not found in document '{path.name}'.",
        )

    @staticmethod
    def _verify_location_or_file(
        path: Path,
        file_text: str,
        location: str | None,
    ) -> ProvenanceMatch:
        if location:
            line_match = re.search(r"(?:line|row)\s*(\d+)", location, re.IGNORECASE)
            if line_match:
                line_num = int(line_match.group(1))
                file_lines = file_text.splitlines()
                if 1 <= line_num <= len(file_lines):
                    line_content = file_lines[line_num - 1].strip()
                    digest = hashlib.sha256(line_content.encode("utf-8")).hexdigest()
                    return ProvenanceMatch(
                        is_verified=True,
                        match_type="LOCATION_MATCH",
                        file_path=str(path),
                        line_numbers=(line_num,),
                        snippet_hash=f"sha256:{digest}",
                        matched_text=line_content,
                        diagnostics=f"Location verified at line {line_num} in {path.name}",
                    )

        file_hash = hashlib.sha256(file_text.encode("utf-8")).hexdigest()
        return ProvenanceMatch(
            is_verified=True,
            match_type="FILE_EXISTS",
            file_path=str(path),
            snippet_hash=f"sha256:{file_hash[:16]}",
            diagnostics=f"Document '{path.name}' verified on disk",
        )

    @staticmethod
    def _read_file_text(path: Path) -> str | None:
        encodings = ("utf-8", "utf-8-sig", "cp950", "latin-1")
        for enc in encodings:
            try:
                return path.read_text(encoding=enc)
            except (UnicodeDecodeError, OSError):
                continue
        return None

    @staticmethod
    def _match_snippet_in_text(
        file_text: str, snippet: str
    ) -> tuple[list[int], str] | None:
        clean_snippet = snippet.strip()
        if not clean_snippet:
            return None

        # Check exact presence
        idx = file_text.find(clean_snippet)
        if idx == -1:
            return None

        # Calculate line number
        start_line = file_text[:idx].count("\n") + 1
        lines_spanned = clean_snippet.count("\n") + 1
        line_numbers = list(range(start_line, start_line + lines_spanned))
        return line_numbers, clean_snippet

    @staticmethod
    def _match_normalized_snippet(
        file_text: str, snippet: str
    ) -> tuple[list[int], str] | None:
        norm_snippet = " ".join(snippet.split()).casefold()
        if not norm_snippet:
            return None

        file_lines = file_text.splitlines()
        for idx, line in enumerate(file_lines, 1):
            norm_line = " ".join(line.split()).casefold()
            if norm_snippet in norm_line or norm_line in norm_snippet:
                return [idx], line.strip()

        # Multi-line sliding window
        for window_size in range(2, 6):
            for i in range(len(file_lines) - window_size + 1):
                chunk = " ".join(
                    " ".join(file_lines[i : i + window_size]).split()
                ).casefold()
                if norm_snippet in chunk:
                    return list(range(i + 1, i + window_size + 1)), " ".join(
                        file_lines[i : i + window_size]
                    ).strip()

        return None
