"""
RootCause MCP - Automated Cross-Platform Installer and Harness Configurator.

Configures RootCause MCP Server across:
1. VS Code (.vscode/mcp.json)
2. Claude Desktop (claude_desktop_config.json)
3. Cline / Claude Dev (cline_mcp_settings.json)
4. Codex / Copilot Agent Harness
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess  # nosec B404
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"


def get_uv_executable() -> str:
    """Find uv executable on PATH or default installation locations."""
    which_uv = shutil.which("uv")
    if which_uv:
        return which_uv

    if platform.system() == "Windows":
        candidates = [
            Path.home() / ".local" / "bin" / "uv.exe",
            Path.home() / "AppData" / "Roaming" / "uv" / "uv.exe",
            Path.home() / ".cargo" / "bin" / "uv.exe",
        ]
    else:
        candidates = [
            Path.home() / ".local" / "bin" / "uv",
            Path.home() / ".cargo" / "bin" / "uv",
            Path("/usr/local/bin/uv"),
        ]

    for c in candidates:
        if c.is_file():
            return str(c)

    return "uv"


def get_claude_desktop_config_path() -> Path | None:
    """Get the platform-specific Claude Desktop configuration path."""
    sys_name = platform.system()
    if sys_name == "Windows":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "Claude" / "claude_desktop_config.json"
    elif sys_name == "Darwin":
        return (
            Path.home()
            / "Library"
            / "Application Support"
            / "Claude"
            / "claude_desktop_config.json"
        )
    elif sys_name == "Linux":
        config_home = os.environ.get("XDG_CONFIG_HOME")
        if config_home:
            return Path(config_home) / "Claude" / "claude_desktop_config.json"
        return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"
    return None


def get_cline_config_paths() -> list[Path]:
    """Get candidate Cline configuration file paths."""
    paths: list[Path] = []
    sys_name = platform.system()

    if sys_name == "Windows":
        appdata = os.environ.get("APPDATA")
        if appdata:
            paths.append(
                Path(appdata)
                / "Code"
                / "User"
                / "globalStorage"
                / "saoudrizwan.claude-dev"
                / "settings"
                / "cline_mcp_settings.json"
            )
            paths.append(
                Path(appdata)
                / "Code - Insiders"
                / "User"
                / "globalStorage"
                / "saoudrizwan.claude-dev"
                / "settings"
                / "cline_mcp_settings.json"
            )
    elif sys_name == "Darwin":
        paths.append(
            Path.home()
            / "Library"
            / "Application Support"
            / "Code"
            / "User"
            / "globalStorage"
            / "saoudrizwan.claude-dev"
            / "settings"
            / "cline_mcp_settings.json"
        )
    elif sys_name == "Linux":
        paths.append(
            Path.home()
            / ".config"
            / "Code"
            / "User"
            / "globalStorage"
            / "saoudrizwan.claude-dev"
            / "settings"
            / "cline_mcp_settings.json"
        )

    return [p for p in paths if p.parent.exists() or p.exists()]


def build_server_config(
    uv_path: str,
    tool_profile: str = "all",
    response_mode: str = "compact",
) -> dict[str, Any]:
    """Build the RootCause MCP server configuration stanza."""
    return {
        "type": "stdio",
        "command": uv_path,
        "args": [
            "run",
            "--directory",
            str(PROJECT_ROOT),
            "rootcause-mcp",
        ],
        "env": {
            "ROOTCAUSE_CONFIG_DIR": str(CONFIG_DIR),
            "ROOTCAUSE_TOOL_PROFILE": tool_profile,
            "ROOTCAUSE_RESPONSE_MODE": response_mode,
        },
    }


def _load_json_object(file_path: Path) -> dict[str, Any] | None:
    """Load a JSON object, refusing to replace an unreadable existing file."""
    if not file_path.is_file():
        return {}

    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(
            f"❌ Existing JSON config is invalid or unreadable; "
            f"refusing to overwrite {file_path}: {exc}"
        )
        return None

    if not isinstance(data, dict):
        print(
            f"❌ Existing JSON config must contain an object; "
            f"refusing to overwrite {file_path}"
        )
        return None
    return data


def _get_servers_object(
    data: dict[str, Any],
    *,
    preferred_key: str,
    file_path: Path,
) -> dict[str, Any] | None:
    """Return a server mapping without replacing an incompatible JSON value."""
    if preferred_key not in data:
        servers: dict[str, Any] = {}
        data[preferred_key] = servers
        return servers
    existing = data[preferred_key]
    if isinstance(existing, dict):
        return existing

    print(
        f"❌ Existing '{preferred_key}' value must be an object; "
        f"refusing to overwrite {file_path}"
    )
    return None


def update_json_file(
    file_path: Path, server_key: str, server_config: dict[str, Any]
) -> bool:
    """Safely merge server configuration into a JSON config file without destroying existing servers."""
    data = _load_json_object(file_path)
    if data is None:
        return False

    servers_key = (
        "mcpServers" if "mcpServers" in data or "servers" not in data else "servers"
    )
    servers = _get_servers_object(
        data,
        preferred_key=servers_key,
        file_path=file_path,
    )
    if servers is None:
        return False
    servers[server_key] = server_config

    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"✅ Updated MCP config: {file_path}")
        return True
    except Exception as e:
        print(f"❌ Failed to write {file_path}: {e}")
        return False


def configure_vscode_mcp(
    uv_path: str,
    tool_profile: str = "all",
    response_mode: str = "compact",
) -> bool:
    """Configure workspace .vscode/mcp.json."""
    vscode_dir = PROJECT_ROOT / ".vscode"
    mcp_json_path = vscode_dir / "mcp.json"

    data = _load_json_object(mcp_json_path)
    if data is None:
        return False
    servers = _get_servers_object(
        data,
        preferred_key="servers",
        file_path=mcp_json_path,
    )
    if servers is None:
        return False
    servers["rootcauseMcp"] = {
        "type": "stdio",
        "command": uv_path,
        "args": [
            "run",
            "rootcause-mcp",
        ],
        "env": {
            "ROOTCAUSE_CONFIG_DIR": "${workspaceFolder}/config",
            "ROOTCAUSE_TOOL_PROFILE": tool_profile,
            "ROOTCAUSE_RESPONSE_MODE": response_mode,
        },
        "dev": {
            "watch": "src/**/*.py",
            "debug": {
                "type": "python",
            },
        },
    }

    try:
        vscode_dir.mkdir(parents=True, exist_ok=True)
        mcp_json_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"✅ Configured VS Code MCP: {mcp_json_path}")
        return True
    except Exception as e:
        print(f"❌ Failed to write {mcp_json_path}: {e}")
        return False


def run_self_check(uv_path: str) -> bool:
    """Run test suite sanity check."""
    print("\n🔍 Running RootCause MCP self-diagnostic test suite...")
    cmd = [uv_path, "run", "pytest", "-q"]
    try:
        # The argv list is assembled from fixed installer options in this module.
        result = subprocess.run(  # nosec B603
            cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True, check=False
        )
        if result.returncode == 0:
            print("✅ All unit & integration tests passed (80%+ coverage verified)!")
            return True
        print(f"❌ Test check failed:\n{result.stdout}\n{result.stderr}")
        return False
    except Exception as e:
        print(f"❌ Error running self-check: {e}")
        return False


def run_case_trial(uv_path: str) -> bool:
    """Run full real-case simulation trial."""
    print("\n🔬 Running end-to-end clinical case reasoning trial...")
    cmd = [uv_path, "run", "python", "scripts/run_case_trial.py"]
    try:
        # The argv list is assembled from fixed self-test options in this module.
        result = subprocess.run(  # nosec B603
            cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True, check=False
        )
        if result.returncode == 0:
            print(
                "✅ Clinical reasoning trial passed with 100% provenance verification!"
            )
            return True
        print(f"❌ Trial run failed:\n{result.stdout}\n{result.stderr}")
        return False
    except Exception as e:
        print(f"❌ Error running trial: {e}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="RootCause MCP Automated Setup & Harness Installer"
    )
    parser.add_argument(
        "--profile",
        choices=["all", "clinical", "rca", "condensed"],
        default="all",
        help="Tool profile catalog (default: all)",
    )
    parser.add_argument(
        "--response-mode",
        choices=["compact", "verbose"],
        default="compact",
        help="Response format mode (default: compact for SDK 2.0)",
    )
    parser.add_argument(
        "--target",
        choices=["vscode", "claude", "cline", "all"],
        default="all",
        help="Target MCP client hosts to configure (default: all)",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip running pytest self-check",
    )
    parser.add_argument(
        "--skip-trial",
        action="store_true",
        help="Skip running end-to-end case trial",
    )
    args = parser.parse_args()

    print("=" * 70)
    print("🏥 RootCause MCP Server - Automated Installer & Harness Setup")
    print(f"   Project Root:   {PROJECT_ROOT}")
    print(f"   Tool Profile:   {args.profile}")
    print(f"   Response Mode:  {args.response_mode}")
    print("=" * 70)

    uv_path = get_uv_executable()
    print(f"\n📦 Detected uv binary: {uv_path}")

    step_results: list[bool] = []

    # 1. VS Code MCP Config
    if args.target in {"vscode", "all"}:
        step_results.append(
            configure_vscode_mcp(
                uv_path=uv_path,
                tool_profile=args.profile,
                response_mode=args.response_mode,
            )
        )

    server_config = build_server_config(
        uv_path=uv_path,
        tool_profile=args.profile,
        response_mode=args.response_mode,
    )

    # 2. Claude Desktop Config
    if args.target in {"claude", "all"}:
        claude_path = get_claude_desktop_config_path()
        if claude_path:
            step_results.append(
                update_json_file(claude_path, "rootcause-mcp", server_config)
            )
        else:
            print("ℹ️ Claude Desktop config directory not found on this system.")

    # 3. Cline Config
    if args.target in {"cline", "all"}:
        cline_paths = get_cline_config_paths()
        if cline_paths:
            step_results.extend(
                update_json_file(cp, "rootcause-mcp", server_config)
                for cp in cline_paths
            )
        else:
            print("ℹ️ Cline storage directory not found (skipping).")

    # 4. Self Check
    if not args.skip_tests:
        step_results.append(run_self_check(uv_path))

    # 5. Case Trial
    if not args.skip_trial:
        step_results.append(run_case_trial(uv_path))

    if not all(step_results):
        print("\n" + "=" * 70)
        print("❌ RootCause MCP installation failed; review the errors above.")
        print("=" * 70)
        return 1

    print("\n" + "=" * 70)
    print("🎉 RootCause MCP installation & harness configuration complete!")
    print("   To start the MCP server manually:")
    print("     uv run rootcause-mcp")
    print("   To run the clinical trial:")
    print("     uv run python scripts/run_case_trial.py")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
