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

_CLINICIAN_ZH_TW_OUTPUT = (
    "\n\n### Clinician-facing output convention\n"
    "Write clinician-facing discussion in Traditional Chinese. Keep canonical diagnosis, "
    "test, drug, device, and procedure names in English; on first use, an established "
    "abbreviation may include an optional Traditional Chinese gloss. Preserve verbatim "
    "source text and units. Keep observation, clinical inference, and causal claim visibly "
    "separate. Do not invent a probability, LR, citation, translation, or causal conclusion."
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
        Prompt(
            name="clinician_ddx_discussion_zh_tw",
            title="Clinician-Facing zh-TW Mechanism-Based DDx Discussion",
            description=(
                "Guide the host Agent to produce a bounded, mechanism-based differential "
                "diagnosis discussion in Traditional Chinese with English canonical medical "
                "names, source-linked evidence, explicit unknowns, discriminating tests, and "
                "qualitative certainty."
            ),
            arguments=[
                PromptArgument(
                    name="case_context",
                    description=(
                        "De-identified phenotype, time course, and source-linked case facts"
                    ),
                    required=True,
                ),
                PromptArgument(
                    name="clinical_question",
                    description="Clinical question the differential should address",
                    required=False,
                ),
                PromptArgument(
                    name="known_unknowns",
                    description=(
                        "Known missing, pending, conflicting, or unverified information"
                    ),
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
            "2. **Step 2: 5H5T Differential**: Review every canonical 5H5T cell and persist a PRIMARY `FIVE_H_FIVE_T` breadth audit with `rc_audit_differential_breadth` (or `rc_hypothesis(action='audit_breadth')`). Propose every plausible cause with source-linked evidence or a discriminator; mark a reviewed empty cell explicitly, and never treat insufficient data as exclusion. Three unique diagnoses are only a deterministic finalization floor, not a stopping target or cap.\n"
            "3. **Step 3: Tri-stream Retro-analysis**: Link evidence using `rc_link_evidence_to_hypothesis` and actively perform rule-out testing across:\n"
            "   - **Stream A**: Patient baseline substrate (e.g. undiagnosed septal hypertrophy, AS, frailty)\n"
            "   - **Stream B**: Surgical insults (e.g. lateral positioning, occult bleeding, cement BCIS, IVC compression)\n"
            "   - **Stream C**: Anesthesia management (e.g. propofol vasodilation, inotrope selection in SAM, syringe swap)\n"
            "4. **Step 4: Cognitive & System Audit**: Call `rc_reflect` and `rc_challenge_assumption` to document cognitive traps (anchoring on 'light anesthesia', alarm fatigue) and HFACS latent errors.\n"
            "5. **Step 5: Synthesize Final M&M Report**: Preview first, then call `rc_generate_contract_report(format='markdown', template_file='config/templates/anesthesia_mm_rca_report_template.md', finalize=True, approved_by='<authorized reviewer>')` only after readiness and safety gates pass.\n\n"
            "Begin by creating a session and adding the initial physical evidence records."
            + _CLINICIAN_ZH_TW_OUTPUT
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
            "The named diagnoses below are candidate prompts for systematic review, not assumed diagnoses or evidence that they are present.\n"
            "1. Define the phenotype/time course, select a syndrome-appropriate framework, and review every cell with `rc_audit_differential_breadth` (or `rc_hypothesis(action='audit_breadth')`). Retain insufficient data with unknowns and discriminators; three diagnoses are only a finalization floor.\n"
            "2. Check for paradoxical worsening after inotropes/epinephrine (Dynamic LVOT Obstruction/SAM substrate).\n"
            "3. Actively rule out Massive PE (evaluate RV size on TEE) and Anaphylaxis (evaluate airway PIP).\n"
            "4. Check for ECG conduction delay or seizures following nerve block (LAST toxicity).\n"
            "5. Use `rc_add_evidence`, `rc_propose_hypothesis`, `rc_link_evidence_to_hypothesis`, and `rc_detect_conflicts` to maintain auditable Bayesian updating."
            + _CLINICIAN_ZH_TW_OUTPUT
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
            "4. Record source-linked candidate Poka-Yoke controls as `PROPOSED`, each with an accountable owner, due date, verification measure, and governance approval state; do not auto-approve an action. Preview the near-miss report using `config/templates/near_miss_adverse_event_rca_template.md`."
            + _CLINICIAN_ZH_TW_OUTPUT
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
            "4. Record source-linked candidate actions (which may include Electronic Critical Test Result Management, CTRM) only when the barrier analysis supports them. Keep each action `PROPOSED` with owner, due date, verification measure, and governance approval state; do not auto-approve a recommendation."
            + _CLINICIAN_ZH_TW_OUTPUT
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

    elif name == "clinician_ddx_discussion_zh_tw":
        context = args.get("case_context", "未提供 case context")
        question = args.get(
            "clinical_question", "找出可解釋目前 phenotype 與 time course 的鑑別診斷"
        )
        unknowns = args.get(
            "known_unknowns", "尚未整理；必須從來源缺口、pending 與 conflicts 主動盤點"
        )

        text = (
            "你是使用 RootCause MCP ledger 的 host Agent。MCP 本身不會思考或下診斷；"
            "你負責臨床推論，MCP 只保存與檢查可稽核狀態。本專案仍是 engineering alpha，"
            "產物必須由 qualified clinician 審閱。\n\n"
            f"### Case context\n{context}\n\n"
            f"### Clinical question\n{question}\n\n"
            f"### Known unknowns\n{unknowns}\n\n"
            "### 推理與 ledger 指令\n"
            "1. 先以 phenotype 與 time course 定義問題，將每一敘述區分為 source observation、"
            "clinical inference 或 causal claim；不得把 inference 寫成 observation。\n"
            "2. 展開最大合理的 mechanism-based DDx。三個不重複診斷、兩個非 UNKNOWN mechanism "
            "與一個適用的 must-not-miss 是 finalization floor，不是推理目標或上限；合併同義項，"
            "刪除沒有 plausible mechanism 或 decision impact 的項目，避免無限 laundry list。\n"
            "3. 選擇 syndrome-appropriate framework（例如 VINDICATE、FIVE_H_FIVE_T、"
            "ANATOMIC_SYSTEM 或 MEDICATION_DEVICE_EXPOSURE），用 `rc_audit_differential_breadth`"
            "（condensed: `rc_hypothesis(action='audit_breadth')`）逐格記錄。每格必須是 "
            "CANDIDATES_PRESENT、REVIEWED_NO_PLAUSIBLE_CANDIDATE、"
            "REVIEWED_INSUFFICIENT_DATA 或 NOT_ASSESSED；final PRIMARY audit 不得留下 "
            "NOT_ASSESSED。INSUFFICIENT_DATA 要列 unknowns 與 typed planned discriminators，"
            "不得當作排除。\n"
            "4. 每個 active candidate 必須記錄 canonical English diagnosis、mechanism_category、"
            "diagnostic_role、reasoning_basis、qualitative certainty、why considered、source-linked "
            "support/refutation/neutral evidence、candidate-specific unknowns，以及 discriminating test "
            "的 purpose/status/預期支持與反證結果。must-not-miss 表示 safety priority，不等於 likelihood。\n"
            "5. 將 unknown 分為 not documented、not measured、pending、conflicting、unverified 或 "
            "unknown；說明它保留哪些 mechanism、影響哪些 candidate，以及何種資料可解決。"
            "Unknown 不得當作 negative finding。\n"
            "6. 僅使用可追溯的 direct LR：>1 support、<1 refute、LR=1.0 neutral/quantitatively "
            "unknown。LR=1.0 不得計為支持或反證。不得捏造 probability、LR、confidence percentage "
            "或 citation；未校準的 prior/posterior 只能標為 implementation placeholder，不得呈現為"
            " clinical probability、rank 或 certainty。\n"
            "7. leading 與每個 must-not-miss 都要有 genuine support，並有真正的 refuting evidence "
            "或 pending DISCONFIRM/RULE_OUT test。較高 certainty 需 genuine evidence 或 completed "
            "discriminating test，CONFIRMED 必須與 persisted status 一致。\n"
            "8. 先 preview 並檢查 conflicts/readiness。需要內建繁中臨床版時，呼叫 "
            "`rc_generate_contract_report(format='markdown', locale='zh-TW', "
            "audience='clinician', finalize=False)`；custom template 保留自身語言，JSON/FHIR values "
            "不翻譯。\n\n"
            "### 輸出結構\n"
            "以繁體中文撰寫：分析狀態與限制、關鍵 observations、逐項 DDx（角色／mechanism／"
            "certainty、Why considered、支持、反證、Neutral、Unknown、Discriminating test）、"
            "整體 interpretation（分列 observation/inference/causal claim）、未解安全問題與 "
            "clinician review。Diagnosis、test、drug、device、procedure 名稱保留 English；"
            "首次既定縮寫可附繁中對照，原始 quote 與 units 不翻譯。"
        )
        return GetPromptResult(
            description="Clinician-Facing Traditional Chinese Mechanism-Based DDx Prompt",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(type="text", text=text),
                )
            ],
        )

    raise ValueError(f"Unknown prompt name: {name}")
