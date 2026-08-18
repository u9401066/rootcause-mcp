#!/usr/bin/env python3
"""Blinded, fail-closed Agent-in-loop evaluation runner for RootCause MCP.

The adapter subprocess receives only one neutral case bundle and the public output
schema. Gold rubrics are loaded by the grader only after the subprocess exits.
Fixture mode verifies runner mechanics and always reports ENGINEERING_DRY_RUN; it
must never be interpreted as an Agent or clinical-validation result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess  # nosec B404
import sys
import tempfile
import time
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator, FormatChecker

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MATRIX = REPO_ROOT / "evals" / "adapter_matrix.example.json"
OUTPUT_SCHEMA = REPO_ROOT / "evals" / "schemas" / "agent_output.schema.json"
CASE_IDS = tuple(f"CASE-{index:03d}" for index in range(1, 7))

RUNNER_READY = "RUNNER_READY"
RUNNER_SCAFFOLD = "RUNNER_SCAFFOLD"
ENGINEERING_DRY_RUN = "ENGINEERING_DRY_RUN"
AGENT_EVAL_NOT_ESTABLISHED = "AGENT_EVAL_NOT_ESTABLISHED"
# Evaluation result label, not an authentication secret.
AGENT_EVAL_PASS = "AGENT_EVAL_PASS"  # nosec B105
AGENT_EVAL_FAIL = "AGENT_EVAL_FAIL"

GENERIC_CAUSAL_OVERCLAIMS = (
    "proven root cause",
    "causation verified",
    "definitively caused",
    "proved causation",
    "已證實為根因",
    "因果關係已驗證",
    "確定導致",
)

PHI_PATTERNS = (
    re.compile(r"\bmrn\s*[:#]?\s*[a-z0-9-]+", re.IGNORECASE),
    re.compile(r"\bdate of birth\b|\bdob\s*:", re.IGNORECASE),
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    re.compile(
        r"\b(?:phone|telephone|tel|mobile|contact)\s*[:#]?\s*\+?\d[\d .()-]{8,}\d\b",
        re.IGNORECASE,
    ),
)

RFC3339_TIMESTAMP = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)
FORMAT_CHECKER = FormatChecker()


@FORMAT_CHECKER.checks("date-time")  # type: ignore[untyped-decorator]
def _is_rfc3339_timestamp(value: object) -> bool:
    if not isinstance(value, str):
        return True
    if RFC3339_TIMESTAMP.fullmatch(value) is None:
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


class EvalError(RuntimeError):
    """Raised when an evaluation invariant fails closed."""


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvalError(f"Unable to read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise EvalError(f"Expected a JSON object in {path}")
    return value


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tree_digest(root: Path) -> str:
    if not root.is_dir():
        raise EvalError(f"Missing directory: {root}")
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise EvalError(
                f"Symbolic links are forbidden in evaluation inputs: {path}"
            )
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(bytes.fromhex(_sha256_file(path)))
    return digest.hexdigest()


def _private_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=False)
    path.chmod(0o700)


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(4)}.tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.chmod(0o600)
    temporary.replace(path)


def _write_json(path: Path, value: Any) -> None:
    _atomic_write_text(path, json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def _resolve_repo_file(raw_path: str) -> Path:
    candidate = (REPO_ROOT / raw_path).resolve()
    try:
        candidate.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise EvalError(f"Evaluation path escapes repository: {raw_path}") from exc
    if not candidate.is_file():
        raise EvalError(f"Missing evaluation file: {candidate}")
    return candidate


def _schema_errors(value: Any, schema_path: Path) -> list[str]:
    schema = _read_json(schema_path)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FORMAT_CHECKER)
    errors = sorted(validator.iter_errors(value), key=lambda item: list(item.path))
    rendered = []
    for error in errors:
        location = ".".join(str(part) for part in error.absolute_path) or "$"
        rendered.append(f"{location}: {error.message}")
    return rendered


def _require_schema(value: Any, schema_path: Path, label: str) -> None:
    errors = _schema_errors(value, schema_path)
    if errors:
        raise EvalError(f"{label} schema validation failed: {'; '.join(errors)}")


def load_matrix(path: Path) -> dict[str, Any]:  # noqa: PLR0912
    matrix = _read_json(path)
    if matrix.get("schema_version") != "rootcause-agent-eval-matrix/1":
        raise EvalError("Unsupported adapter matrix schema_version")
    cases = matrix.get("cases")
    if not isinstance(cases, list) or tuple(cases) != CASE_IDS:
        raise EvalError("Formal matrix must contain the six neutral cases in order")
    repeats = matrix.get("repeats")
    if not isinstance(repeats, int) or repeats < 2:
        raise EvalError("Formal matrix requires at least two repeats")
    adapters = matrix.get("adapters")
    if not isinstance(adapters, list) or len(adapters) < 3:
        raise EvalError("Formal matrix requires at least three runtime adapters")
    adapter_ids: list[str] = []
    for adapter in adapters:
        if not isinstance(adapter, dict):
            raise EvalError("Every adapter must be an object")
        adapter_id = adapter.get("adapter_id")
        command = adapter.get("command")
        if not isinstance(adapter_id, str) or not adapter_id:
            raise EvalError("Every adapter requires a non-empty adapter_id")
        if (
            not isinstance(command, list)
            or not command
            or not all(isinstance(item, str) and item for item in command)
        ):
            raise EvalError(f"Adapter {adapter_id} requires a non-empty command list")
        if adapter.get("prompt_transport") not in {"stdin", "argument"}:
            raise EvalError(f"Adapter {adapter_id} has invalid prompt_transport")
        if adapter.get("candidate_transport") not in {"file", "stdout"}:
            raise EvalError(f"Adapter {adapter_id} has invalid candidate_transport")
        if adapter.get("trace_transport") not in {
            "stdout_jsonl",
            "file_jsonl",
            "unverified",
        }:
            raise EvalError(f"Adapter {adapter_id} has invalid trace_transport")
        if adapter.get("filesystem_isolation_status") not in {
            "ENFORCED",
            "UNVERIFIED",
        }:
            raise EvalError(
                f"Adapter {adapter_id} has invalid filesystem isolation status"
            )
        wiring = adapter.get("mcp_wiring")
        if not isinstance(wiring, dict):
            raise EvalError(f"Adapter {adapter_id} requires mcp_wiring")
        aliases = wiring.get("server_aliases")
        groups = wiring.get("required_tool_groups")
        if not isinstance(aliases, list) or not aliases:
            raise EvalError(f"Adapter {adapter_id} requires MCP server aliases")
        if not isinstance(groups, list) or not groups:
            raise EvalError(f"Adapter {adapter_id} requires MCP tool groups")
        for path_field, hash_field in (
            ("harness_source", "harness_sha256"),
            ("handoff_source", "handoff_sha256"),
        ):
            source = wiring.get(path_field)
            expected_hash = wiring.get(hash_field)
            if not isinstance(source, str) or not isinstance(expected_hash, str):
                raise EvalError(f"Adapter {adapter_id} has incomplete harness identity")
            if _sha256_file(_resolve_repo_file(source)) != expected_hash:
                raise EvalError(f"Adapter {adapter_id} {path_field} hash drift")
        adapter_ids.append(adapter_id)
    if len(adapter_ids) != len(set(adapter_ids)):
        raise EvalError("adapter_id values must be unique")
    return matrix


def _validate_gold_shape(
    gold: dict[str, Any],
    expected_case_id: str,
    *,
    required_status: str | None = None,
) -> None:
    _require_schema(
        gold,
        REPO_ROOT / "evals" / "schemas" / "gold_rubric.schema.json",
        f"Gold rubric {expected_case_id}",
    )
    if gold.get("schema_version") != "rootcause-agent-eval-gold/1":
        raise EvalError(f"Unsupported gold schema for {expected_case_id}")
    if gold.get("case_id") != expected_case_id:
        raise EvalError(f"Gold case_id mismatch for {expected_case_id}")
    if required_status is not None and gold.get("rubric_status") != required_status:
        raise EvalError(
            f"Gold {expected_case_id} must have rubric_status={required_status}"
        )
    required_arrays = (
        "acceptable_ddx",
        "must_not_miss",
        "critical_evidence",
        "allowed_rca",
        "forbidden_claims",
        "input_forbidden_terms",
    )
    for field in required_arrays:
        value = gold.get(field)
        if not isinstance(value, list) or not value:
            raise EvalError(f"Gold {expected_case_id} requires non-empty {field}")
    if len(gold["acceptable_ddx"]) < 3:
        raise EvalError(f"Gold {expected_case_id} needs at least three acceptable DDx")
    if not any(item.get("required_top3") is True for item in gold["acceptable_ddx"]):
        raise EvalError(f"Gold {expected_case_id} needs a required_top3 diagnosis")


def _term_present(text: str, term: str) -> bool:
    escaped = re.escape(term.strip())
    return re.search(rf"(?<!\w){escaped}(?!\w)", text, re.IGNORECASE) is not None


def _load_case_inputs(  # noqa: PLR0912
    corpus_file: Path, case_id: str
) -> tuple[Path, dict[str, Any], dict[str, Any], dict[str, str]]:
    corpus = _read_json(corpus_file)
    if corpus.get("schema_version") != "rootcause-agent-eval-corpus/1":
        raise EvalError("Unsupported corpus schema_version")
    entries = corpus.get("cases")
    if not isinstance(entries, list):
        raise EvalError("Corpus cases must be an array")
    matching = [item for item in entries if item.get("case_id") == case_id]
    if len(matching) != 1:
        raise EvalError(f"Corpus must contain exactly one entry for {case_id}")
    relative = matching[0].get("input_directory")
    if not isinstance(relative, str):
        raise EvalError(f"Corpus entry {case_id} has no input_directory")
    case_directory = (corpus_file.parent / relative).resolve()
    try:
        case_directory.relative_to(corpus_file.parent.resolve())
    except ValueError as exc:
        raise EvalError(f"Case directory escapes corpus: {case_id}") from exc
    case = _read_json(case_directory / "case.json")
    manifest = _read_json(case_directory / "manifest.json")
    if case.get("case_id") != case_id:
        raise EvalError(f"Input case_id mismatch for {case_id}")
    if manifest.get("schema_version") != "1.0":
        raise EvalError(f"Manifest schema mismatch for {case_id}")
    documents = manifest.get("documents")
    if not isinstance(documents, list) or len(documents) < 2:
        raise EvalError(f"Manifest {case_id} must register multiple documents")
    source_text: dict[str, str] = {}
    seen: set[str] = set()
    for document in documents:
        if not isinstance(document, dict):
            raise EvalError(f"Malformed source entry for {case_id}")
        document_id = document.get("document_id")
        source_uri = document.get("source_uri")
        expected_hash = document.get("sha256")
        if not isinstance(document_id, str) or document_id in seen:
            raise EvalError(f"Duplicate or invalid document_id for {case_id}")
        if not isinstance(source_uri, str) or not isinstance(expected_hash, str):
            raise EvalError(f"Incomplete source identity for {case_id}/{document_id}")
        source_path = (case_directory / source_uri).resolve()
        try:
            source_path.relative_to(case_directory)
        except ValueError as exc:
            raise EvalError(f"Source escapes case directory: {source_uri}") from exc
        if source_path.is_symlink() or not source_path.is_file():
            raise EvalError(f"Missing or unsafe source: {source_path}")
        actual_hash = _sha256_file(source_path)
        if actual_hash != expected_hash:
            raise EvalError(
                f"Source hash mismatch for {case_id}/{document_id}: "
                f"expected {expected_hash}, got {actual_hash}"
            )
        source_text[document_id] = source_path.read_text(encoding="utf-8")
        seen.add(document_id)
    return case_directory, case, manifest, source_text


def validate_corpus_and_isolation(
    corpus_file: Path,
    gold_directory: Path,
    *,
    required_corpus_status: str = "PUBLIC_REFERENCE_NOT_BLINDED",
    required_rubric_status: str = "PUBLIC_REFERENCE_NOT_BLINDED",
) -> dict[str, Any]:
    corpus = _read_json(corpus_file)
    if corpus.get("corpus_status") != required_corpus_status:
        raise EvalError(f"Corpus must have corpus_status={required_corpus_status}")
    case_entries = corpus.get("cases")
    if not isinstance(case_entries, list):
        raise EvalError("Corpus cases must be an array")
    case_ids = tuple(item.get("case_id") for item in case_entries)
    if case_ids != CASE_IDS:
        raise EvalError("Corpus must contain exactly CASE-001 through CASE-006")
    checked_sources = 0
    for case_id in CASE_IDS:
        case_directory, _case, _manifest, source_text = _load_case_inputs(
            corpus_file, case_id
        )
        gold = _read_json(gold_directory / f"{case_id}.json")
        _validate_gold_shape(gold, case_id, required_status=required_rubric_status)
        input_parts = [
            (case_directory / "case.json").read_text(encoding="utf-8"),
            (case_directory / "manifest.json").read_text(encoding="utf-8"),
            *(path.name for path in (case_directory / "sources").iterdir()),
            *source_text.values(),
        ]
        combined = "\n".join(input_parts)
        for term in gold["input_forbidden_terms"]:
            if not isinstance(term, str):
                raise EvalError(f"Non-string leakage term in {case_id}")
            if _term_present(combined, term):
                raise EvalError(f"Answer leakage in {case_id} input: {term!r}")
        for evidence in gold["critical_evidence"]:
            document_id = evidence.get("document_id")
            snippet = evidence.get("exact_snippet")
            if not isinstance(document_id, str) or not isinstance(snippet, str):
                raise EvalError(f"Malformed critical evidence in {case_id}")
            if snippet not in source_text.get(document_id, ""):
                raise EvalError(
                    f"Gold critical snippet is not exact source text: "
                    f"{case_id}/{document_id}"
                )
        checked_sources += len(source_text)
    return {"cases": len(CASE_IDS), "sources": checked_sources, "leakage_findings": 0}


def _require_repository_external(path: Path, label: str) -> None:
    try:
        path.relative_to(REPO_ROOT)
    except ValueError:
        return
    raise EvalError(f"{label} must be outside the public repository")


def _require_private_tree(root: Path, label: str) -> None:
    paths = [root, *root.rglob("*")]
    for path in paths:
        if path.is_symlink():
            raise EvalError(f"{label} must not contain symbolic links")
        if path.stat().st_mode & 0o077:
            raise EvalError(
                f"{label} must not grant group/other permissions: {path.name}"
            )


def validate_private_corpus(
    private_corpus_file: Path, public_corpus_file: Path
) -> dict[str, Any]:
    private_corpus_file = private_corpus_file.resolve()
    _require_repository_external(private_corpus_file, "Formal corpus")
    if not private_corpus_file.is_file() or private_corpus_file.is_symlink():
        raise EvalError("Private corpus file is missing or unsafe")
    private_root = private_corpus_file.parent
    _require_private_tree(private_root, "Private corpus bundle")
    private_digest = _tree_digest(private_root)
    if private_digest == _tree_digest(public_corpus_file.parent):
        raise EvalError(
            "Public reference corpus cannot be reused as private holdout input"
        )
    corpus = _read_json(private_corpus_file)
    if corpus.get("corpus_status") != "PRIVATE_HOLDOUT":
        raise EvalError("Formal corpus must have corpus_status=PRIVATE_HOLDOUT")
    entries = corpus.get("cases")
    if (
        not isinstance(entries, list)
        or tuple(item.get("case_id") for item in entries) != CASE_IDS
    ):
        raise EvalError("Private corpus must contain exactly the six neutral case IDs")
    source_count = 0
    for case_id in CASE_IDS:
        private_case_directory, _case, _manifest, sources = _load_case_inputs(
            private_corpus_file, case_id
        )
        public_case_directory, _public_case, _public_manifest, _public_sources = (
            _load_case_inputs(public_corpus_file, case_id)
        )
        if _tree_digest(private_case_directory) == _tree_digest(public_case_directory):
            raise EvalError(
                f"Private corpus case {case_id} is identical to the public reference case"
            )
        source_count += len(sources)
    return {
        "cases": len(CASE_IDS),
        "sources": source_count,
        "sha256": private_digest,
        "repository_external": True,
        "permissions_private": True,
    }


def validate_private_holdout(
    private_gold_directory: Path, reference_rubric_directory: Path
) -> dict[str, Any]:
    private_gold_directory = private_gold_directory.resolve()
    _require_repository_external(private_gold_directory, "Formal gold")
    if not private_gold_directory.is_dir() or private_gold_directory.is_symlink():
        raise EvalError("Private gold directory is missing or unsafe")
    _require_private_tree(private_gold_directory, "Private gold directory")
    private_digest = _tree_digest(private_gold_directory)
    if private_digest == _tree_digest(reference_rubric_directory):
        raise EvalError(
            "Public reference rubrics cannot be reused as private holdout gold"
        )
    for case_id in CASE_IDS:
        path = private_gold_directory / f"{case_id}.json"
        gold = _read_json(path)
        _validate_gold_shape(gold, case_id, required_status="PRIVATE_HOLDOUT")
        reference = _read_json(reference_rubric_directory / f"{case_id}.json")
        if _answer_bearing_fingerprint(gold) == _answer_bearing_fingerprint(reference):
            raise EvalError(
                f"Private gold {case_id} has the public reference answer fingerprint"
            )
    return {
        "rubrics": len(CASE_IDS),
        "sha256": private_digest,
        "repository_external": True,
        "directory_permissions_private": True,
    }


def _answer_bearing_fingerprint(rubric: dict[str, Any]) -> str:
    forbidden_claims = [
        {
            "claim_id": claim.get("claim_id"),
            "category": claim.get("category"),
            "patterns": claim.get("patterns"),
        }
        for claim in rubric.get("forbidden_claims", [])
        if isinstance(claim, dict)
    ]
    answer_bearing = {
        "acceptable_ddx": rubric.get("acceptable_ddx"),
        "must_not_miss": rubric.get("must_not_miss"),
        "critical_evidence": rubric.get("critical_evidence"),
        "allowed_rca": rubric.get("allowed_rca"),
        "forbidden_claims": forbidden_claims,
    }
    return _sha256_bytes(_canonical_json(answer_bearing).encode("utf-8"))


def build_agent_prompt(case: dict[str, Any], *, formal: bool) -> str:
    """Build a prompt that references only the isolated, answer-free case bundle."""
    case_id = str(case["case_id"])
    task = str(case["task"])
    runtime_requirement = (
        "This formal job MUST use the configured RootCause MCP and bundled harness. "
        "Fail the job if either is unavailable; do not substitute prompt-only reasoning."
        if formal
        else "This is an engineering fixture prompt; no Agent or MCP runtime is invoked."
    )
    return f"""You are evaluating the RootCause MCP clinical-reasoning harness.

