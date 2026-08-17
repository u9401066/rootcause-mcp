"""Regression and security tests for release-critical runtime behavior."""

from __future__ import annotations

import inspect
import json
import os
import stat
from pathlib import Path
from typing import Any

import pytest
import yaml

from rootcause_mcp import server_v2
from rootcause_mcp.application.checkpoint_service import CaseCheckpointService
from rootcause_mcp.application.server_state import ServerState
from rootcause_mcp.domain.services import HFACSSuggester, LearnedRulesService
from rootcause_mcp.infrastructure import runtime_paths


def test_console_entrypoint_is_synchronous(monkeypatch: pytest.MonkeyPatch) -> None:
    """A console script must call a normal function rather than return a coroutine."""
    observed: dict[str, bool] = {}

    def fake_run(awaitable: Any) -> None:
        observed["is_coroutine"] = inspect.iscoroutine(awaitable)
        awaitable.close()

    monkeypatch.setattr(server_v2.asyncio, "run", fake_run)

    assert not inspect.iscoroutinefunction(server_v2.main)
    server_v2.main()
    assert observed == {"is_coroutine": True}


def test_default_data_path_uses_platform_user_data(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """An installed server must not write databases into its package or CWD."""
    xdg_home = tmp_path / "xdg-data"
    monkeypatch.delenv("ROOTCAUSE_DATA_DIR", raising=False)
    monkeypatch.setenv("XDG_DATA_HOME", str(xdg_home))
    monkeypatch.setattr(runtime_paths.sys, "platform", "linux")

    assert server_v2._get_data_path() == (xdg_home / "rootcause-mcp").resolve()


def test_config_context_exposes_and_restores_resolved_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Legacy readers see the resolved config only during the context lifetime."""
    monkeypatch.delenv("ROOTCAUSE_CONFIG_DIR", raising=False)

    with server_v2._config_path_context() as config_path:
        assert Path(os.environ["ROOTCAUSE_CONFIG_DIR"]) == config_path
        assert config_path.joinpath("hfacs", "keyword_rules.yaml").is_file()

    assert "ROOTCAUSE_CONFIG_DIR" not in os.environ


def test_learned_rules_write_only_to_user_data(tmp_path: Path) -> None:
    """Packaged baseline rules remain unchanged when a classification is learned."""
    baseline_dir = tmp_path / "read-only-baseline"
    baseline_dir.mkdir()
    baseline_file = baseline_dir / "learned_rules.yaml"
    baseline_data = {
        "metadata": {"version": "1.0", "stats": {}},
        "learned_rules": [
            {
                "keyword": "baseline_only_term",
                "code": "UA-SBE",
                "confidence": 0.9,
                "reason": "curated baseline",
                "source_type": "manual",
            }
        ],
        "pending_rules": [],
        "rejected_rules": [],
    }
    baseline_file.write_text(
        yaml.safe_dump(baseline_data, allow_unicode=True), encoding="utf-8"
    )
    baseline_before = baseline_file.read_bytes()

    writable_dir = tmp_path / "user-data" / "hfacs"
    service = LearnedRulesService(writable_dir, baseline_file=baseline_file)
    assert not service.rules_file.exists()
    assert len(service.get_learned_rules()) == 1

    result = service.confirm_classification(
        description="wheel_only_term",
        hfacs_code="UA-SBE",
        reason="confirmed after installation",
    )

    assert result["success"] is True
    assert service.rules_file.is_file()
    assert baseline_file.read_bytes() == baseline_before

    suggester = HFACSSuggester(
        baseline_dir,
        learned_rules_path=service.rules_file,
        fallback_learned_rules_path=baseline_file,
    )
    suggestions = suggester.suggest("wheel_only_term")
    assert suggestions
    assert suggestions[0].source == "learned"


async def _service_with_session(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    session_id: str = "release-session-001",
) -> tuple[CaseCheckpointService, ServerState]:
    monkeypatch.setenv("ROOTCAUSE_DATA_DIR", str(tmp_path / "data"))
    state = ServerState()
    orchestrator = await state.get_or_create_orchestrator(session_id)
    orchestrator.initial_problem = "baseline problem"
    return CaseCheckpointService(state), state


@pytest.mark.asyncio
async def test_checkpoint_atomic_write_and_valid_restore(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A valid checkpoint is private, confined, and can still be restored."""
    session_id = "release-session-001"
    service, state = await _service_with_session(monkeypatch, tmp_path, session_id)

    created = await service.create_checkpoint(session_id, tag="After TEE / review")

    assert created["status"] == "success"
    checkpoint_path = Path(created["file_path"])
    expected_dir = (
        tmp_path / "data" / "exports" / session_id / "checkpoints"
    ).resolve()
    assert checkpoint_path.parent == expected_dir
    assert checkpoint_path.name.endswith("after_tee_review.json")
    assert not list(expected_dir.glob(".*.tmp"))
    if os.name == "posix":
        assert stat.S_IMODE(expected_dir.stat().st_mode) == 0o700
        assert stat.S_IMODE(checkpoint_path.stat().st_mode) == 0o600

    orchestrator = await state.get_orchestrator(session_id)
    assert orchestrator is not None
    orchestrator.initial_problem = "mutated problem"
    restored = await service.restore_checkpoint(
        session_id,
        checkpoint_id=created["checkpoint_id"],
    )

    assert restored["status"] == "success"
    assert orchestrator.initial_problem == "baseline problem"


@pytest.mark.asyncio
async def test_checkpoint_rejects_tampering_before_state_mutation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A modified payload cannot be restored using its stale content hash."""
    session_id = "tamper-session-001"
    service, state = await _service_with_session(monkeypatch, tmp_path, session_id)
    created = await service.create_checkpoint(session_id, tag="baseline")
    checkpoint_path = Path(created["file_path"])
    payload = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    payload["initial_problem"] = "tampered diagnosis"
    checkpoint_path.write_text(json.dumps(payload), encoding="utf-8")

    orchestrator = await state.get_orchestrator(session_id)
    assert orchestrator is not None
    orchestrator.initial_problem = "live state"
    restored = await service.restore_checkpoint(
        session_id,
        checkpoint_id=created["checkpoint_id"],
    )

    assert restored["status"] == "error"
    assert "integrity" in restored["message"].lower()
    assert orchestrator.initial_problem == "live state"
    listed = await service.list_checkpoints(session_id)
    assert listed["total_checkpoints"] == 0


@pytest.mark.asyncio
async def test_checkpoint_paths_are_confined_to_their_session(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Traversal IDs and arbitrary restore files never escape the session directory."""
    session_id = "confined-session-001"
    service, _state = await _service_with_session(monkeypatch, tmp_path, session_id)
    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")

    traversal = await service.list_checkpoints("../outside-session")
    external_restore = await service.restore_checkpoint(
        session_id,
        checkpoint_file=str(outside),
    )
    id_traversal = await service.restore_checkpoint(
        session_id,
        checkpoint_id="../../outside",
    )

    assert traversal["status"] == "error"
    assert external_restore["status"] == "error"
    assert id_traversal["status"] == "error"
    assert not (tmp_path / "data" / "outside-session").exists()

    checkpoint_dir = service._get_checkpoints_dir(session_id)
    symlink_path = checkpoint_dir / "outside-link.json"
    try:
        symlink_path.symlink_to(outside)
    except OSError:
        symlink_supported = False
    else:
        symlink_supported = True
    if symlink_supported:
        symlink_restore = await service.restore_checkpoint(
            session_id,
            checkpoint_file=symlink_path.name,
        )
        assert symlink_restore["status"] == "error"
