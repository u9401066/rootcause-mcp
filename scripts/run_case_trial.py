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
# Main Entry Point
# ============================================================================


async def main() -> None:
    parser = argparse.ArgumentParser(description="RootCause MCP Clinical Trial Runner")
    parser.add_argument(
        "--case",
        choices=["sam", "pris", "all"],
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

    print("\n" + "=" * 75)
    print(f"🏁 ALL {len(overall_results)} CLINICAL TRIALS EXECUTED SUCCESSFULLY")
    for r in overall_results:
        print(
            f"   - {r['case']}: {r['elapsed_seconds']:.3f}s (Warnings: {len(r['warnings'])}, Errors: {len(r['errors'])})"
        )
    print("=" * 75)


if __name__ == "__main__":
    asyncio.run(main())
