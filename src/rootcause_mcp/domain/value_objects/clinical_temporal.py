"""Typed clinical time semantics that preserve source precision and missingness."""

from __future__ import annotations

import re
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ClinicalTemporalKind(StrEnum):
    """Epistemically distinct kinds of time found in clinical records."""

    INSTANT = "instant"
    DATE = "date"
    RANGE = "range"
    RELATIVE = "relative"
    UNKNOWN = "unknown"


class ClinicalTemporalPrecision(StrEnum):
    """Precision retained from the supplied source representation."""

    DAY = "day"
    MINUTE = "minute"
    SECOND = "second"
    SUBSECOND = "subsecond"
    RELATIVE = "relative"
    UNKNOWN = "unknown"


class TimezoneProvenance(StrEnum):
    """How timezone semantics were established without inventing an offset."""

    SOURCE_EXPLICIT_OFFSET = "source_explicit_offset"
    NOT_APPLICABLE = "not_applicable"
    SOURCE_LOCAL_UNKNOWN = "source_local_unknown"
    UNKNOWN = "unknown"


_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_AWARE_INSTANT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}"
    r"(?::\d{2}(?:\.\d{1,9})?)?(?:Z|[+-]\d{2}:\d{2})$"
)
_INSTANT_PRECISION_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}"
    r"(?::\d{2}(?:\.(?P<fraction>\d{1,9}))?)?"
)


def _parse_aware_instant(value: str, *, field_name: str) -> datetime:
    """Parse only an ISO/RFC3339 instant whose source includes an offset."""
    if not _AWARE_INSTANT_RE.fullmatch(value):
        raise ValueError(
            f"{field_name} must be an ISO 8601 instant containing 'T' and an "
            "explicit Z or numeric timezone offset"
        )
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:  # pragma: no cover - regex catches normal failures
        raise ValueError(f"{field_name} is not a valid ISO 8601 instant") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field_name} must include an explicit timezone offset")
    return parsed


def _normalized_instant(value: datetime) -> str:
    """Return one stable UTC representation for cross-ledger comparison."""
    return value.astimezone(UTC).isoformat()


def _instant_precision(raw_value: str) -> ClinicalTemporalPrecision:
    """Infer precision from fields actually present in the source string."""
    matched = _INSTANT_PRECISION_RE.match(raw_value)
    if matched is None:  # pragma: no cover - guarded by strict instant parsing
        return ClinicalTemporalPrecision.UNKNOWN
    time_without_zone = raw_value.split("T", 1)[1]
    time_without_zone = re.sub(r"(?:Z|[+-]\d{2}:\d{2})$", "", time_without_zone)
    if time_without_zone.count(":") == 1:
        return ClinicalTemporalPrecision.MINUTE
    if matched.group("fraction"):
        return ClinicalTemporalPrecision.SUBSECOND
    return ClinicalTemporalPrecision.SECOND


def _normalize_range_endpoint(value: str, *, field_name: str) -> tuple[str, str]:
    """Normalize one range endpoint and return its temporal domain."""
    if _DATE_RE.fullmatch(value):
        try:
            parsed_date = date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"{field_name} is not a valid ISO 8601 date") from exc
        return parsed_date.isoformat(), "date"
    parsed_instant = _parse_aware_instant(value, field_name=field_name)
    return _normalized_instant(parsed_instant), "instant"


