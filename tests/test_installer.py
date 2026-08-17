"""Focused release tests for the cross-platform installer."""

from __future__ import annotations

import json
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any

import pytest

_INSTALL_PATH = Path(__file__).resolve().parents[1] / "scripts" / "install.py"
_INSTALL_SPEC = spec_from_file_location("rootcause_installer", _INSTALL_PATH)
assert _INSTALL_SPEC is not None and _INSTALL_SPEC.loader is not None
install = module_from_spec(_INSTALL_SPEC)
_INSTALL_SPEC.loader.exec_module(install)


def _configure_isolated_main(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    argv: list[str],
) -> None:
    monkeypatch.setattr(sys, "argv", ["install.py", *argv])
    monkeypatch.setattr(install, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(install, "CONFIG_DIR", tmp_path / "config")
    monkeypatch.setattr(install, "get_uv_executable", lambda: "uv-test")


def test_generated_client_config_uses_safe_runtime_data_default(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """The installer must not direct clinical runtime artifacts into the repo."""
    monkeypatch.setattr(install, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(install, "CONFIG_DIR", tmp_path / "config")

    config = install.build_server_config("uv-test")

    assert "ROOTCAUSE_DATA_DIR" not in config["env"]


def test_profile_accepts_condensed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """The installer exposes the same condensed profile as the MCP server."""
    captured: dict[str, Any] = {}

    def configure(**kwargs: Any) -> bool:
        captured.update(kwargs)
        return True

    _configure_isolated_main(
        monkeypatch,
        tmp_path,
        [
            "--profile",
            "condensed",
            "--target",
            "vscode",
            "--skip-tests",
            "--skip-trial",
        ],
    )
    monkeypatch.setattr(install, "configure_vscode_mcp", configure)

    assert install.main() == 0
    assert captured["tool_profile"] == "condensed"


@pytest.mark.parametrize(
    "existing_content",
    [
        '{"mcpServers":',
        "[]",
        '{"mcpServers": []}',
        '{"mcpServers": null}',
    ],
)
def test_update_json_file_preserves_invalid_or_incompatible_json(
    tmp_path: Path,
    existing_content: str,
) -> None:
    """An unreadable/non-object config is never replaced with a fresh object."""
    config_path = tmp_path / "client.json"
    config_path.write_text(existing_content, encoding="utf-8")
    original = config_path.read_bytes()

    result = install.update_json_file(
        config_path,
        "rootcause-mcp",
        {"command": "uv"},
    )

    assert result is False
    assert config_path.read_bytes() == original


def test_vscode_invalid_json_is_preserved(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """The workspace-specific path follows the same fail-safe JSON behavior."""
    monkeypatch.setattr(install, "PROJECT_ROOT", tmp_path)
    config_path = tmp_path / ".vscode" / "mcp.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text('{"servers":', encoding="utf-8")
    original = config_path.read_bytes()

    assert install.configure_vscode_mcp("uv-test") is False
    assert config_path.read_bytes() == original


def test_update_json_file_merges_valid_config(tmp_path: Path) -> None:
    """Fail-safe loading still preserves and extends a valid client config."""
    config_path = tmp_path / "client.json"
    config_path.write_text(
        json.dumps(
            {
                "mcpServers": {"existing": {"command": "existing-server"}},
                "customSetting": True,
            }
        ),
        encoding="utf-8",
    )

    assert install.update_json_file(
        config_path,
        "rootcause-mcp",
        {"command": "uv-test"},
    )
    updated = json.loads(config_path.read_text(encoding="utf-8"))
    assert updated["customSetting"] is True
    assert updated["mcpServers"]["existing"]["command"] == "existing-server"
    assert updated["mcpServers"]["rootcause-mcp"]["command"] == "uv-test"


@pytest.mark.parametrize(
    ("self_check_result", "trial_result"),
    [(False, True), (True, False)],
)
def test_failed_validation_returns_nonzero_without_completion_message(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    self_check_result: bool,
    trial_result: bool,
) -> None:
    """Either validation failure makes the overall installer fail."""
    _configure_isolated_main(
        monkeypatch,
        tmp_path,
        ["--target", "vscode"],
    )
    monkeypatch.setattr(install, "configure_vscode_mcp", lambda **_kwargs: True)
    monkeypatch.setattr(
        install,
        "run_self_check",
        lambda _uv_path: self_check_result,
    )
    monkeypatch.setattr(
        install,
        "run_case_trial",
        lambda _uv_path: trial_result,
    )

    assert install.main() == 1
    output = capsys.readouterr().out
    assert "installation failed" in output
    assert "installation & harness configuration complete" not in output


def test_invalid_vscode_config_makes_installer_fail_without_overwrite(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A refused configuration update propagates to the process exit status."""
    _configure_isolated_main(
        monkeypatch,
        tmp_path,
        ["--target", "vscode", "--skip-tests", "--skip-trial"],
    )
    config_path = tmp_path / ".vscode" / "mcp.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text("not-json", encoding="utf-8")
    original = config_path.read_bytes()

    assert install.main() == 1
    output = capsys.readouterr().out
    assert "installation & harness configuration complete" not in output
    assert config_path.read_bytes() == original
