"""
Provenance Verifier Domain Service.

Provides deterministic source-span matching for clinical evidence
against raw data files in the workspace or data directory.
"""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar
from urllib.parse import unquote, urlsplit


@dataclass(frozen=True, slots=True)
class ProvenanceMatch:
    """Result of deterministic provenance verification."""

    is_verified: bool
    match_type: str
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

    _SUPPORTED_TEXT_SUFFIXES: ClassVar[frozenset[str]] = frozenset(
        {
            ".csv",
            ".hl7",
            ".json",
            ".log",
            ".md",
            ".msg",
            ".tsv",
            ".txt",
            ".xml",
            ".yaml",
            ".yml",
        }
    )
    _BLOCKED_PATH_PARTS: ClassVar[frozenset[str]] = frozenset(
        {".git", ".venv", "__pycache__", "secrets"}
    )
    _BLOCKED_FILENAMES: ClassVar[frozenset[str]] = frozenset(
        {".env", ".env.local", ".env.production"}
    )
    _MAX_SOURCE_BYTES = 20 * 1024 * 1024

    def __init__(self, search_roots: list[Path] | None = None) -> None:
        roots = search_roots or self._default_search_roots()
        self.search_roots = list(
            dict.fromkeys(root.expanduser().resolve() for root in roots)
        )

    @staticmethod
    def _default_search_roots() -> list[Path]:
        configured_roots = os.environ.get("ROOTCAUSE_SOURCE_ROOTS")
        if configured_roots:
            return list(
                dict.fromkeys(
                    Path(item).expanduser().resolve()
                    for item in configured_roots.split(os.pathsep)
                    if item.strip()
                )
            )

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

        # 1. Direct absolute or relative path, constrained to an approved root.
        direct = candidate.expanduser().resolve()
        if direct.is_file() and self._is_allowed_source(direct):
            return direct

        # 2. Check each search root
        for root in self.search_roots:
            p = (root / clean_doc_id).resolve()
            if p.is_file() and self._is_allowed_source(p):
                return p

        # 3. If filename only, search recursively under search roots
        filename = candidate.name
        if filename:
            matches: list[Path] = []
            for root in self.search_roots:
                if not root.exists():
                    continue
                for match in root.rglob(filename):
                    resolved = match.resolve()
                    if resolved.is_file() and self._is_allowed_source(resolved):
                        matches.append(resolved)
            unique_matches = list(dict.fromkeys(matches))
            if len(unique_matches) == 1:
                return unique_matches[0]

        return None

    def resolve_source_uri(self, source_uri: str) -> Path | ProvenanceMatch:
        """Resolve an exact local path or file URI under an approved source root.

        Manifest URIs are authoritative locations, so unlike legacy document
        references this method never searches recursively by basename.
        """
        candidate_or_failure = self._parse_local_source_uri(source_uri)
        if isinstance(candidate_or_failure, ProvenanceMatch):
            return candidate_or_failure
        candidate = candidate_or_failure
        candidates = (
            [candidate.resolve()]
            if candidate.is_absolute()
            else [(root / candidate).resolve() for root in self.search_roots]
        )
        found_disallowed = False
        for resolved in dict.fromkeys(candidates):
            if not resolved.is_file():
                continue
            if self._is_allowed_source(resolved):
                return resolved
            found_disallowed = True

        if found_disallowed:
            return ProvenanceMatch(
                is_verified=False,
                match_type="SOURCE_PATH_NOT_ALLOWED",
                diagnostics=(
                    "Manifest source_uri resolves outside ROOTCAUSE_SOURCE_ROOTS "
                    "or to a blocked source path."
                ),
            )
        return ProvenanceMatch(
            is_verified=False,
            match_type="FILE_NOT_FOUND",
            diagnostics="Manifest source_uri could not be located on disk.",
        )

    @staticmethod
    def _parse_local_source_uri(source_uri: str) -> Path | ProvenanceMatch:
        """Parse a local manifest reference without touching the filesystem."""
        raw_uri = source_uri.strip()
        if not raw_uri:
            return ProvenanceMatch(
                is_verified=False,
                match_type="SOURCE_URI_MISSING",
                diagnostics="Manifest source_uri is empty.",
            )

        parsed = urlsplit(raw_uri)
        scheme = parsed.scheme.casefold()
        if scheme not in {"", "file"}:
            return ProvenanceMatch(
                is_verified=False,
                match_type="UNSUPPORTED_SOURCE_URI_SCHEME",
                diagnostics=(
                    f"Manifest source_uri scheme '{parsed.scheme}' is not eligible "
                    "for local physical verification."
                ),
            )
        if scheme == "file" and parsed.netloc.casefold() not in {"", "localhost"}:
            return ProvenanceMatch(
                is_verified=False,
                match_type="NON_LOCAL_FILE_URI",
                diagnostics="Only local file URIs may be physically verified.",
            )
        if parsed.query or parsed.fragment:
            return ProvenanceMatch(
                is_verified=False,
                match_type="INVALID_SOURCE_URI",
                diagnostics="Manifest source_uri must not include a query or fragment.",
            )

        path_text = unquote(parsed.path) if scheme == "file" else raw_uri
        return Path(path_text).expanduser()

    def _is_allowed_source(self, path: Path) -> bool:
        if path.name.casefold() in self._BLOCKED_FILENAMES:
            return False
        if any(part.casefold() in self._BLOCKED_PATH_PARTS for part in path.parts):
            return False
        return any(
            path == root or path.is_relative_to(root) for root in self.search_roots
        )

    def verify_provenance(
        self,
        document_id: str | None,
        raw_snippet: str | None = None,
        location: str | None = None,
        content: str | None = None,
        expected_source_sha256: str | None = None,
    ) -> ProvenanceMatch:
        """
        Deterministically verify that evidence matches a physical raw document.

        Args:
            document_id: Document file name or path
            raw_snippet: Exact verbatim quote from the file
            location: Human-readable location (e.g., "Line 14", "Section: Labs")
            content: Fallback content if raw_snippet not provided
            expected_source_sha256: Optional whole-file digest pinned by a manifest
        """
        if not document_id:
            return ProvenanceMatch(
                is_verified=False,
                match_type="NO_DOCUMENT_SPECIFIED",
                diagnostics="No source document ID was specified.",
            )

        source = self._resolve_readable_source(
            document_id,
            expected_source_sha256=expected_source_sha256,
        )
        if isinstance(source, ProvenanceMatch):
            return source
        resolved_path, file_text = source

        snippet_to_match = raw_snippet or (
            content if content and len(content) < 300 else None
        )
        if snippet_to_match:
            return self._verify_snippet(resolved_path, file_text, snippet_to_match)

        return self._inspect_location_or_file(resolved_path, file_text, location)

    def _resolve_readable_source(
        self,
        document_id: str,
        *,
        expected_source_sha256: str | None = None,
    ) -> tuple[Path, str] | ProvenanceMatch:
        """Resolve and safely load one supported, bounded plain-text source."""
        resolved_path = self.resolve_file(document_id)
        if resolved_path is None:
            return ProvenanceMatch(
                is_verified=False,
                match_type="FILE_NOT_FOUND",
                diagnostics=f"Source document '{document_id}' could not be located on disk.",
            )
        if resolved_path.suffix.casefold() not in self._SUPPORTED_TEXT_SUFFIXES:
            return ProvenanceMatch(
                is_verified=False,
                match_type="UNSUPPORTED_FILE_TYPE",
                file_path=str(resolved_path),
                diagnostics=(
                    f"Source document '{resolved_path.name}' is not a supported plain-text record. "
                    "Use the host agent or Asset-Aware MCP to extract a citation-ready text span first."
                ),
            )
        source_bytes = self._read_source_bytes(resolved_path)
        if isinstance(source_bytes, ProvenanceMatch):
            return source_bytes
        hash_failure = self._check_expected_source_hash(
            resolved_path,
            expected_source_sha256,
            source_bytes,
        )
        if hash_failure is not None:
            return hash_failure
        file_text = self._decode_file_text(source_bytes)
        if file_text is None:
            return ProvenanceMatch(
                is_verified=False,
                match_type="FILE_UNREADABLE",
                file_path=str(resolved_path),
                diagnostics=f"Could not read source document at {resolved_path}.",
            )
        return resolved_path, file_text

    @staticmethod
    def _check_expected_source_hash(
        path: Path,
        expected_source_sha256: str | None,
        source_bytes: bytes,
    ) -> ProvenanceMatch | None:
        """Fail closed when physical bytes drift from a manifest digest."""
        if expected_source_sha256 is None:
            return None
        expected_digest = expected_source_sha256.casefold().removeprefix("sha256:")
        if re.fullmatch(r"[a-f0-9]{64}", expected_digest) is None:
            return ProvenanceMatch(
                is_verified=False,
                match_type="INVALID_EXPECTED_SOURCE_HASH",
                file_path=str(path),
                diagnostics="Expected whole-file SHA-256 digest is invalid.",
            )
        actual_digest = hashlib.sha256(source_bytes).hexdigest()
        if actual_digest != expected_digest:
            return ProvenanceMatch(
                is_verified=False,
                match_type="SOURCE_HASH_MISMATCH",
                file_path=str(path),
                diagnostics=(
                    "Physical source bytes do not match the whole-file SHA-256 "
                    "pinned in the session manifest."
                ),
            )
        return None

    def _read_source_bytes(self, path: Path) -> bytes | ProvenanceMatch:
        """Read a bounded byte snapshot used for both hashing and text matching."""
        try:
            with path.open("rb") as source:
                content = source.read(self._MAX_SOURCE_BYTES + 1)
        except OSError:
            return ProvenanceMatch(
                is_verified=False,
                match_type="FILE_UNREADABLE",
                file_path=str(path),
                diagnostics=f"Could not read source document at {path}.",
            )
        if len(content) > self._MAX_SOURCE_BYTES:
            return ProvenanceMatch(
                is_verified=False,
                match_type="FILE_TOO_LARGE",
                file_path=str(path),
                diagnostics=(
                    f"Source document exceeds the {self._MAX_SOURCE_BYTES}-byte "
                    "verification limit."
                ),
            )
        return content

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
    def _inspect_location_or_file(
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
                        is_verified=False,
                        match_type="LOCATION_EXISTS_UNVERIFIED",
                        file_path=str(path),
                        line_numbers=(line_num,),
                        snippet_hash=f"sha256:{digest}",
                        matched_text=line_content,
                        diagnostics=(
                            f"Line {line_num} exists in {path.name}, but no finding text "
                            "was supplied for content verification."
                        ),
                    )

        file_hash = hashlib.sha256(file_text.encode("utf-8")).hexdigest()
        return ProvenanceMatch(
            is_verified=False,
            match_type="FILE_EXISTS_UNVERIFIED",
            file_path=str(path),
            snippet_hash=f"sha256:{file_hash}",
            diagnostics=(
                f"Document '{path.name}' exists, but file existence does not verify "
                "the clinical finding. Supply an exact raw_snippet."
            ),
        )

    @staticmethod
    def _decode_file_text(content: bytes) -> str | None:
        encodings = ("utf-8", "utf-8-sig", "cp950", "latin-1")
        for enc in encodings:
            try:
                return content.decode(enc)
            except UnicodeDecodeError:
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
            # Verification requires the complete normalized finding to occur in
            # the source line.  The reverse containment check allowed a tiny
            # source line (for example "BP") to verify a much longer invented
            # snippet that merely contained those characters.
            if norm_line and norm_snippet in norm_line:
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
