"""Diagnose RootCause MCP workspace configuration and stdio startup.

This doctor validates both VS Code's ``.vscode/mcp.json`` format and the
portable GitHub Copilot Agent Host/CLI ``.mcp.json`` format.  The handshake
uses a temporary data root so a diagnostic run cannot read or mutate the
operator's clinical session database.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import platform
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONTRACT_URIS = {
    "clinical://contracts/case-input-manifest",
    "clinical://contracts/case-analysis-report",
}
ROOTCAUSE_SERVER_NAMES = ("rootcauseMcp", "rootcause-mcp")
EXPECTED_TOOL_COUNTS = {"all": 46, "clinical": 25, "rca": 24, "condensed": 8}
EXPECTED_CAPABILITY_COUNTS = {"resources": 19, "resource_templates": 4, "prompts": 5}
REQUIRED_TOOLS = {
    "all": {
        "rc_start_session",
        "rc_adjudicate_source",
        "rc_select_leading_hypothesis",
        "rc_confirm_classification",
        "rc_generate_contract_report",
    },
    "clinical": {"rc_start_session", "rc_add_evidence", "rc_propose_hypothesis"},
    "rca": {"rc_start_session", "rc_init_fishbone", "rc_confirm_classification"},
    "condensed": {"rc_rca", "rc_evidence", "rc_hypothesis", "rc_report"},
}
FORBIDDEN_SHARED_ENV = {"ROOTCAUSE_DATA_DIR", "ROOTCAUSE_AUTHORIZED_REVIEWERS"}
_WINDOWS_DRIVE_ABSOLUTE = re.compile(r"^[A-Za-z]:[\\/]")
_ENV_VARIABLE = re.compile(r"\$\{env:([^}]+)\}")


class DoctorError(RuntimeError):
    """A configuration or startup problem with an actionable message."""


@dataclass(frozen=True, slots=True)
class ResolvedServer:
    """One validated stdio server ready for an SDK handshake."""

    config_path: Path
    server_name: str
    command: str
    args: tuple[str, ...]
    cwd: Path
    env: dict[str, str]


@dataclass(frozen=True, slots=True)
class DiscoveryResult:
    """Minimal MCP capabilities required by the RootCause harness."""

    tools: int
    resources: int
    resource_templates: int
    prompts: int


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DoctorError(f"MCP config does not exist: {path}") from exc
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DoctorError(
            f"MCP config is unreadable or invalid JSON: {path}: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise DoctorError(f"MCP config must contain a JSON object: {path}")
    return payload


def _server_mapping(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    if path.name == ".mcp.json":
        servers = payload.get("mcpServers", payload)
    else:
        servers = payload.get("servers")
    if not isinstance(servers, dict):
        expected = "mcpServers" if path.name == ".mcp.json" else "servers"
        raise DoctorError(f"MCP config {path} requires an object at '{expected}'")
    return servers


def _rootcause_server(
    path: Path, payload: dict[str, Any]
) -> tuple[str, dict[str, Any]]:
    servers = _server_mapping(path, payload)
    matches = [name for name in ROOTCAUSE_SERVER_NAMES if name in servers]
    if len(matches) != 1:
        raise DoctorError(
            f"MCP config {path} must define exactly one of {ROOTCAUSE_SERVER_NAMES}; "
            f"found {matches}"
        )
    name = matches[0]
    definition = servers[name]
    if not isinstance(definition, dict):
        raise DoctorError(f"MCP server '{name}' in {path} must be an object")
    return name, definition


def _is_host_specific_absolute(value: str) -> bool:
    return bool(_WINDOWS_DRIVE_ABSOLUTE.match(value)) or value.startswith(
        ("/", "~/", "~\\", "\\\\")
    )


def _validate_shared_portability(path: Path, payload: dict[str, Any]) -> None:
    """Reject machine-specific paths anywhere in a committed workspace config."""
    for server_name, definition in _server_mapping(path, payload).items():
        if not isinstance(definition, dict):
            raise DoctorError(f"MCP server '{server_name}' in {path} must be an object")
        values: list[tuple[str, Any]] = [
            ("command", definition.get("command")),
            ("cwd", definition.get("cwd")),
        ]
        args = definition.get("args", [])
        if isinstance(args, list):
            values.extend((f"args[{index}]", value) for index, value in enumerate(args))
        env = definition.get("env", {})
        if isinstance(env, dict):
            values.extend((f"env.{key}", value) for key, value in env.items())
        for field, value in values:
            if isinstance(value, str) and _is_host_specific_absolute(value):
                raise DoctorError(
                    f"Shared MCP config {path} contains a host-specific absolute path "
                    f"at server '{server_name}' {field}: {value}"
                )


def _expand_workspace_value(value: str, project_root: Path) -> str:
    expanded = value.replace("${workspaceFolder}", str(project_root))

    def replace_env(match: re.Match[str]) -> str:
        variable = match.group(1)
        if variable not in os.environ:
            raise DoctorError(
                f"MCP config references unset environment variable: {variable}"
            )
        return os.environ[variable]

    return _ENV_VARIABLE.sub(replace_env, expanded)


def _reject_foreign_absolute(value: str, *, field: str, host_system: str) -> None:
    if host_system != "Windows" and (
        _WINDOWS_DRIVE_ABSOLUTE.match(value) or value.startswith("\\\\")
    ):
        raise DoctorError(
            f"MCP {field} contains a Windows absolute path on a remote/non-Windows "
            f"host: {value}"
        )
    if host_system == "Windows" and value.startswith("/"):
        raise DoctorError(
            f"MCP {field} contains a POSIX absolute path on a Windows host: {value}"
        )


def _resolve_command(
    command: str,
    *,
    cwd: Path,
    host_system: str | None = None,
) -> str:
    system = host_system or platform.system()
    try:
        _reject_foreign_absolute(command, field="command", host_system=system)
    except DoctorError as exc:
        raise DoctorError(
            f"{exc}. Use portable command 'uv' and install uv on this host."
        ) from exc

    command_path = Path(command).expanduser()
    contains_separator = "/" in command or "\\" in command
    if command_path.is_absolute() or contains_separator:
        candidate = command_path if command_path.is_absolute() else cwd / command_path
        if not candidate.is_file():
            raise DoctorError(f"MCP command does not exist on this host: {candidate}")
        return str(candidate.resolve())

    resolved = shutil.which(command)
    if resolved is None:
        raise DoctorError(
            f"MCP command '{command}' is not on the PATH of {system}. Install uv in "
            "the VS Code Remote/WSL/SSH/Dev Container host, reopen that environment, "
            "and run 'uv sync --locked'."
        )
    return resolved


def _validated_definition_fields(
    path: Path,
    server_name: str,
    definition: dict[str, Any],
    project_root: Path,
) -> tuple[str, list[str], str, dict[str, Any]]:
    server_type = definition.get("type", "local")
    allowed_types = {"stdio"} if path.name != ".mcp.json" else {"local", "stdio"}
    if server_type not in allowed_types:
        raise DoctorError(
            f"MCP server '{server_name}' in {path} has unsupported type: {server_type}"
        )

    command = definition.get("command")
    args = definition.get("args", [])
    cwd = definition.get("cwd", str(project_root))
    env = definition.get("env", {})
    if not isinstance(command, str) or not command.strip():
        raise DoctorError(f"MCP server '{server_name}' requires a non-empty command")
    if "/" in command or "\\" in command:
        raise DoctorError(
            "Shared RootCause MCP command must be a PATH-resolved executable name, "
            f"not a machine-specific path: {command}"
        )
    if not isinstance(args, list) or not all(isinstance(item, str) for item in args):
        raise DoctorError(
            f"MCP server '{server_name}' args must be an array of strings"
        )
    if not isinstance(cwd, str) or not cwd.strip():
        raise DoctorError(f"MCP server '{server_name}' cwd must be a non-empty string")
    if not isinstance(env, dict):
        raise DoctorError(f"MCP server '{server_name}' env must be an object")
    return command, args, cwd, env


def _validate_definition_policy(
    path: Path,
    server_name: str,
    definition: dict[str, Any],
    env: dict[str, Any],
) -> None:
    forbidden_env = sorted(FORBIDDEN_SHARED_ENV & env.keys())
    if forbidden_env:
        raise DoctorError(
            f"Shared MCP config {path} must not hard-code clinical data/reviewer "
            f"environment: {forbidden_env}. Configure these in operator-protected "
            "host environment instead."
        )
    if path.name != ".mcp.json":
        return
    if "${workspaceFolder}" in json.dumps(definition):
        raise DoctorError(
            ".mcp.json must not use the VS Code-only ${workspaceFolder} token; "
            "use cwd='.' and relative project paths"
        )
    tools = definition.get("tools")
    if (
        not isinstance(tools, list)
        or not tools
        or not all(isinstance(item, str) and item for item in tools)
    ):
        raise DoctorError(
            f"Copilot MCP server '{server_name}' requires a non-empty tools allowlist"
        )


def _expanded_environment(
    env_value: dict[str, Any],
    *,
    server_name: str,
    project_root: Path,
) -> dict[str, str]:
    env: dict[str, str] = dict(os.environ)
    for key, value in env_value.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise DoctorError(f"MCP server '{server_name}' env values must be strings")
        env[key] = _expand_workspace_value(value, project_root)
    return env


def resolve_server(path: Path, project_root: Path = PROJECT_ROOT) -> ResolvedServer:
    """Load and validate one RootCause MCP server definition."""
    payload = _load_json_object(path)
    _validate_shared_portability(path, payload)
    server_name, definition = _rootcause_server(path, payload)
    command_value, args_value, cwd_value, env_value = _validated_definition_fields(
        path, server_name, definition, project_root
    )
    _validate_definition_policy(path, server_name, definition, env_value)

    system = platform.system()
    _reject_foreign_absolute(cwd_value, field="cwd", host_system=system)
    for index, item in enumerate(args_value):
        _reject_foreign_absolute(item, field=f"args[{index}]", host_system=system)

    expanded_cwd = Path(_expand_workspace_value(cwd_value, project_root)).expanduser()
    if not expanded_cwd.is_absolute():
        expanded_cwd = project_root / expanded_cwd
    expanded_cwd = expanded_cwd.resolve()
    if not expanded_cwd.is_dir():
        raise DoctorError(f"MCP working directory does not exist: {expanded_cwd}")

    expanded_command = _expand_workspace_value(command_value, project_root)
    command = _resolve_command(expanded_command, cwd=expanded_cwd)
    args = tuple(_expand_workspace_value(item, project_root) for item in args_value)
    env = _expanded_environment(
        env_value,
        server_name=server_name,
        project_root=project_root,
    )

    return ResolvedServer(
        config_path=path,
        server_name=server_name,
        command=command,
        args=args,
        cwd=expanded_cwd,
        env=env,
    )


async def discover_server(
    server: ResolvedServer, timeout_seconds: float
) -> DiscoveryResult:
    """Perform a production stdio initialize/list handshake without case data."""
    with tempfile.TemporaryDirectory(prefix="rootcause-mcp-doctor-") as temporary_data:
        env = dict(server.env)
        env["ROOTCAUSE_DATA_DIR"] = temporary_data
        env.pop("ROOTCAUSE_AUTHORIZED_REVIEWERS", None)
        parameters = StdioServerParameters(
            command=server.command,
            args=list(server.args),
            cwd=str(server.cwd),
            env=env,
        )
        try:
            async with asyncio.timeout(timeout_seconds):
                async with stdio_client(parameters) as (read_stream, write_stream):
                    async with ClientSession(read_stream, write_stream) as session:
                        await session.initialize()
                        tools = await session.list_tools()
                        resources = await session.list_resources()
                        templates = await session.list_resource_templates()
                        prompts = await session.list_prompts()
                        for uri in sorted(CONTRACT_URIS):
                            response = await session.read_resource(uri)
                            if not response.contents or not hasattr(
                                response.contents[0], "text"
                            ):
                                raise DoctorError(
                                    f"MCP contract resource has no text content: {uri}"
                                )
                            payload = json.loads(response.contents[0].text)
                            if not isinstance(payload, dict):
                                raise DoctorError(
                                    f"MCP contract resource is not a JSON object: {uri}"
                                )
        except TimeoutError as exc:
            raise DoctorError(
                f"MCP initialize/list handshake timed out after {timeout_seconds:g}s "
                f"for {server.config_path}"
            ) from exc
        except Exception as exc:
            raise DoctorError(
                f"MCP initialize/list handshake failed for {server.config_path}: {exc}"
            ) from exc

    resource_uris = {str(item.uri) for item in resources.resources}
    missing_contracts = sorted(CONTRACT_URIS - resource_uris)
    if not tools.tools:
        raise DoctorError(f"MCP server from {server.config_path} advertised no tools")
    if missing_contracts:
        raise DoctorError(
            f"MCP server from {server.config_path} is missing contract resources: "
            f"{missing_contracts}"
        )
    if not prompts.prompts:
        raise DoctorError(f"MCP server from {server.config_path} advertised no prompts")

    profile = server.env.get("ROOTCAUSE_TOOL_PROFILE", "all").strip().lower()
    if profile not in EXPECTED_TOOL_COUNTS:
        raise DoctorError(f"MCP config selects an unsupported tool profile: {profile}")
    tool_names = {item.name for item in tools.tools}
    missing_tools = sorted(REQUIRED_TOOLS[profile] - tool_names)
    if missing_tools:
        raise DoctorError(
            f"MCP profile '{profile}' is missing required tools: {missing_tools}"
        )
    actual_counts = {
        "tools": len(tools.tools),
        "resources": len(resources.resources),
        "resource_templates": len(templates.resource_templates),
        "prompts": len(prompts.prompts),
    }
    expected_counts = {
        "tools": EXPECTED_TOOL_COUNTS[profile],
        **EXPECTED_CAPABILITY_COUNTS,
    }
    if actual_counts != expected_counts:
        raise DoctorError(
            f"MCP capability snapshot mismatch for profile '{profile}': "
            f"expected {expected_counts}, got {actual_counts}"
        )

    return DiscoveryResult(
        tools=len(tools.tools),
        resources=len(resources.resources),
        resource_templates=len(templates.resource_templates),
        prompts=len(prompts.prompts),
    )


def _config_paths(project_root: Path, selection: str) -> list[Path]:
    candidates = {
        "vscode": project_root / ".vscode" / "mcp.json",
        "copilot": project_root / ".mcp.json",
    }
    if selection in candidates:
        return [candidates[selection]]
    paths = [path for path in candidates.values() if path.is_file()]
    if not paths:
        raise DoctorError(
            f"No MCP workspace config found under {project_root}; expected .vscode/mcp.json "
            "or .mcp.json"
        )
    return paths


def _launch_identity(server: ResolvedServer) -> tuple[object, ...]:
    """Normalize equivalent VS Code and Copilot uv launch definitions."""
    normalized_args: list[str] = []
    index = 0
    while index < len(server.args):
        argument = server.args[index]
        directory_value: str | None = None
        consumed = 1
        if argument == "--directory" and index + 1 < len(server.args):
            directory_value = server.args[index + 1]
            consumed = 2
        elif argument.startswith("--directory="):
            directory_value = argument.partition("=")[2]

        if directory_value is not None:
            directory = Path(directory_value).expanduser()
            if not directory.is_absolute():
                directory = server.cwd / directory
            if directory.resolve() == server.cwd:
                index += consumed
                continue

        normalized_args.append(argument)
        if consumed == 2:
            normalized_args.append(server.args[index + 1])
        index += consumed

    return (
        server.server_name,
        server.command,
        tuple(normalized_args),
        server.cwd,
        server.env.get("ROOTCAUSE_TOOL_PROFILE", "all"),
        server.env.get("ROOTCAUSE_RESPONSE_MODE", "compact"),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate RootCause MCP workspace config and stdio startup"
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=PROJECT_ROOT,
        help="Repository root containing MCP config files",
    )
    parser.add_argument(
        "--config",
        choices=["all", "vscode", "copilot"],
        default="all",
        help="Configuration format to validate (default: all existing configs)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Per-server initialize/list timeout in seconds",
    )
    parser.add_argument(
        "--no-handshake",
        action="store_true",
        help="Validate JSON, paths, cwd, and executable without starting the server",
    )
    return parser


async def _run(args: argparse.Namespace) -> int:
    project_root = args.project_root.expanduser().resolve()
    try:
        if args.timeout <= 0:
            raise DoctorError("--timeout must be greater than zero")
        paths = _config_paths(project_root, args.config)
        servers = [resolve_server(path, project_root) for path in paths]
        if len(servers) > 1:
            first = servers[0]
            for other in servers[1:]:
                if _launch_identity(first) != _launch_identity(other):
                    raise DoctorError(
                        "VS Code and Copilot workspace MCP definitions drifted; use the "
                        "same server name and equivalent command, cwd, args, profile, "
                        "and response mode"
                    )
        for server in servers:
            path = server.config_path
            print(f"PASS config {path}: command={server.command} cwd={server.cwd}")
            if args.no_handshake:
                continue
            result = await discover_server(server, args.timeout)
            print(
                "PASS stdio "
                f"{path}: tools={result.tools} resources={result.resources} "
                f"templates={result.resource_templates} prompts={result.prompts}"
            )
    except DoctorError as exc:
        print(f"FAIL {exc}")
        return 1
    return 0


def main() -> int:
    """CLI entry point."""
    return asyncio.run(_run(_parser().parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
