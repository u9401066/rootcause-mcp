"""
Case Checkpoint & State Snapshot Application Service.

Allows AI agents and clinicians to create integrity-checked, timestamped snapshots
of case progress, and restore or branch cases without context loss.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import re
import tempfile
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rootcause_mcp.domain.entities.hypothesis import HypothesisStatus
from rootcause_mcp.infrastructure.export_paths import get_export_root

if TYPE_CHECKING:
    from rootcause_mcp.application.server_state import ServerState

_SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
_MAX_SESSION_ID_LENGTH = 128
_MAX_CHECKPOINT_ID_LENGTH = 200
_MAX_TAG_LENGTH = 64
logger = logging.getLogger(__name__)


def _validate_component(value: str, *, label: str, max_length: int) -> str:
    """Validate one filesystem component before using it in a path."""
    if (
        not value
        or len(value) > max_length
        or value in {".", ".."}
        or _SAFE_COMPONENT.fullmatch(value) is None
    ):
        raise ValueError(f"Invalid {label}: {value!r}")
    return value


def _normalize_tag(tag: str | None) -> str:
    """Create a bounded filename-safe slug while preserving the original tag in data."""
    normalized = re.sub(r"[^A-Za-z0-9_.-]+", "_", (tag or "snapshot").lower())
    normalized = normalized.strip("._-")[:_MAX_TAG_LENGTH]
    return normalized or "snapshot"


def _checkpoint_hash(payload: dict[str, Any]) -> str:
    """Calculate the stable SHA-256 hash used by existing checkpoint files."""
    unsigned_payload = {
        key: value for key, value in payload.items() if key != "content_hash"
    }
    content_json = json.dumps(
        unsigned_payload,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    )
    digest = hashlib.sha256(content_json.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _has_valid_hash(payload: dict[str, Any]) -> bool:
    """Verify a checkpoint hash without leaking comparison timing."""
    supplied = payload.get("content_hash")
    return isinstance(supplied, str) and hmac.compare_digest(
        supplied, _checkpoint_hash(payload)
    )


class CaseCheckpointService:
    """Application service for managing case checkpoints and snapshot restoration."""

    def __init__(self, server_state: ServerState) -> None:
        """Initialize checkpoint service with shared server state."""
        self._state = server_state

    def _get_checkpoints_dir(self, session_id: str) -> Path:
        """Get checkpoint directory for a specific session."""
        safe_session_id = _validate_component(
            session_id,
            label="session_id",
            max_length=_MAX_SESSION_ID_LENGTH,
        )
        root = get_export_root().resolve()
        root.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        root.mkdir(exist_ok=True, mode=0o700)
        session_dir = (root / safe_session_id).resolve()
        cp_dir = (session_dir / "checkpoints").resolve()
        try:
            cp_dir.relative_to(root)
        except ValueError as exc:
            raise ValueError("Checkpoint path escaped the export root") from exc
        session_dir.mkdir(exist_ok=True, mode=0o700)
        cp_dir.mkdir(exist_ok=True, mode=0o700)
        return cp_dir

    def _resolve_checkpoint_path(
        self,
        session_id: str,
        *,
        checkpoint_id: str | None,
        checkpoint_file: str | None,
    ) -> Path | None:
        """Resolve a restore target confined to this session's checkpoint directory."""
        if checkpoint_id and checkpoint_file:
            raise ValueError("Specify checkpoint_id or checkpoint_file, not both")

        cp_dir = self._get_checkpoints_dir(session_id).resolve()
        if checkpoint_file:
            supplied = Path(checkpoint_file).expanduser()
            candidate = supplied if supplied.is_absolute() else cp_dir / supplied
        elif checkpoint_id:
            safe_checkpoint_id = _validate_component(
                checkpoint_id,
                label="checkpoint_id",
                max_length=_MAX_CHECKPOINT_ID_LENGTH,
            )
            candidate = cp_dir / f"{safe_checkpoint_id}.json"
        else:
            return None

        target = candidate.resolve()
        if target.parent != cp_dir or target.suffix != ".json":
            raise ValueError(
                "Checkpoint file must be a JSON file directly inside the session "
                "checkpoint directory"
            )
        return target

    @staticmethod
    def _atomic_write(file_path: Path, payload: dict[str, Any]) -> None:
        """Atomically publish a private checkpoint file in its final directory."""
        serialized = json.dumps(payload, indent=2, ensure_ascii=False)
        file_descriptor, temporary_name = tempfile.mkstemp(
            dir=file_path.parent,
            prefix=f".{file_path.name}.",
            suffix=".tmp",
            text=True,
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(file_descriptor, "w", encoding="utf-8") as handle:
                handle.write(serialized)
                handle.flush()
                os.fsync(handle.fileno())
            temporary_path.chmod(0o600)
            temporary_path.replace(file_path)
        except Exception:
            with suppress(OSError):
                os.close(file_descriptor)
            temporary_path.unlink(missing_ok=True)
            raise

    async def create_checkpoint(
        self,
        session_id: str,
        tag: str | None = None,
        created_by: str = "agent",
        notes: str = "",
    ) -> dict[str, Any]:
        """
        Create an integrity-checked case snapshot.

        Args:
            session_id: RCA session ID
            tag: Human-readable tag (e.g. 'post_tee_evaluation', 'pre_cpr_baseline')
            created_by: Actor creating checkpoint
            notes: Descriptive notes
        """
        try:
            safe_session_id = _validate_component(
                session_id,
                label="session_id",
                max_length=_MAX_SESSION_ID_LENGTH,
            )
        except ValueError as exc:
            return {"status": "error", "message": str(exc)}

        orch = await self._state.get_orchestrator(safe_session_id)
        if orch is None:
            return {
                "status": "not_found",
                "message": f"No active clinical session found for {session_id}",
            }

        now_utc = datetime.now(UTC)
        ts_str = now_utc.strftime("%Y%m%d_%H%M%S_%f")
        clean_tag = _normalize_tag(tag)
        checkpoint_id = f"CP-{safe_session_id[:8]}-{ts_str}-{clean_tag}"

        # Build payload
        evidence_list = [
            e.model_dump(mode="json") for e in orch.evidence_store.values()
        ]
        hypothesis_list = [
            {
                **h.model_dump(mode="json"),
                "probability_semantics": "UNCALIBRATED_COMPATIBILITY_ONLY",
                "clinical_probability_established": False,
            }
            for h in orch.hypothesis_store.values()
        ]
        thinking_list = [s.model_dump(mode="json") for s in orch.thinking_chain.steps]
        reasoning_list = [s.model_dump(mode="json") for s in orch.reasoning_chain.steps]

        leading_hypothesis_id = orch.get_leading_hypothesis_id()
        leading_h = orch.hypothesis_store.get(leading_hypothesis_id or "")
        leading_is_eligible = bool(
            leading_h is not None
            and leading_h.status
            not in {HypothesisStatus.EXCLUDED, HypothesisStatus.ON_HOLD}
        )
        guidance = orch.get_guidance()

        payload: dict[str, Any] = {
            "checkpoint_id": checkpoint_id,
            "session_id": safe_session_id,
            "tag": tag or "snapshot",
            "notes": notes,
            "created_by": created_by,
            "timestamp": now_utc.isoformat(),
            "initial_problem": orch.initial_problem,
            "stage": guidance.current_stage.value,
            "completeness_score": guidance.completeness_score,
            "leading_diagnosis": (
                leading_h.diagnosis.display
                if leading_is_eligible and leading_h
                else None
            ),
            "leading_hypothesis_id": leading_hypothesis_id,
            "leading_selection_eligible": leading_is_eligible,
            "ordering_semantics": "EXPLICIT_LEAD_SELECTION_SEPARATE_FROM_LEDGER_ORDER",
            "probability_semantics": "UNCALIBRATED_NOT_PRESENTED",
            "evidence_count": len(evidence_list),
            "hypothesis_count": len(hypothesis_list),
            "thinking_steps_count": len(thinking_list),
            "reasoning_steps_count": len(reasoning_list),
            "evidence": evidence_list,
            "hypotheses": hypothesis_list,
            "thinking_chain": thinking_list,
            "reasoning_chain": reasoning_list,
        }

        payload["content_hash"] = _checkpoint_hash(payload)

        cp_dir = self._get_checkpoints_dir(safe_session_id)
        file_path = cp_dir / f"{checkpoint_id}.json"
        self._atomic_write(file_path, payload)

        return {
            "status": "success",
            "checkpoint_id": checkpoint_id,
            "session_id": safe_session_id,
            "file_path": str(file_path),
            "timestamp": now_utc.isoformat(),
            "evidence_count": len(evidence_list),
            "hypothesis_count": len(hypothesis_list),
            "leading_diagnosis": payload["leading_diagnosis"],
            "leading_hypothesis_id": payload["leading_hypothesis_id"],
            "leading_selection_eligible": payload["leading_selection_eligible"],
            "ordering_semantics": payload["ordering_semantics"],
            "probability_semantics": payload["probability_semantics"],
            "content_hash": payload["content_hash"],
        }

    async def restore_checkpoint(  # noqa: PLR0911
        self,
        session_id: str,
        checkpoint_id: str | None = None,
        checkpoint_file: str | None = None,
    ) -> dict[str, Any]:
        """
        Restore a case aggregate from a saved checkpoint.

        Args:
            session_id: RCA session ID
            checkpoint_id: Specific checkpoint ID to restore
            checkpoint_file: JSON filename or confined path inside this session's
                checkpoint directory
        """
        try:
            safe_session_id = _validate_component(
                session_id,
                label="session_id",
                max_length=_MAX_SESSION_ID_LENGTH,
            )
            target_path = self._resolve_checkpoint_path(
                safe_session_id,
                checkpoint_id=checkpoint_id,
                checkpoint_file=checkpoint_file,
            )
        except ValueError as exc:
            return {"status": "error", "message": str(exc)}

        if target_path is None or not target_path.is_file():
            return {
                "status": "not_found",
                "message": f"Checkpoint not found for session {session_id}",
            }

        try:
            raw_data = json.loads(target_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return {
                "status": "error",
                "message": f"Checkpoint could not be read: {exc}",
            }
        if not isinstance(raw_data, dict):
            return {"status": "error", "message": "Invalid checkpoint payload"}
        data: dict[str, Any] = raw_data

        if not _has_valid_hash(data):
            return {
                "status": "error",
                "message": "Checkpoint integrity verification failed",
            }
        if data.get("session_id") != safe_session_id:
            return {
                "status": "error",
                "message": "Checkpoint belongs to a different session",
            }
        stored_checkpoint_id = data.get("checkpoint_id")
        if (
            not isinstance(stored_checkpoint_id, str)
            or target_path.name != f"{stored_checkpoint_id}.json"
            or (checkpoint_id is not None and stored_checkpoint_id != checkpoint_id)
        ):
            return {
                "status": "error",
                "message": "Checkpoint identity verification failed",
            }

        from rootcause_mcp.domain.entities.evidence import Evidence
        from rootcause_mcp.domain.entities.hypothesis import Hypothesis
        from rootcause_mcp.domain.entities.reasoning_step import (
            ReasoningChain,
            ReasoningStep,
        )
        from rootcause_mcp.domain.entities.thinking_step import (
            ThinkingChain,
            ThinkingStep,
        )

        evidence_items = [Evidence.model_validate(e) for e in data.get("evidence", [])]
        hypothesis_items = [
            Hypothesis.model_validate(h) for h in data.get("hypotheses", [])
        ]
        thinking_steps = [
            ThinkingStep.model_validate(s) for s in data.get("thinking_chain", [])
        ]
        reasoning_steps = [
            ReasoningStep.model_validate(s) for s in data.get("reasoning_chain", [])
        ]

        thinking_chain = ThinkingChain(session_id=safe_session_id, steps=thinking_steps)
        reasoning_chain = ReasoningChain(
            session_id=safe_session_id, steps=reasoning_steps
        )

        orch = await self._state.get_or_create_orchestrator(safe_session_id)
        orch.initial_problem = data.get("initial_problem") or orch.initial_problem
        orch.restore(
            evidence=evidence_items,
            hypotheses=hypothesis_items,
            thinking_chain=thinking_chain,
            reasoning_chain=reasoning_chain,
        )
        await self._state.persist_orchestrator(safe_session_id)

        guidance = orch.get_guidance()
        leading_hypothesis_id = orch.get_leading_hypothesis_id()
        leading_h = orch.hypothesis_store.get(leading_hypothesis_id or "")
        leading_is_eligible = bool(
            leading_h is not None
            and leading_h.status
            not in {HypothesisStatus.EXCLUDED, HypothesisStatus.ON_HOLD}
        )

        return {
            "status": "success",
            "session_id": safe_session_id,
            "restored_from": data.get("checkpoint_id"),
            "stage": guidance.current_stage.value,
            "completeness_score": guidance.completeness_score,
            "restored_evidence_count": len(evidence_items),
            "restored_hypothesis_count": len(hypothesis_items),
            "leading_diagnosis": (
                leading_h.diagnosis.display
                if leading_is_eligible and leading_h
                else None
            ),
            "leading_hypothesis_id": leading_hypothesis_id,
            "leading_selection_eligible": leading_is_eligible,
            "ordering_semantics": "EXPLICIT_LEAD_SELECTION_SEPARATE_FROM_LEDGER_ORDER",
            "probability_semantics": "UNCALIBRATED_NOT_PRESENTED",
            "guidance": guidance.model_dump(mode="json"),
        }

    async def list_checkpoints(self, session_id: str) -> dict[str, Any]:
        """List all available checkpoints for a session."""
        try:
            safe_session_id = _validate_component(
                session_id,
                label="session_id",
                max_length=_MAX_SESSION_ID_LENGTH,
            )
            cp_dir = self._get_checkpoints_dir(safe_session_id)
        except ValueError as exc:
            return {"status": "error", "message": str(exc)}
        checkpoints: list[dict[str, Any]] = []

        for p in sorted(cp_dir.glob("*.json"), reverse=True):
            if p.is_symlink():
                continue
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                if (
                    not isinstance(data, dict)
                    or data.get("session_id") != safe_session_id
                    or not _has_valid_hash(data)
                ):
                    continue
                checkpoints.append(
                    {
                        "checkpoint_id": data.get("checkpoint_id", p.stem),
                        "timestamp": data.get("timestamp"),
                        "tag": data.get("tag"),
                        "stage": data.get("stage"),
                        "evidence_count": data.get("evidence_count", 0),
                        "hypothesis_count": data.get("hypothesis_count", 0),
                        "leading_diagnosis": data.get("leading_diagnosis"),
                        "leading_hypothesis_id": data.get("leading_hypothesis_id"),
                        "leading_selection_eligible": data.get(
                            "leading_selection_eligible", False
                        ),
                        "ordering_semantics": data.get(
                            "ordering_semantics", "WORKING_LEDGER_ORDER"
                        ),
                        "probability_semantics": "UNCALIBRATED_NOT_PRESENTED",
                        "content_hash": data.get("content_hash"),
                        "file_path": str(p),
                    }
                )
            except (OSError, json.JSONDecodeError, TypeError, ValueError):
                logger.warning("Skipping an unreadable checkpoint file")

        return {
            "status": "success",
            "session_id": safe_session_id,
            "total_checkpoints": len(checkpoints),
            "checkpoints": checkpoints,
        }
