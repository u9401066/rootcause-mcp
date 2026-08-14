"""Presentation guidance for Why Tree depth levels."""

from __future__ import annotations

from typing import Final

CAUSE_TYPE_BY_LEVEL: Final[dict[int, dict[str, str]]] = {
    1: {
        "type": "Proximate",
        "chinese": "近端原因",
        "emoji": "🔴",
        "hfacs_hint": "通常對應 HFACS Level 1 (Unsafe Acts) 或 Level 2 (Preconditions)",
    },
    2: {
        "type": "Proximate/Intermediate",
        "chinese": "近端/中間原因",
        "emoji": "🟠",
        "hfacs_hint": "通常對應 HFACS Level 2 (Preconditions) 或 Level 3 (Supervision)",
    },
    3: {
        "type": "Intermediate",
        "chinese": "中間原因",
        "emoji": "🟡",
        "hfacs_hint": "通常對應 HFACS Level 3 (Unsafe Supervision)",
    },
    4: {
        "type": "Intermediate/Ultimate",
        "chinese": "中間/遠端原因",
        "emoji": "🟢",
        "hfacs_hint": "通常對應 HFACS Level 3-4 (Supervision/Organizational)",
    },
    5: {
        "type": "Ultimate",
        "chinese": "遠端/根本原因",
        "emoji": "💚",
        "hfacs_hint": "通常對應 HFACS Level 4 (Organizational Influences)",
    },
}


def get_cause_type_by_level(level: int) -> dict[str, str]:
    """Return cause-type and HFACS presentation guidance for one depth."""
    return CAUSE_TYPE_BY_LEVEL.get(
        level,
        {
            "type": "Unknown",
            "chinese": "未知",
            "emoji": "⚪",
            "hfacs_hint": "無對應資訊",
        },
    )
