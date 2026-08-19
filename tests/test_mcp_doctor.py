"""Regression tests for portable VS Code/Copilot MCP startup diagnostics."""

from __future__ import annotations

import json
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

_DOCTOR_PATH = Path(__file__).resolve().parents[1] / "scripts" / "mcp_doctor.py"
_DOCTOR_SPEC = spec_from_file_location("rootcause_mcp_doctor", _DOCTOR_PATH)
assert _DOCTOR_SPEC is not None and _DOCTOR_SPEC.loader is not None
doctor = module_from_spec(_DOCTOR_SPEC)
sys.modules[_DOCTOR_SPEC.name] = doctor
_DOCTOR_SPEC.loader.exec_module(doctor)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_remote_host_rejects_windows_absolute_uv_path(tmp_path: Path) -> None:
    """The exact Copilot ENOENT regression fails before process spawn."""
    config_path = tmp_path / ".vscode" / "mcp.json"
    _write_json(
        config_path,
        {
            "servers": {
                "rootcauseMcp": {
                    "type": "stdio",
                    "command": r"C:\Users\Ericlab\AppData\Local\hermes\bin\uv.EXE",
                    "args": ["run", "rootcause-mcp"],
                    "cwd": "${workspaceFolder}",
                }
            }
        },
    )

    with pytest.raises(doctor.DoctorError, match="host-specific absolute path"):
        doctor.resolve_server(config_path, tmp_path)


