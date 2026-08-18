"""Focused coverage for unified clinical/RCA contract reports."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from mcp.types import ReadResourceRequestParams, TextResourceContents

from rootcause_mcp import server_v2
from rootcause_mcp.application.server_state import ServerState
from rootcause_mcp.domain.entities.fishbone import Fishbone, FishboneCause
from rootcause_mcp.domain.entities.session import RCASession
from rootcause_mcp.domain.entities.thinking_step import ThinkingStep, ThinkingType
from rootcause_mcp.domain.entities.why_node import WhyChain, WhyNode
from rootcause_mcp.domain.value_objects.case_manifest import (
    CaseInputManifest,
    SourceDocument,
    SourceReviewStatus,
)
from rootcause_mcp.domain.value_objects.enums import (
    CaseType,
    FishboneCategoryType,
    Stage,
)
from rootcause_mcp.domain.value_objects.identifiers import CauseId, SessionId
from rootcause_mcp.domain.value_objects.scores import ConfidenceScore
from rootcause_mcp.infrastructure.persistence.database import Database
from rootcause_mcp.infrastructure.persistence.fishbone_repository import (
    SQLiteFishboneRepository,
)
from rootcause_mcp.infrastructure.persistence.session_repository import (
    SQLiteSessionRepository,
)
from rootcause_mcp.infrastructure.persistence.why_tree_repository import (
    SQLiteWhyTreeRepository,
)
from rootcause_mcp.interface.handlers.contract_handlers import ContractHandlers


@pytest.fixture
async def ready_case(
    tmp_path: Path,
) -> AsyncIterator[tuple[ContractHandlers, str, str, str, str]]:
    database = Database(tmp_path / "contract-rca.db")
    database.create_tables()
    session_repository = SQLiteSessionRepository(database)
    fishbone_repository = SQLiteFishboneRepository(database)
    why_tree_repository = SQLiteWhyTreeRepository(database)

    session = RCASession.create(
        case_type=CaseType.NEAR_MISS,
        case_title="Cross-document perioperative review",
        initial_description="Two records require a unified clinical and systems review.",
        created_by="test-agent",
    )
    session.set_problem("Delayed recognition of postoperative shock")
    session.set_source_manifest(
        CaseInputManifest(
            patient_key="case-patient",
            encounter_key="case-encounter",
            documents=(
                SourceDocument(
                    document_id="record-a.txt",
                    source_uri="host://case/record-a.txt",
                    sha256="a" * 64,
                    media_type="text/plain",
                    source_kind="progress_note",
                    status=SourceReviewStatus.REVIEWED,
                    de_identified=True,
                ),
                SourceDocument(
                    document_id="record-b.txt",
                    source_uri="host://case/record-b.txt",
                    sha256="b" * 64,
                    media_type="text/plain",
                    source_kind="imaging",
                    status=SourceReviewStatus.REVIEWED,
                    de_identified=True,
                ),
            ),
        )
    )
    session_repository.save(session)
    session_id = str(session.id)

    state = ServerState()
    orchestrator = await state.get_or_create_orchestrator(session_id)
    first_evidence = orchestrator.add_evidence(
        content="Postoperative hypotension was documented after transfer.",
        source_document="record-a.txt",
        auto_verify=False,
    )
    second_evidence = orchestrator.add_evidence(
        content="Bedside imaging showed right ventricular strain.",
        source_document="record-b.txt",
        auto_verify=False,
    )
    for evidence in (first_evidence, second_evidence):
        orchestrator.evidence_store[evidence.id.value] = evidence.mark_verified(
            verifier="SYSTEM_PROVENANCE_VERIFIER",
            verification_method="EXACT_SNIPPET_MATCH",
        )

    eligible = orchestrator.propose_hypothesis(
        diagnosis="Pulmonary embolism",
        icd10_code="I26.99",
        prior_probability=0.30,
        rationale="Hypotension and right ventricular strain support embolic shock.",
        planned_tests=[
            {
                "name": "CT pulmonary angiography",
                "purpose": "RULE_OUT",
                "expected_supporting_result": "Acute pulmonary arterial filling defect",
                "expected_refuting_result": "Adequate study without pulmonary arterial filling defect",
                "status": "PLANNED",
            }
        ],
    )
    on_hold = orchestrator.propose_hypothesis(
        diagnosis="Cardiogenic shock",
        icd10_code="R57.0",
        prior_probability=0.90,
        rationale="A competing explanation that remains temporarily suspended.",
    )
    excluded = orchestrator.propose_hypothesis(
        diagnosis="Acute myocardial infarction",
        icd10_code="I21.9",
        prior_probability=0.20,
        rationale="Initially plausible but subsequently excluded by review.",
        must_not_miss=True,
    )
    for evidence in (first_evidence, second_evidence):
        orchestrator.link_evidence_to_hypothesis(
            evidence_id=evidence.id.value,
            hypothesis_id=eligible.id.value,
            likelihood_ratio=1.2,
            supports=True,
            rationale="The cross-document finding supports embolic shock.",
        )
    orchestrator.link_evidence_to_hypothesis(
        evidence_id=first_evidence.id.value,
        hypothesis_id=excluded.id.value,
        likelihood_ratio=1.2,
        supports=True,
        rationale="The acute shock presentation initially supported infarction.",
    )
    orchestrator.link_evidence_to_hypothesis(
        evidence_id=second_evidence.id.value,
        hypothesis_id=excluded.id.value,
        likelihood_ratio=0.5,
        supports=False,
        rationale="The imaging pattern refuted the infarction hypothesis.",
    )
    orchestrator.hypothesis_store[on_hold.id.value] = on_hold.mark_on_hold(
        held_by="test-reviewer",
        reason="Awaiting confirmatory cardiac imaging.",
    )
    orchestrator.exclude_hypothesis(
        excluded.id.value,
        excluded_by="test-reviewer",
        reason="Serial testing did not support acute infarction.",
    )
    orchestrator.thinking_chain.add_step(
        ThinkingStep(
            thinking_type=ThinkingType.UNCERTAINTY_ACKNOWLEDGED,
            content="Confirm embolic burden before final therapeutic attribution.",
            internal_reasoning="The current pattern is coherent but confirmatory imaging remains important.",
            confidence=0.8,
            uncertainty_factors=["Definitive angiographic confirmation pending"],
            potential_biases=["Anchoring on the first abnormal imaging result"],
        )
    )
    guidance = orchestrator.get_guidance()
    assert guidance.is_ready_for_report is True, guidance.model_dump(mode="json")

    fishbone = Fishbone.create(session.id, session.problem_statement)
    fishbone.add_cause_to_category(
        FishboneCategoryType.PROCESS,
        FishboneCause(
            cause_id=CauseId.generate(),
            category=FishboneCategoryType.PROCESS,
            description="Escalation trigger was absent from the handoff process",
            hfacs_code="UA.DM",
            hfacs_confidence=ConfidenceScore(0.8),
            evidence=[first_evidence.id.value],
            confidence=ConfidenceScore(0.85),
            verified=True,
        ),
    )
    fishbone_repository.save(fishbone)

    why_node = WhyNode.create_first_why(
        session_id=session.id,
        initial_problem=session.problem_statement,
        answer="The handoff lacked a mandatory escalation trigger",
    )
    why_node.add_evidence(first_evidence.id.value)
    why_node.mark_as_root_cause(0.9)
    why_tree_repository.save_chain(
        WhyChain(
            session_id=session.id,
            initial_problem=session.problem_statement,
            nodes=[why_node],
        )
    )
    session.update_stage_data(
        Stage.VERIFY,
        {
            "causation_verifications": [
                {
                    "verification_id": "ver_contract_fixture",
                    "audit_scope": "CONSERVATIVE_CAUSATION_AUDIT",
                    "clinical_causality_established": False,
                    "verification_level": "comprehensive",
                    "overall_result": "INSUFFICIENT_DATA",
                    "confidence": {"value": 0.4},
                    "cause_event": {
                        "id": str(why_node.id),
                        "description": why_node.answer,
                        "evidence": [first_evidence.id.value],
                    },
                    "effect_event": {
                        "id": None,
                        "description": session.problem_statement,
                        "evidence": [first_evidence.id.value],
                    },
                }
            ]
        },
    )
    session_repository.save(session)

    handler = ContractHandlers(
        state,
        session_repository=session_repository,
        fishbone_repository=fishbone_repository,
        why_tree_repository=why_tree_repository,
    )
    try:
        yield (
            handler,
            session_id,
            eligible.id.value,
            on_hold.id.value,
            excluded.id.value,
        )
    finally:
        database.close()


@pytest.mark.asyncio
async def test_contract_report_unifies_rca_manifest_and_safe_conclusions(
    monkeypatch: pytest.MonkeyPatch,
    ready_case: tuple[ContractHandlers, str, str, str, str],
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("ROOTCAUSE_DATA_DIR", str(tmp_path / "exports"))
    monkeypatch.setenv("ROOTCAUSE_AUTHORIZED_REVIEWERS", "clinical-reviewer")
    handler, session_id, eligible_id, _, _ = ready_case

    json_result = await handler.handle_generate_contract_report(
        {"session_id": session_id, "format": "json"}
    )
    assert json_result["status"] == "success"
    payload = json.loads(json_result["content"])
    assert payload["rca_session"]["source_document_count"] == 2
    assert payload["fishbone"]["categories"][0]["category"] == "Process"
    assert payload["root_causes"][0]["answer"] == (
        "The handoff lacked a mandatory escalation trigger"
    )
    assert payload["hfacs_classifications"][0]["hfacs_code"] == "UA.DM"
    assert payload["causation_verifications"][0]["overall_result"] == (
        "INSUFFICIENT_DATA"
    )
    assert payload["root_causes"][0]["causation_result"] == "INSUFFICIENT_DATA"
    assert payload["gap_analysis"]["total_conflicts"] == 0
    assert payload["report_readiness"]["is_ready_for_report"] is True
    assert [
        (
            item["document"],
            item["source_kind"],
            item["evidence_count"],
            item["verified_count"],
            item["coverage_status"],
        )
        for item in payload["source_inventory"]
    ] == [
        ("record-a.txt", "progress_note", 1, 1, "reviewed"),
        ("record-b.txt", "imaging", 1, 1, "reviewed"),
    ]
    assert [item["sha256"] for item in payload["source_inventory"]] == [
        "a" * 64,
        "b" * 64,
    ]

    markdown_result = await handler.handle_generate_contract_report(
        {"session_id": session_id, "format": "markdown"}
    )
    markdown = markdown_result["content"]
    assert "Leading recorded hypothesis: **Pulmonary embolism**" in markdown
    assert "Leading recorded hypothesis: **Cardiogenic shock**" not in markdown
    assert "## Registered Source Inventory" in markdown
    assert "## Root Cause Analysis" in markdown
    assert "## Deterministic Conformance Checks" in markdown
    assert "### Conservative Causation Audit" in markdown
    assert "do not establish clinical causality" in markdown
    assert "`PROPOSED`" in markdown
    assert "UA.DM" in markdown
    assert "The handoff lacked a mandatory escalation trigger" in markdown

    custom_markdown_result = await handler.handle_generate_contract_report(
        {
            "session_id": session_id,
            "format": "markdown",
            "template_file": "config/templates/clinical_reasoning_report_template.md",
        }
    )
    custom_markdown = custom_markdown_result["content"]
    assert "Leading Working Diagnosis:** Pulmonary embolism" in custom_markdown
    assert (
        "Critical Must-Not-Miss Emergencies Evaluated:** 1 explicitly marked "
        "high-harm rule-out condition(s)"
    ) in custom_markdown
    assert "## Deterministic Conformance Checks" in custom_markdown

    fhir_result = await handler.handle_generate_contract_report(
        {"session_id": session_id, "format": "fhir"}
    )
    fhir = json.loads(fhir_result["content"])
    assert "issued" not in fhir
    assert [coding["coding"][0]["code"] for coding in fhir["conclusionCode"]] == [
        "I26.99"
    ]
    extension_urls = {extension["url"] for extension in fhir["extension"]}
    assert "urn:rootcause-mcp:StructureDefinition/fishbone-cause" in extension_urls
    assert (
        "urn:rootcause-mcp:StructureDefinition/causation-verification" in extension_urls
    )
    assert "urn:rootcause-mcp:StructureDefinition/why-node" in extension_urls
    assert "urn:rootcause-mcp:StructureDefinition/root-cause" in extension_urls
    assert "urn:rootcause-mcp:StructureDefinition/timeline-event" in extension_urls
    assert (
        "urn:rootcause-mcp:StructureDefinition/hfacs-classification" in extension_urls
    )
    assert "urn:rootcause-mcp:StructureDefinition/conformance-check" in extension_urls
    audit_extension = next(
        extension
        for extension in fhir["extension"]
        if extension["url"]
        == "urn:rootcause-mcp:StructureDefinition/causation-verification"
    )
    audit_values = {
        nested["url"]: next(value for key, value in nested.items() if key != "url")
        for nested in audit_extension["extension"]
    }
    assert audit_values["auditScope"] == "CONSERVATIVE_CAUSATION_AUDIT"
    assert audit_values["clinicalCausalityEstablished"] is False

    finalized = await handler.handle_generate_contract_report(
        {
            "session_id": session_id,
            "format": "json",
            "finalize": True,
            "approved_by": "clinical-reviewer",
        }
    )
    finalized_payload = json.loads(finalized["content"])
    assert finalized["status"] == "success"
    assert finalized_payload["is_finalized"] is True
    assert finalized_payload["approved_by"] == "clinical-reviewer"
    assert finalized_payload["content_hash"]
    assert finalized_payload["conformance_checks"]
    assert all(
        check["status"] == "PASS"
        for check in finalized_payload["conformance_checks"]
        if check["severity"] in {"HARD", "BLOCKER", "ERROR"}
    )

    orchestrator = await handler._state.get_orchestrator(session_id)
    assert orchestrator is not None
    unlisted = orchestrator.add_evidence(
        content="An additional finding came from an undeclared source.",
        source_document="record-c.txt",
        auto_verify=False,
    )
    orchestrator.evidence_store[unlisted.id.value] = unlisted.mark_verified(
        verifier="SYSTEM_PROVENANCE_VERIFIER",
        verification_method="EXACT_SNIPPET_MATCH",
    )
    orchestrator.link_evidence_to_hypothesis(
        evidence_id=unlisted.id.value,
        hypothesis_id=eligible_id,
        likelihood_ratio=1.0,
        supports=True,
        rationale="Neutral linkage retained for source coverage audit.",
    )
    manifest_mismatch = await handler.handle_generate_contract_report(
        {
            "session_id": session_id,
            "format": "json",
            "finalize": True,
            "approved_by": "clinical-reviewer",
        }
    )
    assert {blocker["code"] for blocker in manifest_mismatch["blockers"]} == {
        "EVIDENCE_SOURCES_DECLARED"
    }


@pytest.mark.asyncio
async def test_session_report_resource_uses_unified_read_only_preview(
    monkeypatch: pytest.MonkeyPatch,
    ready_case: tuple[ContractHandlers, str, str, str, str],
    tmp_path: Path,
) -> None:
    handler, session_id, _, _, _ = ready_case
    runtime_root = tmp_path / "resource-runtime"
    monkeypatch.setenv("ROOTCAUSE_DATA_DIR", str(runtime_root))
    monkeypatch.setattr(server_v2._runtime, "server_state", handler._state)
    monkeypatch.setattr(server_v2._runtime, "contract_handlers", handler)

    result = await server_v2.on_read_resource(
        None,  # type: ignore[arg-type]
        ReadResourceRequestParams(uri=f"clinical://sessions/{session_id}/report"),
    )

    assert len(result.contents) == 1
    content = result.contents[0]
    assert isinstance(content, TextResourceContents)
    assert content.mime_type == "text/markdown"
    assert "**Status:** Preliminary" in content.text
    assert "Source manifest: 2 document(s)" in content.text
    assert "### Fishbone (Ishikawa)" in content.text
    assert "### Why Tree and Root Causes" in content.text
    assert "### Conservative Causation Audit" in content.text
    assert "ver_contract_fixture" in content.text
    assert "### HFACS Classifications" in content.text
    assert "UA.DM" in content.text
    assert "### Gap and Conflict Detection" in content.text
    assert "Conflicts: 0 total" in content.text
    assert not (runtime_root / "exports").exists()


@pytest.mark.asyncio
async def test_finalize_is_blocked_without_readiness_manifest_and_approver(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ROOTCAUSE_DATA_DIR", str(tmp_path / "exports"))
    monkeypatch.setenv("ROOTCAUSE_AUTHORIZED_REVIEWERS", "clinical-reviewer")
    state = ServerState()
    orchestrator = await state.get_or_create_orchestrator("legacy-clinical-session")
    orchestrator.add_evidence(
        content="MTP unit #7 was administered without a documented electrolyte check.",
        source_document="unmanifested.txt",
        auto_verify=False,
    )

    preview = await ContractHandlers(state).handle_generate_contract_report(
        {"session_id": "legacy-clinical-session", "format": "json"}
    )
    preview_payload = json.loads(preview["content"])
    assert preview_payload["is_finalized"] is False
    assert preview_payload["source_inventory"][0]["coverage_status"] == (
        "registered_evidence_only"
    )

    result = await ContractHandlers(state).handle_generate_contract_report(
        {
            "session_id": "legacy-clinical-session",
            "format": "json",
            "finalize": True,
        }
    )

    assert result["status"] == "error"
    assert result["finalized"] is False
    assert result["preliminary_available"] is True
    blocker_codes = {blocker["code"] for blocker in result["blockers"]}
    assert {
        "GUIDANCE_READY",
        "NO_UNRESOLVED_SAFETY_CONFLICTS",
        "MULTI_SOURCE_MANIFEST",
        "FISHBONE_PRESENT",
        "WHY_ROOT_PRESENT",
        "DIFFERENTIAL_MINIMUM_UNIQUE",
        "REVIEWER_AUTHORIZED",
    } <= blocker_codes
    assert all(
        blocker["status"] == "FAIL" and blocker["severity"] == "HARD"
        for blocker in result["blockers"]
    )


@pytest.mark.asyncio
async def test_finalize_is_blocked_for_unlisted_reviewer(
    monkeypatch: pytest.MonkeyPatch,
    ready_case: tuple[ContractHandlers, str, str, str, str],
) -> None:
    monkeypatch.setenv("ROOTCAUSE_AUTHORIZED_REVIEWERS", "clinical-reviewer")
    handler, session_id, _, _, _ = ready_case

    result = await handler.handle_generate_contract_report(
        {
            "session_id": session_id,
            "format": "json",
            "finalize": True,
            "approved_by": "unlisted-reviewer",
        }
    )

    assert result["status"] == "error"
    assert result["finalized"] is False
    assert [blocker["code"] for blocker in result["blockers"]] == [
        "REVIEWER_AUTHORIZED"
    ]
    assert (
        next(
            check
            for check in result["conformance_checks"]
            if check["code"] == "REVIEWER_AUTHORIZED"
        )["status"]
        == "FAIL"
    )


@pytest.mark.asyncio
async def test_finalize_requires_causation_audit_for_each_proposed_root(
    monkeypatch: pytest.MonkeyPatch,
    ready_case: tuple[ContractHandlers, str, str, str, str],
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("ROOTCAUSE_DATA_DIR", str(tmp_path / "exports"))
    monkeypatch.setenv("ROOTCAUSE_AUTHORIZED_REVIEWERS", "clinical-reviewer")
    handler, session_id, _, _, _ = ready_case
    assert handler._session_repo is not None
    session = handler._session_repo.get_by_id(session_id)
    assert session is not None
    session.update_stage_data(Stage.VERIFY, {"causation_verifications": []})
    handler._session_repo.save(session)

    result = await handler.handle_generate_contract_report(
        {
            "session_id": session_id,
            "format": "json",
            "finalize": True,
            "approved_by": "clinical-reviewer",
        }
    )

    assert result["status"] == "error"
    assert [blocker["code"] for blocker in result["blockers"]] == [
        "ROOT_CAUSATION_AUDIT_LINEAGE"
    ]


@pytest.mark.asyncio
async def test_finalize_requires_every_manifest_document_to_be_reviewed(
    monkeypatch: pytest.MonkeyPatch,
    ready_case: tuple[ContractHandlers, str, str, str, str],
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("ROOTCAUSE_DATA_DIR", str(tmp_path / "exports"))
    monkeypatch.setenv("ROOTCAUSE_AUTHORIZED_REVIEWERS", "clinical-reviewer")
    handler, session_id, _, _, _ = ready_case
    assert handler._session_repo is not None
    session = handler._session_repo.get_by_id(session_id)
    assert session is not None
    manifest = session.get_source_manifest()
    assert manifest is not None
    documents = list(manifest.documents)
    documents[0] = documents[0].model_copy(
        update={"status": SourceReviewStatus.EXTRACTED}
    )
    session.set_source_manifest(
        manifest.model_copy(update={"documents": tuple(documents)})
    )
    handler._session_repo.save(session)

    result = await handler.handle_generate_contract_report(
        {
            "session_id": session_id,
            "format": "json",
            "finalize": True,
            "approved_by": "clinical-reviewer",
        }
    )

    assert result["status"] == "error"
    assert [blocker["code"] for blocker in result["blockers"]] == [
        "MANIFEST_DOCUMENTS_REVIEWED"
    ]
    assert result["blockers"][0]["refs"] == ["record-a.txt"]


@pytest.mark.parametrize("root_evidence", [[], ["EVD-unknown"]])
@pytest.mark.asyncio
async def test_finalize_requires_root_cause_evidence_lineage(
    monkeypatch: pytest.MonkeyPatch,
    ready_case: tuple[ContractHandlers, str, str, str, str],
    tmp_path: Path,
    root_evidence: list[str],
) -> None:
    monkeypatch.setenv("ROOTCAUSE_DATA_DIR", str(tmp_path / "exports"))
    monkeypatch.setenv("ROOTCAUSE_AUTHORIZED_REVIEWERS", "clinical-reviewer")
    handler, session_id, _, _, _ = ready_case
    assert handler._why_tree_repo is not None
    why_tree = handler._why_tree_repo.get_chain(SessionId.from_string(session_id))
    assert why_tree is not None
    root_cause = why_tree.root_causes[0]
    root_cause.evidence = root_evidence
    handler._why_tree_repo.save_chain(why_tree)

    result = await handler.handle_generate_contract_report(
        {
            "session_id": session_id,
            "format": "json",
            "finalize": True,
            "approved_by": "clinical-reviewer",
        }
    )

    assert result["status"] == "error"
    assert {blocker["code"] for blocker in result["blockers"]} == {
        "ROOT_CAUSATION_AUDIT_LINEAGE",
        "ROOT_EVIDENCE_LINEAGE",
    }
    assert all(str(root_cause.id) in blocker["refs"] for blocker in result["blockers"])


@pytest.mark.asyncio
async def test_custom_template_is_confined_to_allowlisted_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ROOTCAUSE_DATA_DIR", str(tmp_path / "exports"))
    template_root = tmp_path / "config" / "templates"
    template_root.mkdir(parents=True)
    (template_root / "allowed.md").write_text(
        "# Allowed {{session_id}}\n{{executive_summary}}\n",
        encoding="utf-8",
    )
    outside = tmp_path / "outside.md"
    outside.write_text("sensitive", encoding="utf-8")
    (template_root / "escape.md").symlink_to(outside)

    state = ServerState()
    await state.get_or_create_orchestrator("template-security-session")
    handler = ContractHandlers(state, template_root=template_root)

    for attack in ("/etc/passwd", "../outside.md", "escape.md"):
        result = await handler.handle_generate_contract_report(
            {
                "session_id": "template-security-session",
                "format": "markdown",
                "template_file": attack,
            }
        )
        assert result["status"] == "error"

    allowed = await handler.handle_generate_contract_report(
        {
            "session_id": "template-security-session",
            "format": "markdown",
            "template_file": "config/templates/allowed.md",
        }
    )
    assert allowed["status"] == "success"
    assert allowed["content"].startswith("# Allowed template-security-session")
    assert "## Registered Source Inventory" in allowed["content"]
    assert "## Root Cause Analysis" in allowed["content"]
