"""Fail-closed regression tests for the Agent-in-loop evaluation scaffold."""

from __future__ import annotations

import copy
import importlib.util
import json
import shutil
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest


def _load_runner_module() -> ModuleType:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_agent_eval.py"
    spec = importlib.util.spec_from_file_location("agent_eval_test_module", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load Agent eval runner from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runner = _load_runner_module()
REPO_ROOT = Path(__file__).resolve().parents[1]
CORPUS = REPO_ROOT / "evals" / "corpus" / "v1" / "corpus.json"
REFERENCES = REPO_ROOT / "evals" / "reference_rubrics" / "v1"
MATRIX = REPO_ROOT / "evals" / "adapter_matrix.example.json"


def _case_inputs(
    case_id: str = "CASE-001",
) -> tuple[Path, dict[str, Any], dict[str, Any], dict[str, str]]:
    return runner._load_case_inputs(CORPUS, case_id)


def _fixture_candidate(case_id: str = "CASE-001") -> dict[str, Any]:
    _case_directory, _case, manifest, sources = _case_inputs(case_id)
    return runner._fixture_candidate(case_id, manifest, sources)


def _score(**overrides: Any) -> dict[str, Any]:
    value = {
        "fabrication_count": 0,
        "phi_leak_count": 0,
        "causal_overclaim_count": 0,
        "must_not_miss_found": 1,
        "must_not_miss_total": 1,
        "gold_top3_pass": True,
        "workflow_complete": True,
        "lineage_and_certainty_pass": True,
    }
    value.update(overrides)
    return value


def test_corpus_matrix_and_public_reference_integrity() -> None:
    integrity = runner.validate_corpus_and_isolation(CORPUS, REFERENCES)
    matrix = runner.load_matrix(MATRIX)
    jobs = runner._job_specs(matrix)

    assert integrity == {"cases": 6, "sources": 24, "leakage_findings": 0}
    assert len(jobs) == 36
    assert len({job["job_id"] for job in jobs}) == 36
    assert {job["repeat"] for job in jobs} == {1, 2}
    assert {job["case_id"] for job in jobs} == set(runner.CASE_IDS)
    assert all(
        adapter["mcp_wiring"]["trace_parser_status"] == runner.RUNNER_SCAFFOLD
        for adapter in matrix["adapters"]
    )
    assert all(
        adapter["mcp_wiring"]["clinician_ddx_sha256"]
        == runner._sha256_file(
            runner._resolve_repo_file(adapter["mcp_wiring"]["clinician_ddx_source"])
        )
        for adapter in matrix["adapters"]
    )
    assert all(
        "rootcauseMcp" in adapter["mcp_wiring"]["server_aliases"]
        for adapter in matrix["adapters"]
    )


def test_matrix_rejects_missing_or_drifted_clinician_reference(
    tmp_path: Path,
) -> None:
    missing_identity = runner._read_json(MATRIX)
    missing_identity["adapters"][0]["mcp_wiring"].pop("clinician_ddx_source")
    missing_identity_path = tmp_path / "missing-identity.json"
    runner._write_json(missing_identity_path, missing_identity)
    with pytest.raises(runner.EvalError, match="incomplete harness identity"):
        runner.load_matrix(missing_identity_path)

    missing_source = runner._read_json(MATRIX)
    missing_source["adapters"][0]["mcp_wiring"]["clinician_ddx_source"] = (
        ".codex/skills/rootcause-clinical-reasoning-harness/references/missing.md"
    )
    missing_source_path = tmp_path / "missing-source.json"
    runner._write_json(missing_source_path, missing_source)
    with pytest.raises(runner.EvalError, match="Missing evaluation file"):
        runner.load_matrix(missing_source_path)

    drifted = runner._read_json(MATRIX)
    drifted["adapters"][0]["mcp_wiring"]["clinician_ddx_sha256"] = "0" * 64
    drifted_path = tmp_path / "drifted.json"
    runner._write_json(drifted_path, drifted)
    with pytest.raises(runner.EvalError, match="clinician_ddx_source hash drift"):
        runner.load_matrix(drifted_path)


def test_prompts_and_requests_are_answer_free_and_formal_mcp_is_mandatory() -> None:
    for case_id in runner.CASE_IDS:
        _directory, case, manifest, _sources = _case_inputs(case_id)
        formal_prompt = runner.build_agent_prompt(case, formal=True)
        fixture_prompt = runner.build_agent_prompt(case, formal=False)
        request = runner.build_request_metadata(case, manifest, formal_prompt)
        serialized = json.dumps(request, ensure_ascii=False)
        reference = runner._read_json(REFERENCES / f"{case_id}.json")

        assert "MUST use the configured RootCause MCP" in formal_prompt
        assert "prompt-only reasoning" in formal_prompt
        assert "harness/references/case-handoff.md" in formal_prompt
        assert "harness/references/clinician-ddx-discussion-zh-tw.md" in formal_prompt
        assert "harness/case-handoff.md" not in formal_prompt
        assert "no Agent or MCP runtime is invoked" in fixture_prompt
        assert "reference_rubrics" not in serialized
        assert "PRIVATE_HOLDOUT" not in serialized
        assert request["raw_source_files_persisted"] is False
        for term in reference["input_forbidden_terms"]:
            assert not runner._term_present(serialized, term)


def test_public_references_cannot_be_formal_holdout(
    tmp_path: Path,
) -> None:
    with pytest.raises(runner.EvalError, match="outside the public repository"):
        runner.validate_private_holdout(REFERENCES, REFERENCES)

    duplicate = tmp_path / "private-gold"
    duplicate.mkdir(mode=0o700)
    for source in REFERENCES.glob("*.json"):
        destination = duplicate / source.name
        destination.write_bytes(source.read_bytes())
        destination.chmod(0o600)
    duplicate.chmod(0o700)

    with pytest.raises(runner.EvalError, match="cannot be reused"):
        runner.validate_private_holdout(duplicate, REFERENCES)

    for rubric_path in duplicate.glob("*.json"):
        rubric = runner._read_json(rubric_path)
        rubric["rubric_status"] = "PRIVATE_HOLDOUT"
        runner._write_json(rubric_path, rubric)
    with pytest.raises(runner.EvalError, match="public reference answer fingerprint"):
        runner.validate_private_holdout(duplicate, REFERENCES)


def test_public_corpus_cannot_be_formal_holdout(tmp_path: Path) -> None:
    with pytest.raises(runner.EvalError, match="outside the public repository"):
        runner.validate_private_corpus(CORPUS, CORPUS)

    duplicate_root = tmp_path / "private-corpus"
    shutil.copytree(CORPUS.parent, duplicate_root)
    for path in [duplicate_root, *duplicate_root.rglob("*")]:
        path.chmod(0o700 if path.is_dir() else 0o600)

    with pytest.raises(runner.EvalError, match="cannot be reused"):
        runner.validate_private_corpus(duplicate_root / "corpus.json", CORPUS)

    corpus = runner._read_json(duplicate_root / "corpus.json")
    corpus["corpus_status"] = "PRIVATE_HOLDOUT"
    runner._write_json(duplicate_root / "corpus.json", corpus)
    with pytest.raises(runner.EvalError, match="CASE-001 is identical"):
        runner.validate_private_corpus(duplicate_root / "corpus.json", CORPUS)


def test_external_private_corpus_and_gold_pair_can_be_validated_without_path_disclosure(
    tmp_path: Path,
) -> None:
    private_corpus_root = tmp_path / "holdout-corpus"
    private_gold_root = tmp_path / "holdout-gold"
    shutil.copytree(CORPUS.parent, private_corpus_root)
    shutil.copytree(REFERENCES, private_gold_root)

    corpus = runner._read_json(private_corpus_root / "corpus.json")
    corpus["corpus_status"] = "PRIVATE_HOLDOUT"
    runner._write_json(private_corpus_root / "corpus.json", corpus)
    holdout_observations = {
        "CASE-001": "The systolic murmur became more prominent while upright.",
        "CASE-002": "The infusion continued while serial creatine kinase values rose.",
        "CASE-003": "The wide-complex morphology preceded the final bradycardia.",
        "CASE-004": "Mechanical prophylaxis was not documented while medication was held.",
        "CASE-005": "Jugular venous pressure remained elevated after crystalloid administration.",
        "CASE-006": "No acknowledgement task appeared in the next-business-day work queue.",
    }
    holdout_evidence: dict[str, tuple[str, str]] = {}
    for case_id in runner.CASE_IDS:
        case_root = private_corpus_root / "cases" / case_id
        manifest_path = case_root / "manifest.json"
        manifest = runner._read_json(manifest_path)
        first_document = manifest["documents"][0]
        source_path = case_root / first_document["source_uri"]
        observation = holdout_observations[case_id]
        source_path.write_text(
            source_path.read_text(encoding="utf-8")
            + f"\nAdditional observation:\n- {observation}\n",
            encoding="utf-8",
        )
        first_document["sha256"] = runner._sha256_file(source_path)
        runner._write_json(manifest_path, manifest)
        holdout_evidence[case_id] = (first_document["document_id"], observation)
    for rubric_path in private_gold_root.glob("*.json"):
        rubric = runner._read_json(rubric_path)
        rubric["rubric_status"] = "PRIVATE_HOLDOUT"
        document_id, observation = holdout_evidence[rubric["case_id"]]
        rubric["critical_evidence"].append(
            {
                "evidence_key": "CE-HOLDOUT",
                "document_id": document_id,
                "exact_snippet": observation,
                "required": True,
            }
        )
        runner._write_json(rubric_path, rubric)
    for root in (private_corpus_root, private_gold_root):
        for path in [root, *root.rglob("*")]:
            path.chmod(0o700 if path.is_dir() else 0o600)

    corpus_state = runner.validate_private_corpus(
        private_corpus_root / "corpus.json", CORPUS
    )
    gold_state = runner.validate_private_holdout(private_gold_root, REFERENCES)
    pair_state = runner.validate_corpus_and_isolation(
        private_corpus_root / "corpus.json",
        private_gold_root,
        required_corpus_status="PRIVATE_HOLDOUT",
        required_rubric_status="PRIVATE_HOLDOUT",
    )
    _code, preflight = runner._preflight(
        MATRIX,
        True,
        private_corpus_root / "corpus.json",
        private_gold_root,
        True,
    )

    assert corpus_state["repository_external"] is True
    assert gold_state["repository_external"] is True
    assert pair_state["leakage_findings"] == 0
    assert preflight["private_corpus"]["status"] == "PRIVATE_CORPUS_VALIDATED"
    assert preflight["private_gold"]["status"] == "PRIVATE_HOLDOUT_VALIDATED"
    assert preflight["private_pair_integrity"]["status"] == "PRIVATE_PAIR_VALIDATED"
    assert str(tmp_path) not in json.dumps(preflight)


def test_preflight_reports_missing_runtime_trace_isolation_gold_and_reviews(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        runner.shutil,
        "which",
        lambda executable: None if executable == "claude" else f"/bin/{executable}",
    )

    code, result = runner._preflight(MATRIX, False, None, None, False)

    assert code == 2
    assert result["runner_status"] == runner.RUNNER_SCAFFOLD
    assert result["agent_eval_status"] == runner.AGENT_EVAL_NOT_ESTABLISHED
    assert result["formal_matrix_ready"] is False
    assert result["matrix"]["expected_jobs"] == 36
    assert result["reviewers"]["missing_review_records_after_matrix"] == 72
    assert result["public_reference_rubrics"]["formal_eligible"] is False
    blockers = "\n".join(result["blockers"])
    assert "Missing runtime executables: claude" in blockers
    assert "Unverified runtime MCP trace adapters: codex, openclaw, claude" in blockers
    assert "Filesystem isolation is not enforced" in blockers
    assert "External private --corpus-file is required" in blockers
    assert "External private --gold-dir is required" in blockers
    assert "--attest-holdout-isolation is required" in blockers


def test_dry_run_uses_fresh_roots_and_honest_tamper_evident_artifacts(
    tmp_path: Path,
) -> None:
    code, run_directory, result = runner._run_dry(tmp_path, 2)
    manifest = runner._load_verified_run(run_directory)

    assert code == 0
    assert result["status"] == runner.ENGINEERING_DRY_RUN
    assert result["agent_eval_status"] == runner.AGENT_EVAL_NOT_ESTABLISHED
    assert result["private_gold_loaded"] is False
    assert result["public_reference_loaded_for_input_integrity_check"] is True
    assert len(manifest["jobs"]) == 12
    markers = set()
    for job_id in manifest["jobs"]:
        job_directory = run_directory / "jobs" / job_id
        execution = runner._read_json(job_directory / "execution.json")
        artifact_manifest = runner._read_json(job_directory / "artifact_manifest.json")
        markers.add(execution["fresh_data_root_marker"])
        assert execution["runtime_invoked"] is False
        assert execution["reference_rubric_sent_to_adapter"] is False
        assert execution["private_gold_used"] is False
        assert artifact_manifest["raw_source_files_persisted"] is False
        assert artifact_manifest["source_snippets_present"] is True
        assert artifact_manifest["phi_bearing"] is True
        assert (job_directory / "runtime_tool_trace.raw.jsonl").is_file()
        assert not (job_directory / "score.json").exists()
        assert not any(
            path.name.startswith("SRC-") for path in job_directory.rglob("*")
        )
    assert len(markers) == 12

    tampered = run_directory / "jobs" / next(iter(manifest["jobs"])) / "report.md"
    tampered.write_text("tampered\n", encoding="utf-8")
    with pytest.raises(runner.EvalError, match="Artifact hash drift"):
        runner._load_verified_run(run_directory)


def test_threshold_arithmetic_and_matrix_completeness_are_fail_closed() -> None:
    thresholds = runner.load_matrix(MATRIX)["thresholds"]
    perfect = [_score() for _ in range(36)]

    assert (
        runner.aggregate_scores(perfect, 36, thresholds, formal_eligible=True)["status"]
        == runner.AGENT_EVAL_PASS
    )

    three_top3_misses = copy.deepcopy(perfect)
    for score in three_top3_misses[:3]:
        score["gold_top3_pass"] = False
    result = runner.aggregate_scores(
        three_top3_misses, 36, thresholds, formal_eligible=True
    )
    assert result["metrics"]["gold_top3_rate"] == pytest.approx(33 / 36)
    assert result["threshold_results"]["gold_top3"] is True

    four_top3_misses = copy.deepcopy(perfect)
    for score in four_top3_misses[:4]:
        score["gold_top3_pass"] = False
    assert (
        runner.aggregate_scores(four_top3_misses, 36, thresholds, formal_eligible=True)[
            "status"
        ]
        == runner.AGENT_EVAL_FAIL
    )

    one_completion_miss = copy.deepcopy(perfect)
    one_completion_miss[0]["workflow_complete"] = False
    assert (
        runner.aggregate_scores(
            one_completion_miss, 36, thresholds, formal_eligible=True
        )["threshold_results"]["completion"]
        is True
    )

    two_completion_misses = copy.deepcopy(perfect)
    for score in two_completion_misses[:2]:
        score["workflow_complete"] = False
    assert (
        runner.aggregate_scores(
            two_completion_misses, 36, thresholds, formal_eligible=True
        )["threshold_results"]["completion"]
        is False
    )

    one_mnm_miss = copy.deepcopy(perfect)
    one_mnm_miss[0]["must_not_miss_found"] = 0
    assert (
        runner.aggregate_scores(one_mnm_miss, 36, thresholds, formal_eligible=True)[
            "status"
        ]
        == runner.AGENT_EVAL_FAIL
    )

    one_fabrication = copy.deepcopy(perfect)
    one_fabrication[0]["fabrication_count"] = 1
    assert (
        runner.aggregate_scores(one_fabrication, 36, thresholds, formal_eligible=True)[
            "status"
        ]
        == runner.AGENT_EVAL_FAIL
    )

    assert (
        runner.aggregate_scores(perfect[:35], 36, thresholds, formal_eligible=True)[
            "status"
        ]
        == runner.AGENT_EVAL_NOT_ESTABLISHED
    )
    assert (
        runner.aggregate_scores(perfect, 36, thresholds, formal_eligible=False)[
            "status"
        ]
        == runner.AGENT_EVAL_NOT_ESTABLISHED
    )


def test_draft_2020_12_validation_rejects_extra_fields_bad_time_and_bad_ranks() -> None:
    candidate = _fixture_candidate()
    assert runner._validate_candidate_shape(candidate, "CASE-001") == []

    extra = copy.deepcopy(candidate)
    extra["unexpected"] = True
    assert any(
        "Additional properties" in item
        for item in runner._validate_candidate_shape(extra, "CASE-001")
    )

    bad_time = copy.deepcopy(candidate)
    bad_time["evidence_ledger"][0]["event_timestamp"] = "yesterday"
    assert any(
        "date-time" in item
        for item in runner._validate_candidate_shape(bad_time, "CASE-001")
    )

    missing_time = copy.deepcopy(candidate)
    del missing_time["evidence_ledger"][0]["event_timestamp"]
    assert any(
        "required property" in item
        for item in runner._validate_candidate_shape(missing_time, "CASE-001")
    )

    duplicate_rank = copy.deepcopy(candidate)
    duplicate_rank["differential"][1]["rank"] = 1
    assert (
        "differential ranks must be unique and consecutive from 1"
        in runner._validate_candidate_shape(duplicate_rank, "CASE-001")
    )


def test_runtime_trace_is_trusted_only_for_a_verified_protocol_and_one_session() -> (
    None
):
    adapter = copy.deepcopy(runner.load_matrix(MATRIX)["adapters"][0])
    tool_names = (
        "rc_start_session",
        "rc_adjudicate_source",
        "rc_add_evidence",
        "rc_propose_hypothesis",
        "rc_audit_differential_breadth",
        "rc_select_leading_hypothesis",
        "rc_audit_reasoning_state",
        "rc_init_fishbone",
        "rc_confirm_classification",
        "rc_generate_contract_report",
    )
    raw_trace = "".join(
        json.dumps(
            {
                "type": "tool_call",
                "tool_name": f"mcp__rootcause-mcp__{tool_name}",
                "arguments": {"session_id": "session-a"},
            }
        )
        + "\n"
        for tool_name in tool_names
    )

    scaffold_trace = runner.extract_trusted_runtime_trace(raw_trace, adapter)
    assert scaffold_trace["required_tool_groups_pass"] is True
    assert scaffold_trace["mcp_workflow_verified"] is False

    adapter["mcp_wiring"]["trace_parser_status"] = "VERIFIED_PROTOCOL"
    trusted_trace = runner.extract_trusted_runtime_trace(raw_trace, adapter)
    assert trusted_trace["mcp_workflow_verified"] is True
    assert trusted_trace["session_ids"] == ["session-a"]

    second_session = raw_trace + json.dumps(
        {
            "type": "tool_call",
            "tool_name": "mcp__rootcause-mcp__rc_add_evidence",
            "arguments": {"session_id": "session-b"},
        }
    )
    assert (
        runner.extract_trusted_runtime_trace(second_session, adapter)[
            "mcp_workflow_verified"
        ]
        is False
    )


def test_candidate_self_reported_tools_cannot_satisfy_mcp_completion_or_trigger_date_phi() -> (
    None
):
    _directory, _case, manifest, sources = _case_inputs()
    candidate = _fixture_candidate()
    gold = runner._read_json(REFERENCES / "CASE-001.json")
    candidate["evidence_ledger"] = [
        {
            "evidence_id": f"EV-{index:03d}",
            "document_id": evidence["document_id"],
            "raw_snippet": evidence["exact_snippet"],
            "source_location": f"critical evidence {index}",
            "event_timestamp": "2025-01-14T08:16:00Z" if index == 1 else None,
            "certainty_label": "VERIFIED_OBSERVATION",
        }
        for index, evidence in enumerate(gold["critical_evidence"], 1)
    ]
    for diagnosis in candidate["differential"]:
        diagnosis["evidence_ids"] = ["EV-001"]
    candidate["root_cause_analysis"].update(
        {
            "fishbone_status": "COMPLETE",
            "why_status": "COMPLETE",
            "hfacs_status": "COMPLETE",
            "causation_status": "INSUFFICIENT_DATA",
            "proposed_roots": [
                {
                    "root_id": "ROOT-001",
                    "statement": "An outdated echocardiogram was not reassessed",
                    "certainty_label": "PROPOSED",
                    "evidence_ids": ["EV-001", "EV-002", "EV-003", "EV-004"],
                }
            ],
        }
    )
    candidate["readiness"].update(
        {"conflicts_checked": True, "readiness_checked": True}
    )
    candidate["tool_trace"] = [
        {"sequence": index, "tool_name": name}
        for index, name in enumerate(
            (
                "rc_start_session",
                "rc_add_evidence",
                "rc_propose_hypothesis",
                "rc_audit_reasoning_state",
                "rc_init_fishbone",
                "rc_generate_contract_report",
            ),
            1,
        )
    ]
    untrusted_score = runner.grade_candidate(
        candidate,
        gold,
        manifest,
        sources,
        {"mcp_workflow_verified": False, "server_ids": [], "session_ids": []},
    )
    trusted_score = runner.grade_candidate(
        candidate,
        gold,
        manifest,
        sources,
        {
            "mcp_workflow_verified": True,
            "server_ids": ["rootcause-mcp"],
            "session_ids": ["session-a"],
        },
    )

    assert untrusted_score["workflow_complete"] is False
    assert untrusted_score["trusted_mcp_workflow_verified"] is False
    assert trusted_score["workflow_complete"] is True
    assert trusted_score["phi_leak_count"] == 0


def test_adapter_workspace_contains_no_gold_or_repository_bundle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case_directory, case, manifest, sources = _case_inputs()
    candidate = runner._fixture_candidate("CASE-001", manifest, sources)
    adapter = copy.deepcopy(runner.load_matrix(MATRIX)["adapters"][0])
    adapter["command"] = ["synthetic-adapter"]
    adapter["candidate_transport"] = "stdout"
    adapter["trace_transport"] = "unverified"
    seen: dict[str, Any] = {}

    def fake_run(command: list[str], **kwargs: Any) -> SimpleNamespace:
        workspace = Path(kwargs["cwd"])
        relative_files = {
            path.relative_to(workspace).as_posix()
            for path in workspace.rglob("*")
            if path.is_file()
        }
        seen["files"] = relative_files
        seen["harness_hashes"] = {
            relative: runner._sha256_file(workspace / relative)
            for relative in (
                "harness/SKILL.md",
                "harness/references/case-handoff.md",
                "harness/references/clinician-ddx-discussion-zh-tw.md",
            )
        }
        seen["environment"] = kwargs["env"]
        seen["command"] = command
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(candidate),
            stderr="",
        )

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    prompt = runner.build_agent_prompt(case, formal=True)
    result = runner._invoke_adapter(
        adapter, case_directory, case, prompt, "codex--CASE-001--r1"
    )

    assert result[-1]["mcp_workflow_verified"] is False
    assert seen["files"]
    assert {
        "harness/SKILL.md",
        "harness/references/case-handoff.md",
        "harness/references/clinician-ddx-discussion-zh-tw.md",
    } <= seen["files"]
    assert seen["harness_hashes"] == {
        "harness/SKILL.md": adapter["mcp_wiring"]["harness_sha256"],
        "harness/references/case-handoff.md": adapter["mcp_wiring"]["handoff_sha256"],
        "harness/references/clinician-ddx-discussion-zh-tw.md": adapter["mcp_wiring"][
            "clinician_ddx_sha256"
        ],
    }
    assert all(
        relative == "agent_output.schema.json"
        or relative.startswith(("case/", "harness/"))
        for relative in seen["files"]
    )
    invocation = json.dumps(
        {"command": seen["command"], "environment": seen["environment"]},
        ensure_ascii=False,
    )
    assert "reference_rubrics" not in invocation
    assert "PRIVATE_HOLDOUT" not in invocation


