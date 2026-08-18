"""
RCA Session Entity.

The aggregate root for a Root Cause Analysis session.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from rootcause_mcp.domain.value_objects.case_manifest import (
    CaseInputManifest,
    SourceReviewAdjudication,
    SourceReviewStatus,
)
from rootcause_mcp.domain.value_objects.enums import (
    CaseType,
    SessionStatus,
    Stage,
    StageStatus,
)
from rootcause_mcp.domain.value_objects.identifiers import SessionId


@dataclass
class StageRecord:
    """Record of a stage's data and status."""

    stage: Stage
    status: StageStatus = StageStatus.NOT_STARTED
    data: dict[str, Any] = field(default_factory=dict)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    validation_errors: list[str] = field(default_factory=list)
    validation_warnings: list[str] = field(default_factory=list)

    def start(self) -> None:
        """Mark stage as in progress."""
        self.status = StageStatus.IN_PROGRESS
        self.started_at = datetime.now(UTC)

    def complete(self) -> None:
        """Mark stage as completed."""
        self.status = StageStatus.COMPLETED
        self.completed_at = datetime.now(UTC)

    def fail(self, errors: list[str]) -> None:
        """Mark stage as failed with validation errors."""
        self.status = StageStatus.FAILED
        self.validation_errors = errors

    @property
    def is_completed(self) -> bool:
        """Check if stage is completed."""
        return self.status == StageStatus.COMPLETED


