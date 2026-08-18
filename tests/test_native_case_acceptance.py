"""Native MCP acceptance test for a complete multi-source clinical/RCA case."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any

import pytest
from mcp.types import CallToolRequestParams, CallToolResult, TextContent

from rootcause_mcp.server_v2 import lifespan, on_call_tool, server


def _text(result: CallToolResult) -> str:
    return "\n".join(
        block.text for block in result.content if isinstance(block, TextContent)
    )


def _structured(result: CallToolResult) -> dict[str, Any]:
    assert isinstance(result.structured_content, dict)
    return result.structured_content


async def _call(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    context: Any = None
    result = await on_call_tool(
        context,
        CallToolRequestParams(name=name, arguments=arguments),
    )
    assert result.is_error is False, _text(result)
    return _structured(result)


def _source_manifest(
    source_files: list[Path],
    document_ids: list[str],
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "patient_key": "acceptance-patient",
        "encounter_key": "acceptance-encounter",
        "default_timezone": "Asia/Taipei",
        "documents": [
            {
                "document_id": document_id,
                "source_uri": source.as_uri(),
                "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "media_type": "text/plain",
                "source_kind": "clinical_note",
                "parser_name": "native-acceptance-fixture",
                "parser_version": "1.0",
                "status": "reviewed",
                "de_identified": True,
            }
            for source, document_id in zip(source_files, document_ids, strict=True)
        ],
    }


async def _add_verified_evidence(
    *,
    session_id: str,
    document: str,
    content: str,
    timestamp: str,
) -> str:
    result = await _call(
        "rc_add_evidence",
        {
            "session_id": session_id,
            "content": content,
            "evidence_type": "OBSERVATION",
            "source_document": document,
            "source_location": "Line 1",
            "raw_snippet": content,
            "extraction_method": "verbatim_quote",
            "event_timestamp": timestamp,
            "clinical_strength": "STRONG",
            "source_reliability": "GRADE_A",
            "auto_verify": True,
        },
    )
    assert result["verified"] is True
    assert result["verification_method"] == "EXACT_SNIPPET_MATCH"
    assert result["match_type"] == "EXACT_SNIPPET_MATCH"
    assert result["matched_lines"] == [1]
    return str(result["evidence_id"])


async def _propose_hypothesis(
    *,
    session_id: str,
    diagnosis: str,
    code: str,
    prior: float,
    must_not_miss: bool = False,
) -> str:
    result = await _call(
        "rc_propose_hypothesis",
        {
            "session_id": session_id,
            "diagnosis": diagnosis,
            "icd10_code": code,
            "prior_probability": prior,
            "must_not_miss": must_not_miss,
            "clinical_reasoning": (
                f"{diagnosis} remains a plausible explanation requiring explicit testing."
            ),
            "differential_diagnoses_considered": [
                {
                    "diagnosis": "Competing mechanism",
                    "reason_rejected": "Not rejected; retained elsewhere in the differential.",
                    "likelihood_if_not_rejected": "moderate",
                }
            ],
            "evidence_supporting": [],
            "uncertainty_factors": ["Confirmatory imaging remains pending"],
            "confidence_rationale": "Prior is a transparent case-fixture estimate.",
            "planned_tests": [
                {
                    "name": f"Definitive test for {diagnosis}",
                    "purpose": "RULE_OUT",
                    "expected_supporting_result": (
                        f"A predefined positive pattern supporting {diagnosis}"
                    ),
                    "expected_refuting_result": (
                        f"A predefined adequate negative pattern refuting {diagnosis}"
                    ),
                    "status": "PLANNED",
                }
            ],
        },
    )
    assert result["must_not_miss"] is must_not_miss
    return str(result["hypothesis_id"])


@pytest.mark.asyncio
async def test_native_multi_source_case_passes_release_gates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exercise public MCP tools from manifest registration through final report."""
    project_root = Path(__file__).resolve().parents[1]
    config_copy = tmp_path / "config"
    shutil.copytree(project_root / "config", config_copy)
    monkeypatch.setenv("ROOTCAUSE_CONFIG_DIR", str(config_copy))
    monkeypatch.setenv("ROOTCAUSE_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("ROOTCAUSE_SOURCE_ROOTS", str(tmp_path))
    monkeypatch.setenv("ROOTCAUSE_TOOL_PROFILE", "all")
    monkeypatch.setenv("ROOTCAUSE_AUTHORIZED_REVIEWERS", "acceptance-reviewer")

    source_contents = [
        "10:00 BP 82/48 after perioperative medication administration.",
        "10:10 Bedside ultrasound showed normal right ventricular size.",
        "10:20 BP improved to 108/64 after a measured fluid bolus.",
    ]
    source_files = [tmp_path / f"record-{index}.txt" for index in range(1, 4)]
    document_ids = [f"SRC-{index:03d}" for index in range(1, 4)]
    for source, content in zip(source_files, source_contents, strict=True):
        source.write_text(f"{content}\n", encoding="utf-8")

    context: Any = None
    async with lifespan(server):
        created_result = await on_call_tool(
            context,
            CallToolRequestParams(
                name="rc_start_session",
                arguments={
                    "case_type": "near_miss",
                    "case_title": "Native multi-source acceptance case",
                    "initial_description": (
                        "De-identified retrospective reasoning and system review."
                    ),
                    "source_manifest": _source_manifest(source_files, document_ids),
                },
            ),
        )
        assert created_result.is_error is False, _text(created_result)
        assert _structured(created_result)["session_id"].startswith("rc_sess_")
        session_match = re.search(r"`(rc_sess_[a-f0-9]+)`", _text(created_result))
        assert session_match is not None
        session_id = session_match.group(1)

        evidence_ids = [
            await _add_verified_evidence(
                session_id=session_id,
                document=document_id,
                content=content,
                timestamp=f"2026-08-17T10:{minute}:00+08:00",
            )
            for document_id, content, minute in zip(
                document_ids,
                source_contents,
                ("00", "10", "20"),
                strict=True,
            )
        ]

        primary_id = await _propose_hypothesis(
            session_id=session_id,
            diagnosis="Relative intravascular volume depletion",
            code="E86.1",
            prior=0.35,
        )
        secondary_id = await _propose_hypothesis(
            session_id=session_id,
            diagnosis="Medication-associated hypotension",
            code="I95.2",
            prior=0.30,
        )
        must_not_miss_id = await _propose_hypothesis(
            session_id=session_id,
            diagnosis="Acute pulmonary embolism",
            code="I26.99",
            prior=0.20,
            must_not_miss=True,
        )

        first_support = await _call(
            "rc_link_evidence_to_hypothesis",
            {
                "session_id": session_id,
                "evidence_id": evidence_ids[0],
                "hypothesis_id": primary_id,
                "likelihood_ratio": 2.0,
                "supports": True,
                "rationale": "Observed hypotension supports a volume-sensitive mechanism.",
            },
        )
        second_support = await _call(
            "rc_link_evidence_to_hypothesis",
            {
                "session_id": session_id,
                "evidence_id": evidence_ids[2],
                "hypothesis_id": primary_id,
                "likelihood_ratio": 3.0,
                "supports": True,
                "rationale": "Measured improvement after fluid supports volume responsiveness.",
            },
        )
        secondary_support = await _call(
            "rc_link_evidence_to_hypothesis",
            {
                "session_id": session_id,
                "evidence_id": evidence_ids[0],
                "hypothesis_id": secondary_id,
                "likelihood_ratio": 1.5,
                "supports": True,
                "rationale": "The documented timing supports medication-associated hypotension.",
            },
        )
        must_not_miss_support = await _call(
            "rc_link_evidence_to_hypothesis",
            {
                "session_id": session_id,
                "evidence_id": evidence_ids[0],
                "hypothesis_id": must_not_miss_id,
                "likelihood_ratio": 1.2,
                "supports": True,
                "rationale": "Acute hypotension initially keeps pulmonary embolism visible.",
            },
        )
        disconfirming = await _call(
            "rc_link_evidence_to_hypothesis",
            {
                "session_id": session_id,
                "evidence_id": evidence_ids[1],
                "hypothesis_id": must_not_miss_id,
                "likelihood_ratio": 0.2,
                "supports": False,
                "rationale": "Normal right ventricular size argues against massive PE.",
            },
        )
        assert first_support["applied_likelihood_ratio"] == 2.0
        assert second_support["applied_likelihood_ratio"] == 3.0
        assert secondary_support["applied_likelihood_ratio"] == 1.5
        assert must_not_miss_support["applied_likelihood_ratio"] == 1.2
        assert disconfirming["applied_likelihood_ratio"] == 0.2
        assert disconfirming["supports"] is False

        await _call(
            "rc_reflect",
            {
                "session_id": session_id,
                "reflection_content": (
                    "Volume responsiveness is informative but does not prove one mechanism."
                ),
                "identified_gaps": ["Definitive embolic imaging was not obtained"],
                "identified_biases": ["Anchoring on medication timing"],
                "alternative_approaches": ["Reassess competing obstructive causes"],
            },
        )

        await _call(
            "rc_init_fishbone",
            {
                "session_id": session_id,
                "problem_statement": "Delayed escalation for perioperative hypotension",
            },
        )
        await _call(
            "rc_add_cause",
            {
                "session_id": session_id,
                "category": "Process",
                "description": "The handoff lacked a mandatory escalation threshold",
                "hfacs_code": "OI-OP",
                "evidence": [evidence_ids[0]],
            },
        )
        why_result = await on_call_tool(
            context,
            CallToolRequestParams(
                name="rc_ask_why",
                arguments={
                    "session_id": session_id,
                    "initial_problem": "Delayed escalation for hypotension",
                    "answer": "No explicit escalation threshold was present",
                    "evidence": [evidence_ids[0]],
                },
            ),
        )
        assert why_result.is_error is False, _text(why_result)
        node_match = re.search(r"\*\*Node ID:\*\* `([^`]+)`", _text(why_result))
        assert node_match is not None
        await _call(
            "rc_mark_root_cause",
            {
                "session_id": session_id,
                "node_id": node_match.group(1),
                "confidence": 0.8,
            },
        )
        causation = await on_call_tool(
            context,
            CallToolRequestParams(
                name="rc_verify_causation",
                arguments={
                    "session_id": session_id,
                    "cause": {
                        "id": node_match.group(1),
                        "description": "No explicit escalation threshold was present",
                        "timestamp": "2026-08-17T09:55:00+08:00",
                        "evidence": [evidence_ids[0]],
                    },
                    "effect": {
                        "description": "Hypotension escalation delayed",
                        "timestamp": "2026-08-17T10:00:00+08:00",
                        "evidence": [evidence_ids[0]],
                    },
                    "verification_level": "comprehensive",
                },
            ),
        )
        assert causation.is_error is False, _text(causation)
        assert "Audit Disposition:** INSUFFICIENT_DATA" in _text(causation)
        assert "does not establish clinical causality" in _text(causation)

        audit = await _call("rc_audit_reasoning_state", {"session_id": session_id})
        conflicts = await _call("rc_detect_conflicts", {"session_id": session_id})
        assert audit["is_ready_for_report"] is True
        assert audit["checklist"]["hypotheses_count"] == 3
        assert audit["checklist"]["must_not_miss_hypotheses_count"] == 1
        assert audit["checklist"]["disconfirming_evidence_tested"] is True
        assert audit["checklist"]["bias_reviewed"] is True
        assert conflicts["critical_count"] == 0
        assert conflicts["high_count"] == 0

        preview = await _call(
            "rc_generate_contract_report",
            {"session_id": session_id, "format": "json", "finalize": False},
        )
        preview_payload = json.loads(preview["content"])
        assert preview_payload["is_finalized"] is False
        assert {
            item["coverage_status"] for item in preview_payload["source_inventory"]
        } == {"reviewed"}

        missing_approval = await on_call_tool(
            context,
            CallToolRequestParams(
                name="rc_generate_contract_report",
                arguments={
                    "session_id": session_id,
                    "format": "json",
                    "finalize": True,
                },
            ),
        )
        assert missing_approval.is_error is True
        assert [
            blocker["code"] for blocker in _structured(missing_approval)["blockers"]
        ] == ["REVIEWER_AUTHORIZED"]

        final_report = await _call(
            "rc_generate_contract_report",
            {
                "session_id": session_id,
                "format": "json",
                "finalize": True,
                "approved_by": "acceptance-reviewer",
            },
        )
        report = json.loads(final_report["content"])

    assert final_report["finalized"] is True
    assert report["is_finalized"] is True
    assert report["approved_by"] == "acceptance-reviewer"
    assert len(report["source_inventory"]) == 3
    assert all(item["evidence_count"] == 1 for item in report["source_inventory"])
    assert all(item["verified_count"] == 1 for item in report["source_inventory"])
    assert {item["document"] for item in report["source_inventory"]} == set(
        document_ids
    )
    assert all(item["sha256"] for item in report["source_inventory"])
    assert all(
        item["source_kind"] == "clinical_note" for item in report["source_inventory"]
    )
    assert len(report["hypotheses"]) == 3
    must_not_miss = next(item for item in report["hypotheses"] if item["must_not_miss"])
    assert must_not_miss["id"] == must_not_miss_id
    assert must_not_miss["contradicting_evidence_ids"] == [evidence_ids[1]]
    assert all(item["source"]["location"] == "Line 1" for item in report["evidence"])
    assert {item["source"]["document_id"] for item in report["evidence"]} == set(
        document_ids
    )
    assert all(item["event_timestamp"] is not None for item in report["evidence"])
    assert [event["time"] for event in report["timeline"]["events"]] == [
        "2026-08-17 10:00:00+08:00",
        "2026-08-17 10:10:00+08:00",
        "2026-08-17 10:20:00+08:00",
    ]
    assert final_report["timeline_events"] == 3
    assert report["fishbone"] is not None
    assert report["why_tree"] is not None
    assert report["root_causes"]
    assert report["root_causes"][0]["causation_result"] == "INSUFFICIENT_DATA"
    assert len(report["causation_verifications"]) == 1
    assert (
        report["causation_verifications"][0]["cause_event"]["id"]
        == report["root_causes"][0]["id"]
    )
    assert report["hfacs_classifications"][0]["hfacs_code"] == "OI-OP"
    assert report["gap_analysis"]["safety_invariants_met"] is True
    assert all(
        check["status"] == "PASS"
        for check in report["conformance_checks"]
        if check["severity"] == "HARD"
    )
    assert (
        next(
            check
            for check in report["conformance_checks"]
            if check["code"] == "FINAL_REPORT_SECTIONS_INCLUDED"
        )["status"]
        == "PASS"
    )
    assert final_report["artifact_sha256"].startswith("sha256:")