def _create_formal_review_run(tmp_path: Path) -> tuple[Path, str, dict[str, Any]]:
    run_id, run_directory = runner._new_run_directory(tmp_path, "review-test")
    job_id = "codex--CASE-001--r1"
    candidate = _fixture_candidate()
    job_directory = run_directory / "jobs" / job_id
    runner._private_directory(job_directory)
    artifact_hash = runner._write_job_artifacts(
        job_directory,
        request_record={"case_id": "CASE-001", "prompt": "formal"},
        candidate=candidate,
        stdout=json.dumps(candidate),
        stderr="",
        execution={"runtime_invoked": True},
        raw_runtime_trace="",
        trusted_runtime_trace={"mcp_workflow_verified": False},
        score=_score(),
    )
    manifest = {
        "schema_version": "rootcause-agent-eval-run/1",
        "run_id": run_id,
        "mode": "FORMAL",
        "status": runner.AGENT_EVAL_NOT_ESTABLISHED,
        "expected_jobs": 1,
        "thresholds": runner.load_matrix(MATRIX)["thresholds"],
        "jobs": {
            job_id: {
                "job_id": job_id,
                "case_id": "CASE-001",
                "status": "COMPLETE",
                "artifact_manifest_sha256": artifact_hash,
            }
        },
    }
    runner._write_run_manifest(run_directory, manifest)
    return run_directory, job_id, manifest