@dataclass
class RCASession:
    """
    Root Cause Analysis Session - Aggregate Root.

    Represents a complete RCA analysis workflow from problem identification
    to action plan.
    """

    # Identity
    id: SessionId
    case_type: CaseType
    case_title: str

    # State
    current_stage: Stage = Stage.GATHER
    status: SessionStatus = SessionStatus.ACTIVE

    # Content
    problem_statement: str = ""
    initial_description: str = ""

    # Stage Records
    stage_records: dict[Stage, StageRecord] = field(default_factory=dict)

    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    created_by: str = ""

    def __post_init__(self) -> None:
        """Initialize stage records for all stages."""
        if not self.stage_records:
            for stage in Stage:
                self.stage_records[stage] = StageRecord(stage=stage)
            # Auto-start first stage
            self.stage_records[Stage.GATHER].start()

    # === Stage Management ===

    def can_advance_to(self, target_stage: Stage) -> bool:
        """Check if session can advance to target stage."""
        if self.status != SessionStatus.ACTIVE:
            return False
        return self.current_stage.can_transition_to(target_stage)

    def advance_stage(self) -> Stage | None:
        """
        Advance to the next stage.

        Returns the new stage, or None if cannot advance.
        """
        next_stage = self.current_stage.next()
        if next_stage is None:
            return None

        # Complete current stage
        self.stage_records[self.current_stage].complete()

        # Start next stage
        self.current_stage = next_stage
        self.stage_records[next_stage].start()
        self._touch()

        return next_stage

    def rollback_to(self, target_stage: Stage, reason: str) -> bool:
        """
        Rollback to a previous stage.

        This will clear data from all stages after the target.
        """
        if not self.can_advance_to(target_stage):
            return False

        # Clear stages after target
        stages = list(Stage)
        target_idx = stages.index(target_stage)
        for stage in stages[target_idx + 1 :]:
            self.stage_records[stage] = StageRecord(stage=stage)

        # Reset current stage
        self.current_stage = target_stage
        self.stage_records[target_stage].start()
        self.stage_records[target_stage].data["rollback_reason"] = reason
        self._touch()

        return True

    def get_stage_data(self, stage: Stage) -> dict[str, Any]:
        """Get data for a specific stage."""
        return self.stage_records[stage].data

    def set_stage_data(self, stage: Stage, data: dict[str, Any]) -> None:
        """Set data for a specific stage."""
        self.stage_records[stage].data = data
        self._touch()

    def update_stage_data(self, stage: Stage, data: dict[str, Any]) -> None:
        """Update (merge) data for a specific stage."""
        self.stage_records[stage].data.update(data)
        self._touch()

    def set_source_manifest(self, manifest: CaseInputManifest) -> None:
        """Pin the versioned multi-source handoff manifest to the gather stage."""
        self.update_stage_data(
            Stage.GATHER,
            {
                "source_manifest": manifest.model_dump(mode="json"),
                "source_manifest_digest": manifest.digest,
            },
        )

    def get_source_manifest(self) -> CaseInputManifest | None:
        """Return the pinned source manifest, if this session has one."""
        payload = self.get_stage_data(Stage.GATHER).get("source_manifest")
        if not payload:
            return None
        return CaseInputManifest.model_validate(payload)

    def record_source_review(self, adjudication: SourceReviewAdjudication) -> None:
        """Append a human-adjudicated processing state without mutating the manifest."""
        if not self.is_active:
            raise ValueError("source review requires an active session")
        manifest = self.get_source_manifest()
        if manifest is None:
            raise ValueError("source review requires a pinned source manifest")
        if adjudication.manifest_digest != manifest.digest:
            raise ValueError("source review manifest_digest does not match the session")
        document_ids = {document.document_id for document in manifest.documents}
        if adjudication.document_id not in document_ids:
            raise ValueError("source review document_id is not in the pinned manifest")
        if (
            adjudication.parent_document_id is not None
            and adjudication.parent_document_id not in document_ids
        ):
            raise ValueError("derived source parent_document_id is not in the manifest")

        ledger = list(self.get_source_review_ledger())
        if any(item.adjudication_id == adjudication.adjudication_id for item in ledger):
            raise ValueError("source review adjudication_id must be unique")
        manifest_document = next(
            document
            for document in manifest.documents
            if document.document_id == adjudication.document_id
        )
        previous = next(
            (
                item
                for item in reversed(ledger)
                if item.document_id == adjudication.document_id
            ),
            None,
        )
        if previous is not None and adjudication.reviewed_at < previous.reviewed_at:
            raise ValueError("source review timestamps must be append-only")
        if (
            (previous is not None and previous.status is SourceReviewStatus.REVIEWED)
            or (
                previous is None
                and manifest_document.status is SourceReviewStatus.REVIEWED
            )
        ) and adjudication.status is not SourceReviewStatus.REVIEWED:
            raise ValueError("a reviewed source cannot regress to a non-reviewed state")

        ledger.append(adjudication)
        self.update_stage_data(
            Stage.GATHER,
            {"source_review_ledger": [item.model_dump(mode="json") for item in ledger]},
        )

    def get_source_review_ledger(self) -> tuple[SourceReviewAdjudication, ...]:
        """Return the validated append-only source-review transition history."""
        payloads = self.get_stage_data(Stage.GATHER).get("source_review_ledger", [])
        return tuple(SourceReviewAdjudication.model_validate(item) for item in payloads)

    def get_latest_source_reviews(self) -> dict[str, SourceReviewAdjudication]:
        """Return the latest review transition for each manifest document."""
        latest: dict[str, SourceReviewAdjudication] = {}
        for item in self.get_source_review_ledger():
            latest[item.document_id] = item
        return latest

    # === Problem Statement ===

    def set_problem(self, statement: str) -> None:
        """Set the problem statement (fish head)."""
        self.problem_statement = statement
        self._touch()

    # === Status Management ===

    def complete(self) -> None:
        """Mark session as completed."""
        self.status = SessionStatus.COMPLETED
        self.stage_records[self.current_stage].complete()
        self._touch()

    def abandon(self) -> None:
        """Mark session as abandoned."""
        self.status = SessionStatus.ABANDONED
        self._touch()

    def archive(self) -> None:
        """Archive the session."""
        self.status = SessionStatus.ARCHIVED
        self._touch()

    # === Queries ===

    @property
    def is_active(self) -> bool:
        """Check if session is active."""
        return self.status == SessionStatus.ACTIVE

    @property
    def is_completed(self) -> bool:
        """Check if session is completed."""
        return self.status == SessionStatus.COMPLETED

    def get_progress(self) -> dict[str, str]:
        """Get progress of all stages."""
        return {stage.value: self.stage_records[stage].status.value for stage in Stage}

    def get_completed_stages(self) -> list[Stage]:
        """Get list of completed stages."""
        return [
            stage
            for stage in Stage
            if self.stage_records[stage].status == StageStatus.COMPLETED
        ]

    # === Private Methods ===

    def _touch(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now(UTC)

    # === Factory Methods ===

    @classmethod
    def create(
        cls,
        case_type: CaseType,
        case_title: str,
        initial_description: str = "",
        created_by: str = "",
    ) -> RCASession:
        """Factory method to create a new RCA Session."""
        return cls(
            id=SessionId.generate(),
            case_type=case_type,
            case_title=case_title,
            initial_description=initial_description,
            created_by=created_by,
        )
