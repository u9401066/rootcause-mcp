"""
Evidence Management MCP Tools.

Tools for adding, retrieving, and linking evidence in clinical reasoning.
"""

from __future__ import annotations

from mcp.types import Tool


def get_evidence_tools() -> list[Tool]:
    """Get all evidence management tools."""
    return [
        Tool(
            name="rc_add_evidence",
            description="Add structured evidence with automatic quality grading and provenance tracking",
            input_schema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "RCA session ID",
                    },
                    "content": {
                        "type": "string",
                        "description": "Natural language evidence description",
                    },
                    "evidence_type": {
                        "type": "string",
                        "enum": [
                            "DOCUMENT",
                            "OBSERVATION",
                            "LAB_RESULT",
                            "IMAGING",
                            "INTERVIEW",
                            "DEVICE_LOG",
                            "MEDICATION_RECORD",
                            "LITERATURE",
                            "EXPERT_OPINION",
                            "OTHER",
                        ],
                        "description": "Type of evidence",
                        "default": "DOCUMENT",
                    },
                    "source_document": {
                        "type": "string",
                        "description": "Source document ID (e.g., file path, record ID)",
                    },
                    "source_location": {
                        "type": "string",
                        "description": "Location within document (e.g., 'Line 42', 'Page 3')",
                    },
                    "raw_snippet": {
                        "type": "string",
                        "description": "Exact literal excerpt or data line from the raw source document for deterministic lineage",
                    },
                    "content_hash": {
                        "type": "string",
                        "description": "Optional SHA-256 cryptographic digest of the raw snippet",
                    },
                    "extraction_method": {
                        "type": "string",
                        "enum": [
                            "verbatim_quote",
                            "table_cell",
                            "structured_field",
                            "inference",
                            "other",
                        ],
                        "description": "Method used to extract this finding",
                        "default": "verbatim_quote",
                    },
                    "collected_by": {
                        "type": "string",
                        "description": "Who collected this evidence",
                        "default": "agent",
                    },
                    "clinical_strength": {
                        "type": "string",
                        "enum": ["STRONG", "MODERATE", "WEAK", "ANECDOTAL"],
                        "description": "Evidence strength (Oxford CEBM)",
                        "default": "MODERATE",
                    },
                    "source_reliability": {
                        "type": "string",
                        "enum": ["GRADE_A", "GRADE_B", "GRADE_C", "GRADE_D"],
                        "description": "Source reliability grade",
                        "default": "GRADE_B",
                    },
                    "clinical_context": {
                        "type": "string",
                        "description": "Clinical context (e.g., 'Post-op Day 1 hypotension')",
                    },
                    "auto_verify": {
                        "type": "boolean",
                        "description": "Automatically verify snippet against physical file on disk if available",
                        "default": True,
                    },
                },
                "required": ["session_id", "content"],
            },
        ),
        Tool(
            name="rc_get_evidence",
            description="Retrieve evidence by ID",
            input_schema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "RCA session ID",
                    },
                    "evidence_id": {
                        "type": "string",
                        "description": "Evidence ID (e.g., 'EVD-abc123')",
                    },
                },
                "required": ["session_id", "evidence_id"],
            },
        ),
        Tool(
            name="rc_verify_evidence",
            description="Verify evidence against raw physical files or record independent reviewer audit",
            input_schema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "RCA session ID",
                    },
                    "evidence_id": {
                        "type": "string",
                        "description": "Evidence ID to verify",
                    },
                    "verified_by": {
                        "type": "string",
                        "description": "Who verified this evidence",
                        "default": "agent",
                    },
                    "raw_snippet": {
                        "type": "string",
                        "description": "Verbatim quote to search and verify in the source file on disk",
                    },
                    "document_id": {
                        "type": "string",
                        "description": "Optional file path override if not previously set on evidence",
                    },
                },
                "required": ["session_id", "evidence_id"],
            },
        ),
    ]