def _review(
    run_directory: Path,
    manifest: dict[str, Any],
    job_id: str,
    sequence: int,
    decision: str,
) -> dict[str, Any]:
    return {
        "schema_version": "rootcause-clinical-review/1",
        "review_id": f"review-{sequence}",
        "run_id": manifest["run_id"],
        "job_id": job_id,
        "reviewer_id": f"clinician-{sequence}",
        "reviewer_role": "Attending physician",
        "reviewed_artifact_sha256": runner._sha256_file(
            run_directory / "jobs" / job_id / "report.json"
        ),
        "attestation": {
            "qualified_clinician": True,
            "blinded_to_gold": True,
            "blinded_to_other_review": True,
            "no_conflict_of_interest": True,
        },
        "ratings": {
            "clinical_plausibility": 4,
            "ddx_completeness": 4,
            "must_not_miss_safety": "PASS",
            "evidence_fidelity": "PASS",
            "causal_calibration": "PASS",
        },
        "decision": decision,
        "concerns": [] if decision == "ACCEPT" else ["Needs adjudication"],
        "reviewed_at": "2026-08-17T12:00:00Z",
    }


def test_review_and_adjudication_imports_are_schema_validated_and_tamper_evident(
    tmp_path: Path,
) -> None:
    run_directory, job_id, manifest = _create_formal_review_run(tmp_path)
    review_one = _review(run_directory, manifest, job_id, 1, "ACCEPT")
    review_two = _review(run_directory, manifest, job_id, 2, "REVISE")
    source_one = tmp_path / "review-one.json"
    source_two = tmp_path / "review-two.json"
    runner._write_json(source_one, review_one)
    runner._write_json(source_two, review_two)

    runner._import_review(run_directory, source_one)
    runner._import_review(run_directory, source_two)
    registered = runner._load_verified_run(run_directory)
    review_state = runner._review_state(run_directory, registered)
    assert review_state["status"] == runner.AGENT_EVAL_NOT_ESTABLISHED

    adjudication = {
        "schema_version": "rootcause-clinical-adjudication/1",
        "adjudication_id": "adjudication-1",
        "run_id": manifest["run_id"],
        "job_id": job_id,
        "review_ids": ["review-1", "review-2"],
        "adjudicator_id": "clinician-3",
        "adjudicator_role": "Clinical quality chair",
        "qualified_clinician": True,
        "disagreements": ["Whether revision is necessary"],
        "resolution": "The output is acceptable with the recorded limitation.",
        "decision": "ACCEPT",
        "adjudicated_at": "2026-08-17T13:00:00Z",
    }
    adjudication_source = tmp_path / "adjudication.json"
    runner._write_json(adjudication_source, adjudication)
    runner._import_adjudication(run_directory, adjudication_source)

    registered = runner._load_verified_run(run_directory)
    assert (
        runner._review_state(run_directory, registered)["status"]
        == runner.AGENT_EVAL_PASS
    )

    persisted_review = run_directory / "reviews" / job_id / "review-1.json"
    tampered_review = runner._read_json(persisted_review)
    tampered_review["concerns"] = ["changed after import"]
    runner._write_json(persisted_review, tampered_review)
    with pytest.raises(runner.EvalError, match="integrity check failed"):
        runner._review_state(run_directory, registered)


def test_handwritten_reviews_without_cli_registry_are_rejected(tmp_path: Path) -> None:
    run_directory, job_id, manifest = _create_formal_review_run(tmp_path)
    review_directory = run_directory / "reviews" / job_id
    review_directory.mkdir(parents=True)
    for sequence in (1, 2):
        runner._write_json(
            review_directory / f"review-{sequence}.json",
            _review(run_directory, manifest, job_id, sequence, "ACCEPT"),
        )

    with pytest.raises(runner.EvalError, match="integrity check failed"):
        runner._review_state(run_directory, manifest)
