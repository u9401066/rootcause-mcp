"""Security invariants for clinical artifact exports."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from rootcause_mcp.infrastructure.export_paths import (
    build_export_path,
    write_export_text,
)


def test_export_writer_is_confined_atomic_and_owner_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ROOTCAUSE_DATA_DIR", str(tmp_path / "runtime"))
    output_path = build_export_path(
        session_id="safe-session",
        artifact="contract-report",
        extension="md",
    )

    write_export_text(output_path, "clinical artifact")

    assert output_path.read_text(encoding="utf-8") == "clinical artifact"
    assert not list(output_path.parent.glob(f".{output_path.name}.*"))
    if os.name == "posix":
        assert output_path.stat().st_mode & 0o777 == 0o600
        assert output_path.parent.stat().st_mode & 0o777 == 0o700


def test_export_writer_rejects_path_outside_runtime_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ROOTCAUSE_DATA_DIR", str(tmp_path / "runtime"))

    with pytest.raises(ValueError, match="must remain under"):
        write_export_text(tmp_path / "outside.md", "must not be written")

    assert not (tmp_path / "outside.md").exists()
