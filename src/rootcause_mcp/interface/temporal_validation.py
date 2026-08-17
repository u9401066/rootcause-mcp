"""Strict parsing for timestamps used as canonical clinical temporality."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

_OFFSET_SUFFIX = re.compile(r"(?:Z|[+-]\d{2}:\d{2})$")


def parse_offset_datetime(value: Any, *, field_name: str) -> datetime:
    """Parse one timezone-aware ISO/RFC3339 datetime or fail closed.

    Date-only and naive values are intentionally rejected: silently coercing
    either to local midnight would fabricate temporal ordering in the clinical
    and causation ledgers.
    """
    raw_value = value.strip() if isinstance(value, str) else ""
    requirement = (
        f"{field_name} must be an ISO 8601/RFC3339 datetime containing 'T' "
        "and ending in Z or a numeric timezone offset (for example "
        "2026-08-17T08:15:00+08:00); omit the canonical timestamp when only "
        "a date or unknown/local time is available"
    )
    if "T" not in raw_value or _OFFSET_SUFFIX.search(raw_value) is None:
        raise ValueError(requirement)

    normalized = f"{raw_value[:-1]}+00:00" if raw_value.endswith("Z") else raw_value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        raise ValueError(requirement) from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(requirement)
    return parsed
