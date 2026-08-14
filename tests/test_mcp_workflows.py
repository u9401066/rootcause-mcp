"""Transport-level workflows through the MCP SDK 2.0 callbacks."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any

import pytest
from mcp.types import CallToolRequestParams, CallToolResult, TextContent

from rootcause_mcp import server_v2
from rootcause_mcp.server_v2 import lifespan, on_call_tool, server


async def _call(name: str, arguments: dict[str, Any]) -> CallToolResult:
    context: Any = None
    result: CallToolResult = await on_call_tool(
        context,
        CallToolRequestParams(name=name, arguments=arguments),
    )
    assert not result.is_error, _text(result)
    return result


def _text(result: CallToolResult) -> str:
    return "\n".join(
        block.text for block in result.content if isinstance(block, TextContent)
    )


def _structured(result: CallToolResult) -> dict[str, Any]:
    assert isinstance(result.structured_content, dict)
    return result.structured_content


def test_structured_results_use_compact_text_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Modern results must not duplicate a large structured payload by default."""
    payload = {
        "status": "success",
        "session_id": "case",
        "total_evidence": 50,
        "evidence": [{"content": "x" * 1000} for _ in range(50)],
    }

    monkeypatch.delenv("ROOTCAUSE_RESPONSE_MODE", raising=False)
    compact_result = server_v2._to_call_tool_result(payload)
    compact = _text(compact_result)
    assert len(compact.encode()) == 174
    assert "x" * 100 not in compact
    assert _structured(compact_result) == payload

    monkeypatch.setenv("ROOTCAUSE_RESPONSE_MODE", "verbose")
    verbose = _text(server_v2._to_call_tool_result(payload))
    assert len(verbose.encode()) == 51743
    assert len(verbose.encode()) > len(compact.encode()) * 50