def test_vscode_portable_config_resolves_on_execution_host(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / ".vscode" / "mcp.json"
    _write_json(
        config_path,
        {
            "servers": {
                "rootcauseMcp": {
                    "type": "stdio",
                    "command": "uv",
                    "args": ["run", "--locked", "rootcause-mcp"],
                    "cwd": "${workspaceFolder}",
                    "env": {"ROOTCAUSE_CONFIG_DIR": "${workspaceFolder}/config"},
                }
            }
        },
    )
    (tmp_path / "config").mkdir()
    monkeypatch.setattr(doctor.shutil, "which", lambda _command: "/remote/bin/uv")

    resolved = doctor.resolve_server(config_path, tmp_path)

    assert resolved.command == "/remote/bin/uv"
    assert resolved.args == ("run", "--locked", "rootcause-mcp")
    assert resolved.cwd == tmp_path.resolve()
    assert resolved.env["ROOTCAUSE_CONFIG_DIR"] == str(tmp_path / "config")


def test_copilot_agent_host_config_uses_mcpservers_shape(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / ".mcp.json"
    _write_json(
        config_path,
        {
            "mcpServers": {
                "rootcauseMcp": {
                    "type": "local",
                    "command": "uv",
                    "args": ["run", "--locked", "rootcause-mcp"],
                    "cwd": ".",
                    "tools": ["*"],
                }
            }
        },
    )
    monkeypatch.setattr(doctor.shutil, "which", lambda _command: "/remote/bin/uv")

    resolved = doctor.resolve_server(config_path, tmp_path)

    assert resolved.server_name == "rootcauseMcp"
    assert resolved.command == "/remote/bin/uv"
    assert resolved.cwd == tmp_path.resolve()


def test_config_rejects_two_rootcause_aliases(tmp_path: Path) -> None:
    config_path = tmp_path / ".mcp.json"
    definition = {"type": "local", "command": "uv", "args": []}
    _write_json(
        config_path,
        {
            "mcpServers": {
                "rootcauseMcp": definition,
                "rootcause-mcp": definition,
            }
        },
    )

    with pytest.raises(doctor.DoctorError, match="exactly one"):
        doctor.resolve_server(config_path, tmp_path)


@pytest.mark.parametrize(
    "host_path",
    [r"C:\Users\someone\bin\tool.exe", r"\\server\share\tool.exe"],
)
def test_config_rejects_host_path_in_another_shared_server(
    tmp_path: Path,
    host_path: str,
) -> None:
    config_path = tmp_path / ".vscode" / "mcp.json"
    _write_json(
        config_path,
        {
            "servers": {
                "rootcauseMcp": {
                    "type": "stdio",
                    "command": "uv",
                    "args": ["run", "--locked", "rootcause-mcp"],
                },
                "unrelated": {
                    "type": "stdio",
                    "command": host_path,
                    "args": [],
                },
            }
        },
    )

    with pytest.raises(doctor.DoctorError, match="host-specific absolute path"):
        doctor.resolve_server(config_path, tmp_path)


@pytest.mark.parametrize(
    "forbidden_key",
    ["ROOTCAUSE_DATA_DIR", "ROOTCAUSE_AUTHORIZED_REVIEWERS"],
)
def test_shared_config_rejects_clinical_state_or_reviewer_hardcoding(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    forbidden_key: str,
) -> None:
    config_path = tmp_path / ".vscode" / "mcp.json"
    _write_json(
        config_path,
        {
            "servers": {
                "rootcauseMcp": {
                    "type": "stdio",
                    "command": "uv",
                    "args": ["run", "--locked", "rootcause-mcp"],
                    "env": {forbidden_key: "unsafe-shared-value"},
                }
            }
        },
    )
    monkeypatch.setattr(doctor.shutil, "which", lambda _command: "/remote/bin/uv")

    with pytest.raises(doctor.DoctorError, match="must not hard-code"):
        doctor.resolve_server(config_path, tmp_path)


def test_config_rejects_unset_vscode_env_variable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / ".vscode" / "mcp.json"
    _write_json(
        config_path,
        {
            "servers": {
                "rootcauseMcp": {
                    "type": "stdio",
                    "command": "uv",
                    "args": [],
                    "env": {"TOKEN": "${env:ROOTCAUSE_DOCTOR_MISSING}"},
                }
            }
        },
    )
    monkeypatch.delenv("ROOTCAUSE_DOCTOR_MISSING", raising=False)
    monkeypatch.setattr(doctor.shutil, "which", lambda _command: "/usr/bin/uv")

    with pytest.raises(doctor.DoctorError, match="unset environment variable"):
        doctor.resolve_server(config_path, tmp_path)


def test_config_rejects_command_missing_from_remote_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / ".vscode" / "mcp.json"
    _write_json(
        config_path,
        {
            "servers": {
                "rootcauseMcp": {
                    "type": "stdio",
                    "command": "uv",
                    "args": [],
                }
            }
        },
    )
    monkeypatch.setattr(doctor.shutil, "which", lambda _command: None)

    with pytest.raises(doctor.DoctorError, match="not on the PATH"):
        doctor.resolve_server(config_path, tmp_path)


def test_all_selection_requires_at_least_one_config(tmp_path: Path) -> None:
    with pytest.raises(doctor.DoctorError, match="No MCP workspace config"):
        doctor._config_paths(tmp_path, "all")


def test_repository_vscode_config_has_no_host_or_clinical_state_hardcoding() -> None:
    """Shared workspace config remains portable and fail-closed for reviewers/data."""
    project_root = Path(__file__).resolve().parents[1]
    config_path = project_root / ".vscode" / "mcp.json"
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    definition = payload["servers"]["rootcauseMcp"]

    assert definition["command"] == "uv"
    assert definition["cwd"] == "${workspaceFolder}"
    assert definition["args"] == [
        "run",
        "--locked",
        "--directory",
        "${workspaceFolder}",
        "rootcause-mcp",
    ]
    assert "ROOTCAUSE_DATA_DIR" not in definition.get("env", {})
    assert "ROOTCAUSE_AUTHORIZED_REVIEWERS" not in definition.get("env", {})


def test_repository_copilot_config_is_portable() -> None:
    project_root = Path(__file__).resolve().parents[1]
    config_path = project_root / ".mcp.json"
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    definition = payload["mcpServers"]["rootcauseMcp"]

    assert definition["type"] == "local"
    assert definition["command"] == "uv"
    assert definition["args"] == ["run", "--locked", "rootcause-mcp"]
    assert definition["cwd"] == "."
    assert definition["tools"] == ["*"]
    assert "ROOTCAUSE_DATA_DIR" not in definition.get("env", {})
    assert "ROOTCAUSE_AUTHORIZED_REVIEWERS" not in definition.get("env", {})


def test_cross_format_launch_identity_normalizes_equivalent_uv_directory(
    tmp_path: Path,
) -> None:
    uv = str(tmp_path / "uv")
    vscode = doctor.ResolvedServer(
        config_path=tmp_path / ".vscode" / "mcp.json",
        server_name="rootcauseMcp",
        command=uv,
        args=("run", "--locked", "--directory", str(tmp_path), "rootcause-mcp"),
        cwd=tmp_path,
        env={
            "ROOTCAUSE_TOOL_PROFILE": "all",
            "ROOTCAUSE_RESPONSE_MODE": "compact",
        },
    )
    copilot = doctor.ResolvedServer(
        config_path=tmp_path / ".mcp.json",
        server_name="rootcauseMcp",
        command=uv,
        args=("run", "--locked", "rootcause-mcp"),
        cwd=tmp_path,
        env={
            "ROOTCAUSE_TOOL_PROFILE": "all",
            "ROOTCAUSE_RESPONSE_MODE": "compact",
        },
    )

    assert doctor._launch_identity(vscode) == doctor._launch_identity(copilot)


def test_vscode_config_handles_workspace_path_with_spaces(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "root cause workspace"
    project_root.mkdir()
    config_path = project_root / ".vscode" / "mcp.json"
    _write_json(
        config_path,
        {
            "servers": {
                "rootcauseMcp": {
                    "type": "stdio",
                    "command": "uv",
                    "args": [
                        "run",
                        "--locked",
                        "--directory",
                        "${workspaceFolder}",
                        "rootcause-mcp",
                    ],
                    "cwd": "${workspaceFolder}",
                }
            }
        },
    )
    monkeypatch.setattr(doctor.shutil, "which", lambda _command: "/remote/bin/uv")

    resolved = doctor.resolve_server(config_path, project_root)

    assert resolved.cwd == project_root.resolve()
    assert resolved.args[3] == str(project_root.resolve())
