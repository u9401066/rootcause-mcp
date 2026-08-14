"""
Case Checkpoint & State Snapshot Application Service.

Allows AI agents and clinicians to create immutable, timestamped snapshots
of case progress, and restore or branch cases without context loss.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rootcause_mcp.infrastructure.export_paths import get_export_root

if TYPE_CHECKING:
    from rootcause_mcp.application.server_state import ServerState


class CaseCheckpointService:
    """Application service for managing case checkpoints and snapshot restoration."""

    def __init__(self, server_state: ServerState) -> None:
        """Initialize checkpoint service with shared server state."""
        self._state = server_state

    def _get_checkpoints_dir(self, session_id: str) -> Path:
        """Get checkpoint directory for a specific session."""
        root = get_export_root()
        cp_dir = root / session_id / "checkpoints"
        cp_dir.mkdir(parents=True, exist_ok=True)
        return cp_dir

    async def create_checkpoint(
        self,
        session_id: str,
        tag: str | None = None,
        created_by: str = "agent",
        notes: str = "",
    ) -> dict[str, Any]:
        """
        Create an immutable case snapshot.

        Args:
            session_id: RCA session ID
            tag: Human-readable tag (e.g. 'post_tee_evaluation', 'pre_cpr_baseline')
            created_by: Actor creating checkpoint
            notes: Descriptive notes
        """
        orch = await self._state.get_orchestrator(session_id)
        if orch is None:
            return {
                "status": "not_found",
                "message": f"No active clinical session found for {session_id}",
            }

        now_utc = datetime.now(UTC)
        ts_str = now_utc.strftime("%Y%m%d_%H%M%S")
        clean_tag = (tag or "snapshot").replace(" ", "_").lower()
        checkpoint_id = f"CP-{session_id[:8]}-{ts_str}-{clean_tag}"

        # Build payload
        evidence_list = [
            e.model_dump(mode="json") for e in orch.evidence_store.values()
        ]
        hypothesis_list = [
            h.model_dump(mode="json") for h in orch.hypothesis_store.values()
        ]
        thinking_list = [s.model_dump(mode="json") for s in orch.thinking_chain.steps]
        reasoning_list = [s.model_dump(mode="json") for s in orch.reasoning_chain.steps]

        top_h = (
            max(orch.hypothesis_store.values(), key=lambda h: h.current_probability)
            if orch.hypothesis_store
            else None
        )
        guidance = orch.get_guidance()

        payload: dict[str, Any] = {
            "checkpoint_id": checkpoint_id,
            "session_id": session_id,
            "tag": tag or "snapshot",
            "notes": notes,
            "created_by": created_by,
            "timestamp": now_utc.isoformat(),
            "initial_problem": orch.initial_problem,
            "stage": guidance.current_stage.value,
            "completeness_score": guidance.completeness_score,
            "top_diagnosis": top_h.diagnosis.display if top_h else None,
            "top_probability": top_h.current_probability if top_h else None,
            "evidence_count": len(evidence_list),
            "hypothesis_count": len(hypothesis_list),
            "thinking_steps_count": len(thinking_list),
            "reasoning_steps_count": len(reasoning_list),
            "evidence": evidence_list,
            "hypotheses": hypothesis_list,
            "thinking_chain": thinking_list,
            "reasoning_chain": reasoning_list,
        }

        # Calculate cryptographic digest
        content_json = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)
        digest = hashlib.sha256(content_json.encode("utf-8")).hexdigest()
        payload["content_hash"] = f"sha256:{digest}"

        # Write file
        cp_dir = self._get_checkpoints_dir(session_id)
        file_path = cp_dir / f"{checkpoint_id}.json"
        file_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        return {
            "status": "success",
            "checkpoint_id": checkpoint_id,
            "session_id": session_id,
            "file_path": str(file_path),
            "timestamp": now_utc.isoformat(),
            "evidence_count": len(evidence_list),
            "hypothesis_count": len(hypothesis_list),
            "top_diagnosis": payload["top_diagnosis"],
            "top_probability": payload["top_probability"],
            "content_hash": payload["content_hash"],
        }

    async def restore_checkpoint(
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
            checkpoint_file: Full or relative path to checkpoint JSON file
        """
        target_path: Path | None = None
        if checkpoint_file:
            target_path = Path(checkpoint_file).resolve()
        elif checkpoint_id:
            cp_dir = self._get_checkpoints_dir(session_id)
            target_path = cp_dir / f"{checkpoint_id}.json"

        if target_path is None or not target_path.is_file():
            return {
                "status": "not_found",
                "message": f"Checkpoint not found for session {session_id}",
            }

        data: dict[str, Any] = json.loads(target_path.read_text(encoding="utf-8"))

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

        thinking_chain = ThinkingChain(session_id=session_id, steps=thinking_steps)
        reasoning_chain = ReasoningChain(session_id=session_id, steps=reasoning_steps)

        orch = await self._state.get_or_create_orchestrator(session_id)
        orch.initial_problem = data.get("initial_problem") or orch.initial_problem
        orch.restore(
            evidence=evidence_items,
            hypotheses=hypothesis_items,
            thinking_chain=thinking_chain,
            reasoning_chain=reasoning_chain,
        )
        await self._state.persist_orchestrator(session_id)

        guidance = orch.get_guidance()
        top_h = (
            max(orch.hypothesis_store.values(), key=lambda h: h.current_probability)
            if orch.hypothesis_store
            else None
        )

        return {
            "status": "success",
            "session_id": session_id,
            "restored_from": data.get("checkpoint_id"),
            "stage": guidance.current_stage.value,
            "completeness_score": guidance.completeness_score,
            "restored_evidence_count": len(evidence_items),
            "restored_hypothesis_count": len(hypothesis_items),
            "top_diagnosis": top_h.diagnosis.display if top_h else None,
            "top_probability": top_h.current_probability if top_h else None,
            "guidance": guidance.model_dump(mode="json"),
        }

    async def list_checkpoints(self, session_id: str) -> dict[str, Any]:
        """List all available checkpoints for a session."""
        cp_dir = self._get_checkpoints_dir(session_id)
        checkpoints: list[dict[str, Any]] = []

        for p in sorted(cp_dir.glob("*.json"), reverse=True):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                checkpoints.append(
                    {
                        "checkpoint_id": data.get("checkpoint_id", p.stem),
                        "timestamp": data.get("timestamp"),
                        "tag": data.get("tag"),
                        "stage": data.get("stage"),
                        "evidence_count": data.get("evidence_count", 0),
                        "hypothesis_count": data.get("hypothesis_count", 0),
                        "top_diagnosis": data.get("top_diagnosis"),
                        "top_probability": data.get("top_probability"),
                        "content_hash": data.get("content_hash"),
                        "file_path": str(p),
                    }
                )
            except Exception:
                continue

        return {
            "status": "success",
            "session_id": session_id,
            "total_checkpoints": len(checkpoints),
            "checkpoints": checkpoints,
        }
