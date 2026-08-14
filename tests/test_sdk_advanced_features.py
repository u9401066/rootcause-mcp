"""
Unit and Integration Tests for Advanced MCP SDK 2.0 Capabilities:
1. Condensed Facade Profile (8 unified tools reducing tool context size).
2. MCP Static Resources (clinical://protocols/*, clinical://domains/*, clinical://templates/*).
3. MCP Dynamic Session Resource Templates (clinical://sessions/{session_id}/*).
4. MCP Pre-configured Clinical Prompts (anesthesia_mm_investigation, etc.).
5. Server Instructions & Metadata Injection.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from mcp.types import (
    ReadResourceRequestParams,
    TextContent,
    TextResourceContents,
)

from rootcause_mcp.interface.prompts import get_all_prompts, get_prompt_result
from rootcause_mcp.interface.resources import (
    get_resource_templates,
    get_static_resources,
    read_clinical_resource,
)
from rootcause_mcp.interface.tools import get_all_tools
from rootcause_mcp.server_v2 import (
    lifespan,
    on_call_tool,
    on_list_prompts,
    on_list_resource_templates,
    on_list_resources,
    on_list_tools,
    on_read_resource,
    server,
)


def test_condensed_tool_profile_returns_eight_facades() -> None:
    """Condensed profile should return exactly 8 unified facade tools."""
    condensed_tools = get_all_tools("condensed")
    assert len(condensed_tools) == 8

    names = {t.name for t in condensed_tools}
    assert names == {
        "rc_evidence",
        "rc_hypothesis",
        "rc_thinking",
        "rc_audit",
        "rc_report",
        "rc_diagram",
        "rc_checkpoint",
        "rc_rca",
    }


def test_static_resources_enumeration_and_read() -> None:
    """Static resources should list protocols, playbooks, and templates and allow reading."""
    resources = get_static_resources()
    assert len(resources) >= 10

    uris = {r.uri for r in resources}
    assert "clinical://protocols/anesthesia-mm-rca-protocol" in uris
    assert "clinical://protocols/clinical-reasoning-sop" in uris
    assert "clinical://domains/perioperative-shock" in uris
    assert "clinical://templates/anesthesia-mm-rca-report-template" in uris


@pytest.mark.asyncio
async def test_read_static_protocol_resource() -> None:
    """Reading a protocol resource by URI should return YAML content."""
    res = await read_clinical_resource("clinical://protocols/anesthesia-mm-rca-protocol")
    assert len(res.contents) == 1
    content = res.contents[0]
    assert isinstance(content, TextResourceContents)
    assert content.mime_type == "application/yaml"
    assert "4-Tier Backward Reasoning Framework" in content.text


@pytest.mark.asyncio
async def test_read_static_template_resource() -> None:
    """Reading a template resource by URI should return Markdown content."""
    res = await read_clinical_resource("clinical://templates/anesthesia-mm-rca-report-template")
    assert len(res.contents) == 1
    content = res.contents[0]
    assert isinstance(content, TextResourceContents)
    assert content.mime_type == "text/markdown"
    assert "# 🏥 麻醉與圍術期重症事件 4-Tier 根因分析報告" in content.text


def test_resource_templates_enumeration() -> None:
    """Dynamic session resource templates should advertise session URI patterns."""
    templates = get_resource_templates()
    assert len(templates) == 4

    patterns = {t.uri_template for t in templates}
    assert "clinical://sessions/{session_id}/report" in patterns
    assert "clinical://sessions/{session_id}/timeline" in patterns
    assert "clinical://sessions/{session_id}/guidance" in patterns
    assert "clinical://sessions/{session_id}/conflicts" in patterns


def test_clinical_prompts_enumeration_and_generation() -> None:
    """Prompt catalog should advertise clinical prompts and generate messages."""
    prompts = get_all_prompts()
    assert len(prompts) == 4

    names = {p.name for p in prompts}
    assert "anesthesia_mm_investigation" in names
    assert "perioperative_crisis_differential" in names
    assert "near_miss_barrier_analysis" in names
    assert "delayed_diagnosis_investigation" in names

    # Test prompt generation
    res = get_prompt_result(
        "anesthesia_mm_investigation",
        {
            "case_summary": "72yo female arrest post-induction",
            "initial_rhythm": "PEA 35/15",
            "surgery_type": "Right Total Hip Replacement",
        },
    )
    assert len(res.messages) == 1
    msg = res.messages[0]
    assert msg.role == "user"
    assert isinstance(msg.content, TextContent)
    assert "Mandatory 4-Tier Backward Causal Protocol" in msg.content.text
    assert "72yo female arrest post-induction" in msg.content.text


@pytest.mark.asyncio
async def test_server_advanced_mcp_callbacks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Full server instance should handle prompts, resources, and condensed tool dispatch."""
    monkeypatch.setenv("ROOTCAUSE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ROOTCAUSE_TOOL_PROFILE", "condensed")

    async with lifespan(server):
        context: Any = None

        # 1. Test Server Instructions & Metadata
        assert server.title == "RootCause MCP: Clinical Reasoning & Medical RCA Harness"
        assert server.instructions is not None
        assert "5-stage progression" in server.instructions

        # 2. Test Tools Callback (Condensed Profile)
        tools_res = await on_list_tools(context, None)
        assert len(tools_res.tools) == 8

        # 3. Test Resources Callback
        res_list = await on_list_resources(context, None)
        assert len(res_list.resources) >= 10

        templates_list = await on_list_resource_templates(context, None)
        assert len(templates_list.resource_templates) == 4

        # 4. Test Prompts Callback
        prompts_list = await on_list_prompts(context, None)
        assert len(prompts_list.prompts) == 4

        # 5. Test Facade Tool Call: rc_evidence(action='add')
        session_id = "test-facade-session-001"
        from mcp.types import CallToolRequestParams
        call_ev = await on_call_tool(
            context,
            CallToolRequestParams(
                name="rc_evidence",
                arguments={
                    "action": "add",
                    "session_id": session_id,
                    "content": "08:18 CRASH BP 35/15 post-epinephrine",
                    "source_document": "anesthesia.csv",
                    "raw_snippet": "CRASH,35/15",
                },
            ),
        )
        assert call_ev.is_error is not True
        assert call_ev.structured_content is not None
        assert call_ev.structured_content["status"] == "success"

        # 6. Test Facade Tool Call: rc_hypothesis(action='propose')
        call_hyp = await on_call_tool(
            context,
            CallToolRequestParams(
                name="rc_hypothesis",
                arguments={
                    "action": "propose",
                    "session_id": session_id,
                    "diagnosis": "Dynamic LVOT Obstruction (SAM)",
                    "clinical_reasoning": "Inotrope worsening",
                    "prior_probability": 0.35,
                },
            ),
        )
        assert call_hyp.is_error is not True
        assert call_hyp.structured_content is not None
        assert call_hyp.structured_content["status"] == "success"

        # Add 2nd evidence to advance guidance state
        await on_call_tool(
            context,
            CallToolRequestParams(
                name="rc_evidence",
                arguments={
                    "action": "add",
                    "session_id": session_id,
                    "content": "08:20 Emergency TEE Dagger Doppler >80mmHg",
                    "source_document": "tee.txt",
                },
            ),
        )

        # 7. Test Facade Tool Call: rc_audit(action='stage_guidance')
        call_audit = await on_call_tool(
            context,
            CallToolRequestParams(
                name="rc_audit",
                arguments={
                    "action": "stage_guidance",
                    "session_id": session_id,
                },
            ),
        )
        assert call_audit.is_error is not True
        assert "stage" in call_audit.structured_content

        # 8. Test Dynamic Session Resource Reading
        read_dyn = await on_read_resource(
            context,
            ReadResourceRequestParams(
                uri=f"clinical://sessions/{session_id}/guidance"
            ),
        )
        assert len(read_dyn.contents) == 1
        dyn_content = read_dyn.contents[0]
        assert isinstance(dyn_content, TextResourceContents)
        assert "DIFFERENTIAL_EXPANSION" in dyn_content.text

        # 9. Test Facade Tool Call: rc_thinking(action='think', 'reflect', 'gap', 'challenge', 'get_chain')
        call_think = await on_call_tool(
            context,
            CallToolRequestParams(
                name="rc_thinking",
                arguments={
                    "action": "think",
                    "session_id": session_id,
                    "content": "SAM is high probability",
                    "internal_reasoning": "Classic inotrope collapse",
                },
            ),
        )
        assert call_think.is_error is not True

        call_reflect = await on_call_tool(
            context,
            CallToolRequestParams(
                name="rc_thinking",
                arguments={
                    "action": "reflect",
                    "session_id": session_id,
                    "reflection_content": "Reviewed anchoring on light anesthesia",
                    "identified_biases": ["ANCHORING"],
                },
            ),
        )
        assert call_reflect.is_error is not True

        call_gap = await on_call_tool(
            context,
            CallToolRequestParams(
                name="rc_thinking",
                arguments={
                    "action": "gap",
                    "session_id": session_id,
                    "gap_description": "Baseline septal thickness",
                },
            ),
        )
        assert call_gap.is_error is not True

        call_chal = await on_call_tool(
            context,
            CallToolRequestParams(
                name="rc_thinking",
                arguments={
                    "action": "challenge",
                    "session_id": session_id,
                    "assumption": "Epi helps all shock",
                    "challenge_reasoning": "Fatal in SAM",
                },
            ),
        )
        assert call_chal.is_error is not True

        call_chain = await on_call_tool(
            context,
            CallToolRequestParams(
                name="rc_thinking",
                arguments={
                    "action": "get_chain",
                    "session_id": session_id,
                },
            ),
        )
        assert call_chain.is_error is not True

        # 10. Test Facade Tool Call: rc_checkpoint(action='create', 'list', 'restore')
        call_cp_save = await on_call_tool(
            context,
            CallToolRequestParams(
                name="rc_checkpoint",
                arguments={
                    "action": "create",
                    "session_id": session_id,
                    "tag": "facade_checkpoint",
                },
            ),
        )
        assert call_cp_save.is_error is not True
        cp_id = call_cp_save.structured_content["checkpoint_id"]

        call_cp_list = await on_call_tool(
            context,
            CallToolRequestParams(
                name="rc_checkpoint",
                arguments={
                    "action": "list",
                    "session_id": session_id,
                },
            ),
        )
        assert call_cp_list.is_error is not True

        call_cp_restore = await on_call_tool(
            context,
            CallToolRequestParams(
                name="rc_checkpoint",
                arguments={
                    "action": "restore",
                    "session_id": session_id,
                    "checkpoint_id": cp_id,
                },
            ),
        )
        assert call_cp_restore.is_error is not True

        # 11. Test Facade Tool Call: rc_diagram(action='timeline', 'validate', 'reasoning_chain', 'evidence_graph')
        call_diag_tl = await on_call_tool(
            context,
            CallToolRequestParams(
                name="rc_diagram",
                arguments={
                    "action": "timeline",
                    "session_id": session_id,
                    "pattern": "perioperative_sequence",
                },
            ),
        )
        assert call_diag_tl.is_error is not True

        call_diag_val = await on_call_tool(
            context,
            CallToolRequestParams(
                name="rc_diagram",
                arguments={
                    "action": "validate",
                    "mermaid_source": "flowchart TB\n  A --> B",
                },
            ),
        )
        assert call_diag_val.is_error is not True

        call_diag_rc = await on_call_tool(
            context,
            CallToolRequestParams(
                name="rc_diagram",
                arguments={
                    "action": "reasoning_chain",
                    "session_id": session_id,
                },
            ),
        )
        assert call_diag_rc.is_error is not True

        call_diag_eg = await on_call_tool(
            context,
            CallToolRequestParams(
                name="rc_diagram",
                arguments={
                    "action": "evidence_graph",
                    "session_id": session_id,
                },
            ),
        )
        assert call_diag_eg.is_error is not True

        # 12. Test Facade Tool Call: rc_report(action='generate')
        call_rep = await on_call_tool(
            context,
            CallToolRequestParams(
                name="rc_report",
                arguments={
                    "action": "generate",
                    "session_id": session_id,
                    "format": "markdown",
                    "detail_level": "standard",
                },
            ),
        )
        assert call_rep.is_error is not True

        # 13. Test Facade Tool Call: rc_rca(action='session_start', 'fishbone_init', 'fishbone_add_cause', 'why_ask', 'hfacs_suggest')
        rca_sess_id = "rc_sess_facade_rca_01"
        call_rca_start = await on_call_tool(
            context,
            CallToolRequestParams(
                name="rc_rca",
                arguments={
                    "action": "session_start",
                    "case_title": "Near miss syringe swap",
                    "case_type": "near_miss",
                },
            ),
        )
        assert call_rca_start.is_error is not True

        call_fb_init = await on_call_tool(
            context,
            CallToolRequestParams(
                name="rc_rca",
                arguments={
                    "action": "fishbone_init",
                    "session_id": rca_sess_id,
                    "problem_statement": "Syringe swap near miss",
                },
            ),
        )
        assert call_fb_init.is_error is not True

        call_why = await on_call_tool(
            context,
            CallToolRequestParams(
                name="rc_rca",
                arguments={
                    "action": "why_ask",
                    "session_id": rca_sess_id,
                    "initial_problem": "Syringe swap near miss",
                    "answer": "Ampules had similar appearance and color",
                },
            ),
        )
        assert call_why.is_error is not True

        call_hfacs = await on_call_tool(
            context,
            CallToolRequestParams(
                name="rc_rca",
                arguments={
                    "action": "hfacs_suggest",
                    "description": "Similar packaging caused confusion under fatigue",
                },
            ),
        )
        assert call_hfacs.is_error is not True
