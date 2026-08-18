"""
MCP Prompts Module for RootCause MCP (SDK 2.0).

Exposes expert clinical reasoning prompts directly to MCP clients
(Claude Desktop, VS Code Copilot Chat, Cline).
"""

from __future__ import annotations

from typing import Any

from mcp.types import (
    GetPromptResult,
    Prompt,
    PromptArgument,
    PromptMessage,
    TextContent,
)


def get_all_prompts() -> list[Prompt]:
    """Return all available clinical reasoning prompts."""
    return [
        Prompt(
            name="anesthesia_mm_investigation",
            title="Anesthesia Perioperative M&M Backward Causal Investigation",
            description=(
                "Guide the agent through a 4-Tier backward causal M&M root cause analysis on a "
                "perioperative cardiac arrest or critical collapse case (Tier 0 Rhythm -> Tier 1 5H5T -> "
                "Tier 2 Tri-stream [Patient vs Surgical vs Anesthesia] -> Tier 3 HFACS System Gaps)."
            ),
            arguments=[
                PromptArgument(
                    name="case_summary",
                    description="Summary of the perioperative cardiac arrest or critical event",
                    required=True,
                ),
                PromptArgument(
                    name="initial_rhythm",
                    description="Initial arrest rhythm (e.g. PEA, Asystole, VF/VT, Refractory Shock)",
                    required=False,
                ),
                PromptArgument(
                    name="surgery_type",
                    description="Surgical procedure performed (e.g., Total Hip Replacement, Laparoscopy)",
                    required=False,
                ),
            ],
        ),
        Prompt(
            name="perioperative_crisis_differential",
            title="Acute Intraoperative Shock & Paradoxical Deterioration Differential",
            description=(
                "Systematically investigate sudden post-induction hypotensive shock, evaluate "
                "paradoxical inotrope worsening (Dynamic LVOT Obstruction / SAM, LAST), "
                "and rule out massive PE, tension pneumothorax, and anaphylaxis."
            ),
            arguments=[
                PromptArgument(
                    name="clinical_presentation",
                    description="Patient presentation, vital signs, and onset timing",
                    required=True,
                ),
                PromptArgument(
                    name="drug_response",
                    description="Response to initial vasopressor/inotrope bolus (e.g. worsened with Epi)",
                    required=False,
                ),
            ],
        ),
        Prompt(
            name="near_miss_barrier_analysis",
            title="Non-Death Adverse Event & Near Miss Swiss Cheese Barrier RCA",
            description=(
                "Perform a structured Swiss Cheese defense barrier analysis on a non-death clinical "
                "near miss, medication adverse event, or device alarm incident to formulate poka-yoke error-proofing."
            ),
            arguments=[
                PromptArgument(
                    name="incident_description",
                    description="Description of the near-miss or adverse incident",
                    required=True,
                ),
                PromptArgument(
                    name="affected_department",
                    description="Clinical unit or department involved (e.g. ICU, Ward, OR, Pharmacy)",
                    required=False,
                ),
            ],
        ),
        Prompt(
            name="delayed_diagnosis_investigation",
            title="Delayed Diagnosis & Closed-Loop Communication Breakdown Investigation",
            description=(
                "Investigate a missed critical finding, radiology/pathology notification failure, "
                "or latent disease progression using the 6-phase delayed diagnosis timeline pattern."
            ),
            arguments=[
                PromptArgument(
                    name="missed_finding",
                    description="The critical diagnostic finding that was missed or delayed",
                    required=True,
                ),
                PromptArgument(
                    name="delay_duration",
                    description="Duration of the delay before discovery (e.g., '44 days')",
                    required=False,
                ),
            ],
        ),
    ]