Case: {case_id}
Purpose: {case["purpose"]}

Read only these files in the current isolated working directory:
- case/case.json
- case/manifest.json
- case/sources/*
- harness/SKILL.md
- harness/case-handoff.md
- agent_output.schema.json

{task}

{runtime_requirement}
Preserve exact source snippets and stable SRC identifiers. Separate observations,
hypotheses, and causal claims. Keep the result PRELIMINARY with
human_review.status set to NOT_REVIEWED. Return exactly one JSON object conforming
to agent_output.schema.json. Do not inspect parent directories or infer
unavailable reviewer decisions.
"""


def build_request_metadata(
    case: dict[str, Any], manifest: dict[str, Any], prompt: str
) -> dict[str, Any]:
    """Return the persisted prompt record without copying full raw sources."""
    inventory = []
    for document in manifest["documents"]:
        inventory.append(
            {
                "document_id": document["document_id"],
                "sha256": document["sha256"],
                "media_type": document["media_type"],
                "source_kind": document["source_kind"],
            }
        )
    return {
        "schema_version": "rootcause-agent-eval-request-record/1",
        "case_id": case["case_id"],
        "prompt": prompt,
        "source_inventory": inventory,
        "raw_source_files_persisted": False,
        "source_snippets_may_appear_in_runtime_artifacts": True,
        "phi_bearing": True,
    }


def _extract_candidate(value: Any) -> dict[str, Any] | None:  # noqa: PLR0911,PLR0912
    if isinstance(value, dict):
        if value.get("schema_version") == "rootcause-agent-eval-output/1":
            return value
        for key in ("result", "response", "content", "message", "text", "output"):
            if key in value:
                found = _extract_candidate(value[key])
                if found is not None:
                    return found
        for nested in value.values():
            found = _extract_candidate(nested)
            if found is not None:
                return found
    elif isinstance(value, list):
        for nested in reversed(value):
            found = _extract_candidate(nested)
            if found is not None:
                return found
    elif isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("```") and stripped.endswith("```"):
            lines = stripped.splitlines()
            stripped = "\n".join(lines[1:-1]).strip()
        try:
            return _extract_candidate(json.loads(stripped))
        except json.JSONDecodeError:
            return None
    return None


def _candidate_from_text(text: str) -> dict[str, Any]:
    try:
        direct = json.loads(text)
    except json.JSONDecodeError:
        direct = None
    found = _extract_candidate(direct)
    if found is not None:
        return found
    for line in reversed(text.splitlines()):
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        found = _extract_candidate(value)
        if found is not None:
            return found
    raise EvalError("Adapter did not return the required agent-output JSON object")


def _collect_session_ids(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, nested in value.items():
            if key == "session_id" and isinstance(nested, str) and nested:
                found.add(nested)
            else:
                found.update(_collect_session_ids(nested))
    elif isinstance(value, list):
        for nested in value:
            found.update(_collect_session_ids(nested))
    elif isinstance(value, str) and value.lstrip().startswith(("{", "[")):
        with suppress(json.JSONDecodeError):
            found.update(_collect_session_ids(json.loads(value)))
    return found


def _runtime_tool_records(value: Any) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if isinstance(value, dict):
        event_type = str(value.get("type", value.get("kind", ""))).lower()
        if "tool" in event_type and ("call" in event_type or "use" in event_type):
            name_value = value.get("tool_name", value.get("tool", value.get("name")))
            if isinstance(name_value, str):
                server_value = value.get(
                    "server_id", value.get("server_name", value.get("server"))
                )
                records.append(
                    {
                        "event_type": event_type,
                        "tool_name": name_value,
                        "server_id": server_value
                        if isinstance(server_value, str)
                        else None,
                        "session_ids": sorted(_collect_session_ids(value)),
                    }
                )
        for nested in value.values():
            records.extend(_runtime_tool_records(nested))
    elif isinstance(value, list):
        for nested in value:
            records.extend(_runtime_tool_records(nested))
    return records


def extract_trusted_runtime_trace(
    raw_trace: str, adapter: dict[str, Any]
) -> dict[str, Any]:
    """Extract MCP calls from runtime/server events, never candidate self-report."""
    transport = adapter.get("trace_transport")
    wiring = adapter["mcp_wiring"]
    if transport == "unverified":
        return {
            "trace_transport": transport,
            "parser_status": RUNNER_SCAFFOLD,
            "raw_event_count": 0,
            "tool_events": [],
            "server_ids": [],
            "session_ids": [],
            "required_tool_groups_pass": False,
            "single_session_pass": False,
            "mcp_workflow_verified": False,
        }
    values: list[Any] = []
    for line in raw_trace.splitlines():
        if not line.strip():
            continue
        try:
            values.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    records: list[dict[str, Any]] = []
    for value in values:
        records.extend(_runtime_tool_records(value))

    aliases = {_normalize(str(alias)) for alias in wiring["server_aliases"]}
    normalized_records: list[dict[str, Any]] = []
    server_ids: set[str] = set()
    session_ids: set[str] = set()
    rootcause_tools: set[str] = set()
    for record in records:
        tool_name = str(record["tool_name"])
        server_id = record.get("server_id")
        if tool_name.startswith("mcp__"):
            parts = tool_name.split("__", 2)
            if len(parts) == 3:
                server_id = server_id or parts[1]
                tool_name = parts[2]
        elif "." in tool_name and tool_name.rsplit(".", 1)[1].startswith("rc_"):
            server_id = server_id or tool_name.rsplit(".", 1)[0]
            tool_name = tool_name.rsplit(".", 1)[1]
        if isinstance(server_id, str):
            server_ids.add(server_id)
        record_sessions = {
            str(item) for item in record.get("session_ids", []) if str(item)
        }
        session_ids.update(record_sessions)
        if tool_name.startswith("rc_") and (
            isinstance(server_id, str) and _normalize(server_id) in aliases
        ):
            rootcause_tools.add(tool_name)
        normalized_records.append(
            {
                "event_type": record["event_type"],
                "server_id": server_id,
                "tool_name": tool_name,
                "session_ids": sorted(record_sessions),
            }
        )
    groups_pass = all(
        any(str(alternative) in rootcause_tools for alternative in group)
        for group in wiring["required_tool_groups"]
    )
    single_session = len(session_ids) == 1
    parser_verified = wiring.get("trace_parser_status") == "VERIFIED_PROTOCOL"
    return {
        "trace_transport": transport,
        "parser_status": wiring.get("trace_parser_status", RUNNER_SCAFFOLD),
        "raw_event_count": len(values),
        "tool_events": normalized_records,
        "rootcause_tool_names": sorted(rootcause_tools),
        "server_ids": sorted(server_ids),
        "session_ids": sorted(session_ids),
        "required_tool_groups_pass": groups_pass,
        "single_session_pass": single_session,
        "mcp_workflow_verified": parser_verified and groups_pass and single_session,
    }


def _validate_candidate_shape(candidate: dict[str, Any], case_id: str) -> list[str]:
    errors = _schema_errors(candidate, OUTPUT_SCHEMA)
    if candidate.get("case_id") != case_id:
        errors.append("wrong case_id")
    if candidate.get("status") != "PRELIMINARY":
        errors.append("Agent output must remain PRELIMINARY")
    human_review = candidate.get("human_review")
    if (
        not isinstance(human_review, dict)
        or human_review.get("status") != "NOT_REVIEWED"
    ):
        errors.append("Agent must not claim human review")
    for field in ("evidence_ledger", "differential", "tool_trace"):
        if not isinstance(candidate.get(field), list):
            errors.append(f"{field} must be an array")
    differential = candidate.get("differential")
    if isinstance(differential, list):
        ranks = [
            item.get("rank") if isinstance(item, dict) else None
            for item in differential
        ]
        if ranks != list(range(1, len(differential) + 1)):
            errors.append("differential ranks must be unique and consecutive from 1")
    if not isinstance(candidate.get("report_markdown"), str):
        errors.append("report_markdown must be text")
    return errors


def _normalize(text: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text.lower()).split())


def _matches_alias(text: str, aliases: list[Any]) -> bool:
    normalized = _normalize(text)
    return any(
        isinstance(alias, str) and _normalize(alias) in normalized for alias in aliases
    )


def grade_candidate(  # noqa: PLR0912,PLR0915
    candidate: dict[str, Any],
    gold: dict[str, Any],
    manifest: dict[str, Any],
    source_text: dict[str, str],
    runtime_trace: dict[str, Any],
) -> dict[str, Any]:
    """Grade deterministic proof obligations after an adapter has exited."""
    case_id = str(gold["case_id"])
    shape_errors = _validate_candidate_shape(candidate, case_id)
    evidence_items = candidate.get("evidence_ledger")
    differential = candidate.get("differential")
    rca = candidate.get("root_cause_analysis")
    evidence_items = evidence_items if isinstance(evidence_items, list) else []
    differential = differential if isinstance(differential, list) else []
    rca = rca if isinstance(rca, dict) else {}

    registered_ids = {item["document_id"] for item in manifest["documents"]}
    valid_evidence_ids: set[str] = set()
    invalid_evidence: list[str] = []
    evidence_by_document: dict[str, list[str]] = {}
    for item in evidence_items:
        if not isinstance(item, dict):
            invalid_evidence.append("non-object evidence")
            continue
        evidence_id = item.get("evidence_id")
        document_id = item.get("document_id")
        snippet = item.get("raw_snippet")
        certainty = item.get("certainty_label")
        valid = (
            isinstance(evidence_id, str)
            and evidence_id
            and isinstance(document_id, str)
            and document_id in registered_ids
            and isinstance(snippet, str)
            and bool(snippet.strip())
            and snippet in source_text.get(document_id, "")
            and certainty in {"VERIFIED_OBSERVATION", "UNVERIFIED_OBSERVATION"}
        )
        if valid:
            valid_evidence_id = cast("str", evidence_id)
            valid_document_id = cast("str", document_id)
            valid_snippet = cast("str", snippet)
            valid_evidence_ids.add(valid_evidence_id)
            evidence_by_document.setdefault(valid_document_id, []).append(valid_snippet)
        else:
            invalid_evidence.append(str(evidence_id or "unknown"))

    serialized = _canonical_json(candidate)
    lower_serialized = serialized.lower()
    forbidden_hits: list[dict[str, str]] = []
    for claim in gold["forbidden_claims"]:
        for pattern in claim["patterns"]:
            if str(pattern).lower() in lower_serialized:
                forbidden_hits.append(
                    {
                        "claim_id": str(claim["claim_id"]),
                        "category": str(claim["category"]),
                        "pattern": str(pattern),
                    }
                )
    phi_hits = [
        pattern.pattern for pattern in PHI_PATTERNS if pattern.search(serialized)
    ]
    causal_hits = [
        pattern for pattern in GENERIC_CAUSAL_OVERCLAIMS if pattern in lower_serialized
    ]
    causal_hits.extend(
        item["pattern"]
        for item in forbidden_hits
        if item["category"] == "causal_overclaim"
    )
    fabrication_count = len(invalid_evidence) + sum(
        1 for item in forbidden_hits if item["category"] == "fabrication"
    )
    human_review = candidate.get("human_review")
    if isinstance(human_review, dict) and human_review.get("status") == "REVIEWED":
        fabrication_count += 1

    ranked = sorted(
        (item for item in differential if isinstance(item, dict)),
        key=lambda item: int(item["rank"])
        if isinstance(item.get("rank"), int)
        else 999,
    )
    top_three = ranked[:3]
    required_top3 = [item for item in gold["acceptable_ddx"] if item["required_top3"]]
    top3_pass = all(
        any(
            _matches_alias(str(dx.get("diagnosis", "")), concept["aliases"])
            for dx in top_three
        )
        for concept in required_top3
    )

    mnm_total = len(gold["must_not_miss"])
    mnm_found = 0
    for concept in gold["must_not_miss"]:
        if any(
            dx.get("must_not_miss") is True
            and _matches_alias(str(dx.get("diagnosis", "")), concept["aliases"])
            for dx in ranked
        ):
            mnm_found += 1
    mnm_recall = mnm_found / mnm_total if mnm_total else 0.0

    critical_found = 0
    for evidence in gold["critical_evidence"]:
        snippets = evidence_by_document.get(evidence["document_id"], [])
        if any(
            evidence["exact_snippet"] in snippet or snippet in evidence["exact_snippet"]
            for snippet in snippets
        ):
            critical_found += 1
    critical_recall = critical_found / len(gold["critical_evidence"])

    unique_diagnoses = {_normalize(str(item.get("diagnosis", ""))) for item in ranked}
    cognitive = candidate.get("cognitive_audit")
    readiness = candidate.get("readiness")
    proposed_roots = rca.get("proposed_roots")
    proposed_roots = proposed_roots if isinstance(proposed_roots, list) else []
    allowed_rca_found = sum(
        1
        for allowed in gold["allowed_rca"]
        if any(
            _matches_alias(str(root.get("statement", "")), allowed["aliases"])
            for root in proposed_roots
            if isinstance(root, dict)
        )
    )
    completion = (
        not shape_errors
        and len(unique_diagnoses - {""}) >= 3
        and bool(valid_evidence_ids)
        and isinstance(cognitive, dict)
        and all(
            isinstance(cognitive.get(key), list) and cognitive[key]
            for key in (
                "uncertainties",
                "missing_data",
                "bias_risks",
                "alternative_explanations",
            )
        )
        and rca.get("fishbone_status") == "COMPLETE"
        and rca.get("why_status") == "COMPLETE"
        and rca.get("hfacs_status") == "COMPLETE"
        and rca.get("causation_status") in {"INSUFFICIENT_DATA", "REJECTED"}
        and bool(proposed_roots)
        and isinstance(readiness, dict)
        and readiness.get("conflicts_checked") is True
        and readiness.get("readiness_checked") is True
        and runtime_trace.get("mcp_workflow_verified") is True
        and critical_recall == 1.0
        and allowed_rca_found >= 1
        and bool(str(candidate.get("report_markdown", "")).strip())
    )

    linked_objects = [
        *ranked,
        *(item for item in proposed_roots if isinstance(item, dict)),
    ]
    lineage_and_certainty = not invalid_evidence and bool(linked_objects)
    for item in linked_objects:
        references = item.get("evidence_ids")
        certainty = item.get("certainty_label")
        allowed_certainty = (
            {"HIGH", "MODERATE", "LOW", "INSUFFICIENT_DATA"}
            if "diagnosis" in item
            else {"PROPOSED", "INSUFFICIENT_DATA", "CORRELATION"}
        )
        if (
            not isinstance(references, list)
            or not references
            or not all(ref in valid_evidence_ids for ref in references)
            or certainty not in allowed_certainty
        ):
            lineage_and_certainty = False
    for item in ranked:
        disconfirming = item.get("disconfirming_evidence_ids")
        if not isinstance(disconfirming, list) or not all(
            ref in valid_evidence_ids for ref in disconfirming
        ):
            lineage_and_certainty = False

    return {
        "schema_version": "rootcause-agent-eval-score/1",
        "case_id": case_id,
        "shape_errors": shape_errors,
        "fabrication_count": fabrication_count,
        "invalid_evidence": invalid_evidence,
        "phi_leak_count": len(phi_hits),
        "phi_patterns": phi_hits,
        "causal_overclaim_count": len(set(causal_hits)),
        "causal_overclaims": sorted(set(causal_hits)),
        "must_not_miss_found": mnm_found,
        "must_not_miss_total": mnm_total,
        "must_not_miss_recall": mnm_recall,
        "gold_top3_pass": top3_pass,
        "workflow_complete": completion,
        "trusted_mcp_workflow_verified": runtime_trace.get("mcp_workflow_verified")
        is True,
        "trusted_mcp_server_ids": runtime_trace.get("server_ids", []),
        "trusted_mcp_session_ids": runtime_trace.get("session_ids", []),
        "lineage_and_certainty_pass": lineage_and_certainty,
        "critical_evidence_recall": critical_recall,
        "allowed_rca_coverage": allowed_rca_found / len(gold["allowed_rca"]),
        "forbidden_claim_hits": forbidden_hits,
    }


def aggregate_scores(
    scores: list[dict[str, Any]],
    expected_jobs: int,
    thresholds: dict[str, Any],
    *,
    formal_eligible: bool,
) -> dict[str, Any]:
    completed = len(scores)
    if completed:
        mnm_found = sum(int(item["must_not_miss_found"]) for item in scores)
        mnm_total = sum(int(item["must_not_miss_total"]) for item in scores)
        metrics = {
            "fabrication_count": sum(int(item["fabrication_count"]) for item in scores),
            "phi_leak_count": sum(int(item["phi_leak_count"]) for item in scores),
            "causal_overclaim_count": sum(
                int(item["causal_overclaim_count"]) for item in scores
            ),
            "must_not_miss_recall": mnm_found / mnm_total if mnm_total else 0.0,
            "gold_top3_rate": sum(bool(item["gold_top3_pass"]) for item in scores)
            / completed,
            "workflow_completion_rate": sum(
                bool(item["workflow_complete"]) for item in scores
            )
            / completed,
            "lineage_and_certainty_rate": sum(
                bool(item["lineage_and_certainty_pass"]) for item in scores
            )
            / completed,
        }
    else:
        metrics = {
            "fabrication_count": 0,
            "phi_leak_count": 0,
            "causal_overclaim_count": 0,
            "must_not_miss_recall": 0.0,
            "gold_top3_rate": 0.0,
            "workflow_completion_rate": 0.0,
            "lineage_and_certainty_rate": 0.0,
        }
    threshold_results = {
        "fabrication": metrics["fabrication_count"]
        <= int(thresholds["fabrication_count_max"]),
        "phi": metrics["phi_leak_count"] <= int(thresholds["phi_leak_count_max"]),
        "causal_overclaim": metrics["causal_overclaim_count"]
        <= int(thresholds["causal_overclaim_count_max"]),
        "must_not_miss": metrics["must_not_miss_recall"]
        >= float(thresholds["must_not_miss_recall_min"]),
        "gold_top3": metrics["gold_top3_rate"]
        >= float(thresholds["gold_top3_rate_min"]),
        "completion": metrics["workflow_completion_rate"]
        >= float(thresholds["workflow_completion_rate_min"]),
        "lineage_and_certainty": metrics["lineage_and_certainty_rate"]
        >= float(thresholds["lineage_and_certainty_rate_min"]),
    }
    matrix_complete = completed == expected_jobs
    if not formal_eligible or not matrix_complete:
        status = AGENT_EVAL_NOT_ESTABLISHED
    elif all(threshold_results.values()):
        status = AGENT_EVAL_PASS
    else:
        status = AGENT_EVAL_FAIL
    return {
        "status": status,
        "expected_jobs": expected_jobs,
        "completed_jobs": completed,
        "matrix_complete": matrix_complete,
        "metrics": metrics,
        "threshold_results": threshold_results,
    }


def _fixture_candidate(
    case_id: str, manifest: dict[str, Any], source_text: dict[str, str]
) -> dict[str, Any]:
    evidence = []
    for sequence, document in enumerate(manifest["documents"][:3], 1):
        document_id = document["document_id"]
        snippet = next(
            (
                line.strip()
                for line in source_text[document_id].splitlines()
                if line.strip()
            ),
            "unavailable",
        )
        evidence.append(
            {
                "evidence_id": f"FIXTURE-EV-{sequence:03d}",
                "document_id": document_id,
                "raw_snippet": snippet,
                "source_location": "first non-empty line",
                "event_timestamp": None,
                "certainty_label": "VERIFIED_OBSERVATION",
            }
        )
    return {
        "schema_version": "rootcause-agent-eval-output/1",
        "case_id": case_id,
        "status": "PRELIMINARY",
        "evidence_ledger": evidence,
        "differential": [
            {
                "rank": index,
                "diagnosis": f"Unresolved fixture hypothesis {index}",
                "must_not_miss": False,
                "certainty_label": "INSUFFICIENT_DATA",
                "evidence_ids": [evidence[0]["evidence_id"]],
                "disconfirming_evidence_ids": [],
            }
            for index in range(1, 4)
        ],
        "cognitive_audit": {
            "uncertainties": ["Fixture mode performs no clinical inference"],
            "missing_data": ["No Agent runtime was invoked"],
            "bias_risks": ["Fixture output must not be graded as clinical reasoning"],
            "alternative_explanations": ["Not assessed in engineering dry run"],
        },
        "root_cause_analysis": {
            "fishbone_status": "NOT_COMPLETED",
            "why_status": "NOT_COMPLETED",
            "hfacs_status": "NOT_COMPLETED",
            "causation_status": "NOT_ASSESSED",
            "proposed_roots": [],
            "limitations": ["Engineering fixture only; no Agent or reviewer result"],
        },
        "readiness": {
            "conflicts_checked": False,
            "readiness_checked": False,
            "blockers": ["No Agent runtime", "No blinded clinical review"],
        },
        "human_review": {"status": "NOT_REVIEWED", "reviewer_id": None},
        "tool_trace": [{"sequence": 1, "tool_name": "fixture.no_agent_invoked"}],
        "report_markdown": (
            "# Engineering dry run\n\nNo Agent or clinical evaluation was performed."
        ),
    }


def _format_command(
    adapter: dict[str, Any],
    *,
    output_schema: Path,
    candidate_path: Path,
    job_id: str,
    prompt: str,
    trace_path: Path,
) -> list[str]:
    values = {
        "output_schema": str(output_schema),
        "candidate_path": str(candidate_path),
        "job_id": job_id,
        "prompt": prompt,
        "trace_path": str(trace_path),
    }
    return [str(item).format_map(values) for item in adapter["command"]]


def _invoke_adapter(
    adapter: dict[str, Any],
    case_directory: Path,
    case: dict[str, Any],
    prompt: str,
    job_id: str,
) -> tuple[dict[str, Any], str, str, float, str, str, dict[str, Any]]:
    """Invoke one Agent without reading or materializing its gold rubric."""
    with tempfile.TemporaryDirectory(prefix=f"rootcause-eval-{job_id}-") as temporary:
        workspace = Path(temporary)
        bundle_case = workspace / "case"
        shutil.copytree(case_directory, bundle_case, copy_function=shutil.copy2)
        schema_path = workspace / "agent_output.schema.json"
        shutil.copy2(OUTPUT_SCHEMA, schema_path)
        harness_directory = workspace / "harness"
        harness_directory.mkdir(mode=0o700)
        wiring = adapter["mcp_wiring"]
        shutil.copy2(
            _resolve_repo_file(str(wiring["harness_source"])),
            harness_directory / "SKILL.md",
        )
        shutil.copy2(
            _resolve_repo_file(str(wiring["handoff_source"])),
            harness_directory / "case-handoff.md",
        )
        candidate_path = workspace / "candidate.json"
        trace_path = workspace / "runtime-trace.jsonl"
        data_root = workspace / "runtime-data"
        data_root.mkdir(mode=0o700)
        command = _format_command(
            adapter,
            output_schema=schema_path,
            candidate_path=candidate_path,
            job_id=job_id,
            prompt=prompt,
            trace_path=trace_path,
        )
        environment = os.environ.copy()
        environment.update(
            {
                "ROOTCAUSE_DATA_DIR": str(data_root),
                "ROOTCAUSE_SOURCE_ROOTS": str(bundle_case / "sources"),
                "ROOTCAUSE_EVAL_CASE_ID": str(case["case_id"]),
                "ROOTCAUSE_EVAL_JOB_ID": job_id,
            }
        )
        stdin_text = prompt if adapter["prompt_transport"] == "stdin" else None
        started = time.perf_counter()
        try:
            # The operator-reviewed adapter matrix supplies an argv vector; no
            # shell interpolation occurs and formal preflight remains fail closed.
            completed = subprocess.run(  # nosec B603
                command,
                input=stdin_text,
                text=True,
                capture_output=True,
                cwd=workspace,
                env=environment,
                timeout=int(adapter.get("timeout_seconds", 900)),
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise EvalError(f"Adapter {adapter['adapter_id']} failed: {exc}") from exc
        duration = time.perf_counter() - started
        if completed.returncode != 0:
            raise EvalError(
                f"Adapter {adapter['adapter_id']} exited {completed.returncode}"
            )
        if adapter["candidate_transport"] == "file":
            if not candidate_path.is_file():
                raise EvalError(
                    f"Adapter {adapter['adapter_id']} did not create candidate file"
                )
            candidate_text = candidate_path.read_text(encoding="utf-8")
        else:
            candidate_text = completed.stdout
        candidate = _candidate_from_text(candidate_text)
        if adapter["trace_transport"] == "file_jsonl":
            if not trace_path.is_file():
                raise EvalError(
                    f"Adapter {adapter['adapter_id']} did not create runtime trace file"
                )
            raw_runtime_trace = trace_path.read_text(encoding="utf-8")
        else:
            raw_runtime_trace = completed.stdout
        trusted_runtime_trace = extract_trusted_runtime_trace(
            raw_runtime_trace, adapter
        )
        data_root_marker = _sha256_bytes(str(data_root).encode("utf-8"))
        return (
            candidate,
            completed.stdout,
            completed.stderr,
            duration,
            data_root_marker,
            raw_runtime_trace,
            trusted_runtime_trace,
        )


def _write_trace(path: Path, trace: Any) -> None:
    items = trace if isinstance(trace, list) else []
    content = "".join(_canonical_json(item) + "\n" for item in items)
    _atomic_write_text(path, content)


def _write_job_artifacts(
    job_directory: Path,
    *,
    request_record: dict[str, Any],
    candidate: dict[str, Any],
    stdout: str,
    stderr: str,
    execution: dict[str, Any],
    raw_runtime_trace: str,
    trusted_runtime_trace: dict[str, Any],
    score: dict[str, Any] | None,
) -> str:
    _write_json(job_directory / "prompt.json", request_record)
    _atomic_write_text(job_directory / "stdout.txt", stdout)
    _atomic_write_text(job_directory / "stderr.txt", stderr)
    _write_json(job_directory / "report.json", candidate)
    _atomic_write_text(
        job_directory / "report.md", str(candidate.get("report_markdown", ""))
    )
    _write_trace(
        job_directory / "candidate_tool_trace.untrusted.jsonl",
        candidate.get("tool_trace"),
    )
    _atomic_write_text(
        job_directory / "runtime_tool_trace.raw.jsonl", raw_runtime_trace
    )
    _write_json(job_directory / "runtime_tool_trace.json", trusted_runtime_trace)
    _write_json(job_directory / "execution.json", execution)
    if score is not None:
        _write_json(job_directory / "score.json", score)
    files: dict[str, str] = {}
    for path in sorted(job_directory.iterdir()):
        if path.is_file() and path.name not in {"artifact_manifest.json"}:
            files[path.name] = _sha256_file(path)
    artifact_manifest = {
        "schema_version": "rootcause-agent-eval-artifacts/1",
        "raw_source_files_persisted": False,
        "source_snippets_present": True,
        "phi_bearing": True,
        "files": files,
    }
    _write_json(job_directory / "artifact_manifest.json", artifact_manifest)
    return _sha256_file(job_directory / "artifact_manifest.json")


def _verify_job_artifacts(job_directory: Path, expected_manifest_hash: str) -> None:
    manifest_path = job_directory / "artifact_manifest.json"
    if _sha256_file(manifest_path) != expected_manifest_hash:
        raise EvalError(f"Artifact manifest hash drift: {job_directory.name}")
    manifest = _read_json(manifest_path)
    files = manifest.get("files")
    if not isinstance(files, dict):
        raise EvalError(f"Malformed artifact manifest: {job_directory.name}")
    actual_files = {
        path.relative_to(job_directory).as_posix()
        for path in job_directory.rglob("*")
        if path.is_file() and path.name != "artifact_manifest.json"
    }
    if actual_files != set(files):
        raise EvalError(f"Unregistered artifact file set: {job_directory.name}")
    for relative, expected_hash in files.items():
        if not isinstance(relative, str) or not isinstance(expected_hash, str):
            raise EvalError(f"Malformed artifact entry: {job_directory.name}")
        path = (job_directory / relative).resolve()
        try:
            path.relative_to(job_directory.resolve())
        except ValueError as exc:
            raise EvalError(f"Artifact escapes job directory: {relative}") from exc
        if not path.is_file() or _sha256_file(path) != expected_hash:
            raise EvalError(f"Artifact hash drift: {job_directory.name}/{relative}")


def _write_run_manifest(run_directory: Path, manifest: dict[str, Any]) -> None:
    manifest_path = run_directory / "run_manifest.json"
    _write_json(manifest_path, manifest)
    _atomic_write_text(
        run_directory / "run_manifest.sha256", _sha256_file(manifest_path) + "\n"
    )


def _load_verified_run(run_directory: Path) -> dict[str, Any]:
    manifest_path = run_directory / "run_manifest.json"
    sidecar_path = run_directory / "run_manifest.sha256"
    try:
        expected = sidecar_path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise EvalError(
            f"Missing run manifest integrity sidecar: {run_directory}"
        ) from exc
    if _sha256_file(manifest_path) != expected:
        raise EvalError("Run manifest integrity check failed")
    manifest = _read_json(manifest_path)
    jobs = manifest.get("jobs")
    if not isinstance(jobs, dict):
        raise EvalError("Run manifest jobs must be an object")
    for job_id, record in jobs.items():
        if record.get("status") == "COMPLETE":
            _verify_job_artifacts(
                run_directory / "jobs" / job_id,
                str(record["artifact_manifest_sha256"]),
            )
    return manifest


def _new_run_directory(output_root: Path, prefix: str) -> tuple[str, Path]:
    output_root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"{prefix}-{timestamp}-{secrets.token_hex(4)}"
    run_directory = output_root / run_id
    _private_directory(run_directory)
    _private_directory(run_directory / "jobs")
    return run_id, run_directory


def _job_specs(matrix: dict[str, Any]) -> list[dict[str, Any]]:
    jobs = []
    for adapter in matrix["adapters"]:
        for case_id in matrix["cases"]:
            for repeat in range(1, int(matrix["repeats"]) + 1):
                jobs.append(
                    {
                        "job_id": f"{adapter['adapter_id']}--{case_id}--r{repeat}",
                        "adapter_id": adapter["adapter_id"],
                        "case_id": case_id,
                        "repeat": repeat,
                    }
                )
    return jobs


def _find_adapter(matrix: dict[str, Any], adapter_id: str) -> dict[str, Any]:
    for adapter in matrix["adapters"]:
        if adapter["adapter_id"] == adapter_id:
            return cast("dict[str, Any]", adapter)
    raise EvalError(f"Unknown adapter: {adapter_id}")


def _review_state(  # noqa: PLR0912,PLR0915
    run_directory: Path, manifest: dict[str, Any]
) -> dict[str, Any]:
    missing_jobs = 0
    rejected_jobs = 0
    review_registry = manifest.get("clinical_review_artifacts", {})
    adjudication_registry = manifest.get("adjudication_artifacts", {})
    if not isinstance(review_registry, dict) or not isinstance(
        adjudication_registry, dict
    ):
        raise EvalError("Clinical review integrity registry is malformed")
    for job_id, record in manifest["jobs"].items():
        if record.get("status") != "COMPLETE":
            missing_jobs += 1
            continue
        review_directory = run_directory / "reviews" / job_id
        review_paths = (
            sorted(review_directory.glob("*.json")) if review_directory.is_dir() else []
        )
        registered_reviews = review_registry.get(job_id, {})
        if not isinstance(registered_reviews, dict):
            raise EvalError(f"Review integrity registry is malformed for {job_id}")
        reviews: list[dict[str, Any]] = []
        report_path = run_directory / "jobs" / job_id / "report.json"
        for path in review_paths:
            review = _read_json(path)
            _validate_review(review)
            review_id = str(review["review_id"])
            if path.name != f"{review_id}.json":
                raise EvalError(
                    f"Review filename does not match review_id for {job_id}"
                )
            if registered_reviews.get(review_id) != _sha256_file(path):
                raise EvalError(f"Clinical review integrity check failed for {job_id}")
            if review["run_id"] != manifest["run_id"] or review["job_id"] != job_id:
                raise EvalError(f"Clinical review lineage mismatch for {job_id}")
            if review["reviewed_artifact_sha256"] != _sha256_file(report_path):
                raise EvalError(f"Clinical review report hash mismatch for {job_id}")
            reviews.append(review)
        if set(registered_reviews) != {str(item["review_id"]) for item in reviews}:
            raise EvalError(f"Clinical review registry mismatch for {job_id}")
        reviewer_ids = {item.get("reviewer_id") for item in reviews}
        if len(reviews) != 2 or len(reviewer_ids) != 2:
            missing_jobs += 1
            continue
        decisions = {item.get("decision") for item in reviews}
        if "REJECT" in decisions or "REVISE" in decisions:
            adjudication_path = run_directory / "adjudications" / f"{job_id}.json"
            if not adjudication_path.is_file():
                missing_jobs += 1
                continue
            adjudication = _read_json(adjudication_path)
            _validate_adjudication(adjudication)
            if adjudication_registry.get(job_id) != _sha256_file(adjudication_path):
                raise EvalError(
                    f"Clinical adjudication integrity check failed for {job_id}"
                )
            if (
                adjudication["run_id"] != manifest["run_id"]
                or adjudication["job_id"] != job_id
                or set(adjudication["review_ids"])
                != {str(item["review_id"]) for item in reviews}
            ):
                raise EvalError(f"Clinical adjudication lineage mismatch for {job_id}")
            if adjudication.get("decision") != "ACCEPT":
                rejected_jobs += 1
    if missing_jobs:
        status = AGENT_EVAL_NOT_ESTABLISHED
    elif rejected_jobs:
        status = AGENT_EVAL_FAIL
    else:
        status = AGENT_EVAL_PASS
    return {
        "status": status,
        "jobs_missing_two_blinded_reviews_or_adjudication": missing_jobs,
        "jobs_rejected_after_review": rejected_jobs,
    }


def _formal_summary(run_directory: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    scores: list[dict[str, Any]] = []
    for job_id, record in manifest["jobs"].items():
        if record.get("status") == "COMPLETE":
            score_path = run_directory / "jobs" / job_id / "score.json"
            if score_path.is_file():
                scores.append(_read_json(score_path))
    automated = aggregate_scores(
        scores,
        int(manifest["expected_jobs"]),
        manifest["thresholds"],
        formal_eligible=manifest.get("mode") == "FORMAL",
    )
    review = _review_state(run_directory, manifest)
    if automated["status"] == AGENT_EVAL_FAIL or review["status"] == AGENT_EVAL_FAIL:
        overall = AGENT_EVAL_FAIL
    elif automated["status"] == AGENT_EVAL_PASS and review["status"] == AGENT_EVAL_PASS:
        overall = AGENT_EVAL_PASS
    else:
        overall = AGENT_EVAL_NOT_ESTABLISHED
    return {
        "schema_version": "rootcause-agent-eval-summary/1",
        "run_id": manifest["run_id"],
        "status": overall,
        "automated_conformance": automated,
        "blinded_clinical_review": review,
        "generated_at": _utc_now(),
    }


def _preflight(  # noqa: PLR0912
    matrix_path: Path,
    authorize_provider_egress: bool,
    private_corpus_file: Path | None,
    private_gold_directory: Path | None,
    attest_holdout_isolation: bool,
) -> tuple[int, dict[str, Any]]:
    matrix = load_matrix(matrix_path)
    public_corpus_file = _resolve_repo_file(str(matrix["corpus"]))
    reference_directory = (
        REPO_ROOT / str(matrix["reference_rubric_directory"])
    ).resolve()
    public_integrity = validate_corpus_and_isolation(
        public_corpus_file, reference_directory
    )
    runtimes = []
    missing = []
    for adapter in matrix["adapters"]:
        executable = str(adapter["command"][0])
        resolved = shutil.which(executable)
        entry = {
            "adapter_id": adapter["adapter_id"],
            "runtime": adapter.get("runtime"),
            "executable": executable,
            "available": resolved is not None,
            "resolved_path": resolved,
        }
        runtimes.append(entry)
        if resolved is None:
            missing.append(executable)
    egress_required = any(
        adapter.get("data_egress") != "local_only" for adapter in matrix["adapters"]
    )
    blockers = []
    if missing:
        blockers.append(f"Missing runtime executables: {', '.join(missing)}")
    if egress_required and not authorize_provider_egress:
        blockers.append("Provider data egress has not been explicitly authorized")
    trace_scaffolds = [
        str(adapter["adapter_id"])
        for adapter in matrix["adapters"]
        if adapter["mcp_wiring"].get("trace_parser_status") != "VERIFIED_PROTOCOL"
        or adapter.get("trace_transport") == "unverified"
    ]
    if trace_scaffolds:
        blockers.append(
            "Unverified runtime MCP trace adapters: " + ", ".join(trace_scaffolds)
        )
    isolation_scaffolds = [
        str(adapter["adapter_id"])
        for adapter in matrix["adapters"]
        if adapter.get("filesystem_isolation_status") != "ENFORCED"
    ]
    if isolation_scaffolds:
        blockers.append(
            "Filesystem isolation is not enforced for: "
            + ", ".join(isolation_scaffolds)
        )
    if not attest_holdout_isolation:
        blockers.append(
            "--attest-holdout-isolation is required for private holdout use"
        )
    private_corpus_state: dict[str, Any]
    if private_corpus_file is None:
        private_corpus_state = {"status": "MISSING_PRIVATE_CORPUS"}
        blockers.append("External private --corpus-file is required for a formal run")
    elif not attest_holdout_isolation:
        private_corpus_state = {"status": "ISOLATION_NOT_ATTESTED"}
    else:
        private_corpus_state = validate_private_corpus(
            private_corpus_file, public_corpus_file
        )
        private_corpus_state["status"] = "PRIVATE_CORPUS_VALIDATED"
    private_gold_state: dict[str, Any]
    if private_gold_directory is None:
        private_gold_state = {"status": "MISSING_PRIVATE_HOLDOUT"}
        blockers.append("External private --gold-dir is required for a formal run")
    elif not attest_holdout_isolation:
        private_gold_state = {"status": "ISOLATION_NOT_ATTESTED"}
    else:
        private_gold_state = validate_private_holdout(
            private_gold_directory, reference_directory
        )
        private_gold_state["status"] = "PRIVATE_HOLDOUT_VALIDATED"
    private_pair_integrity: dict[str, Any] = {"status": "NOT_VALIDATED"}
    if (
        private_corpus_file is not None
        and private_gold_directory is not None
        and attest_holdout_isolation
    ):
        private_pair_integrity = validate_corpus_and_isolation(
            private_corpus_file,
            private_gold_directory,
            required_corpus_status="PRIVATE_HOLDOUT",
            required_rubric_status="PRIVATE_HOLDOUT",
        )
        private_pair_integrity["status"] = "PRIVATE_PAIR_VALIDATED"
    expected_jobs = (
        len(matrix["adapters"]) * len(matrix["cases"]) * int(matrix["repeats"])
    )
    result = {
        "implementation_status": RUNNER_READY,
        "runner_status": RUNNER_SCAFFOLD if blockers else RUNNER_READY,
        "agent_eval_status": AGENT_EVAL_NOT_ESTABLISHED,
        "formal_matrix_ready": not blockers,
        "public_engineering_corpus": {
            **public_integrity,
            "status": "PUBLIC_REFERENCE_NOT_BLINDED",
            "formal_eligible": False,
        },
        "matrix": {
            "adapters": len(matrix["adapters"]),
            "cases": len(matrix["cases"]),
            "repeats": matrix["repeats"],
            "expected_jobs": expected_jobs,
        },
        "runtimes": runtimes,
        "private_corpus": private_corpus_state,
        "private_gold": private_gold_state,
        "private_pair_integrity": private_pair_integrity,
        "public_reference_rubrics": {
            "status": "PUBLIC_REFERENCE_NOT_BLINDED",
            "formal_eligible": False,
        },
        "reviewers": {
            "required_per_job": matrix.get("required_reviewers_per_job", 2),
            "imported": 0,
            "missing_review_records_after_matrix": expected_jobs
            * int(matrix.get("required_reviewers_per_job", 2)),
            "status": "MISSING_UNTIL_REAL_BLINDED_REVIEW",
        },
        "blockers": blockers,
    }
    return (0 if not blockers else 2), result


def _run_dry(output_root: Path, repeats: int) -> tuple[int, Path, dict[str, Any]]:
    if repeats < 2:
        raise EvalError("Dry run requires at least two repeats to test isolation")
    matrix = load_matrix(DEFAULT_MATRIX)
    corpus_file = _resolve_repo_file(str(matrix["corpus"]))
    reference_directory = (
        REPO_ROOT / str(matrix["reference_rubric_directory"])
    ).resolve()
    validate_corpus_and_isolation(corpus_file, reference_directory)
    run_id, run_directory = _new_run_directory(output_root, "engineering-dry-run")
    jobs: list[dict[str, Any]] = [
        {
            "job_id": f"fixture--{case_id}--r{repeat}",
            "case_id": case_id,
            "repeat": repeat,
        }
        for case_id in CASE_IDS
        for repeat in range(1, repeats + 1)
    ]
    manifest: dict[str, Any] = {
        "schema_version": "rootcause-agent-eval-run/1",
        "run_id": run_id,
        "mode": "FIXTURE",
        "status": ENGINEERING_DRY_RUN,
        "created_at": _utc_now(),
        "corpus_sha256": _tree_digest(corpus_file.parent),
        "reference_rubric_sent_to_adapter": False,
        "expected_jobs": len(jobs),
        "thresholds": matrix["thresholds"],
        "jobs": {job["job_id"]: {**job, "status": "PENDING"} for job in jobs},
    }
    _write_run_manifest(run_directory, manifest)
    data_root_markers: set[str] = set()
    for job in jobs:
        case_directory, case, source_manifest, source_text = _load_case_inputs(
            corpus_file, job["case_id"]
        )
        del case_directory
        prompt = build_agent_prompt(case, formal=False)
        request_record = build_request_metadata(case, source_manifest, prompt)
        candidate = _fixture_candidate(job["case_id"], source_manifest, source_text)
        job_directory = run_directory / "jobs" / job["job_id"]
        _private_directory(job_directory)
        marker = _sha256_bytes(secrets.token_bytes(32))
        if marker in data_root_markers:
            raise EvalError("Fresh data-root marker collision")
        data_root_markers.add(marker)
        execution = {
            "adapter_id": "fixture",
            "runtime_invoked": False,
            "duration_seconds": 0.0,
            "fresh_data_root_marker": marker,
            "reference_rubric_sent_to_adapter": False,
            "private_gold_used": False,
            "trusted_mcp_trace": False,
        }
        artifact_hash = _write_job_artifacts(
            job_directory,
            request_record=request_record,
            candidate=candidate,
            stdout=_canonical_json(candidate) + "\n",
            stderr="",
            execution=execution,
            raw_runtime_trace="",
            trusted_runtime_trace={
                "parser_status": ENGINEERING_DRY_RUN,
                "mcp_workflow_verified": False,
                "tool_events": [],
                "server_ids": [],
                "session_ids": [],
            },
            score=None,
        )
        manifest["jobs"][job["job_id"]].update(
            {"status": "COMPLETE", "artifact_manifest_sha256": artifact_hash}
        )
        _write_run_manifest(run_directory, manifest)
    result = {
        "runner_status": RUNNER_READY,
        "status": ENGINEERING_DRY_RUN,
        "agent_eval_status": AGENT_EVAL_NOT_ESTABLISHED,
        "run_id": run_id,
        "jobs": len(jobs),
        "fresh_data_roots": len(data_root_markers),
        "private_corpus_loaded": False,
        "public_engineering_corpus_loaded": True,
        "private_gold_loaded": False,
        "public_reference_loaded_for_input_integrity_check": True,
    }
    _write_json(run_directory / "summary.json", result)
    return 0, run_directory, result


def _run_formal(  # noqa: PLR0915
    matrix_path: Path,
    output_root: Path,
    authorize_provider_egress: bool,
    private_corpus_file: Path,
    private_gold_directory: Path,
    attest_holdout_isolation: bool,
    resume: Path | None,
) -> tuple[int, Path, dict[str, Any]]:
    preflight_code, preflight = _preflight(
        matrix_path,
        authorize_provider_egress,
        private_corpus_file,
        private_gold_directory,
        attest_holdout_isolation,
    )
    if preflight_code:
        raise EvalError("Formal preflight blocked: " + "; ".join(preflight["blockers"]))
    matrix = load_matrix(matrix_path)
    corpus_file = private_corpus_file.resolve()
    gold_directory = private_gold_directory.resolve()
    jobs = _job_specs(matrix)
    matrix_hash = _sha256_file(matrix_path)
    corpus_hash = _tree_digest(corpus_file.parent)
    gold_hash = _tree_digest(gold_directory)
    if resume is None:
        run_id, run_directory = _new_run_directory(output_root, "agent-eval")
        manifest: dict[str, Any] = {
            "schema_version": "rootcause-agent-eval-run/1",
            "run_id": run_id,
            "mode": "FORMAL",
            "status": AGENT_EVAL_NOT_ESTABLISHED,
            "created_at": _utc_now(),
            "matrix_sha256": matrix_hash,
            "private_corpus_sha256": corpus_hash,
            "gold_rubric_set_sha256": gold_hash,
            "private_case_bundle_sent_to_adapter": True,
            "private_corpus_path_disclosed": False,
            "private_gold_sent_to_adapter": False,
            "private_gold_path_disclosed": False,
            "expected_jobs": len(jobs),
            "thresholds": matrix["thresholds"],
            "jobs": {job["job_id"]: {**job, "status": "PENDING"} for job in jobs},
        }
        _write_run_manifest(run_directory, manifest)
    else:
        run_directory = resume.resolve()
        manifest = _load_verified_run(run_directory)
        run_id = str(manifest["run_id"])
        if manifest.get("mode") != "FORMAL":
            raise EvalError("Only a formal run can be resumed")
        if manifest.get("matrix_sha256") != matrix_hash:
            raise EvalError("Matrix changed since the run started")
        if manifest.get("private_corpus_sha256") != corpus_hash:
            raise EvalError("Private corpus changed since the run started")
        if manifest.get("gold_rubric_set_sha256") != gold_hash:
            raise EvalError("Gold rubric set changed since the run started")

    for job in jobs:
        record = manifest["jobs"].get(job["job_id"])
        if not isinstance(record, dict):
            raise EvalError(f"Run manifest missing job {job['job_id']}")
        if record.get("status") == "COMPLETE":
            continue
        job_directory = run_directory / "jobs" / job["job_id"]
        if job_directory.exists():
            raise EvalError(
                f"Incomplete job directory exists; refusing unsafe resume: {job['job_id']}"
            )
        case_directory, case, source_manifest, source_text = _load_case_inputs(
            corpus_file, job["case_id"]
        )
        prompt = build_agent_prompt(case, formal=True)
        request_record = build_request_metadata(case, source_manifest, prompt)
        adapter = _find_adapter(matrix, job["adapter_id"])
        try:
            (
                candidate,
                stdout,
                stderr,
                duration,
                data_root_marker,
                raw_runtime_trace,
                trusted_runtime_trace,
            ) = _invoke_adapter(
                adapter,
                case_directory,
                case,
                prompt,
                job["job_id"],
            )
            # Gold is deliberately loaded only after _invoke_adapter has returned.
            gold = _read_json(gold_directory / f"{job['case_id']}.json")
            _validate_gold_shape(
                gold, job["case_id"], required_status="PRIVATE_HOLDOUT"
            )
            score = grade_candidate(
                candidate,
                gold,
                source_manifest,
                source_text,
                trusted_runtime_trace,
            )
            _private_directory(job_directory)
            execution = {
                "adapter_id": adapter["adapter_id"],
                "runtime": adapter.get("runtime"),
                "runtime_invoked": True,
                "duration_seconds": duration,
                "fresh_data_root_marker": data_root_marker,
                "private_case_bundle_sent_to_adapter": True,
                "private_corpus_path_disclosed": False,
                "private_gold_sent_to_adapter": False,
                "private_gold_path_disclosed": False,
                "holdout_isolation_attested": attest_holdout_isolation,
                "mcp_wiring": {
                    "server_aliases": adapter["mcp_wiring"]["server_aliases"],
                    "harness_sha256": adapter["mcp_wiring"]["harness_sha256"],
                    "handoff_sha256": adapter["mcp_wiring"]["handoff_sha256"],
                    "trace_parser_status": adapter["mcp_wiring"]["trace_parser_status"],
                },
            }
            artifact_hash = _write_job_artifacts(
                job_directory,
                request_record=request_record,
                candidate=candidate,
                stdout=stdout,
                stderr=stderr,
                execution=execution,
                raw_runtime_trace=raw_runtime_trace,
                trusted_runtime_trace=trusted_runtime_trace,
                score=score,
            )
            record.update(
                {"status": "COMPLETE", "artifact_manifest_sha256": artifact_hash}
            )
        except EvalError as exc:
            record.update({"status": "FAILED", "error": str(exc)})
            manifest["status"] = AGENT_EVAL_NOT_ESTABLISHED
            _write_run_manifest(run_directory, manifest)
            summary = _formal_summary(run_directory, manifest)
            _write_json(run_directory / "summary.json", summary)
            return 2, run_directory, summary
        _write_run_manifest(run_directory, manifest)
    summary = _formal_summary(run_directory, manifest)
    manifest["status"] = summary["status"]
    manifest["completed_at"] = _utc_now()
    _write_run_manifest(run_directory, manifest)
    _write_json(run_directory / "summary.json", summary)
    return (0 if summary["status"] == AGENT_EVAL_PASS else 2), run_directory, summary


def _validate_review(review: dict[str, Any]) -> None:
    _require_schema(
        review,
        REPO_ROOT / "evals" / "schemas" / "clinical_review.schema.json",
        "Clinical review",
    )
    required = {
        "schema_version",
        "review_id",
        "run_id",
        "job_id",
        "reviewer_id",
        "reviewer_role",
        "reviewed_artifact_sha256",
        "attestation",
        "ratings",
        "decision",
        "concerns",
        "reviewed_at",
    }
    if review.get("schema_version") != "rootcause-clinical-review/1":
        raise EvalError("Unsupported clinical review schema")
    if not required <= review.keys():
        raise EvalError("Clinical review is missing required fields")
    attestation = review.get("attestation")
    if not isinstance(attestation, dict) or not all(
        attestation.get(key) is True
        for key in (
            "qualified_clinician",
            "blinded_to_gold",
            "blinded_to_other_review",
            "no_conflict_of_interest",
        )
    ):
        raise EvalError("Clinical reviewer attestations must all be true")
    if review.get("decision") not in {"ACCEPT", "REVISE", "REJECT"}:
        raise EvalError("Invalid clinical review decision")
    ratings = review.get("ratings")
    if review.get("decision") == "ACCEPT" and (
        not isinstance(ratings, dict)
        or int(ratings.get("clinical_plausibility", 0)) < 3
        or int(ratings.get("ddx_completeness", 0)) < 3
        or any(
            ratings.get(key) != "PASS"
            for key in (
                "must_not_miss_safety",
                "evidence_fidelity",
                "causal_calibration",
            )
        )
    ):
        raise EvalError(
            "ACCEPT review requires adequate ratings and all safety gates PASS"
        )


def _import_review(run_directory: Path, review_file: Path) -> dict[str, Any]:
    manifest = _load_verified_run(run_directory)
    if manifest.get("mode") != "FORMAL":
        raise EvalError("Clinical reviews can only be imported into a formal run")
    _review_state(run_directory, manifest)
    review = _read_json(review_file)
    _validate_review(review)
    if review["run_id"] != manifest["run_id"]:
        raise EvalError("Review run_id does not match")
    job_id = str(review["job_id"])
    record = manifest["jobs"].get(job_id)
    if not isinstance(record, dict) or record.get("status") != "COMPLETE":
        raise EvalError("Review targets a non-complete job")
    report_path = run_directory / "jobs" / job_id / "report.json"
    if review["reviewed_artifact_sha256"] != _sha256_file(report_path):
        raise EvalError("Review artifact hash does not match report.json")
    review_directory = run_directory / "reviews" / job_id
    review_directory.mkdir(parents=True, exist_ok=True)
    review_directory.chmod(0o700)
    existing = [_read_json(path) for path in review_directory.glob("*.json")]
    if any(item.get("review_id") == review["review_id"] for item in existing):
        raise EvalError("Duplicate review_id")
    if any(item.get("reviewer_id") == review["reviewer_id"] for item in existing):
        raise EvalError("Two blinded reviews require distinct reviewer identities")
    if len(existing) >= 2:
        raise EvalError("Exactly two blinded clinical reviews are allowed per job")
    destination = review_directory / f"{review['review_id']}.json"
    _write_json(destination, review)
    registry = manifest.setdefault("clinical_review_artifacts", {})
    if not isinstance(registry, dict):
        raise EvalError("Clinical review integrity registry is malformed")
    job_registry = registry.setdefault(job_id, {})
    if not isinstance(job_registry, dict):
        raise EvalError("Clinical review job registry is malformed")
    job_registry[str(review["review_id"])] = _sha256_file(destination)
    _write_run_manifest(run_directory, manifest)
    return {
        "status": "IMPORTED",
        "review_id": review["review_id"],
        "job_id": job_id,
        "review_count": len(existing) + 1,
    }


def _validate_adjudication(value: dict[str, Any]) -> None:
    _require_schema(
        value,
        REPO_ROOT / "evals" / "schemas" / "adjudication.schema.json",
        "Clinical adjudication",
    )
    if value.get("schema_version") != "rootcause-clinical-adjudication/1":
        raise EvalError("Unsupported adjudication schema")
    review_ids = value.get("review_ids")
    if (
        not isinstance(review_ids, list)
        or len(review_ids) != 2
        or len(set(review_ids)) != 2
    ):
        raise EvalError("Adjudication requires exactly two distinct review_ids")
    if value.get("qualified_clinician") is not True:
        raise EvalError("Adjudicator must attest qualified_clinician=true")
    if value.get("decision") not in {"ACCEPT", "REVISE", "REJECT"}:
        raise EvalError("Invalid adjudication decision")
    if not isinstance(value.get("resolution"), str) or not value["resolution"].strip():
        raise EvalError("Adjudication resolution is required")


def _import_adjudication(run_directory: Path, source: Path) -> dict[str, Any]:
    manifest = _load_verified_run(run_directory)
    if manifest.get("mode") != "FORMAL":
        raise EvalError("Adjudication can only be imported into a formal run")
    _review_state(run_directory, manifest)
    value = _read_json(source)
    _validate_adjudication(value)
    if value.get("run_id") != manifest["run_id"]:
        raise EvalError("Adjudication run_id does not match")
    job_id = str(value.get("job_id"))
    review_directory = run_directory / "reviews" / job_id
    reviews = {
        item["review_id"]: item
        for item in (_read_json(path) for path in review_directory.glob("*.json"))
    }
    if set(value["review_ids"]) != set(reviews):
        raise EvalError("Adjudication must reference the two imported reviews")
    reviewer_ids = {item["reviewer_id"] for item in reviews.values()}
    if len(reviewer_ids) != 2:
        raise EvalError("Adjudication requires two distinct blinded reviewers")
    destination_directory = run_directory / "adjudications"
    destination_directory.mkdir(parents=True, exist_ok=True)
    destination_directory.chmod(0o700)
    destination = destination_directory / f"{job_id}.json"
    if destination.exists():
        raise EvalError("Adjudication already exists for this job")
    _write_json(destination, value)
    registry = manifest.setdefault("adjudication_artifacts", {})
    if not isinstance(registry, dict):
        raise EvalError("Adjudication integrity registry is malformed")
    registry[job_id] = _sha256_file(destination)
    _write_run_manifest(run_directory, manifest)
    return {
        "status": "IMPORTED",
        "adjudication_id": value["adjudication_id"],
        "job_id": job_id,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="Validate corpus, matrix, runtime availability, and review prerequisites",
    )
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument(
        "--authorize-provider-egress",
        action="store_true",
        help="Explicitly authorize configured runtime providers to receive synthetic inputs",
    )
    parser.add_argument(
        "--corpus-file",
        type=Path,
        help="Repository-external private holdout corpus.json and case bundle",
    )
    parser.add_argument(
        "--gold-dir",
        type=Path,
        help="Repository-external private holdout rubrics; never use public references",
    )
    parser.add_argument(
        "--attest-holdout-isolation",
        "--attest-gold-isolation",
        dest="attest_holdout_isolation",
        action="store_true",
        help=(
            "Attest adapters can read only the copied case bundle, not repository, "
            "private corpus root, or private gold"
        ),
    )
    subparsers = parser.add_subparsers(dest="command")

    dry = subparsers.add_parser("dry-run", help="Exercise artifacts without an Agent")
    dry.add_argument("--output-root", type=Path, required=True)
    dry.add_argument("--repeats", type=int, default=2)

    run = subparsers.add_parser("run", help="Execute a real multi-runtime matrix")
    run.add_argument("--output-root", type=Path, required=True)
    run.add_argument("--resume", type=Path)

    summary = subparsers.add_parser("summary", help="Verify and summarize a run")
    summary.add_argument("--run-dir", type=Path, required=True)

    review = subparsers.add_parser(
        "import-review", help="Import one real blinded clinical review"
    )
    review.add_argument("--run-dir", type=Path, required=True)
    review.add_argument("--file", type=Path, required=True)

    adjudication = subparsers.add_parser(
        "import-adjudication", help="Import adjudication of two reviews"
    )
    adjudication.add_argument("--run-dir", type=Path, required=True)
    adjudication.add_argument("--file", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:  # noqa: PLR0911
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.preflight:
            code, result = _preflight(
                args.matrix.resolve(),
                args.authorize_provider_egress,
                args.corpus_file.resolve() if args.corpus_file is not None else None,
                args.gold_dir.resolve() if args.gold_dir is not None else None,
                args.attest_holdout_isolation,
            )
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return code
        if args.command == "dry-run":
            code, run_directory, result = _run_dry(
                args.output_root.resolve(), args.repeats
            )
            result["run_directory"] = str(run_directory)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return code
        if args.command == "run":
            if args.corpus_file is None:
                raise EvalError("Formal run requires repository-external --corpus-file")
            if args.gold_dir is None:
                raise EvalError("Formal run requires repository-external --gold-dir")
            code, run_directory, result = _run_formal(
                args.matrix.resolve(),
                args.output_root.resolve(),
                args.authorize_provider_egress,
                args.corpus_file.resolve(),
                args.gold_dir.resolve(),
                args.attest_holdout_isolation,
                args.resume,
            )
            result["run_directory"] = str(run_directory)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return code
        if args.command == "summary":
            run_directory = args.run_dir.resolve()
            manifest = _load_verified_run(run_directory)
            result = _formal_summary(run_directory, manifest)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0 if result["status"] == AGENT_EVAL_PASS else 2
        if args.command == "import-review":
            result = _import_review(args.run_dir.resolve(), args.file.resolve())
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0
        if args.command == "import-adjudication":
            result = _import_adjudication(args.run_dir.resolve(), args.file.resolve())
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0
        parser.error("Choose --preflight or a command")
    except EvalError as exc:
        print(
            json.dumps(
                {"status": AGENT_EVAL_NOT_ESTABLISHED, "error": str(exc)},
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
