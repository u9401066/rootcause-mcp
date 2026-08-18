"""
Condensed Facade Tool Definitions for RootCause MCP (SDK 2.0).

Reduces 46 discrete tools into 8 high-cohesion, action-based unified facade tools,
reducing tool schema context window overhead by >80% for AI Agents.
"""

from __future__ import annotations

from mcp.types import Tool

from rootcause_mcp.interface.tools.schema_fragments import (
    case_input_manifest_schema,
    clinical_temporal_input_schema,
    differential_breadth_audit_input_schema,
    hypothesis_classification_input_properties,
    likelihood_ratio_calibration_input_properties,
    planned_diagnostic_test_input_schema,
    timeline_event_input_schema,
)


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
                        "description": (
                            "Stable manifest document_id (for example 'SRC-001'); "
                            "legacy sessions may use a local path"
                        ),
                    },
                    "source_location": {
                        "type": "string",
                        "description": "Location within document (e.g., 'Line 42', 'CV line 14')",
                    },
                    "event_timestamp": {
                        "type": "string",
                        "format": "date-time",
                        "description": (
                            "Legacy alias for temporal.kind='instant' only; requires "
                            "'T' plus Z or a numeric timezone offset. Use temporal for date, "
                            "range, relative, or unknown time (action='add')."
                        ),
                    },
                    "temporal": clinical_temporal_input_schema(),
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
                    "verified_by": {
                        "type": "string",
                        "description": "Named reviewer (for action='verify')",
                        "default": "agent",
                    },
                    "manual_confirmation": {
                        "type": "boolean",
                        "default": False,
                        "description": "Explicit human confirmation; verified_by must be in ROOTCAUSE_AUTHORIZED_REVIEWERS",
                    },
                    "document_id": {
                        "type": "string",
                        "description": (
                            "Optional stable document_id; manifest-bound evidence cannot "
                            "be rebound to another source (for action='verify')"
                        ),
                    },
                },
                "required": ["session_id"],
            },
        ),
        Tool(
            name="rc_hypothesis",
            description=(
                "Unified Differential Diagnosis (DDx): Propose, link evidence (Bayesian update), rank, or exclude hypotheses. "
                "Actions: 'propose' (create hypothesis with prior & reasoning), "
                "'audit_breadth' (persist systematic framework coverage), "
                "'link' (apply LR to update probability), "
                "'select_leading' (explicitly select the current lead with history), "
                "'rank' (get ledger-order differential diagnoses), 'exclude' (rule out hypothesis with reason)."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "propose",
                            "audit_breadth",
                            "link",
                            "select_leading",
                            "rank",
                            "exclude",
                        ],
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
                        "description": (
                            "Numeric Bayesian starting value. Omission uses a neutral "
                            "0.5 UNCALIBRATED implementation baseline, not a clinical "
                            "probability or certainty label."
                        ),
                        "default": 0.5,
                    },
                    "must_not_miss": {
                        "type": "boolean",
                        "description": "Explicit high-harm rule-out marker (for action='propose')",
                        "default": False,
                    },
                    **hypothesis_classification_input_properties(),
                    "differential_diagnoses_considered": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": (
                            "DEPRECATED context-only notes. Propose every plausible "
                            "candidate separately; this cannot replace audit_breadth "
                            "or justify exclusion."
                        ),
                    },
                    "uncertainty_factors": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Known diagnostic uncertainty factors",
                    },
                    "confidence_rationale": {
                        "type": "string",
                        "description": (
                            "Why the candidate is considered and the calibration/source "
                            "limitations of any numeric prior"
                        ),
                    },
                    "planned_tests": {
                        "type": "array",
                        "items": planned_diagnostic_test_input_schema(),
                        "description": (
                            "Typed pending diagnostic tests for action='propose'; "
                            "the server binds each target to the new hypothesis"
                        ),
                    },
                    "breadth_audit": {
                        **differential_breadth_audit_input_schema(),
                        "description": (
                            "Typed systematic DDx coverage artifact for "
                            "action='audit_breadth'"
                        ),
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
                        "enum": [
                            "SUPPORTS",
                            "REFUTES",
                            "CONTRADICTS",
                            "NEUTRAL",
                        ],
                        "description": (
                            "Direction for action='link': SUPPORTS only with LR>1, "
                            "REFUTES/CONTRADICTS only with LR<1, and NEUTRAL only "
                            "with LR=1. Omit to derive from the direct LR."
                        ),
                    },
                    "likelihood_ratio": {
                        "type": "number",
                        "minimum": 0.01,
                        "maximum": 100.0,
                        "description": (
                            "Direct applied likelihood ratio for action='link': >1 "
                            "supports, <1 refutes, and 1.0 is neutral. The server "
                            "never invents, converts, or inverts an LR."
                        ),
                    },
                    **likelihood_ratio_calibration_input_properties(),
                    "reason": {
                        "type": "string",
                        "minLength": 10,
                        "description": (
                            "Reason for selection (action='select_leading') or "
                            "exclusion (action='exclude')"
                        ),
                    },
                    "changed_by": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 128,
                        "description": (
                            "Auditable identity for action='select_leading'"
                        ),
                    },
                },
                "required": ["session_id"],
                "allOf": [
                    {
                        "if": {
                            "properties": {"action": {"const": "link"}},
                            "required": ["action"],
                        },
                        "then": {"required": ["calibration_status"]},
                    },
                    {
                        "if": {
                            "properties": {"action": {"const": "select_leading"}},
                            "required": ["action"],
                        },
                        "then": {
                            "required": [
                                "hypothesis_id",
                                "reason",
                                "changed_by",
                            ]
                        },
                    },
                    {
                        "if": {
                            "properties": {
                                "calibration_status": {"const": "SOURCE_CALIBRATED"}
                            },
                            "required": ["calibration_status"],
                        },
                        "then": {"required": ["calibration_source_ref"]},
                    },
                ],
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
                        "minimum": 0,
                        "maximum": 1,
                        "description": (
                            "Optional caller-supplied compatibility metadata; not "
                            "clinical probability or calibrated confidence"
                        ),
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
                "or perform a conservative counterfactual causation audit that does "
                "not establish clinical causality. "
                "Actions: 'stage_guidance' (audit stage progression & next prompt directives), "
                "'detect_conflicts' (auto-detect contradictions & guideline omissions), "
                "'verify_causation' (compatibility action name; conservative 4-factor audit)."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "stage_guidance",
                            "detect_conflicts",
                            "verify_causation",
                        ],
                        "description": "Audit operation to perform",
                        "default": "stage_guidance",
                    },
                    "session_id": {
                        "type": "string",
                        "description": "RCA session ID",
                    },
                    "cause": {
                        "type": "object",
                        "description": (
                            "Cause event {id, description, evidence, timestamp}; id, "
                            "description, and evidence must exactly match a persisted Why "
                            "root for durable audits. If timestamp is supplied "
                            "it must contain 'T' and end in Z or a numeric timezone offset "
                            "(for action='verify_causation')"
                        ),
                        "properties": {
                            "id": {"type": "string"},
                            "description": {"type": "string"},
                            "evidence": {
                                "type": "array",
                                "items": {"type": "string"},
                                "minItems": 1,
                                "uniqueItems": True,
                            },
                            "timestamp": {"type": "string", "format": "date-time"},
                        },
                        "required": ["id", "description", "evidence"],
                    },
                    "effect": {
                        "type": "object",
                        "description": (
                            "Effect event {description, evidence, timestamp}; evidence "
                            "must resolve in the clinical ledger. If timestamp is supplied "
                            "it must contain 'T' and end in Z or a numeric timezone offset "
                            "(for action='verify_causation')"
                        ),
                        "properties": {
                            "id": {"type": "string"},
                            "description": {"type": "string"},
                            "evidence": {
                                "type": "array",
                                "items": {"type": "string"},
                                "minItems": 1,
                                "uniqueItems": True,
                            },
                            "timestamp": {"type": "string", "format": "date-time"},
                        },
                        "required": ["description", "evidence"],
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
                    "locale": {
                        "type": "string",
                        "enum": ["en", "zh-TW"],
                        "description": (
                            "Built-in Markdown renderer locale; default: en"
                        ),
                        "default": "en",
                    },
                    "audience": {
                        "type": "string",
                        "enum": ["general", "clinician"],
                        "description": (
                            "Markdown audience; clinician expands evidence-grounded "
                            "DDx discussion while preserving English medical terms"
                        ),
                        "default": "general",
                    },
                    "template_file": {
                        "type": "string",
                        "description": "Optional path to custom Markdown template file",
                    },
                    "finalize": {
                        "type": "boolean",
                        "description": "Finalize only after readiness, conflict, manifest, and reviewer gates pass",
                        "default": False,
                    },
                    "approved_by": {
                        "type": "string",
                        "description": "Explicit reviewer identity from ROOTCAUSE_AUTHORIZED_REVIEWERS; required when finalize=true",
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
                        "enum": [
                            "timeline",
                            "validate",
                            "reasoning_chain",
                            "evidence_graph",
                        ],
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
                    "events": {
                        "type": "array",
                        "items": timeline_event_input_schema(),
                        "description": (
                            "Optional custom timeline events with typed temporal "
                            "semantics (for action='timeline')."
                        ),
                    },
                    "include_table": {
                        "type": "boolean",
                        "description": "Include Markdown event table (for action='timeline')",
                        "default": True,
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
                "Unified Case Snapshotting & Branching: Create integrity-checked, timestamped snapshots of active case state, "
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
                            "session_adjudicate_source",
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
                    "case_title": {
                        "type": "string",
                        "description": "Case title (for session_start)",
                    },
                    "case_type": {
                        "type": "string",
                        "enum": [
                            "death",
                            "complication",
                            "near_miss",
                            "safety",
                            "staffing",
                        ],
                        "description": "Case type (for session_start)",
                    },
                    "source_manifest": {
                        **case_input_manifest_schema(),
                        "description": "Versioned raw-source manifest (for session_start)",
                    },
                    "document_id": {
                        "type": "string",
                        "description": "Manifest document_id (for session_adjudicate_source)",
                    },
                    "source_status": {
                        "type": "string",
                        "enum": ["extracted", "reviewed", "failed"],
                    },
                    "de_identified": {"type": "boolean"},
                    "independence_status": {
                        "type": "string",
                        "enum": ["unknown", "independent", "derived"],
                    },
                    "source_group_id": {"type": "string"},
                    "parent_document_id": {"type": "string"},
                    "derivation_method": {"type": "string"},
                    "reviewed_by": {
                        "type": "string",
                        "description": "Allowlisted reviewer for source adjudication",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Auditable source-review rationale",
                    },
                    "problem_statement": {
                        "type": "string",
                        "description": "Initial problem (for fishbone_init, why_ask)",
                    },
                    "category": {
                        "type": "string",
                        "description": "Personnel, Equipment, Material, Process, Environment, Monitoring",
                    },
                    "description": {
                        "type": "string",
                        "description": "Description of cause or finding",
                    },
                    "cause_id": {
                        "type": "string",
                        "description": "Persisted Fishbone cause ID (for hfacs_confirm)",
                    },
                    "answer": {
                        "type": "string",
                        "description": "Answer to why question (for why_ask)",
                    },
                    "source_node_id": {
                        "type": "string",
                        "description": "Source Why node ID (for why_link)",
                    },
                    "target_node_id": {
                        "type": "string",
                        "description": "Target Why node ID (for why_link)",
                    },
                    "relationship": {
                        "type": "string",
                        "description": "contributes_to, escalates, mitigates, feedback",
                    },
                    "hfacs_code": {
                        "type": "string",
                        "description": "Recognized HFACS classification code",
                    },
                    "review_status": {
                        "type": "string",
                        "enum": ["CONFIRMED", "NOT_APPLICABLE"],
                        "description": "Persisted HFACS review disposition",
                    },
                },
            },
        ),
    ]
