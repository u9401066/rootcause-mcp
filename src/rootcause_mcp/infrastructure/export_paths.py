"""Safe export-path construction for generated clinical artifacts."""

from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path

_SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9_.-]+$")


def get_export_root() -> Path:
    """Get root directory for all generated exports."""
    data_root = Path(os.environ.get("ROOTCAUSE_DATA_DIR", "data")).resolve()
    return (data_root / "exports").resolve()


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

    output_path.parent.mkdir(parents=True, exist_ok=True)
    return output_path
