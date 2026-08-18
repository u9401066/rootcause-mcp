"""Versioned handoff contract for a set of raw clinical source documents."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SourceReviewStatus(StrEnum):
    """Processing state for one registered source document."""

    REGISTERED = "registered"
    EXTRACTED = "extracted"
    REVIEWED = "reviewed"
    FAILED = "failed"


class SourceDocument(BaseModel):
    """Immutable identity and processing metadata for one source document."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    document_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
        description="Stable case-local source identifier; never use direct patient identifiers",
    )
    source_uri: str = Field(
        ...,
        min_length=1,
        max_length=2048,
        description="URI or approved local path retained by the host; raw bytes are not embedded",
    )
    sha256: str = Field(
        ...,
        pattern=r"^[a-fA-F0-9]{64}$",
        description="Whole-source SHA-256 digest",
    )
    media_type: str = Field(..., min_length=1, max_length=255)
    source_kind: str = Field(
        ...,
        min_length=1,
        max_length=80,
        description="For example progress_note, medication_record, imaging, or device_log",
    )
    revision: str | None = Field(default=None, max_length=128)
    captured_at: datetime | None = None
    parser_name: str | None = Field(default=None, max_length=128)
    parser_version: str | None = Field(default=None, max_length=64)
    status: SourceReviewStatus = SourceReviewStatus.REGISTERED
    de_identified: bool | None = Field(
        default=None,
        description="Host attestation; null means de-identification has not been established",
    )


class CaseInputManifest(BaseModel):
    """Canonical manifest exchanged between a host agent and RootCause MCP."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    patient_key: str | None = Field(
        default=None,
        max_length=128,
        description="Pseudonymous case-local patient key, never a direct identifier",
    )
    encounter_key: str | None = Field(
        default=None,
        max_length=128,
        description="Pseudonymous encounter key",
    )
    default_timezone: str | None = Field(
        default=None,
        max_length=64,
        description="IANA timezone used when a source omits its timezone",
    )
    documents: tuple[SourceDocument, ...] = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_unique_document_ids(self) -> CaseInputManifest:
        """Require stable, unambiguous document identities."""
        document_ids = [document.document_id for document in self.documents]
        if len(document_ids) != len(set(document_ids)):
            raise ValueError("source manifest document_id values must be unique")
        return self

    @property
    def digest(self) -> str:
        """Return a stable digest of the canonical manifest payload."""
        payload = json.dumps(
            self.model_dump(mode="json", exclude_none=True),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return f"sha256:{hashlib.sha256(payload).hexdigest()}"