def get_prompt_result(
    name: str, arguments: dict[str, Any] | None = None
) -> GetPromptResult:
    """
    Generate the structured PromptMessages for a requested clinical prompt.

    Args:
        name: Name of the prompt
        arguments: Argument values passed by the client host
    """
    args = arguments or {}

    if name == "anesthesia_mm_investigation":
        case_summary = args.get("case_summary", "Unknown Perioperative Arrest Case")
        rhythm = args.get("initial_rhythm", "PEA / Unspecified Shock")
        surgery = args.get("surgery_type", "Surgical Procedure")

        system_directive = (
            f"You are conducting a formal Anesthesiology Department M&M Root Cause Analysis for a case of '{surgery}'.\n\n"
            f"### Case Summary:\n{case_summary}\n"
            f"### Initial Rhythm / Event: {rhythm}\n\n"
            "### Mandatory 4-Tier Backward Causal Protocol:\n"
            "1. **Step 1: Physical Grounding**: Call `rc_add_evidence` with verbatim snippets and file locations for every key vitals, labs, and monitor finding.\n"
            "2. **Step 2: 5H5T Differential**: Call `rc_propose_hypothesis` to evaluate at least 3 plausible ACLS 5H5T causes (Hypovolemia, Hypoxia, Acidosis, Hyperkalemia, Tension Pneumothorax, Tamponade, Toxins/SAM/LAST, Pulmonary Embolism, MI).\n"
            "3. **Step 3: Tri-stream Retro-analysis**: Link evidence using `rc_link_evidence_to_hypothesis` and actively perform rule-out testing across:\n"
            "   - **Stream A**: Patient baseline substrate (e.g. undiagnosed septal hypertrophy, AS, frailty)\n"
            "   - **Stream B**: Surgical insults (e.g. lateral positioning, occult bleeding, cement BCIS, IVC compression)\n"
            "   - **Stream C**: Anesthesia management (e.g. propofol vasodilation, inotrope selection in SAM, syringe swap)\n"
            "4. **Step 4: Cognitive & System Audit**: Call `rc_reflect` and `rc_challenge_assumption` to document cognitive traps (anchoring on 'light anesthesia', alarm fatigue) and HFACS latent errors.\n"
            "5. **Step 5: Synthesize Final M&M Report**: Preview first, then call `rc_generate_contract_report(format='markdown', template_file='config/templates/anesthesia_mm_rca_report_template.md', finalize=True, approved_by='<authorized reviewer>')` only after readiness and safety gates pass.\n\n"
            "Begin by creating a session and adding the initial physical evidence records."
        )
        return GetPromptResult(
            description="Anesthesia Perioperative M&M 4-Tier Backward Causal Investigation Prompt",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(type="text", text=system_directive),
                )
            ],
        )

    elif name == "perioperative_crisis_differential":
        pres = args.get(
            "clinical_presentation", "Acute Hypotensive Collapse Post-Induction"
        )
        resp = args.get("drug_response", "Unspecified response")

        text = (
            f"Perform an expert differential diagnosis on acute intraoperative collapse:\n\n"
            f"**Presentation:** {pres}\n"
            f"**Drug / Resuscitation Response:** {resp}\n\n"
            "**Clinical Reasoning Directives:**\n"
            "1. Check for paradoxical worsening after inotropes/epinephrine (Dynamic LVOT Obstruction/SAM substrate).\n"
            "2. Actively rule out Massive PE (evaluate RV size on TEE) and Anaphylaxis (evaluate airway PIP).\n"
            "3. Check for ECG conduction delay or seizures following nerve block (LAST toxicity).\n"
            "4. Use `rc_add_evidence`, `rc_propose_hypothesis`, `rc_link_evidence_to_hypothesis`, and `rc_detect_conflicts` to maintain auditable Bayesian updating."
        )
        return GetPromptResult(
            description="Acute Perioperative Crisis Differential Prompt",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(type="text", text=text),
                )
            ],
        )

    elif name == "near_miss_barrier_analysis":
        desc = args.get("incident_description", "Clinical Near Miss Event")
        dept = args.get("affected_department", "Hospital Unit")

        text = (
            f"Conduct a Swiss Cheese Barrier Failure RCA for a near-miss / adverse incident in {dept}:\n\n"
            f"**Incident:** {desc}\n\n"
            "**Investigation Directives:**\n"
            "1. Reconstruct the event timeline using `rc_render_timeline(pattern='barrier_failure')`.\n"
            "2. Audit the 5 barrier layers: Ordering -> Dispensing -> Administration -> Monitoring -> Interception.\n"
            "3. Identify why the error was intercepted before causing irreversible harm.\n"
            "4. Formulate Poka-Yoke engineering controls and generate the near-miss report using `config/templates/near_miss_adverse_event_rca_template.md`."
        )
        return GetPromptResult(
            description="Near Miss Swiss Cheese Barrier Analysis Prompt",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(type="text", text=text),
                )
            ],
        )

    elif name == "delayed_diagnosis_investigation":
        finding = args.get("missed_finding", "Critical Finding")
        delay = args.get("delay_duration", "Unspecified Interval")

        text = (
            f"Investigate a delayed diagnosis breakdown ({delay} delay for '{finding}'):\n\n"
            "**Investigation Directives:**\n"
            "1. Reconstruct the 6-phase timeline with `rc_render_timeline(pattern='delayed_diagnosis')`.\n"
            "2. Analyze the communication breakdown between diagnostic service (Radiology/Pathology) and primary team.\n"
            "3. Review systemic vulnerabilities: non-closed-loop faxes, clean-desk paper displacement, lack of EMR critical value alert escalation.\n"
            "4. Synthesize recommendations for automated Electronic Critical Test Result Management (CTRM)."
        )
        return GetPromptResult(
            description="Delayed Diagnosis Closed-Loop Breakdown Prompt",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(type="text", text=text),
                )
            ],
        )

    raise ValueError(f"Unknown prompt name: {name}")