class ClinicalTemporal(BaseModel):
    """One source-faithful clinical temporal statement.

    Only ``instant`` is an absolute, sortable point in time. ``date``, ``range``,
    ``relative``, and ``unknown`` remain valid clinical observations but cannot
    satisfy a causation-temporality obligation or be silently assigned an order.
    """

    kind: ClinicalTemporalKind
    raw_value: str | None = Field(
        default=None,
        max_length=1000,
        description="Exact source time expression, retained without translation",
    )
    precision: ClinicalTemporalPrecision
    normalized_start: str | None = Field(
        default=None,
        description="Canonical ISO date or timezone-aware UTC interval start",
    )
    normalized_end: str | None = Field(
        default=None,
        description="Canonical ISO date or timezone-aware UTC interval end",
    )
    timezone_provenance: TimezoneProvenance

    @model_validator(mode="before")
    @classmethod
    def derive_canonical_fields(cls, value: Any) -> Any:  # noqa: PLR0912, PLR0915
        """Derive rather than trust normalized fields and precision metadata."""
        if isinstance(value, cls):
            return value
        if not isinstance(value, dict):
            raise ValueError("temporal must be an object")
        payload = dict(value)
        try:
            kind = ClinicalTemporalKind(str(payload.get("kind") or ""))
        except ValueError as exc:
            raise ValueError(
                "temporal.kind must be instant, date, range, relative, or unknown"
            ) from exc
        raw_value = payload.get("raw_value")
        if raw_value is not None and not isinstance(raw_value, str):
            raise ValueError("temporal.raw_value must be a string or null")
        if isinstance(raw_value, str) and not raw_value.strip():
            raise ValueError("temporal.raw_value cannot be blank")

        if kind is ClinicalTemporalKind.INSTANT:
            if raw_value is None:
                raise ValueError("instant temporal records require raw_value")
            instant = _parse_aware_instant(raw_value, field_name="temporal.raw_value")
            normalized = _normalized_instant(instant)
            expected_precision = _instant_precision(raw_value)
            expected_zone = TimezoneProvenance.SOURCE_EXPLICIT_OFFSET
            supplied_start = payload.get("normalized_start")
            supplied_end = payload.get("normalized_end")
            if supplied_start not in {None, normalized} or supplied_end not in {
                None,
                normalized,
            }:
                raise ValueError(
                    "instant normalized_start/end must match raw_value exactly"
                )
            payload.update(
                precision=expected_precision,
                normalized_start=normalized,
                normalized_end=normalized,
                timezone_provenance=expected_zone,
            )

        elif kind is ClinicalTemporalKind.DATE:
            if raw_value is None or not _DATE_RE.fullmatch(raw_value):
                raise ValueError("date temporal records require raw_value YYYY-MM-DD")
            try:
                normalized = date.fromisoformat(raw_value).isoformat()
            except ValueError as exc:
                raise ValueError("temporal.raw_value is not a valid date") from exc
            supplied_start = payload.get("normalized_start")
            supplied_end = payload.get("normalized_end")
            if supplied_start not in {None, normalized} or supplied_end not in {
                None,
                normalized,
            }:
                raise ValueError("date normalized_start/end must match raw_value")
            payload.update(
                precision=ClinicalTemporalPrecision.DAY,
                normalized_start=normalized,
                normalized_end=normalized,
                timezone_provenance=TimezoneProvenance.NOT_APPLICABLE,
            )

        elif kind is ClinicalTemporalKind.RANGE:
            if raw_value is None:
                raise ValueError("range temporal records require raw_value")
            raw_start = payload.get("normalized_start")
            raw_end = payload.get("normalized_end")
            if raw_start is None or raw_end is None:
                split_range = raw_value.split("/", 1)
                if len(split_range) == 2:
                    raw_start, raw_end = split_range
            if not isinstance(raw_start, str) or not isinstance(raw_end, str):
                raise ValueError(
                    "range temporal records require normalized_start and normalized_end"
                )
            start, start_domain = _normalize_range_endpoint(
                raw_start, field_name="temporal.normalized_start"
            )
            end, end_domain = _normalize_range_endpoint(
                raw_end, field_name="temporal.normalized_end"
            )
            if start_domain != end_domain:
                raise ValueError("range endpoints must both be dates or aware instants")
            if start_domain == "date":
                if date.fromisoformat(start) > date.fromisoformat(end):
                    raise ValueError(
                        "range normalized_start must not follow normalized_end"
                    )
                expected_precision = ClinicalTemporalPrecision.DAY
                expected_zone = TimezoneProvenance.NOT_APPLICABLE
            else:
                start_instant = _parse_aware_instant(
                    start, field_name="temporal.normalized_start"
                )
                end_instant = _parse_aware_instant(
                    end, field_name="temporal.normalized_end"
                )
                if start_instant > end_instant:
                    raise ValueError(
                        "range normalized_start must not follow normalized_end"
                    )
                supplied_precision = payload.get("precision")
                try:
                    expected_precision = ClinicalTemporalPrecision(
                        supplied_precision or ClinicalTemporalPrecision.SECOND
                    )
                except ValueError as exc:
                    raise ValueError("range precision is invalid") from exc
                if expected_precision not in {
                    ClinicalTemporalPrecision.MINUTE,
                    ClinicalTemporalPrecision.SECOND,
                    ClinicalTemporalPrecision.SUBSECOND,
                }:
                    raise ValueError("aware-instant range precision must be time-based")
                expected_zone = TimezoneProvenance.SOURCE_EXPLICIT_OFFSET
            payload.update(
                precision=expected_precision,
                normalized_start=start,
                normalized_end=end,
                timezone_provenance=expected_zone,
            )

        elif kind is ClinicalTemporalKind.RELATIVE:
            if raw_value is None:
                raise ValueError("relative temporal records require raw_value")
            if (
                payload.get("normalized_start") is not None
                or payload.get("normalized_end") is not None
            ):
                raise ValueError(
                    "relative temporal records cannot claim absolute bounds"
                )
            payload.update(
                precision=ClinicalTemporalPrecision.RELATIVE,
                normalized_start=None,
                normalized_end=None,
                timezone_provenance=TimezoneProvenance.NOT_APPLICABLE,
            )

        else:
            if (
                payload.get("normalized_start") is not None
                or payload.get("normalized_end") is not None
            ):
                raise ValueError(
                    "unknown temporal records cannot claim absolute bounds"
                )
            supplied_zone = payload.get("timezone_provenance")
            zone = (
                TimezoneProvenance.SOURCE_LOCAL_UNKNOWN
                if supplied_zone == TimezoneProvenance.SOURCE_LOCAL_UNKNOWN.value
                else TimezoneProvenance.UNKNOWN
            )
            payload.update(
                precision=ClinicalTemporalPrecision.UNKNOWN,
                normalized_start=None,
                normalized_end=None,
                timezone_provenance=zone,
            )

        payload["kind"] = kind
        return payload

    @classmethod
    def unknown(cls, raw_value: str | None = None) -> Self:
        """Construct explicit unknown time without inventing an instant."""
        return cls(
            kind=ClinicalTemporalKind.UNKNOWN,
            raw_value=raw_value,
            precision=ClinicalTemporalPrecision.UNKNOWN,
            timezone_provenance=TimezoneProvenance.UNKNOWN,
        )

    @classmethod
    def from_legacy_event_timestamp(
        cls,
        value: datetime | str,
        *,
        raw_value: str | None = None,
    ) -> Self:
        """Map a legacy aware timestamp to ``instant`` and reject weak precision."""
        if isinstance(value, datetime):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(
                    "event_timestamp must include an explicit timezone offset; "
                    "use temporal.kind=date/relative/unknown for weaker time data"
                )
            source_value = raw_value or value.isoformat()
        elif isinstance(value, str):
            source_value = raw_value or value
            try:
                _parse_aware_instant(source_value, field_name="event_timestamp")
            except ValueError as exc:
                raise ValueError(
                    "event_timestamp must be an ISO 8601 datetime containing 'T' "
                    "and an explicit timezone offset; use temporal.kind=date, "
                    "range, relative, or unknown for weaker time data"
                ) from exc
        else:
            raise ValueError("event_timestamp must be a datetime string")
        return cls(
            kind=ClinicalTemporalKind.INSTANT,
            raw_value=source_value,
            precision=ClinicalTemporalPrecision.SECOND,
            timezone_provenance=TimezoneProvenance.SOURCE_EXPLICIT_OFFSET,
        )

    @classmethod
    def from_lost_local_timestamp(cls, value: datetime | str) -> Self:
        """Preserve a legacy naive database value without promoting it to instant."""
        raw_value = value.isoformat() if isinstance(value, datetime) else str(value)
        return cls(
            kind=ClinicalTemporalKind.UNKNOWN,
            raw_value=raw_value,
            precision=ClinicalTemporalPrecision.UNKNOWN,
            timezone_provenance=TimezoneProvenance.SOURCE_LOCAL_UNKNOWN,
        )

    @property
    def aware_instant(self) -> datetime | None:
        """Return an aware instant only when this record genuinely represents one."""
        if self.kind is not ClinicalTemporalKind.INSTANT or not self.normalized_start:
            return None
        return _parse_aware_instant(
            self.normalized_start,
            field_name="temporal.normalized_start",
        )

    @property
    def source_aware_instant(self) -> datetime | None:
        """Return the instant using the source's explicit offset for compatibility."""
        if self.kind is not ClinicalTemporalKind.INSTANT or self.raw_value is None:
            return None
        return _parse_aware_instant(
            self.raw_value,
            field_name="temporal.raw_value",
        )

    @property
    def is_chronologically_sortable(self) -> bool:
        """Only aware instants may participate in absolute chronology."""
        return self.aware_instant is not None

    def display_value(self) -> str:
        """Return source-facing time text without fabricating a placeholder event."""
        if self.raw_value is not None:
            return self.raw_value
        return "Unknown time"

    model_config = ConfigDict(frozen=True, extra="forbid")


def resolve_clinical_temporal(
    temporal: ClinicalTemporal | dict[str, Any] | None,
    event_timestamp: datetime | str | None,
) -> ClinicalTemporal:
    """Resolve typed or legacy time input while requiring cross-field consistency."""
    if temporal is None:
        if event_timestamp is None:
            return ClinicalTemporal.unknown()
        return ClinicalTemporal.from_legacy_event_timestamp(event_timestamp)

    resolved = ClinicalTemporal.model_validate(temporal)
    if event_timestamp is None:
        return resolved
    legacy = ClinicalTemporal.from_legacy_event_timestamp(event_timestamp)
    if resolved.kind is not ClinicalTemporalKind.INSTANT:
        raise ValueError(
            "event_timestamp can accompany only temporal.kind=instant; remove it "
            "for date, range, relative, or unknown time"
        )
    if resolved.normalized_start != legacy.normalized_start:
        raise ValueError(
            "event_timestamp and temporal instant identify different times"
        )
    return resolved


__all__ = [
    "ClinicalTemporal",
    "ClinicalTemporalKind",
    "ClinicalTemporalPrecision",
    "TimezoneProvenance",
    "resolve_clinical_temporal",
]
