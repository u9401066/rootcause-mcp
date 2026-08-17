"""Runtime paths that remain safe outside an editable source checkout."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_APP_DIRECTORY = "rootcause-mcp"


def get_user_data_root() -> Path:
    """Return the configured or platform-appropriate writable data directory."""
    configured = os.environ.get("ROOTCAUSE_DATA_DIR")
    if configured:
        return Path(configured).expanduser().resolve()

    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        data_home = Path(base) if base else Path.home() / "AppData" / "Local"
    elif sys.platform == "darwin":
        data_home = Path.home() / "Library" / "Application Support"
    else:
        xdg_data_home = os.environ.get("XDG_DATA_HOME")
        data_home = (
            Path(xdg_data_home).expanduser()
            if xdg_data_home
            else Path.home() / ".local" / "share"
        )

    return (data_home / _APP_DIRECTORY).resolve()
