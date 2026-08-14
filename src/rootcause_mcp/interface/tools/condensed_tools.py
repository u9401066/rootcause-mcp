"""
Condensed Facade Tool Definitions for RootCause MCP (SDK 2.0).

Reduces 43 discrete tools into 8 high-cohesion, action-based unified facade tools,
reducing tool schema context window overhead by >80% for AI Agents.
"""

from __future__ import annotations

from mcp.types import Tool


def get_condensed_tools() -> list[Tool]:
    """Return the 8 unified facade tool definitions."""
    return [
        Tool(
            name="rc_evidence",
            description=(
                "Unified Evidence Management: Add, retrieve, or deterministically verify physical evidence. "
                "Actions: 'add' (register clinical finding with raw snippet & hash), "
                "'get' (retrieve evidence by ID), 'verify' (verify verbatim quote against file on disk)."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["add", "get", "verify"],
                        "description": "Evidence operation to perform",
                        "default": "add",
                    },
                    "session_id": {
                        "type": "string",
                        "description": "RCA session ID",
                    },
                    "content": {
                        "type": "string",
                        "description": "Natural language evidence description (for action='add')",
                    },
                    "evidence_id": {
                        "type": "string",
                        "description": "Evidence ID (for action='get' or 'verify')",
                    },
                    "source_document": {
                        "type": "string",
                        "description": "Source file name or path (e.g. 'flowsheet.csv', 'RAD_REPORT.hl7')",
                    },
                    "source_location": {
                        "type": "string",
                        "description": "Location within document (e.g., 'Line 42', 'CV line 14')",
                    },
                    "raw_snippet": {
                        "type": "string",
                        "description": "Exact literal quote from the raw document for deterministic lineage",
                    },
                    "clinical_strength": {
                        "type": "string",
                        "enum": ["STRONG", "MODERATE", "WEAK", "ANECDOTAL"],
                        "description": "Evidence strength grade (default: MODERATE)",
                        "default": "MODERATE",
                    },
                    "source_reliability": {
                        "type": "string",
                        "enum": ["GRADE_A", "GRADE_B", "GRADE_C", "GRADE_D"],
                        "description": "Source reliability grade (default: GRADE_B)",
                        "default": "GRADE_B",
                    },
                    "evidence_type": {
                        "type": "string",
                        "description": "DOCUMENT, OBSERVATION, LAB_RESULT, IMAGING, DEVICE_LOG, MEDICATION_RECORD",
                        "default": "DOCUMENT",
                    },
                    "auto_verify": {
                        "type": "boolean",
                        "description": "Automatically verify snippet against disk file (default: true)",
                        "default": True,
                    },
                },
                "required": ["session_id"],
            },
        ),
        Tool(
            name="rc_hypothesis",
            description=(
                "Unified Differential Diagnosis (DDx): Propose, link evidence (Bayesian update), rank, or exclude hypotheses. "
                "Actions: 'propose' (create hypothesis with prior & reasoning), 'link' (apply LR to update probability), "
                "'rank' (get ranked differential diagnoses), 'exclude' (rule out hypothesis with reason)."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["propose", "link", "rank", "exclude"],
                        "description": "Hypothesis operation to perform",
                        "default": "propose",
                    },
                    "session_id": {
                        "type": "string",
                        "description": "RCA session ID",
                    },
                    "diagnosis": {
                        "type": "string",
                        "description": "Diagnosis name (for action='propose')",
                    },
                    "icd10_code": {
                        "type": "string",
                        "description": "ICD-10 code (e.g., 'I42.1', 'T88.59', 'I26.0')",
                    },
                    "prior_probability": {
                        "type": "number",
                        "description": "Prior probability P(H) between 0.0 and 1.0 (default: 0.1)",
                        "default": 0.1,
                    },
                    "clinical_reasoning": {
                        "type": "string",
                        "description": "Clinical reasoning rationale for proposing/linking this hypothesis",
                    },
                    "hypothesis_id": {
                        "type": "string",
                        "description": "Hypothesis ID (for action='link' or 'exclude')",
                    },
                    "evidence_id": {
                        "type": "string",
                        "description": "Evidence ID (for action='link')",
                    },
                    "direction": {
                        "type": "string",
                        "enum": ["SUPPORTS", "REFUTES", "CONTRADICTS"],
                        "description": "Direction of evidence effect (for action='link')",
                        "default": "SUPPORTS",
                    },
                    "weight": {
                        "type": "number",
                        "description": "Strength weight (0.0 to 1.0) or exact likelihood ratio (for action='link')",
                    },
                    "likelihood_ratio": {
                        "type": "number",
                        "description": "Exact Bayesian likelihood ratio (LR+ or LR-)",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for exclusion (for action='exclude')",
                    },
                },
                "required": ["session_id"],
            },
        ),
        Tool(
            name="rc_thinking",
            description=(
                "Unified Cognitive Transparency & Metacognition: Record internal agent rationale, reflections, "
                "evidence gaps, and challenged assumptions. "
                "Actions: 'think' (record explicit decision point), 'reflect' (metacognitive review & biases), "
                "'gap' (identify missing test/data), 'challenge' (question clinical assumption), 'get_chain' (retrieve thinking history)."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["think", "reflect", "gap", "challenge", "get_chain"],
                        "description": "Thinking operation to perform",
                        "default": "think",
                    },
                    "session_id": {
                        "type": "string",
                        "description": "RCA session ID",
                    },
                    "content": {
                        "type": "string",
                        "description": "Main thought or decision description (for action='think')",
                    },
                    "internal_reasoning": {
                        "type": "string",
                        "description": "Clinical explanation and rationale (for action='think')",
                    },
                    "thinking_type": {
                        "type": "string",
                        "enum": [
                            "HYPOTHESIS_CONSIDERED",
                            "EVIDENCE_EVALUATED",
                            "UNCERTAINTY_ACKNOWLEDGED",
                            "ASSUMPTION_QUESTIONED",
                            "EVIDENCE_GAP_IDENTIFIED",
                            "BIAS_CHECK",
                            "DECISION_POINT",
                        ],
                        "default": "DECISION_POINT",
                    },
                    "confidence": {
                        "type": "number",
                        "description": "Confidence level between 0.0 and 1.0",
                        "default": 0.8,
                    },
                    "reflection_content": {
                        "type": "string",
                        "description": "Metacognitive reflection text (for action='reflect')",
                    },
                    "identified_biases": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of identified cognitive biases (e.g. ['ANCHORING', 'CONFIRMATION_BIAS'])",
                    },
                    "identified_gaps": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of identified missing clinical data points",
                    },
                    "gap_description": {
                        "type": "string",
                        "description": "Description of missing diagnostic test or parameter (for action='gap')",
                    },
                    "gap_type": {
                        "type": "string",
                        "description": "MISSING_DATA, PROCESS_GAP, KNOWLEDGE_GAP",
                        "default": "MISSING_DATA",
                    },
                    "assumption": {
                        "type": "string",
                        "description": "The clinical assumption being questioned (for action='challenge')",
                    },
                    "challenge_reasoning": {
                        "type": "string",
                        "description": "Why the assumption may be flawed or dangerous (for action='challenge')",
                    },
                },
                "required": ["session_id"],
            },
        ),
        Tool(
            name="rc_audit",
            description=(
                "Unified Clinical Audit & Verification: Audit reasoning readiness, detect contradictions/guideline gaps, "
                "or perform counterfactual causation verification. "
                "Actions: 'stage_guidance' (audit stage progression & next prompt directives), "
                "'detect_conflicts' (auto-detect contradictions & guideline omissions), "
                "'verify_causation' (4-factor counterfactual causation check)."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["stage_guidance", "detect_conflicts", "verify_causation"],
                        "description": "Audit operation to perform",
                        "default": "stage_guidance",
                    },
                    "session_id": {
                        "type": "string",
                        "description": "RCA session ID",
                    },
                    "cause": {
                        "type": "object",
                        "description": "Cause event {description, timestamp} (for action='verify_causation')",
                    },
                    "effect": {
                        "type": "object",
                        "description": "Effect event {description, timestamp} (for action='verify_causation')",
                    },
                    "verification_level": {
                        "type": "string",
                        "enum": ["standard", "comprehensive"],
                        "default": "standard",
                    },
                },
                "required": ["session_id"],
            },
        ),
        Tool(
            name="rc_report",
            description=(
                "Unified Deterministic Report Synthesis: Generate auditable Markdown, FHIR DiagnosticReport, or JSON reports. "
                "Supports custom template overrides (e.g. 'config/templates/anesthesia_mm_rca_report_template.md', "
                "'config/templates/near_miss_adverse_event_rca_template.md') with zero server-side LLM tokens."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["generate", "preview"],
                        "default": "generate",
                    },
                    "session_id": {
                        "type": "string",
                        "description": "RCA session ID",
                    },
                    "format": {
                        "type": "string",
                        "enum": ["markdown", "fhir", "json"],
                        "description": "Output format (default: markdown)",
                        "default": "markdown",
                    },
                    "detail_level": {
                        "type": "string",
                        "enum": ["brief", "standard", "full"],
                        "description": "Markdown detail level (default: standard)",
                        "default": "standard",
                    },
                    "template_file": {
                        "type": "string",
                        "description": "Optional path to custom Markdown template file",
                    },
                    "finalize": {
                        "type": "boolean",
                        "description": "Finalize report and compute SHA-256 cryptographic content digest",
                        "default": False,
                    },
                },
                "required": ["session_id"],
            },
        ),
        Tool(
            name="rc_diagram",
            description=(
                "Unified Diagram Generation & Syntax Validator: Render chronological timelines, evidence graphs, "
                "reasoning chains, fishbone, why trees, or validate/auto-sanitize custom Mermaid syntax. "
                "Actions: 'timeline' (5 clinical patterns), 'validate' (syntax audit & auto-fix), "
                "'reasoning_chain' (audit trail diagram), 'evidence_graph' (support/contradict network)."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["timeline", "validate", "reasoning_chain", "evidence_graph"],
                        "description": "Diagram operation to perform",
                        "default": "timeline",
                    },
                    "session_id": {
                        "type": "string",
                        "description": "RCA session ID (for timeline, reasoning_chain, evidence_graph)",
                    },
                    "pattern": {
                        "type": "string",
                        "enum": [
                            "auto",
                            "perioperative_sequence",
                            "acute_crisis",
                            "delayed_diagnosis",
                            "barrier_failure",
                            "device_incident",
                            "custom",
                        ],
                        "description": "Clinical timeline pattern (for action='timeline')",
                        "default": "auto",
                    },
                    "title": {
                        "type": "string",
                        "description": "Custom diagram title (for action='timeline')",
                    },
                    "mermaid_source": {
                        "type": "string",
                        "description": "Raw Mermaid code to audit and auto-sanitize (for action='validate')",
                    },
                    "diagram_type": {
                        "type": "string",
                        "description": "flowchart, timeline, sequenceDiagram, etc. (for action='validate')",
                    },
                    "auto_fix": {
                        "type": "boolean",
                        "description": "Auto-fix quotes, brackets, and colons (for action='validate')",
                        "default": True,
                    },
                },
            },
        ),
        Tool(
            name="rc_checkpoint",
            description=(
                "Unified Case Snapshotting & Branching: Create immutable, timestamped snapshots of active case state, "
                "list available checkpoints, or restore cases without context loss. "
                "Actions: 'create' (save snapshot with SHA-256 digest), 'list' (view all checkpoints), 'restore' (load state)."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["create", "list", "restore"],
                        "description": "Checkpoint operation to perform",
                        "default": "create",
                    },
                    "session_id": {
                        "type": "string",
                        "description": "RCA session ID",
                    },
                    "tag": {
                        "type": "string",
                        "description": "Human-readable tag (for action='create')",
                    },
                    "notes": {
                        "type": "string",
                        "description": "Snapshot notes (for action='create')",
                    },
                    "checkpoint_id": {
                        "type": "string",
                        "description": "Checkpoint ID (for action='restore')",
                    },
                },
                "required": ["session_id"],
            },
        ),
        Tool(
            name="rc_rca",
            description=(
                "Unified Traditional RCA (Fishbone, 5-Why, HFACS-MES, Session): "
                "Execute traditional 6M Ishikawa diagrams, 5-Why root cause drill-down, "
                "HFACS-MES human factors classification, and RCA session lifecycle."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "session_start",
                            "session_get",
                            "session_list",
                            "session_archive",
                            "fishbone_init",
                            "fishbone_add_cause",
                            "fishbone_get",
                            "fishbone_export",
                            "why_ask",
                            "why_get",
                            "why_link",
                            "why_mark_root",
                            "why_export",
                            "why_teach",
                            "hfacs_suggest",
                            "hfacs_confirm",
                            "hfacs_framework",
                        ],
                        "description": "RCA operation to perform",
                        "default": "session_start",
                    },
                    "session_id": {"type": "string", "description": "Session ID"},
                    "case_title": {"type": "string", "description": "Case title (for session_start)"},
                    "case_type": {"type": "string", "description": "death, sentinel, near_miss (for session_start)"},
                    "problem_statement": {"type": "string", "description": "Initial problem (for fishbone_init, why_ask)"},
                    "category": {"type": "string", "description": "Personnel, Equipment, Material, Process, Environment, Monitoring"},
                    "description": {"type": "string", "description": "Description of cause or finding"},
                    "answer": {"type": "string", "description": "Answer to why question (for why_ask)"},
                    "source_node_id": {"type": "string", "description": "Source Why node ID (for why_link)"},
                    "target_node_id": {"type": "string", "description": "Target Why node ID (for why_link)"},
                    "relationship": {"type": "string", "description": "contributes_to, escalates, mitigates, feedback"},
                    "hfacs_code": {"type": "string", "description": "HFACS classification code (e.g. UA-S, PC-C)"},
                },
            },
        ),
    ]
