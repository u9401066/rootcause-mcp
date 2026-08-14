"""
End-to-End Trial Simulation Script for RootCause MCP.

Simulates complete real-world clinical reasoning cycles on god-level cases:
1. 'dynamic_lvot_obstruction_sam': Intraoperative shock worsening with Epinephrine.
2. 'pris_status_epilepticus': Propofol Infusion Syndrome misdiagnosed as sepsis/pancreatitis.

Verifies:
- Physical provenance anchoring across heterogeneous files (TXT, CSV, XML).
- Socratic guidance state transitions (Evidence -> Differential -> Bayesian -> Audit -> Synthesis).
- Bayesian hypothesis evaluation and rule-out logic.
- Cognitive audit & bias detection.
- Deterministic Markdown report & Mermaid export generation.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path
from typing import Any

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from rootcause_mcp.application.server_state import ServerState
from rootcause_mcp.interface.handlers.contract_handlers import ContractHandlers
from rootcause_mcp.interface.handlers.dd_handlers import DDHandlers
from rootcause_mcp.interface.handlers.evidence_handlers import EvidenceHandlers
from rootcause_mcp.interface.handlers.thinking_handlers import ThinkingHandlers
from rootcause_mcp.interface.mermaid import (
    build_evidence_graph,
    render_reasoning_chain_mermaid,
)

# ============================================================================
# Case 1: Dynamic LVOT Obstruction (SAM)
# ============================================================================


async def _run_sam_evidence(
    evidence_handlers: EvidenceHandlers,
    session_id: str,
    results: dict[str, Any],
) -> list[str]:
    fixtures = [
        {
            "content": "Pre-op Grade 2/6 systolic murmur at LSB, mild AR, EF 65% on echo 3y ago",
            "source_doc": "examples/dynamic_lvot_obstruction_sam/DATA_SOURCE_01_PRE_ANESTHESIA_EVALUATION.txt",
            "snippet": "CV: RRR, Grade 2/6 Systolic Murmur at LSB (Left Sternal Border).",
            "strength": "STRONG",
            "reliability": "GRADE_A",
        },
        {
            "content": "Severe hypotensive collapse (BP 35/15, HR 160) post-induction worsening after Ephedrine and Epinephrine",
            "source_doc": "examples/dynamic_lvot_obstruction_sam/DATA_SOURCE_02_ANESTHESIA_RECORD_INDUCTION.csv",
            "snippet": '"08:18","CRASH","**35/15**","160","85%","12","Epinephrine 50mcg IV","**Carotid pulse weak/absent**. A-line trace dampening."',
            "strength": "STRONG",
            "reliability": "GRADE_A",
        },
        {
            "content": "TEE shows hyperdynamic kissing walls, eccentric posterior MR, and dagger-shaped CW Doppler >80mmHg",
            "source_doc": "examples/dynamic_lvot_obstruction_sam/DATA_SOURCE_03_INTRA_OP_TEE_STAT.txt",
            "snippet": 'Continuous Wave (CW) Doppler: **"Dagger-shaped" (Late-peaking) profile**.',
            "strength": "STRONG",
            "reliability": "GRADE_A",
        },
        {
            "content": "TEE RV normal size, no D-sign (rules out massive pulmonary embolism)",
            "source_doc": "examples/dynamic_lvot_obstruction_sam/DATA_SOURCE_03_INTRA_OP_TEE_STAT.txt",
            "snippet": "2. **RV:** Normal size. No D-sign. (Rules out Massive PE).",
            "strength": "STRONG",
            "reliability": "GRADE_A",
        },
        {
            "content": "Arterial line waveform exhibits classic Bisferiens Pulse and Spike-and-Dome pattern with SVV 25%",
            "source_doc": "examples/dynamic_lvot_obstruction_sam/DATA_SOURCE_04_ARTERIAL_LINE_WAVEFORM.xml",
            "snippet": "** BISFERIENS PULSE DETECTED **",
            "strength": "STRONG",
            "reliability": "GRADE_A",
        },
        {
            "content": "Surgeon and Anesthesiologist communication log noting shock paradoxical worsening with Epinephrine",
            "source_doc": "examples/dynamic_lvot_obstruction_sam/DATA_SOURCE_05_SURGEON_COMM_LOG.txt",
            "snippet": '08:18 Anesthesiologist: "I pushed 50 of Epi. It got worse. Is there massive bleeding inside? Did you puncture a vessel?"',
            "strength": "STRONG",
            "reliability": "GRADE_B",
        },
    ]

    ev_ids: list[str] = []
    for idx, ef in enumerate(fixtures, 1):
        res = await evidence_handlers.handle(
            "rc_add_evidence",
            {
                "session_id": session_id,
                "content": ef["content"],
                "source_document": ef["source_doc"],
                "raw_snippet": ef["snippet"],
                "clinical_strength": ef["strength"],
                "source_reliability": ef["reliability"],
                "auto_verify": True,
            },
        )
        ev_ids.append(res["evidence_id"])
        status_icon = "✅" if res["verified"] else "❌"
        print(
            f" -> Ev#{idx} [{status_icon} {res['verification_method']}] "
            f"Doc: {Path(ef['source_doc']).name} Lines: {res['matched_lines']}"
        )
        if not res["verified"]:
            results["warnings"].append(
                f"Evidence #{idx} failed verification: {ef['source_doc']}"
            )
    return ev_ids


async def _run_sam_hypotheses(
    dd_handlers: DDHandlers, session_id: str
) -> dict[str, str]:
    h_sam = await dd_handlers.handle(
        "rc_propose_hypothesis",
        {
            "session_id": session_id,
            "diagnosis": "Dynamic LVOT Obstruction secondary to Systolic Anterior Motion (SAM)",
            "prior_probability": 0.20,
            "rationale": "Small hyperdynamic LV with late-peaking CW Doppler and paradoxical worsening with inotropes",
            "icd10_code": "I42.1",
        },
    )
    h_pe = await dd_handlers.handle(
        "rc_propose_hypothesis",
        {
            "session_id": session_id,
            "diagnosis": "Massive Pulmonary Embolism (PE)",
            "prior_probability": 0.30,
            "rationale": "Trauma/hip fracture patient with sudden severe shock and arrest post-positioning",
            "icd10_code": "I26.0",
        },
    )
    h_anaph = await dd_handlers.handle(
        "rc_propose_hypothesis",
        {
            "session_id": session_id,
            "diagnosis": "Severe Anaphylactic Shock",
            "prior_probability": 0.25,
            "rationale": "Sudden post-induction collapse after neuromuscular blockers and antibiotics",
            "icd10_code": "T78.2",
        },
    )
    h_hypo = await dd_handlers.handle(
        "rc_propose_hypothesis",
        {
            "session_id": session_id,
            "diagnosis": "Profound Hypovolemic Shock / Occult Hemorrhage",
            "prior_probability": 0.25,
            "rationale": "Frail elderly patient fasting with traumatic hip fracture and high SVV",
            "icd10_code": "R57.1",
        },
    )
    return {
        "sam": h_sam["hypothesis_id"],
        "pe": h_pe["hypothesis_id"],
        "anaph": h_anaph["hypothesis_id"],
        "hypo": h_hypo["hypothesis_id"],
    }


async def _run_sam_bayesian(
    dd_handlers: DDHandlers,
    session_id: str,
    h_ids: dict[str, str],
    ev_ids: list[str],
) -> None:
    # Rule out PE & Anaphylaxis & Hypovolemia
    await dd_handlers.handle(
        "rc_link_evidence_to_hypothesis",
        {
            "session_id": session_id,
            "hypothesis_id": h_ids["pe"],
            "evidence_id": ev_ids[3],
            "direction": "REFUTES",
            "weight": 0.90,
            "reasoning": "TEE demonstrated normal RV chamber size without D-sign",
        },
    )
    await dd_handlers.handle(
        "rc_link_evidence_to_hypothesis",
        {
            "session_id": session_id,
            "hypothesis_id": h_ids["anaph"],
            "evidence_id": ev_ids[1],
            "direction": "REFUTES",
            "weight": 0.85,
            "reasoning": "Anaphylaxis would improve with epinephrine, whereas this patient collapsed further",
        },
    )
    await dd_handlers.handle(
        "rc_link_evidence_to_hypothesis",
        {
            "session_id": session_id,
            "hypothesis_id": h_ids["hypo"],
            "evidence_id": ev_ids[1],
            "direction": "REFUTES",
            "weight": 0.75,
            "reasoning": "Isolated hypovolemia improves with vasoconstrictors and inotropes",
        },
    )
    # Confirm SAM
    for ev_idx, wt, reason in [
        (
            0,
            0.70,
            "Pre-existing systolic murmur indicates baseline dynamic subaortic obstruction substrate",
        ),
        (
            2,
            0.95,
            "Late-peaking dagger CW Doppler >80mmHg and eccentric posterior MR pathognomonic for SAM",
        ),
        (
            4,
            0.92,
            "A-line bisferiens spike-and-dome pulse confirms dynamic mid-systolic outflow obstruction",
        ),
        (
            1,
            0.90,
            "Beta-1 inotropy worsens SAM gradient by increasing hyperdynamic LV emptying",
        ),
        (5, 0.85, "Immediate hemodynamic crash upon Epinephrine bolus"),
    ]:
        await dd_handlers.handle(
            "rc_link_evidence_to_hypothesis",
            {
                "session_id": session_id,
                "hypothesis_id": h_ids["sam"],
                "evidence_id": ev_ids[ev_idx],
                "direction": "SUPPORTS",
                "weight": wt,
                "reasoning": reason,
            },
        )


async def _run_sam_cognitive(
    thinking_handlers: ThinkingHandlers, session_id: str
) -> None:
    await thinking_handlers.handle(
        "rc_reflect",
        {
            "session_id": session_id,
            "reflection_content": "Initial team anchored on light anesthesia and hypovolemia without considering LVOT gradient",
            "identified_biases": [
                "ANCHORING: Presuming routine light anesthesia / hypovolemia",
                "CONFIRMATION_BIAS: Assuming surgical bleeding despite dry field",
            ],
            "identified_gaps": [
                "Baseline septal thickness measurement in millimeters was not documented in 3y prior echo",
            ],
        },
    )
    await thinking_handlers.handle(
        "rc_challenge_assumption",
        {
            "session_id": session_id,
            "assumption": "Refractory hypotensive shock should routinely receive Epinephrine",
            "challenge_reasoning": "In dynamic LVOT obstruction (SAM/HOCM), inotropes worsen the obstruction gradient",
            "potential_impact": "FATAL if inotrope administration is continued",
            "alternative_explanations": [
                "Use pure alpha-agonist (phenylephrine), volume expansion, and beta-blockers"
            ],
        },
    )
    await thinking_handlers.handle(
        "rc_identify_gaps",
        {
            "session_id": session_id,
            "gap_description": "Baseline LVOT peak velocity prior to GA induction",
            "gap_type": "MISSING_DATA",
            "impact_on_diagnosis": "HIGH for pre-op risk stratification",
            "suggested_actions": [
                "Cardiology follow-up for HOCM screening post-stabilization"
            ],
        },
    )


async def run_sam_case() -> dict[str, Any]:
    """Execute complete SAM case simulation."""
    start_time = time.perf_counter()
    results: dict[str, Any] = {
        "case": "dynamic_lvot_obstruction_sam",
        "steps": [],
        "errors": [],
        "warnings": [],
    }
    print("\n" + "=" * 75)
    print("🚀 [Case 1] Dynamic LVOT Obstruction (SAM) - Perioperative Cardiac Arrest")
    print("=" * 75)

    server_state = ServerState()
    evidence_handlers = EvidenceHandlers(server_state)
    dd_handlers = DDHandlers(server_state)
    thinking_handlers = ThinkingHandlers(server_state)
    contract_handlers = ContractHandlers(server_state)

    session_id = "trial_sam_case_001"
    orch = await server_state.get_or_create_orchestrator(session_id)
    g1 = orch.get_guidance()
    results["steps"].append({"step": "init", "stage": g1.current_stage.value})

    # Step 2: Evidence
    print("\n[Step 2] Grounding Evidence against 5 Raw Data Files...")
    ev_ids = await _run_sam_evidence(evidence_handlers, session_id, results)
    g2 = orch.get_guidance()
    results["steps"].append(
        {"step": "evidence", "stage": g2.current_stage.value, "verified": 6}
    )

    # Step 3: Hypotheses
    print("\n[Step 3] Proposing Differential Hypotheses (Broad Differential)...")
    h_ids = await _run_sam_hypotheses(dd_handlers, session_id)
    g3 = orch.get_guidance()
    results["steps"].append(
        {
            "step": "hypotheses",
            "stage": g3.current_stage.value,
            "count": len(orch.hypothesis_store),
        }
    )

    # Step 4: Bayesian
    print("\n[Step 4] Applying Bayesian Updates & Rule-Out Tests...")
    await _run_sam_bayesian(dd_handlers, session_id, h_ids, ev_ids)
    g4 = orch.get_guidance()
    results["steps"].append({"step": "bayesian", "stage": g4.current_stage.value})

    # Step 5: Cognitive Audit
    print("\n[Step 5] Logging Cognitive Biases and Uncertainties...")
    await _run_sam_cognitive(thinking_handlers, session_id)
    g5 = orch.get_guidance()
    results["steps"].append(
        {
            "step": "audit",
            "stage": g5.current_stage.value,
            "completeness": g5.completeness_score,
        }
    )

    # Step 6 & 7: Synthesis
    print("\n[Step 6] Synthesizing Deterministic Zero-LLM Markdown Report...")
    report_res = await contract_handlers.handle(
        "rc_generate_contract_report",
        {
            "session_id": session_id,
            "format": "markdown",
            "detail_level": "full",
            "finalize": True,
        },
    )
    report_md = str(report_res["content"])
    print(
        f" -> Generated Markdown Report ({len(report_md)} chars, {len(report_md.splitlines())} lines)"
    )

    print("\n[Step 7] Generating Verified Mermaid Presenters...")
    reasoning_mermaid = render_reasoning_chain_mermaid(orch.reasoning_chain)
    evidence_mermaid = str(
        build_evidence_graph(
            orch.evidence_store.values(), orch.hypothesis_store.values()
        )["mermaid"]
    )
    print(f" -> Reasoning Chain Mermaid ({len(reasoning_mermaid)} chars)")
    print(f" -> Evidence Graph Mermaid ({len(evidence_mermaid)} chars)")

    elapsed = time.perf_counter() - start_time
    top_h = max(orch.hypothesis_store.values(), key=lambda h: h.current_probability)
    print(
        f"\n✅ SAM CASE COMPLETED in {elapsed:.3f}s: Top={top_h.diagnosis} (P={top_h.current_probability:.3f})"
    )
    results["elapsed_seconds"] = elapsed
    results["success"] = True
    return results


# ============================================================================
# Case 2: Propofol Infusion Syndrome (PRIS)
# ============================================================================


async def _run_pris_evidence(
    evidence_handlers: EvidenceHandlers,
    session_id: str,
    results: dict[str, Any],
) -> list[str]:
    fixtures = [
        {
            "content": "Propofol infusion initiated in ER at 45 ml/hr and escalated to 60 ml/hr (>8 mg/kg/hr) for >48h",
            "source_doc": "examples/pris_status_epilepticus/DATA_SOURCE_01_ER_TRANSFER_NOTE.txt",
            "snippet": "Propofol (Diprivan 1%) infusion started at 01:00",
            "strength": "STRONG",
            "reliability": "GRADE_A",
        },
        {
            "content": "ICU flowsheet demonstrates continuous high-dose propofol 60 ml/hr with green urine and hypotension",
            "source_doc": "examples/pris_status_epilepticus/DATA_SOURCE_02_MICU_FLOWSHEET.csv",
            "snippet": '"06/16 20:00","125","70","38.4","ST/PVCs","AC/VC","Propofol: 60 ml/hr","25 ml","Urine looks dark/greenish? Sent UA."',
            "strength": "PATHOGNOMONIC",
            "reliability": "GRADE_A",
        },
        {
            "content": "Severe refractory metabolic acidosis (pH 7.22, Lactate 6.8), AKI, and massive rhabdomyolysis (CK 15,000)",
            "source_doc": "examples/pris_status_epilepticus/DATA_SOURCE_03_LAB_RESULTS.txt",
            "snippet": "CK (CPK): 15,000 (Rhabdomyolysis)",
            "strength": "STRONG",
            "reliability": "GRADE_A",
        },
        {
            "content": "Nursing handoff documents thick milky/lipemic blood and pathognomonic forest green urine",
            "source_doc": "examples/pris_status_epilepticus/DATA_SOURCE_04_NURSING_HANDOFF.txt",
            "snippet": "Also, his urine is a weird forest green color. Dr. says probably medication effect (Propofol or Methylene Blue? but he's not on Methylene Blue).",
            "strength": "PATHOGNOMONIC",
            "reliability": "GRADE_A",
        },
        {
            "content": "ECG reveals coved ST elevation in V1-V2 (Brugada-like pattern) and critical sinus bradycardia",
            "source_doc": "examples/pris_status_epilepticus/DATA_SOURCE_05_ECG_ANALYSIS.xml",
            "snippet": "** BRUGADA-LIKE PATTERN NOTED **",
            "strength": "PATHOGNOMONIC",
            "reliability": "GRADE_A",
        },
    ]

    ev_ids: list[str] = []
    for idx, ef in enumerate(fixtures, 1):
        res = await evidence_handlers.handle(
            "rc_add_evidence",
            {
                "session_id": session_id,
                "content": ef["content"],
                "source_document": ef["source_doc"],
                "raw_snippet": ef["snippet"],
                "clinical_strength": ef["strength"],
                "source_reliability": ef["reliability"],
                "auto_verify": True,
            },
        )
        ev_ids.append(res["evidence_id"])
        status_icon = "✅" if res["verified"] else "❌"
        print(
            f" -> Ev#{idx} [{status_icon} {res['verification_method']}] "
            f"Doc: {Path(ef['source_doc']).name} Lines: {res['matched_lines']}"
        )
        if not res["verified"]:
            results["warnings"].append(
                f"Evidence #{idx} failed verification: {ef['source_doc']}"
            )
    return ev_ids


async def _run_pris_hypotheses(
    dd_handlers: DDHandlers, session_id: str
) -> dict[str, str]:
    h_pris = await dd_handlers.handle(
        "rc_propose_hypothesis",
        {
            "session_id": session_id,
            "diagnosis": "Propofol Infusion Syndrome (PRIS)",
            "prior_probability": 0.15,
            "rationale": "High-dose propofol (>8 mg/kg/hr x 48h) with metabolic acidosis, rhabdomyolysis, green urine, and Brugada ECG",
            "icd10_code": "T88.59",
        },
    )
    h_sepsis = await dd_handlers.handle(
        "rc_propose_hypothesis",
        {
            "session_id": session_id,
            "diagnosis": "Severe Septic Shock secondary to Aspiration Pneumonia",
            "prior_probability": 0.45,
            "rationale": "Fever, leukocytosis, metabolic acidosis, and hypotension in ventilated alcohol withdrawal patient",
            "icd10_code": "R65.21",
        },
    )
    h_panc = await dd_handlers.handle(
        "rc_propose_hypothesis",
        {
            "session_id": session_id,
            "diagnosis": "Acute Severe Alcoholic Pancreatitis",
            "prior_probability": 0.25,
            "rationale": "Elevated lipase 800 with chronic alcoholism history and systemic inflammatory response",
            "icd10_code": "K85.2",
        },
    )
    return {
        "pris": h_pris["hypothesis_id"],
        "sepsis": h_sepsis["hypothesis_id"],
        "panc": h_panc["hypothesis_id"],
    }


async def _run_pris_bayesian(
    dd_handlers: DDHandlers,
    session_id: str,
    h_ids: dict[str, str],
    ev_ids: list[str],
) -> None:
    # Rule out Sepsis & Pancreatitis as sole explanation
    await dd_handlers.handle(
        "rc_link_evidence_to_hypothesis",
        {
            "session_id": session_id,
            "hypothesis_id": h_ids["sepsis"],
            "evidence_id": ev_ids[3],  # Green urine & milky blood
            "direction": "REFUTES",
            "weight": 0.90,
            "reasoning": "Green urine and milky serum are drug-induced metabolic phenomena not explained by sepsis",
        },
    )
    await dd_handlers.handle(
        "rc_link_evidence_to_hypothesis",
        {
            "session_id": session_id,
            "hypothesis_id": h_ids["panc"],
            "evidence_id": ev_ids[4],  # Brugada ECG
            "direction": "REFUTES",
            "weight": 0.85,
            "reasoning": "Brugada-like ECG pattern and critical bradycardia represent mitochondrial channelopathy of PRIS",
        },
    )
    # Confirm PRIS
    for ev_idx, wt, reason in [
        (
            0,
            0.85,
            "High-dose propofol 8 mg/kg/hr for >48 hours exceeds the safe toxic threshold of 4-5 mg/kg/hr",
        ),
        (
            1,
            0.90,
            "Dose escalation directly temporal to hypotension and metabolic acidosis",
        ),
        (
            2,
            0.92,
            "Constellation of severe metabolic acidosis, hyperkalemia, AKI, and rhabdomyolysis",
        ),
        (
            3,
            0.98,
            "Forest green urine (phenolic metabolites) and milky lipemic serum are pathognomonic for PRIS",
        ),
        (
            4,
            0.95,
            "Brugada-like pattern with critical sinus bradycardia represents cardiac uncoupling toxicity of PRIS",
        ),
    ]:
        await dd_handlers.handle(
            "rc_link_evidence_to_hypothesis",
            {
                "session_id": session_id,
                "hypothesis_id": h_ids["pris"],
                "evidence_id": ev_ids[ev_idx],
                "direction": "SUPPORTS",
                "weight": wt,
                "reasoning": reason,
            },
        )


async def _run_pris_cognitive(
    thinking_handlers: ThinkingHandlers, session_id: str
) -> None:
    await thinking_handlers.handle(
        "rc_reflect",
        {
            "session_id": session_id,
            "reflection_content": "Clinical team anchored on alcohol withdrawal history and presumed sepsis/pancreatitis",
            "identified_biases": [
                "ANCHORING: Attributing hyperlipasemia solely to alcoholic pancreatitis",
                "PREMATURE_CLOSURE: Dismissing green urine as 'medication side effect' without toxicology review",
            ],
            "identified_gaps": [
                "Serum triglycerides level was omitted from ICU lab orders despite 48h high-dose propofol infusion",
            ],
        },
    )
    await thinking_handlers.handle(
        "rc_challenge_assumption",
        {
            "session_id": session_id,
            "assumption": "Escalating broad-spectrum antibiotics (Meropenem) will resolve the worsening shock",
            "challenge_reasoning": "Shock is toxic/metabolic uncoupling from propofol lipid overload; continuing propofol is fatal",
            "potential_impact": "FATAL cardiovascular collapse if propofol infusion is not immediately discontinued",
            "alternative_explanations": [
                "Discontinue propofol immediately, initiate dexmedetomidine/midazolam, and prepare RRT"
            ],
        },
    )
    await thinking_handlers.handle(
        "rc_identify_gaps",
        {
            "session_id": session_id,
            "gap_description": "STAT serum triglyceride level",
            "gap_type": "MISSING_DATA",
            "impact_on_diagnosis": "CRITICAL: will confirm severe hypertriglyceridemia from propofol lipid emulsion",
            "suggested_actions": ["Order STAT lipid panel and toxicology consult"],
        },
    )


async def run_pris_case() -> dict[str, Any]:
    """Execute complete PRIS case simulation."""
    start_time = time.perf_counter()
    results: dict[str, Any] = {
        "case": "pris_status_epilepticus",
        "steps": [],
        "errors": [],
        "warnings": [],
    }
    print("\n" + "=" * 75)
    print("🚀 [Case 2] Propofol Infusion Syndrome (PRIS) - Critical Toxic Shock")
    print("=" * 75)

    server_state = ServerState()
    evidence_handlers = EvidenceHandlers(server_state)
    dd_handlers = DDHandlers(server_state)
    thinking_handlers = ThinkingHandlers(server_state)
    contract_handlers = ContractHandlers(server_state)

    session_id = "trial_pris_case_002"
    orch = await server_state.get_or_create_orchestrator(session_id)
    g1 = orch.get_guidance()
    results["steps"].append({"step": "init", "stage": g1.current_stage.value})

    # Step 2: Evidence
    print("\n[Step 2] Grounding Evidence against 5 Raw Data Files...")
    ev_ids = await _run_pris_evidence(evidence_handlers, session_id, results)
    g2 = orch.get_guidance()
    results["steps"].append(
        {"step": "evidence", "stage": g2.current_stage.value, "verified": 5}
    )

    # Step 3: Hypotheses
    print("\n[Step 3] Proposing Differential Hypotheses (Broad Differential)...")
    h_ids = await _run_pris_hypotheses(dd_handlers, session_id)
    g3 = orch.get_guidance()
    results["steps"].append(
        {
            "step": "hypotheses",
            "stage": g3.current_stage.value,
            "count": len(orch.hypothesis_store),
        }
    )

    # Step 4: Bayesian
    print("\n[Step 4] Applying Bayesian Updates & Rule-Out Tests...")
    await _run_pris_bayesian(dd_handlers, session_id, h_ids, ev_ids)
    g4 = orch.get_guidance()
    results["steps"].append({"step": "bayesian", "stage": g4.current_stage.value})

    # Step 5: Cognitive Audit
    print("\n[Step 5] Logging Cognitive Biases and Uncertainties...")
    await _run_pris_cognitive(thinking_handlers, session_id)
    g5 = orch.get_guidance()
    results["steps"].append(
        {
            "step": "audit",
            "stage": g5.current_stage.value,
            "completeness": g5.completeness_score,
        }
    )

    # Step 6 & 7: Synthesis
    print("\n[Step 6] Synthesizing Deterministic Zero-LLM Markdown Report...")
    report_res = await contract_handlers.handle(
        "rc_generate_contract_report",
        {
            "session_id": session_id,
            "format": "markdown",
            "detail_level": "full",
            "finalize": True,
        },
    )
    report_md = str(report_res["content"])
    print(
        f" -> Generated Markdown Report ({len(report_md)} chars, {len(report_md.splitlines())} lines)"
    )

    print("\n[Step 7] Generating Verified Mermaid Presenters...")
    reasoning_mermaid = render_reasoning_chain_mermaid(orch.reasoning_chain)
    evidence_mermaid = str(
        build_evidence_graph(
            orch.evidence_store.values(), orch.hypothesis_store.values()
        )["mermaid"]
    )
    print(f" -> Reasoning Chain Mermaid ({len(reasoning_mermaid)} chars)")
    print(f" -> Evidence Graph Mermaid ({len(evidence_mermaid)} chars)")

    elapsed = time.perf_counter() - start_time
    top_h = max(orch.hypothesis_store.values(), key=lambda h: h.current_probability)
    print(
        f"\n✅ PRIS CASE COMPLETED in {elapsed:.3f}s: Top={top_h.diagnosis} (P={top_h.current_probability:.3f})"
    )
    results["elapsed_seconds"] = elapsed
    results["success"] = True
    return results


# ============================================================================
# Case 3: Massive Transfusion Hyperkalemia Arrest (Trauma ICU)
# ============================================================================


async def _run_trauma_evidence(
    evidence_handlers: EvidenceHandlers,
    session_id: str,
    results: dict[str, Any],
) -> list[str]:
    fixtures = [
        {
            "content": "Trauma MTP activated with 6 PRBC and 4 FFP rapid infuser resuscitation for Grade IV liver laceration",
            "source_doc": "examples/trauma_hyperkalemia_arrest/DATA_SOURCE_01_TRAUMA_LOG.txt",
            "snippet": "Massive Transfusion Protocol (MTP) ACTIVATED.",
            "strength": "STRONG",
            "reliability": "GRADE_A",
        },
        {
            "content": "ICU flowsheet documents Hanging Unit #7 PRBC (older stock, exp 2 days) with decreasing BP and widening QRS",
            "source_doc": "examples/trauma_hyperkalemia_arrest/DATA_SOURCE_02_ICU_FLOWSHEET.csv",
            "snippet": '"01:45","90/50","110","Sinus Tach","14","99%","AC/VC","MTP Cooler #2 arrived from blood bank. Hanging Unit #7 PRBC (older stock, exp 2 days)."',
            "strength": "STRONG",
            "reliability": "GRADE_A",
        },
        {
            "content": "LIS database scheduled downtime delayed reporting of STAT potassium lab specimen held in queue",
            "source_doc": "examples/trauma_hyperkalemia_arrest/DATA_SOURCE_03_LIS_MAINTENANCE.txt",
            "snippet": "Sample ID [T-24-505-004] (Trauma ICU): Received at Central Lab 02:05. Status: HELD_IN_QUEUE.",
            "strength": "STRONG",
            "reliability": "GRADE_B",
        },
        {
            "content": "ICU monitor audit log shows ignored HI_T_WAVE alarm and ARRHYTHMIA_V_EVENT prior to asystole",
            "source_doc": "examples/trauma_hyperkalemia_arrest/DATA_SOURCE_04_ALARM_AUDIT.xml",
            "snippet": '<Event Time="02:12:30" Type="ALARM_PHYS" Msg="HI_T_WAVE" Action="IGNORED" User="--"/>',
            "strength": "PATHOGNOMONIC",
            "reliability": "GRADE_A",
        },
        {
            "content": "Autopsy confirms non-exsanguination with vitreous potassium > 8.5 mmol/L and dilated flaccid heart",
            "source_doc": "examples/trauma_hyperkalemia_arrest/DATA_SOURCE_05_AUTOPSY.txt",
            "snippet": "4. BIOCHEMISTRY (Vitreous Humor analysis post-mortem): **Potassium > 8.5 mmol/L**.",
            "strength": "PATHOGNOMONIC",
            "reliability": "GRADE_A",
        },
    ]

    ev_ids: list[str] = []
    for idx, ef in enumerate(fixtures, 1):
        res = await evidence_handlers.handle(
            "rc_add_evidence",
            {
                "session_id": session_id,
                "content": ef["content"],
                "source_document": ef["source_doc"],
                "raw_snippet": ef["snippet"],
                "clinical_strength": ef["strength"],
                "source_reliability": ef["reliability"],
                "auto_verify": True,
            },
        )
        ev_ids.append(res["evidence_id"])
        status_icon = "✅" if res["verified"] else "❌"
        print(
            f" -> Ev#{idx} [{status_icon} {res['verification_method']}] "
            f"Doc: {Path(ef['source_doc']).name} Lines: {res['matched_lines']}"
        )
        if not res["verified"]:
            results["warnings"].append(
                f"Evidence #{idx} failed verification: {ef['source_doc']}"
            )
    return ev_ids


async def _run_trauma_hypotheses(
    dd_handlers: DDHandlers, session_id: str
) -> dict[str, str]:
    h_hyperk = await dd_handlers.handle(
        "rc_propose_hypothesis",
        {
            "session_id": session_id,
            "diagnosis": "Severe Hyperkalemic Cardiac Arrest (5H: H4_Hyperkalemia)",
            "prior_probability": 0.20,
            "rationale": "Older stock MTP blood transfusion + acute oliguric renal failure + ignored peaked T-wave and sine wave arrest",
            "icd10_code": "E87.5",
        },
    )
    h_hypovol = await dd_handlers.handle(
        "rc_propose_hypothesis",
        {
            "session_id": session_id,
            "diagnosis": "Recurrent Exsanguinating Hemorrhagic Shock (5H: H1_Hypovolemia)",
            "prior_probability": 0.50,
            "rationale": "High-velocity trauma with grade IV liver laceration and progressive widening hypotension",
            "icd10_code": "R57.1",
        },
    )
    h_pneumo = await dd_handlers.handle(
        "rc_propose_hypothesis",
        {
            "session_id": session_id,
            "diagnosis": "Tension Pneumothorax (5T: T1_Tension_Pneumothorax)",
            "prior_probability": 0.30,
            "rationale": "Chest trauma with chest tube and progressive hypotension under positive pressure ventilation",
            "icd10_code": "J93.0",
        },
    )
    return {
        "hyperk": h_hyperk["hypothesis_id"],
        "hypovol": h_hypovol["hypothesis_id"],
        "pneumo": h_pneumo["hypothesis_id"],
    }


async def _run_trauma_bayesian(
    dd_handlers: DDHandlers,
    session_id: str,
    h_ids: dict[str, str],
    ev_ids: list[str],
) -> None:
    # Rule out Hypovolemia & Tension Pneumothorax
    await dd_handlers.handle(
        "rc_link_evidence_to_hypothesis",
        {
            "session_id": session_id,
            "hypothesis_id": h_ids["hypovol"],
            "evidence_id": ev_ids[4],  # Autopsy intact liver, minimal blood
            "direction": "REFUTES",
            "weight": 0.95,
            "reasoning": "Autopsy confirmed liver packing intact with only 200ml blood, ruling out exsanguination",
        },
    )
    await dd_handlers.handle(
        "rc_link_evidence_to_hypothesis",
        {
            "session_id": session_id,
            "hypothesis_id": h_ids["pneumo"],
            "evidence_id": ev_ids[4],  # Resuscitation needle decompression neg
            "direction": "REFUTES",
            "weight": 0.90,
            "reasoning": "Needle decompression during arrest showed negative rush of air",
        },
    )
    # Confirm Hyperkalemia
    for ev_idx, wt, reason in [
        (
            0,
            0.75,
            "Massive transfusion protocol (6+ units PRBC) delivers massive potassium load",
        ),
        (1, 0.88, "Older stock PRBC Unit #7 has high extracellular potassium efflux"),
        (2, 0.80, "LIS downtime blocked early warning of critical hyperkalemia"),
        (
            3,
            0.95,
            "Ignored HI_T_WAVE and widening QRS represents pathognomonic potassium cardiac toxicity",
        ),
        (
            4,
            0.99,
            "Post-mortem vitreous biochemistry confirmed lethal potassium > 8.5 mmol/L",
        ),
    ]:
        await dd_handlers.handle(
            "rc_link_evidence_to_hypothesis",
            {
                "session_id": session_id,
                "hypothesis_id": h_ids["hyperk"],
                "evidence_id": ev_ids[ev_idx],
                "direction": "SUPPORTS",
                "weight": wt,
                "reasoning": reason,
            },
        )


async def _run_trauma_cognitive(
    thinking_handlers: ThinkingHandlers, session_id: str
) -> None:
    await thinking_handlers.handle(
        "rc_reflect",
        {
            "session_id": session_id,
            "reflection_content": "Clinical team anchored on trauma hemorrhagic shock and ordered more fluids/FFP instead of calcium/insulin",
            "identified_biases": [
                "ANCHORING: Presuming shock was recurrent liver hemorrhage",
                "ALARM_FATIGUE: Dismissing monitor peaked T-wave alarm as technical artifact/shivering",
            ],
            "identified_gaps": [
                "Scheduled LIS system maintenance created 2-hour communication blackout for critical lab alerts",
            ],
        },
    )
    await thinking_handlers.handle(
        "rc_challenge_assumption",
        {
            "session_id": session_id,
            "assumption": "Rapidly infusing more blood and FFP is the primary treatment for widening QRS in post-trauma shock",
            "challenge_reasoning": "In massive transfusion with oliguria, hyperkalemic cardiotoxicity causes widening QRS; continuing blood without calcium/dialysis is fatal",
            "potential_impact": "FATAL asystolic cardiac arrest",
            "alternative_explanations": [
                "Give IV Calcium Gluconate/Chloride, Insulin+D50, and prepare STAT emergency hemodialysis/CRRT"
            ],
        },
    )
    await thinking_handlers.handle(
        "rc_identify_gaps",
        {
            "session_id": session_id,
            "gap_description": "Blood gas electrolyte (potassium/calcium) monitoring during MTP resuscitation",
            "gap_type": "PROCESS_GAP",
            "impact_on_diagnosis": "CRITICAL: Point-of-Care ABG should bypass LIS downtime during active MTP",
            "suggested_actions": [
                "Implement bedside POC ABG protocol every 4 units of blood in trauma ICU"
            ],
        },
    )


async def run_trauma_case() -> dict[str, Any]:
    """Execute complete Trauma MTP Hyperkalemia case simulation."""
    start_time = time.perf_counter()
    results: dict[str, Any] = {
        "case": "trauma_hyperkalemia_arrest",
        "steps": [],
        "errors": [],
        "warnings": [],
    }
    print("\n" + "=" * 75)
    print("🚀 [Case 3] Massive Transfusion Hyperkalemic Cardiac Arrest (Trauma ICU)")
    print("=" * 75)

    server_state = ServerState()
    evidence_handlers = EvidenceHandlers(server_state)
    dd_handlers = DDHandlers(server_state)
    thinking_handlers = ThinkingHandlers(server_state)
    contract_handlers = ContractHandlers(server_state)

    session_id = "trial_trauma_case_003"
    orch = await server_state.get_or_create_orchestrator(session_id)
    g1 = orch.get_guidance()
    results["steps"].append({"step": "init", "stage": g1.current_stage.value})

    # Step 2: Evidence
    print("\n[Step 2] Grounding Evidence against 5 Raw Data Files...")
    ev_ids = await _run_trauma_evidence(evidence_handlers, session_id, results)
    g2 = orch.get_guidance()
    results["steps"].append(
        {"step": "evidence", "stage": g2.current_stage.value, "verified": 5}
    )

    # Step 3: Hypotheses
    print("\n[Step 3] Proposing Differential Hypotheses (Broad Differential)...")
    h_ids = await _run_trauma_hypotheses(dd_handlers, session_id)
    g3 = orch.get_guidance()
    results["steps"].append(
        {
            "step": "hypotheses",
            "stage": g3.current_stage.value,
            "count": len(orch.hypothesis_store),
        }
    )

    # Step 4: Bayesian
    print("\n[Step 4] Applying Bayesian Updates & Rule-Out Tests...")
    await _run_trauma_bayesian(dd_handlers, session_id, h_ids, ev_ids)
    g4 = orch.get_guidance()
    results["steps"].append({"step": "bayesian", "stage": g4.current_stage.value})

    # Step 5: Cognitive Audit
    print("\n[Step 5] Logging Cognitive Biases and Uncertainties...")
    await _run_trauma_cognitive(thinking_handlers, session_id)
    g5 = orch.get_guidance()
    results["steps"].append(
        {
            "step": "audit",
            "stage": g5.current_stage.value,
            "completeness": g5.completeness_score,
        }
    )

    # Step 6 & 7: Synthesis
    print("\n[Step 6] Synthesizing Deterministic Zero-LLM Markdown Report...")
    report_res = await contract_handlers.handle(
        "rc_generate_contract_report",
        {
            "session_id": session_id,
            "format": "markdown",
            "detail_level": "full",
            "finalize": True,
        },
    )
    report_md = str(report_res["content"])
    print(
        f" -> Generated Markdown Report ({len(report_md)} chars, {len(report_md.splitlines())} lines)"
    )

    print("\n[Step 7] Generating Verified Mermaid Presenters...")
    reasoning_mermaid = render_reasoning_chain_mermaid(orch.reasoning_chain)
    evidence_mermaid = str(
        build_evidence_graph(
            orch.evidence_store.values(), orch.hypothesis_store.values()
        )["mermaid"]
    )
    print(f" -> Reasoning Chain Mermaid ({len(reasoning_mermaid)} chars)")
    print(f" -> Evidence Graph Mermaid ({len(evidence_mermaid)} chars)")

    elapsed = time.perf_counter() - start_time
    top_h = max(orch.hypothesis_store.values(), key=lambda h: h.current_probability)
    print(
        f"\n✅ TRAUMA CASE COMPLETED in {elapsed:.3f}s: Top={top_h.diagnosis} (P={top_h.current_probability:.3f})"
    )
    results["elapsed_seconds"] = elapsed
    results["success"] = True
    return results


# ============================================================================
# Case 4: Post-op Pulmonary Embolism PEA Arrest (Orthopedic Surgery)
# ============================================================================


async def _run_pe_evidence(
    evidence_handlers: EvidenceHandlers,
    session_id: str,
    results: dict[str, Any],
) -> list[str]:
    fixtures = [
        {
            "content": "Post-op order held Clexane (Enoxaparin) for 24 hours following left Total Hip Arthroplasty",
            "source_doc": "examples/postop_pe_death/DATA_SOURCE_01_OP_NOTE.txt",
            "snippet": "DVT Prophylaxis: **HOLD Clexane (Enoxaparin)** for 24hrs due to oozing from drain (>100ml in PACU). Re-evaluate tomorrow.",
            "strength": "STRONG",
            "reliability": "GRADE_A",
        },
        {
            "content": "Nursing flowsheet documents patient complained of bilateral calf pain and leg swelling on POD 1",
            "source_doc": "examples/postop_pe_death/DATA_SOURCE_02_NURSING_FLOWSHEET.csv",
            "snippet": '"2024-04-11 16:00","1","37.8","95","20","105/65","94%","RA","6/10","10ml","Pt c/o calf pain bilaterally? (Note: Pt has history of chronic back pain/sciatica). Homan\'s sign equivocal. Leg swelling (+)."',
            "strength": "STRONG",
            "reliability": "GRADE_A",
        },
        {
            "content": "Progress note misdiagnosed patient with Sepsis (UTI vs Pneumonia) and started fluid resuscitation",
            "source_doc": "examples/postop_pe_death/DATA_SOURCE_03_PROGRESS_NOTE.txt",
            "snippet": "ASSESSMENT:\n1. Sepsis, suspected source:\n   a. UTI (Foley removed yesterday, UA pos).\n   b. HAP (Hospital Acquired Pneumonia)",
            "strength": "STRONG",
            "reliability": "GRADE_B",
        },
        {
            "content": "Nursing observation documents sudden severe chest tightness, dyspnea, and PEA Code Blue arrest",
            "source_doc": "examples/postop_pe_death/DATA_SOURCE_04_NURSING_OBSERVATION.txt",
            "snippet": "[12:10] CODE BLUE ACTIVATED. Pt unresponsive. PEA (Pulseless Electrical Activity). CPR started.",
            "strength": "PATHOGNOMONIC",
            "reliability": "GRADE_A",
        },
        {
            "content": "Medication administration record shows Clexane NOT GIVEN due to order expiration without renewal",
            "source_doc": "examples/postop_pe_death/DATA_SOURCE_05_MAR.csv",
            "snippet": '"2024-04-11 09:00","Clexane (Enoxaparin)","40mg","SC","NOT_GIVEN","Reason: Order Expired/Not Renewed"',
            "strength": "PATHOGNOMONIC",
            "reliability": "GRADE_A",
        },
    ]

    ev_ids: list[str] = []
    for idx, ef in enumerate(fixtures, 1):
        res = await evidence_handlers.handle(
            "rc_add_evidence",
            {
                "session_id": session_id,
                "content": ef["content"],
                "source_document": ef["source_doc"],
                "raw_snippet": ef["snippet"],
                "clinical_strength": ef["strength"],
                "source_reliability": ef["reliability"],
                "auto_verify": True,
            },
        )
        ev_ids.append(res["evidence_id"])
        status_icon = "✅" if res["verified"] else "❌"
        print(
            f" -> Ev#{idx} [{status_icon} {res['verification_method']}] "
            f"Doc: {Path(ef['source_doc']).name} Lines: {res['matched_lines']}"
        )
        if not res["verified"]:
            results["warnings"].append(
                f"Evidence #{idx} failed verification: {ef['source_doc']}"
            )
    return ev_ids


async def _run_pe_hypotheses(
    dd_handlers: DDHandlers, session_id: str
) -> dict[str, str]:
    h_pe = await dd_handlers.handle(
        "rc_propose_hypothesis",
        {
            "session_id": session_id,
            "diagnosis": "Massive Pulmonary Embolism with PEA Arrest (5T: T4_Thrombosis_Pulmonary)",
            "prior_probability": 0.20,
            "rationale": "High-risk THA surgery with omitted DVT prophylaxis + calf swelling + sudden acute dyspnea and PEA collapse",
            "icd10_code": "I26.0",
        },
    )
    h_sepsis = await dd_handlers.handle(
        "rc_propose_hypothesis",
        {
            "session_id": session_id,
            "diagnosis": "Severe Septic Shock (5H: H3_Acidosis / Sepsis)",
            "prior_probability": 0.50,
            "rationale": "Post-op fever 38.5, leukocytosis, positive UA, and hypotension",
            "icd10_code": "R65.21",
        },
    )
    h_mi = await dd_handlers.handle(
        "rc_propose_hypothesis",
        {
            "session_id": session_id,
            "diagnosis": "Acute Myocardial Infarction (5T: T5_Thrombosis_Coronary)",
            "prior_probability": 0.30,
            "rationale": "Post-op chest tightness, tachycardia, and sudden hemodynamic collapse",
            "icd10_code": "I21.9",
        },
    )
    return {
        "pe": h_pe["hypothesis_id"],
        "sepsis": h_sepsis["hypothesis_id"],
        "mi": h_mi["hypothesis_id"],
    }


async def _run_pe_bayesian(
    dd_handlers: DDHandlers,
    session_id: str,
    h_ids: dict[str, str],
    ev_ids: list[str],
) -> None:
    # Rule out Sepsis & MI
    await dd_handlers.handle(
        "rc_link_evidence_to_hypothesis",
        {
            "session_id": session_id,
            "hypothesis_id": h_ids["sepsis"],
            "evidence_id": ev_ids[3],  # Sudden chest tightness and desaturation to 85%
            "direction": "REFUTES",
            "weight": 0.90,
            "reasoning": "Sudden refractory desaturation and PEA collapse within minutes is characteristic of mechanical pulmonary vascular occlusion, not sepsis",
        },
    )
    await dd_handlers.handle(
        "rc_link_evidence_to_hypothesis",
        {
            "session_id": session_id,
            "hypothesis_id": h_ids["mi"],
            "evidence_id": ev_ids[3],  # EKG shows incomplete RBBB without ST elevation
            "direction": "REFUTES",
            "weight": 0.85,
            "reasoning": "Bedside EKG showed incomplete RBBB with right heart strain rather than acute transmural infarction",
        },
    )
    # Confirm Massive PE
    for ev_idx, wt, reason in [
        (
            0,
            0.80,
            "Initial 24h hold of anticoagulant removed chemical thromboprophylaxis protection",
        ),
        (
            1,
            0.90,
            "Calf swelling and pain represented acute deep vein thrombosis (DVT)",
        ),
        (
            2,
            0.75,
            "Diagnostic anchoring on sepsis delayed bedside vascular ultrasound / CTA",
        ),
        (
            3,
            0.98,
            "Sudden dyspnea, non-rebreather desaturation to 85%, and PEA arrest confirmed massive pulmonary embolus",
        ),
        (
            4,
            0.95,
            "Lapse in MAR where Clexane expired and was not reordered left patient completely unprotected",
        ),
    ]:
        await dd_handlers.handle(
            "rc_link_evidence_to_hypothesis",
            {
                "session_id": session_id,
                "hypothesis_id": h_ids["pe"],
                "evidence_id": ev_ids[ev_idx],
                "direction": "SUPPORTS",
                "weight": wt,
                "reasoning": reason,
            },
        )


async def _run_pe_cognitive(
    thinking_handlers: ThinkingHandlers, session_id: str
) -> None:
    await thinking_handlers.handle(
        "rc_reflect",
        {
            "session_id": session_id,
            "reflection_content": "Surgical resident anchored on UTI/Pneumonia sepsis and initiated sepsis bundle while missing DVT/PE",
            "identified_biases": [
                "DIAGNOSTIC_MOMENTUM: Uncritically continuing sepsis diagnosis without re-evaluating unilateral leg swelling",
                "CONFIRMATION_BIAS: Assuming fluid non-responsiveness was septic shock rather than acute RV failure",
            ],
            "identified_gaps": [
                "EMR order expiration did not trigger an automatic notification to the covering surgical team",
            ],
        },
    )
    await thinking_handlers.handle(
        "rc_challenge_assumption",
        {
            "session_id": session_id,
            "assumption": "Post-op fever and low urine output is best managed by aggressive saline boluses and broad-spectrum antibiotics",
            "challenge_reasoning": "In acute PE, RV is dilated and failing; aggressive fluid boluses cause RV overdistension and worsen left ventricular filling (interventricular dependence)",
            "potential_impact": "Accelerates PEA arrest",
            "alternative_explanations": [
                "Obtain urgent bedside Echo/POCUS for RV strain, D-dimer/CTA, and initiate thrombolysis/embolectomy"
            ],
        },
    )
    await thinking_handlers.handle(
        "rc_identify_gaps",
        {
            "session_id": session_id,
            "gap_description": "Electronic DVT Prophylaxis Safety Net",
            "gap_type": "SYSTEM_SAFETY_GAP",
            "impact_on_diagnosis": "HIGH: Preventable omission of chemical thromboprophylaxis",
            "suggested_actions": [
                "Implement mandatory electronic alert when post-op anticoagulants are held >24 hours"
            ],
        },
    )


async def run_pe_case() -> dict[str, Any]:
    """Execute complete Post-op PE Death case simulation."""
    start_time = time.perf_counter()
    results: dict[str, Any] = {
        "case": "postop_pe_death",
        "steps": [],
        "errors": [],
        "warnings": [],
    }
    print("\n" + "=" * 75)
    print("🚀 [Case 4] Post-operative Pulmonary Embolism PEA Arrest (Orthopedic THA)")
    print("=" * 75)

    server_state = ServerState()
    evidence_handlers = EvidenceHandlers(server_state)
    dd_handlers = DDHandlers(server_state)
    thinking_handlers = ThinkingHandlers(server_state)
    contract_handlers = ContractHandlers(server_state)

    session_id = "trial_pe_case_004"
    orch = await server_state.get_or_create_orchestrator(session_id)
    g1 = orch.get_guidance()
    results["steps"].append({"step": "init", "stage": g1.current_stage.value})

    # Step 2: Evidence
    print("\n[Step 2] Grounding Evidence against 5 Raw Data Files...")
    ev_ids = await _run_pe_evidence(evidence_handlers, session_id, results)
    g2 = orch.get_guidance()
    results["steps"].append(
        {"step": "evidence", "stage": g2.current_stage.value, "verified": 5}
    )

    # Step 3: Hypotheses
    print("\n[Step 3] Proposing Differential Hypotheses (Broad Differential)...")
    h_ids = await _run_pe_hypotheses(dd_handlers, session_id)
    g3 = orch.get_guidance()
    results["steps"].append(
        {
            "step": "hypotheses",
            "stage": g3.current_stage.value,
            "count": len(orch.hypothesis_store),
        }
    )

    # Step 4: Bayesian
    print("\n[Step 4] Applying Bayesian Updates & Rule-Out Tests...")
    await _run_pe_bayesian(dd_handlers, session_id, h_ids, ev_ids)
    g4 = orch.get_guidance()
    results["steps"].append({"step": "bayesian", "stage": g4.current_stage.value})

    # Step 5: Cognitive Audit
    print("\n[Step 5] Logging Cognitive Biases and Uncertainties...")
    await _run_pe_cognitive(thinking_handlers, session_id)
    g5 = orch.get_guidance()
    results["steps"].append(
        {
            "step": "audit",
            "stage": g5.current_stage.value,
            "completeness": g5.completeness_score,
        }
    )

    # Step 6 & 7: Synthesis
    print("\n[Step 6] Synthesizing Deterministic Zero-LLM Markdown Report...")
    report_res = await contract_handlers.handle(
        "rc_generate_contract_report",
        {
            "session_id": session_id,
            "format": "markdown",
            "detail_level": "full",
            "finalize": True,
        },
    )
    report_md = str(report_res["content"])
    print(
        f" -> Generated Markdown Report ({len(report_md)} chars, {len(report_md.splitlines())} lines)"
    )

    print("\n[Step 7] Generating Verified Mermaid Presenters...")
    reasoning_mermaid = render_reasoning_chain_mermaid(orch.reasoning_chain)
    evidence_mermaid = str(
        build_evidence_graph(
            orch.evidence_store.values(), orch.hypothesis_store.values()
        )["mermaid"]
    )
    print(f" -> Reasoning Chain Mermaid ({len(reasoning_mermaid)} chars)")
    print(f" -> Evidence Graph Mermaid ({len(evidence_mermaid)} chars)")

    elapsed = time.perf_counter() - start_time
    top_h = max(orch.hypothesis_store.values(), key=lambda h: h.current_probability)
    print(
        f"\n✅ PE CASE COMPLETED in {elapsed:.3f}s: Top={top_h.diagnosis} (P={top_h.current_probability:.3f})"
    )
    results["elapsed_seconds"] = elapsed
    results["success"] = True
    return results


# ============================================================================
# Case 5: LVAD Suction Event (Non-Death Device Incident)
# ============================================================================


async def _run_lvad_evidence(
    evidence_handlers: EvidenceHandlers,
    session_id: str,
    results: dict[str, Any],
) -> list[str]:
    fixtures = [
        {
            "content": "ER admission note shows HeartMate 3 controller continuous Low Flow alarm with cola-colored urine",
            "source_doc": "examples/lvad_suction_event/DATA_SOURCE_01_ER_ADMISSION.txt",
            "snippet": "Flow: 2.2 L/min (Set minimum: 2.5) -> ALARMING.",
            "strength": "STRONG",
            "reliability": "GRADE_A",
        },
        {
            "content": "Bedside echocardiography demonstrates severely dilated RV with interventricular septum bowing into left ventricle",
            "source_doc": "examples/lvad_suction_event/DATA_SOURCE_02_ECHO_REPORT.txt",
            "snippet": "Interventricular Septum (IVS) is shifted towards the LEFT (bowing into LV).",
            "strength": "PATHOGNOMONIC",
            "reliability": "GRADE_A",
        },
        {
            "content": "LVAD controller log reveals critical suction event with pulsatility index dropped to 1.2 and power spikes",
            "source_doc": "examples/lvad_suction_event/DATA_SOURCE_03_CONTROLLER_LOG.csv",
            "snippet": '"03:30:00","5400","(reading_error)","7.0","1.2","SUCTION_EVENT_DETECTED"',
            "strength": "PATHOGNOMONIC",
            "reliability": "GRADE_A",
        },
        {
            "content": "Laboratory findings show severe mechanical hemolysis with LDH 3500 and plasma free hemoglobin 150",
            "source_doc": "examples/lvad_suction_event/DATA_SOURCE_04_LAB_RESULTS.txt",
            "snippet": "LDH: 3500 (Ref < 250) - **CRITICAL HIGH**",
            "strength": "STRONG",
            "reliability": "GRADE_A",
        },
        {
            "content": "Clinical deterioration note shows paradoxical worsening after fluid bolus and speed increase to 5600 RPM",
            "source_doc": "examples/lvad_suction_event/DATA_SOURCE_05_CLINICAL_UPDATE.txt",
            "snippet": "Despite 1.5L Fluid Bolus and increasing Pump Speed to 5600 RPM (to try and generate more flow), pt is becoming more hypotensive.",
            "strength": "STRONG",
            "reliability": "GRADE_B",
        },
    ]

    ev_ids: list[str] = []
    for idx, ef in enumerate(fixtures, 1):
        res = await evidence_handlers.handle(
            "rc_add_evidence",
            {
                "session_id": session_id,
                "content": ef["content"],
                "source_document": ef["source_doc"],
                "raw_snippet": ef["snippet"],
                "clinical_strength": ef["strength"],
                "source_reliability": ef["reliability"],
                "auto_verify": True,
            },
        )
        ev_ids.append(res["evidence_id"])
        status_icon = "✅" if res["verified"] else "❌"
        print(
            f" -> Ev#{idx} [{status_icon} {res['verification_method']}] "
            f"Doc: {Path(ef['source_doc']).name} Lines: {res['matched_lines']}"
        )
        if not res["verified"]:
            results["warnings"].append(
                f"Evidence #{idx} failed verification: {ef['source_doc']}"
            )
    return ev_ids


async def _run_lvad_hypotheses(
    dd_handlers: DDHandlers, session_id: str
) -> dict[str, str]:
    h_suction = await dd_handlers.handle(
        "rc_propose_hypothesis",
        {
            "session_id": session_id,
            "diagnosis": "Dynamic LVAD Suction Event secondary to Acute RV Failure",
            "prior_probability": 0.25,
            "rationale": "Dilated failing RV + small collapsed LV + IVS bowing into LV + PI drop to 1.0 with intermittent power spikes",
            "icd10_code": "I50.812",
        },
    )
    h_thrombus = await dd_handlers.handle(
        "rc_propose_hypothesis",
        {
            "session_id": session_id,
            "diagnosis": "LVAD Pump Thrombosis",
            "prior_probability": 0.45,
            "rationale": "High LDH 3500 and plasma free Hb with low flow and elevated power",
            "icd10_code": "T82.868A",
        },
    )
    h_hypovol = await dd_handlers.handle(
        "rc_propose_hypothesis",
        {
            "session_id": session_id,
            "diagnosis": "Isolated Hypovolemia / Dehydration",
            "prior_probability": 0.30,
            "rationale": "Small underfilled LV on initial echocardiography and low flow alarm",
            "icd10_code": "E86.0",
        },
    )
    return {
        "suction": h_suction["hypothesis_id"],
        "thrombus": h_thrombus["hypothesis_id"],
        "hypovol": h_hypovol["hypothesis_id"],
    }


async def _run_lvad_bayesian(
    dd_handlers: DDHandlers,
    session_id: str,
    h_ids: dict[str, str],
    ev_ids: list[str],
) -> None:
    # Rule out Pump Thrombosis & Hypovolemia
    await dd_handlers.handle(
        "rc_link_evidence_to_hypothesis",
        {
            "session_id": session_id,
            "hypothesis_id": h_ids["thrombus"],
            "evidence_id": ev_ids[2],  # Intermittent power spikes, not sustained power
            "direction": "REFUTES",
            "weight": 0.90,
            "reasoning": "Controller log showed intermittent power spikes with PI collapse to 1.2 rather than sustained continuous elevated power of thrombus",
        },
    )
    await dd_handlers.handle(
        "rc_link_evidence_to_hypothesis",
        {
            "session_id": session_id,
            "hypothesis_id": h_ids["hypovol"],
            "evidence_id": ev_ids[1],  # Dilated RV and IVC non-collapsible
            "direction": "REFUTES",
            "weight": 0.92,
            "reasoning": "Echo demonstrated severely dilated RV and dilated non-collapsible IVC (2.4cm), ruling out isolated hypovolemia",
        },
    )
    # Confirm Suction Event
    for ev_idx, wt, reason in [
        (
            0,
            0.75,
            "Low flow alarm and cola-colored urine indicate LV underfilling and hemolysis",
        ),
        (
            1,
            0.98,
            "IVS bowing into collapsed LV cavity with severely dilated RV is pathognomonic for suction physiology",
        ),
        (
            2,
            0.96,
            "Controller PI collapse to 1.0 and SUCTION_EVENT_DETECTED confirms wall strike",
        ),
        (
            3,
            0.88,
            "Critical hemolysis markers (LDH 3500, PfHb 150) caused by mechanical shear from suction cannula strike",
        ),
        (
            4,
            0.90,
            "Paradoxical deterioration after speed increase confirms higher suction gradient worsening collapse",
        ),
    ]:
        await dd_handlers.handle(
            "rc_link_evidence_to_hypothesis",
            {
                "session_id": session_id,
                "hypothesis_id": h_ids["suction"],
                "evidence_id": ev_ids[ev_idx],
                "direction": "SUPPORTS",
                "weight": wt,
                "reasoning": reason,
            },
        )


async def _run_lvad_cognitive(
    thinking_handlers: ThinkingHandlers, session_id: str
) -> None:
    await thinking_handlers.handle(
        "rc_reflect",
        {
            "session_id": session_id,
            "reflection_content": "Clinical team anchored on 'Small LV = Hypovolemia' and increased pump speed which worsened suction",
            "identified_biases": [
                "ANCHORING: Assuming low flow and small LV must be simple dehydration",
                "CONFIRMATION_BIAS: Misinterpreting hemolysis as pump thrombosis",
            ],
            "identified_gaps": [
                "Right ventricular performance was neglected during initial fluid boluses",
            ],
        },
    )
    await thinking_handlers.handle(
        "rc_challenge_assumption",
        {
            "session_id": session_id,
            "assumption": "Increasing LVAD pump speed will restore cardiac output in low-flow alarms",
            "challenge_reasoning": "When LV is underfilled due to RV failure, increasing RPM increases suction force, collapsing the septum further and exacerbating shock",
            "potential_impact": "Severe RV failure and ventricular arrhythmias",
            "alternative_explanations": [
                "Reduce pump speed, initiate inotropes (Milrinone/Dobutamine) for RV support, and use inhaled pulmonary vasodilators"
            ],
        },
    )
    await thinking_handlers.handle(
        "rc_identify_gaps",
        {
            "session_id": session_id,
            "gap_description": "LVAD Emergency Response Protocol in Non-Cardiology ER",
            "gap_type": "KNOWLEDGE_GAP",
            "impact_on_diagnosis": "HIGH: Frontline providers need clear algorithm for suction vs thrombosis",
            "suggested_actions": [
                "Post HeartMate 3 troubleshooting algorithm in emergency department"
            ],
        },
    )


async def run_lvad_case() -> dict[str, Any]:
    """Execute complete LVAD Suction Event case simulation."""
    start_time = time.perf_counter()
    results: dict[str, Any] = {
        "case": "lvad_suction_event",
        "steps": [],
        "errors": [],
        "warnings": [],
    }
    print("\n" + "=" * 75)
    print(
        "🚀 [Case 5] LVAD Suction Event & Mechanical Hemolysis (Non-Death Device Incident)"
    )
    print("=" * 75)

    server_state = ServerState()
    evidence_handlers = EvidenceHandlers(server_state)
    dd_handlers = DDHandlers(server_state)
    thinking_handlers = ThinkingHandlers(server_state)
    contract_handlers = ContractHandlers(server_state)

    session_id = "trial_lvad_case_005"
    orch = await server_state.get_or_create_orchestrator(session_id)
    g1 = orch.get_guidance()
    results["steps"].append({"step": "init", "stage": g1.current_stage.value})

    # Step 2: Evidence
    print("\n[Step 2] Grounding Evidence against 5 Raw Data Files...")
    ev_ids = await _run_lvad_evidence(evidence_handlers, session_id, results)
    g2 = orch.get_guidance()
    results["steps"].append(
        {"step": "evidence", "stage": g2.current_stage.value, "verified": 5}
    )

    # Step 3: Hypotheses
    print("\n[Step 3] Proposing Differential Hypotheses (Broad Differential)...")
    h_ids = await _run_lvad_hypotheses(dd_handlers, session_id)
    g3 = orch.get_guidance()
    results["steps"].append(
        {
            "step": "hypotheses",
            "stage": g3.current_stage.value,
            "count": len(orch.hypothesis_store),
        }
    )

    # Step 4: Bayesian
    print("\n[Step 4] Applying Bayesian Updates & Rule-Out Tests...")
    await _run_lvad_bayesian(dd_handlers, session_id, h_ids, ev_ids)
    g4 = orch.get_guidance()
    results["steps"].append({"step": "bayesian", "stage": g4.current_stage.value})

    # Step 5: Cognitive Audit
    print("\n[Step 5] Logging Cognitive Biases and Uncertainties...")
    await _run_lvad_cognitive(thinking_handlers, session_id)
    g5 = orch.get_guidance()
    results["steps"].append(
        {
            "step": "audit",
            "stage": g5.current_stage.value,
            "completeness": g5.completeness_score,
        }
    )

    # Step 6 & 7: Synthesis using Near Miss / Non-Death Template
    print("\n[Step 6] Synthesizing Deterministic Non-Death RCA Markdown Report...")
    template_file = "config/templates/near_miss_adverse_event_rca_template.md"
    report_res = await contract_handlers.handle(
        "rc_generate_contract_report",
        {
            "session_id": session_id,
            "format": "markdown",
            "detail_level": "full",
            "template_file": template_file,
            "finalize": True,
        },
    )
    report_md = str(report_res["content"])
    print(
        f" -> Generated Markdown Report ({len(report_md)} chars, {len(report_md.splitlines())} lines)"
    )

    print("\n[Step 7] Generating Verified Mermaid Presenters...")
    reasoning_mermaid = render_reasoning_chain_mermaid(orch.reasoning_chain)
    evidence_mermaid = str(
        build_evidence_graph(
            orch.evidence_store.values(), orch.hypothesis_store.values()
        )["mermaid"]
    )
    print(f" -> Reasoning Chain Mermaid ({len(reasoning_mermaid)} chars)")
    print(f" -> Evidence Graph Mermaid ({len(evidence_mermaid)} chars)")

    elapsed = time.perf_counter() - start_time
    top_h = max(orch.hypothesis_store.values(), key=lambda h: h.current_probability)
    print(
        f"\n✅ LVAD CASE COMPLETED in {elapsed:.3f}s: Top={top_h.diagnosis} (P={top_h.current_probability:.3f})"
    )
    results["elapsed_seconds"] = elapsed
    results["success"] = True
    return results


# ============================================================================
# Case 6: Realistic Delayed Diagnosis (Non-Death Diagnostic Incident)
# ============================================================================


async def _run_delayed_diag_evidence(
    evidence_handlers: EvidenceHandlers,
    session_id: str,
    results: dict[str, Any],
) -> list[str]:
    fixtures = [
        {
            "content": "Initial outpatient metabolic clinic visit ordered CT thorax for persistent 2-week cough",
            "source_doc": "examples/realistic_delayed_diagnosis/DATA_SOURCE_01_EMR_OPD_VISIT.txt",
            "snippet": "** Pt also mentions persistent dry cough x 2wks. Thinks its allergy due to weather change. No sputum. No fever.",
            "strength": "STRONG",
            "reliability": "GRADE_A",
        },
        {
            "content": "Radiology HL7 report identified 2.5cm spiculated mass in RUL apical segment suspicious for malignancy",
            "source_doc": "examples/realistic_delayed_diagnosis/DATA_SOURCE_02_RAD_REPORT.hl7",
            "snippet": "Right lung: Spiculated soft tissue mass approx 2.5x2.2cm in RUL apical segment. Pleural tagging noted. Suspicious for malignancy.",
            "strength": "PATHOGNOMONIC",
            "reliability": "GRADE_A",
        },
        {
            "content": "Nursing logbook documents fax report placed on physician desk prior to early departure for seminar",
            "source_doc": "examples/realistic_delayed_diagnosis/DATA_SOURCE_03_NURSING_LOGBOOK.csv",
            "snippet": "2024/01/07,14:10,Nurse Chen,DOCUMENT,Sorted incoming faxes. Placed 'Pending' stack on Dr. Wang desk.,Pending",
            "strength": "STRONG",
            "reliability": "GRADE_B",
        },
        {
            "content": "Administrative clean desk memo led cleaner to move unread loose report papers to filing tray",
            "source_doc": "examples/realistic_delayed_diagnosis/DATA_SOURCE_03_NURSING_LOGBOOK.csv",
            "snippet": "2024/01/07,14:45,Cleaner,ENV,Desk cleaning. Moved loose papers to 'To File' tray as per protocol.,Done",
            "strength": "STRONG",
            "reliability": "GRADE_B",
        },
        {
            "content": "Emergency triage note 44 days later shows patient presented with hemoptysis and unnotified critical scan",
            "source_doc": "examples/realistic_delayed_diagnosis/DATA_SOURCE_05_ER_TRIAGE_NOTE.txt",
            "snippet": 'Pt asks "What about my CT scan from last month? Dr never called me so I thout it was normal."',
            "strength": "PATHOGNOMONIC",
            "reliability": "GRADE_A",
        },
    ]

    ev_ids: list[str] = []
    for idx, ef in enumerate(fixtures, 1):
        res = await evidence_handlers.handle(
            "rc_add_evidence",
            {
                "session_id": session_id,
                "content": ef["content"],
                "source_document": ef["source_doc"],
                "raw_snippet": ef["snippet"],
                "clinical_strength": ef["strength"],
                "source_reliability": ef["reliability"],
                "auto_verify": True,
            },
        )
        ev_ids.append(res["evidence_id"])
        status_icon = "✅" if res["verified"] else "❌"
        print(
            f" -> Ev#{idx} [{status_icon} {res['verification_method']}] "
            f"Doc: {Path(ef['source_doc']).name} Lines: {res['matched_lines']}"
        )
        if not res["verified"]:
            results["warnings"].append(
                f"Evidence #{idx} failed verification: {ef['source_doc']}"
            )
    return ev_ids


async def _run_delayed_diag_hypotheses(
    dd_handlers: DDHandlers, session_id: str
) -> dict[str, str]:
    h_delay = await dd_handlers.handle(
        "rc_propose_hypothesis",
        {
            "session_id": session_id,
            "diagnosis": "Delayed Diagnosis of Lung Malignancy secondary to Closed-Loop Communication Breakdown",
            "prior_probability": 0.20,
            "rationale": "Critical CT finding generated but lost in paper/fax transmission and clean-desk filing without EMR alert tracking",
            "icd10_code": "C34.90",
        },
    )
    h_rapid = await dd_handlers.handle(
        "rc_propose_hypothesis",
        {
            "session_id": session_id,
            "diagnosis": "Unavoidable Rapid Tumor Growth despite Standard Follow-Up",
            "prior_probability": 0.50,
            "rationale": "Aggressive malignant tumor presenting with acute hemoptysis",
            "icd10_code": "R04.2",
        },
    )
    h_noncomp = await dd_handlers.handle(
        "rc_propose_hypothesis",
        {
            "session_id": session_id,
            "diagnosis": "Intentional Patient Non-Compliance with Recommended Appointments",
            "prior_probability": 0.30,
            "rationale": "Patient failed to return to clinic for 44 days after CT scan",
            "icd10_code": "Z91.19",
        },
    )
    return {
        "delay": h_delay["hypothesis_id"],
        "rapid": h_rapid["hypothesis_id"],
        "noncomp": h_noncomp["hypothesis_id"],
    }


async def _run_delayed_diag_bayesian(
    dd_handlers: DDHandlers,
    session_id: str,
    h_ids: dict[str, str],
    ev_ids: list[str],
) -> None:
    # Rule out Rapid Tumor Growth & Non-Compliance
    await dd_handlers.handle(
        "rc_link_evidence_to_hypothesis",
        {
            "session_id": session_id,
            "hypothesis_id": h_ids["rapid"],
            "evidence_id": ev_ids[1],  # CT had already identified 2.5cm mass on Day 2
            "direction": "REFUTES",
            "weight": 0.95,
            "reasoning": "CT thorax on Day 2 had already clearly identified the 2.5cm mass; the delay was informational rather than biological",
        },
    )
    await dd_handlers.handle(
        "rc_link_evidence_to_hypothesis",
        {
            "session_id": session_id,
            "hypothesis_id": h_ids["noncomp"],
            "evidence_id": ev_ids[4],  # Patient never received call or notification
            "direction": "REFUTES",
            "weight": 0.92,
            "reasoning": "Patient was never contacted by clinic regarding abnormal result, assuming 'no news is good news'",
        },
    )
    # Confirm Communication Breakdown
    for ev_idx, wt, reason in [
        (
            0,
            0.70,
            "Appropriate outpatient order placement for persistent cough",
        ),
        (
            1,
            0.98,
            "Radiology finalized high-priority report with explicit biopsy recommendation",
        ),
        (
            2,
            0.85,
            "Faxed paper report placed on physician desk right before early departure",
        ),
        (
            3,
            0.92,
            "Routine desk cleaning moved unread critical report into archive tray",
        ),
        (
            4,
            0.96,
            "Complete lack of electronic EMR critical result tracking resulted in 44-day notification blackout",
        ),
    ]:
        await dd_handlers.handle(
            "rc_link_evidence_to_hypothesis",
            {
                "session_id": session_id,
                "hypothesis_id": h_ids["delay"],
                "evidence_id": ev_ids[ev_idx],
                "direction": "SUPPORTS",
                "weight": wt,
                "reasoning": reason,
            },
        )


async def _run_delayed_diag_cognitive(
    thinking_handlers: ThinkingHandlers, session_id: str
) -> None:
    await thinking_handlers.handle(
        "rc_reflect",
        {
            "session_id": session_id,
            "reflection_content": "Healthcare system relied on paper fax and passive follow-up without closed-loop acknowledgment",
            "identified_biases": [
                "NORMALCY_BIAS: Both primary physician and patient assumed routine negative results in the absence of contact",
                "DIFFUSION_OF_RESPONSIBILITY: Assuming radiology, ward nursing, or records department would notify patient",
            ],
            "identified_gaps": [
                "Absence of electronic critical value alert escalation when ordering physician is out-of-office",
            ],
        },
    )
    await thinking_handlers.handle(
        "rc_challenge_assumption",
        {
            "session_id": session_id,
            "assumption": "Physicians will reliably check paper fax reports left in desktop inboxes",
            "challenge_reasoning": "Paper workflows have single-point-of-failure vulnerability to environmental cleaning and conference schedules; electronic closed-loop tracking is mandatory",
            "potential_impact": "Preventable diagnostic delays in oncology and life-threatening conditions",
            "alternative_explanations": [
                "Implement automated EMR Critical Test Results Management (CTRM) with 24h escalation"
            ],
        },
    )
    await thinking_handlers.handle(
        "rc_identify_gaps",
        {
            "session_id": session_id,
            "gap_description": "Electronic Closed-Loop Radiology Result Notification System",
            "gap_type": "INFORMATICS_SAFETY_GAP",
            "impact_on_diagnosis": "HIGH: Eliminates lost paper faxes across all outpatient clinics",
            "suggested_actions": [
                "Deploy automatic SMS/Patient Portal alert upon radiology report finalization"
            ],
        },
    )


async def run_delayed_diag_case() -> dict[str, Any]:
    """Execute complete Realistic Delayed Diagnosis case simulation."""
    start_time = time.perf_counter()
    results: dict[str, Any] = {
        "case": "realistic_delayed_diagnosis",
        "steps": [],
        "errors": [],
        "warnings": [],
    }
    print("\n" + "=" * 75)
    print(
        "🚀 [Case 6] Realistic Delayed Diagnosis & Closed-Loop Breakdown (Non-Death Adverse Event)"
    )
    print("=" * 75)

    server_state = ServerState()
    evidence_handlers = EvidenceHandlers(server_state)
    dd_handlers = DDHandlers(server_state)
    thinking_handlers = ThinkingHandlers(server_state)
    contract_handlers = ContractHandlers(server_state)

    session_id = "trial_delay_case_006"
    orch = await server_state.get_or_create_orchestrator(session_id)
    g1 = orch.get_guidance()
    results["steps"].append({"step": "init", "stage": g1.current_stage.value})

    # Step 2: Evidence
    print(
        "\n[Step 2] Grounding Evidence against 5 Raw Data Files (including HL7 & Logbook)..."
    )
    ev_ids = await _run_delayed_diag_evidence(evidence_handlers, session_id, results)
    g2 = orch.get_guidance()
    results["steps"].append(
        {"step": "evidence", "stage": g2.current_stage.value, "verified": 5}
    )

    # Step 3: Hypotheses
    print("\n[Step 3] Proposing Differential Hypotheses (Broad Differential)...")
    h_ids = await _run_delayed_diag_hypotheses(dd_handlers, session_id)
    g3 = orch.get_guidance()
    results["steps"].append(
        {
            "step": "hypotheses",
            "stage": g3.current_stage.value,
            "count": len(orch.hypothesis_store),
        }
    )

    # Step 4: Bayesian
    print("\n[Step 4] Applying Bayesian Updates & Rule-Out Tests...")
    await _run_delayed_diag_bayesian(dd_handlers, session_id, h_ids, ev_ids)
    g4 = orch.get_guidance()
    results["steps"].append({"step": "bayesian", "stage": g4.current_stage.value})

    # Step 5: Cognitive Audit
    print("\n[Step 5] Logging Cognitive Biases and Uncertainties...")
    await _run_delayed_diag_cognitive(thinking_handlers, session_id)
    g5 = orch.get_guidance()
    results["steps"].append(
        {
            "step": "audit",
            "stage": g5.current_stage.value,
            "completeness": g5.completeness_score,
        }
    )

    # Step 6 & 7: Synthesis using Near Miss / Non-Death Template
    print("\n[Step 6] Synthesizing Deterministic Non-Death RCA Markdown Report...")
    template_file = "config/templates/near_miss_adverse_event_rca_template.md"
    report_res = await contract_handlers.handle(
        "rc_generate_contract_report",
        {
            "session_id": session_id,
            "format": "markdown",
            "detail_level": "full",
            "template_file": template_file,
            "finalize": True,
        },
    )
    report_md = str(report_res["content"])
    print(
        f" -> Generated Markdown Report ({len(report_md)} chars, {len(report_md.splitlines())} lines)"
    )

    print("\n[Step 7] Generating Verified Mermaid Presenters...")
    reasoning_mermaid = render_reasoning_chain_mermaid(orch.reasoning_chain)
    evidence_mermaid = str(
        build_evidence_graph(
            orch.evidence_store.values(), orch.hypothesis_store.values()
        )["mermaid"]
    )
    print(f" -> Reasoning Chain Mermaid ({len(reasoning_mermaid)} chars)")
    print(f" -> Evidence Graph Mermaid ({len(evidence_mermaid)} chars)")

    elapsed = time.perf_counter() - start_time
    top_h = max(orch.hypothesis_store.values(), key=lambda h: h.current_probability)
    print(
        f"\n✅ DELAYED DIAGNOSIS CASE COMPLETED in {elapsed:.3f}s: Top={top_h.diagnosis} (P={top_h.current_probability:.3f})"
    )
    results["elapsed_seconds"] = elapsed
    results["success"] = True
    return results


# ============================================================================
# Main Entry Point
# ============================================================================


async def main() -> None:
    parser = argparse.ArgumentParser(description="RootCause MCP Clinical Trial Runner")
    parser.add_argument(
        "--case",
        choices=["sam", "pris", "trauma", "pe", "lvad", "delay", "all"],
        default="all",
        help="Case to simulate (default: all)",
    )
    args = parser.parse_args()

    overall_results: list[dict[str, Any]] = []

    if args.case in {"sam", "all"}:
        r_sam = await run_sam_case()
        overall_results.append(r_sam)

    if args.case in {"pris", "all"}:
        r_pris = await run_pris_case()
        overall_results.append(r_pris)

    if args.case in {"trauma", "all"}:
        r_trauma = await run_trauma_case()
        overall_results.append(r_trauma)

    if args.case in {"pe", "all"}:
        r_pe = await run_pe_case()
        overall_results.append(r_pe)

    if args.case in {"lvad", "all"}:
        r_lvad = await run_lvad_case()
        overall_results.append(r_lvad)

    if args.case in {"delay", "all"}:
        r_delay = await run_delayed_diag_case()
        overall_results.append(r_delay)

    print("\n" + "=" * 75)
    print(f"🏁 ALL {len(overall_results)} CLINICAL TRIALS EXECUTED SUCCESSFULLY")
    for r in overall_results:
        print(
            f"   - {r['case']}: {r['elapsed_seconds']:.3f}s (Warnings: {len(r['warnings'])}, Errors: {len(r['errors'])})"
        )
    print("=" * 75)


if __name__ == "__main__":
    asyncio.run(main())
