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


class SourceIndependenceStatus(StrEnum):
    """Relationship of a document to independently acquired clinical sources."""

    UNKNOWN = "unknown"
    INDEPENDENT = "independent"
    DERIVED = "derived"


class SourceReviewAdjudication(BaseModel):
    """Append-only human review state layered over an immutable manifest entry."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    adjudication_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        pattern=r"^SRV-[A-Za-z0-9._-]+$",
    )
    manifest_digest: str = Field(..., pattern=r"^sha256:[a-fA-F0-9]{64}$")
    document_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
    )
    status: SourceReviewStatus
    de_identified: bool | None = None
    independence_status: SourceIndependenceStatus = SourceIndependenceStatus.UNKNOWN
    source_group_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
    )
    parent_document_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
    )
    derivation_method: str | None = Field(default=None, min_length=1, max_length=255)
    reviewed_by: str = Field(..., min_length=1, max_length=255)
    reason: str = Field(..., min_length=1, max_length=2000)
    reviewed_at: datetime

    @model_validator(mode="after")
    def validate_review_claim(self) -> SourceReviewAdjudication:
        """Make a REVIEWED transition complete without changing source identity."""
        if self.reviewed_at.tzinfo is None or self.reviewed_at.utcoffset() is None:
            raise ValueError("reviewed_at must include an explicit timezone")
        if self.status is SourceReviewStatus.REGISTERED:
            raise ValueError(
                "append-only review transitions cannot reset to registered"
            )
        if self.status is SourceReviewStatus.REVIEWED:
            if self.de_identified is not True:
                raise ValueError("reviewed sources require de_identified=true")
            if self.independence_status is SourceIndependenceStatus.UNKNOWN:
                raise ValueError(
                    "reviewed sources require an explicit independence_status"
                )
            if not self.source_group_id:
                raise ValueError("reviewed sources require source_group_id")
        if self.independence_status is SourceIndependenceStatus.DERIVED:
            if not self.parent_document_id or not self.derivation_method:
                raise ValueError(
                    "derived review claims require parent_document_id and derivation_method"
                )
        elif self.parent_document_id is not None or self.derivation_method is not None:
            raise ValueError(
                "parent_document_id/derivation_method require independence_status=derived"
            )
        if self.parent_document_id == self.document_id:
            raise ValueError("a source document cannot derive from itself")
        return self


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
    independence_status: SourceIndependenceStatus = Field(
        default=SourceIndependenceStatus.UNKNOWN,
        description=(
            "Whether this is an independently acquired source, a derivative of "
            "another manifest document, or not yet adjudicated"
        ),
    )
    source_group_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
        description=(
            "Host-declared independence group; documents in one group count as "
            "one source root for final conformance"
        ),
    )
    parent_document_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
        description="Immediate manifest parent when independence_status is derived",
    )
    derivation_method: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Auditable extraction/transcription/transformation method",
    )

    @model_validator(mode="after")
    def validate_independence_metadata(self) -> SourceDocument:
        """Make explicit derivation claims structurally complete."""
        if self.independence_status is SourceIndependenceStatus.DERIVED:
            if not self.parent_document_id or not self.derivation_method:
                raise ValueError(
                    "derived sources require parent_document_id and derivation_method"
                )
        elif self.parent_document_id is not None:
            raise ValueError(
                "parent_document_id is only valid when independence_status is derived"
            )
        if self.parent_document_id == self.document_id:
            raise ValueError("a source document cannot derive from itself")
        return self


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
        """Require stable identities and an acyclic in-manifest derivation graph."""
        document_ids = [document.document_id for document in self.documents]
        if len(document_ids) != len(set(document_ids)):
            raise ValueError("source manifest document_id values must be unique")
        by_id = {document.document_id: document for document in self.documents}
        for document in self.documents:
            parent_id = document.parent_document_id
            if parent_id is not None and parent_id not in by_id:
                raise ValueError(
                    f"derived source parent_document_id {parent_id!r} is not in the manifest"
                )

        for document in self.documents:
            seen: set[str] = set()
            cursor = document
            while cursor.parent_document_id is not None:
                if cursor.document_id in seen:
                    raise ValueError(
                        "source manifest derivation graph cannot contain cycles"
                    )
                seen.add(cursor.document_id)
                cursor = by_id[cursor.parent_document_id]
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