def _configure_runtime(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_root = Path(__file__).resolve().parents[1]
    config_copy = tmp_path / "config"
    shutil.copytree(project_root / "config", config_copy)
    monkeypatch.setenv("ROOTCAUSE_CONFIG_DIR", str(config_copy))
    monkeypatch.setenv("ROOTCAUSE_DATA_DIR", str(tmp_path / "data"))


@pytest.mark.asyncio
async def test_medical_reasoning_mcp_workflow(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_runtime(monkeypatch, tmp_path)
    session_id = "medical-case-001"

    async with lifespan(server):
        evidence_result = _structured(
            await _call(
                "rc_add_evidence",
                {
                    "session_id": session_id,
                    "content": "Troponin I 2.5 ng/mL",
                    "evidence_type": "LAB_RESULT",
                    "source_document": "lab-report.pdf",
                    "source_location": "page 1",
                    "clinical_strength": "STRONG",
                    "source_reliability": "GRADE_A",
                },
            )
        )
        evidence_id = evidence_result["evidence_id"]

        thinking_result = _structured(
            await _call(
                "rc_think_aloud",
                {
                    "session_id": session_id,
                    "thinking_type": "HYPOTHESIS_CONSIDERED",
                    "content": "Acute MI is a leading diagnosis",
                    "internal_reasoning": (
                        "Chest pain and marked troponin elevation support acute MI."
                    ),
                    "confidence": 0.8,
                    "related_evidence_ids": [evidence_id],
                    "alternatives": [
                        {
                            "alternative": "Pulmonary embolism",
                            "reason_rejected": "No hypoxemia or right-heart strain.",
                        }
                    ],
                    "uncertainty_factors": ["Serial ECG is pending"],
                    "potential_biases": ["Anchoring"],
                },
            )
        )
        assert thinking_result["total_thinking_steps"] == 1

        await _call(
            "rc_reflect",
            {
                "session_id": session_id,
                "reflection_content": "The leading diagnosis still needs serial ECG.",
                "identified_gaps": ["Serial ECG pending"],
                "identified_biases": ["Anchoring"],
            },
        )
        await _call(
            "rc_identify_gaps",
            {
                "session_id": session_id,
                "gap_type": "MISSING_EVIDENCE",
                "gap_description": "No serial ECG result",
                "impact_on_diagnosis": "Limits certainty",
                "suggested_actions": ["Repeat ECG"],
            },
        )
        await _call(
            "rc_challenge_assumption",
            {
                "session_id": session_id,
                "assumption": "Troponin elevation proves acute MI",
                "challenge_reasoning": (
                    "Other myocardial injury mechanisms can elevate troponin."
                ),
            },
        )

        hypothesis_result = _structured(
            await _call(
                "rc_propose_hypothesis",
                {
                    "session_id": session_id,
                    "diagnosis": "Acute myocardial infarction",
                    "icd10_code": "I21.9",
                    "prior_probability": 0.3,
                    "clinical_reasoning": (
                        "Chest pain and troponin elevation support acute MI."
                    ),
                    "differential_diagnoses_considered": [],
                    "evidence_supporting": [evidence_id],
                    "uncertainty_factors": ["Serial ECG pending"],
                    "confidence_rationale": "Typical presentation with one pending test.",
                },
            )
        )
        hypothesis_id = hypothesis_result["hypothesis_id"]

        linked = _structured(
            await _call(
                "rc_link_evidence_to_hypothesis",
                {
                    "session_id": session_id,
                    "evidence_id": evidence_id,
                    "hypothesis_id": hypothesis_id,
                    "likelihood_ratio": 5.0,
                    "supports": True,
                    "rationale": "Marked troponin elevation supports myocardial injury.",
                },
            )
        )
        assert linked["posterior_probability"] > 0.3

        assert (
            _structured(
                await _call(
                    "rc_get_evidence",
                    {"session_id": session_id, "evidence_id": evidence_id},
                )
            )["status"]
            == "success"
        )
        await _call(
            "rc_verify_evidence",
            {
                "session_id": session_id,
                "evidence_id": evidence_id,
                "verified_by": "reviewer-1",
            },
        )
        assert (
            _structured(
                await _call(
                    "rc_get_differential_diagnosis",
                    {"session_id": session_id},
                )
            )["total"]
            == 1
        )
        assert (
            _structured(
                await _call(
                    "rc_get_thinking_chain",
                    {"session_id": session_id},
                )
            )["total_steps"]
            == 4
        )
        assert (
            _structured(
                await _call(
                    "rc_get_reasoning_chain",
                    {"session_id": session_id},
                )
            )["total_steps"]
            == 3
        )
        await _call(
            "rc_export_reasoning_chain",
            {"session_id": session_id, "format": "json"},
        )
        mermaid_export = _structured(
            await _call(
                "rc_export_reasoning_chain",
                {"session_id": session_id, "format": "mermaid"},
            )
        )
        mermaid_path = Path(mermaid_export["output_path"])
        mermaid_content = mermaid_path.read_text(encoding="utf-8")
        assert mermaid_path.suffix == ".md"
        assert mermaid_content.startswith("```mermaid\nflowchart TB")
        assert "S1 --> S2" in mermaid_content
        assert f'E1["Evidence<br/>{evidence_id}"]' in mermaid_content
        assert f'H1["Hypothesis<br/>{hypothesis_id}"]' in mermaid_content
        await _call(
            "rc_export_reasoning_chain",
            {"session_id": session_id, "format": "markdown"},
        )
        unsupported = _structured(
            await _call(
                "rc_export_reasoning_chain",
                {"session_id": session_id, "format": "unsupported"},
            )
        )
        assert unsupported["status"] == "error"
        report = _structured(
            await _call(
                "rc_generate_contract_report",
                {"session_id": session_id, "format": "json", "finalize": True},
            )
        )
        assert report["total_evidence"] == 1
        assert report["total_hypotheses"] == 1


@pytest.mark.asyncio
async def test_legacy_rca_mcp_workflow(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_runtime(monkeypatch, tmp_path)

    async with lifespan(server):
        created = await _call(
            "rc_start_session",
            {
                "case_type": "near_miss",
                "case_title": "Medication dose near miss",
                "initial_description": "A ten-fold dose error was intercepted.",
            },
        )
        assert created.structured_content is not None
        assert created.structured_content["status"] == "success"
        match = re.search(r"`(rc_sess_[a-f0-9]+)`", _text(created))
        assert match is not None
        session_id = match.group(1)

        await _call("rc_get_session", {"session_id": session_id})
        await _call("rc_list_sessions", {"limit": 5})
        await _call(
            "rc_init_fishbone",
            {
                "session_id": session_id,
                "problem_statement": "Ten-fold medication dose error",
            },
        )
        await _call(
            "rc_add_cause",
            {
                "session_id": session_id,
                "category": "Process",
                "description": "No independent double check",
                "evidence": ["Medication administration policy"],
            },
        )
        await _call("rc_get_fishbone", {"session_id": session_id})
        await _call(
            "rc_export_fishbone",
            {"session_id": session_id, "format": "json"},
        )
        await _call(
            "rc_export_fishbone",
            {"session_id": session_id, "format": "markdown"},
        )
        await _call(
            "rc_export_fishbone",
            {"session_id": session_id, "format": "mermaid"},
        )

        await _call(
            "rc_suggest_hfacs",
            {"description": "護理師經驗不足導致計算錯誤", "max_suggestions": 2},
        )
        await _call(
            "rc_suggest_hfacs",
            {"description": "unmapped neutral phrase", "max_suggestions": 2},
        )
        await _call("rc_get_hfacs_framework", {})
        await _call("rc_get_hfacs_framework", {"level": "OI"})
        await _call("rc_get_6m_hfacs_mapping", {"category": "Process"})
        await _call("rc_get_6m_hfacs_mapping", {})
        await _call("rc_list_learned_rules", {})
        await _call("rc_reload_rules", {})
        await _call(
            "rc_confirm_classification",
            {
                "description": "No independent double check",
                "hfacs_code": "OF-OP",
                "reason": "The verification process was absent.",
                "session_id": session_id,
            },
        )
        await _call(
            "rc_list_learned_rules",
            {"hfacs_code": "OF-OP", "min_confidence": 0.1},
        )

        first = await _call(
            "rc_ask_why",
            {
                "session_id": session_id,
                "initial_problem": "Ten-fold medication dose error",
                "answer": "The dose was not independently checked",
                "evidence": ["Medication record"],
            },
        )
        first_match = re.search(r"`(c_[a-f0-9]+)`", _text(first))
        assert first_match is not None
        first_id = first_match.group(1)
        second = await _call(
            "rc_ask_why",
            {
                "session_id": session_id,
                "parent_node_id": first_id,
                "answer": "The policy did not require a double check",
            },
        )
        second_match = re.search(r"`(c_[a-f0-9]+)`", _text(second))
        assert second_match is not None
        second_id = second_match.group(1)

        await _call("rc_get_why_tree", {"session_id": session_id})
        await _call(
            "rc_add_causal_link",
            {
                "session_id": session_id,
                "source_node_id": first_id,
                "target_node_id": second_id,
                "relationship": "contributes_to",
                "strength": 0.7,
            },
        )
        await _call(
            "rc_mark_root_cause",
            {"session_id": session_id, "node_id": second_id, "confidence": 0.8},
        )
        await _call(
            "rc_export_why_tree",
            {"session_id": session_id, "format": "json"},
        )
        await _call(
            "rc_export_why_tree",
            {"session_id": session_id, "format": "markdown"},
        )
        await _call(
            "rc_export_why_tree",
            {"session_id": session_id, "format": "mermaid"},
        )
        await _call(
            "rc_build_teaching_case",
            {
                "session_id": session_id,
                "format": "json",
                "learner_level": "resident",
            },
        )
        await _call(
            "rc_build_teaching_case",
            {
                "session_id": session_id,
                "format": "markdown",
                "learner_level": "medical_student",
            },
        )
        verification = await _call(
            "rc_verify_causation",
            {
                "session_id": session_id,
                "cause": {"description": "No independent double check"},
                "effect": {"description": "Ten-fold medication dose error"},
                "verification_level": "comprehensive",
            },
        )
        assert "VERIFIED_WITH_CAVEATS" in _text(verification)
        await _call("rc_archive_session", {"session_id": session_id})


@pytest.mark.asyncio
async def test_missing_medical_session_responses(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_runtime(monkeypatch, tmp_path)
    missing = "missing-case"

    async with lifespan(server):
        for tool_name, arguments in (
            ("rc_get_evidence", {"session_id": missing, "evidence_id": "EVD-none"}),
            ("rc_get_thinking_chain", {"session_id": missing}),
            ("rc_get_reasoning_chain", {"session_id": missing}),
            ("rc_get_differential_diagnosis", {"session_id": missing}),
            ("rc_generate_contract_report", {"session_id": missing}),
        ):
            response = _structured(await _call(tool_name, arguments))
            assert response["status"] in {"not_found", "success"}
