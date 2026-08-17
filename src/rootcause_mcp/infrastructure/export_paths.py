"""Safe export-path construction for generated clinical artifacts."""

from __future__ import annotations

import os
import re
import tempfile
from datetime import datetime
from pathlib import Path

from rootcause_mcp.infrastructure.runtime_paths import get_user_data_root

_SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9_.-]+$")


def get_export_root() -> Path:
    """Get root directory for all generated exports."""
    return (get_user_data_root() / "exports").resolve()


def build_export_path(
    *,
    session_id: str,
    artifact: str,
    extension: str,
    requested_path: str | None = None,
) -> Path:
    """Build an export path confined to the configured exports directory."""
    for name, value in (
        ("session_id", session_id),
        ("artifact", artifact),
        ("extension", extension),
    ):
        if not _SAFE_COMPONENT.fullmatch(value):
            raise ValueError(f"Invalid {name}: {value!r}")

    export_root = get_export_root()

    if requested_path:
        output_path = Path(requested_path).resolve()
        try:
            output_path.relative_to(export_root)
        except ValueError as exc:
            raise ValueError(f"Export path must remain under {export_root}") from exc
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        output_path = export_root / session_id / f"{artifact}_{timestamp}.{extension}"

    output_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    # Tighten an existing directory as well. These folders can contain raw
    # snippets and clinical conclusions, so the process umask is not enough.
    if os.name == "posix":
        output_path.parent.chmod(0o700)
    return output_path


def write_export_text(path: Path, content: str, *, encoding: str = "utf-8") -> None:
    """Atomically write a confined clinical export with owner-only permissions."""
    export_root = get_export_root()
    resolved_path = path.resolve()
    try:
        resolved_path.relative_to(export_root)
    except ValueError as exc:
        raise ValueError(f"Export path must remain under {export_root}") from exc

    resolved_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if os.name == "posix":
        resolved_path.parent.chmod(0o700)

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{resolved_path.name}.",
        dir=resolved_path.parent,
        text=True,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding=encoding) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if os.name == "posix":
            temporary_path.chmod(0o600)
        temporary_path.replace(resolved_path)
        if os.name == "posix":
            resolved_path.chmod(0o600)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
