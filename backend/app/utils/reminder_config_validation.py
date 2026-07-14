"""Validation helpers for generic reminder config scheduling modes."""

from __future__ import annotations

from datetime import datetime, time

from app.core.enums import (
    DEFAULT_REMINDER_ANCHOR_KEY,
    ReminderAnchorType,
    ReminderOffsetDirection,
)


class ReminderSchedulingValidationError(ValueError):
    """Raised when reminder config scheduling fields are invalid."""


def normalize_anchor_type(value: str | ReminderAnchorType | None) -> str:
    if value is None or (isinstance(value, str) and not value.strip()):
        return ReminderAnchorType.DATE.value
    normalized = value.value if isinstance(value, ReminderAnchorType) else str(value).strip().lower()
    allowed = {item.value for item in ReminderAnchorType}
    if normalized not in allowed:
        raise ReminderSchedulingValidationError(
            f"anchor_type must be one of: {', '.join(sorted(allowed))}"
        )
    return normalized


def normalize_offset_direction(value: str | ReminderOffsetDirection | None) -> str:
    if value is None or (isinstance(value, str) and not value.strip()):
        return ReminderOffsetDirection.BEFORE.value
    normalized = (
        value.value if isinstance(value, ReminderOffsetDirection) else str(value).strip().lower()
    )
    allowed = {item.value for item in ReminderOffsetDirection}
    if normalized not in allowed:
        raise ReminderSchedulingValidationError(
            f"offset_direction must be one of: {', '.join(sorted(allowed))}"
        )
    return normalized


def normalize_anchor_key(value: str | None) -> str:
    if value is None:
        return DEFAULT_REMINDER_ANCHOR_KEY
    normalized = str(value).strip()
    if not normalized:
        raise ReminderSchedulingValidationError("anchor_key must not be empty")
    return normalized


def validate_anchor_fields(
    *,
    anchor_type: str | ReminderAnchorType | None = None,
    anchor_key: str | None = None,
    offset_direction: str | ReminderOffsetDirection | None = None,
) -> tuple[str, str, str]:
    """Return normalized (anchor_type, anchor_key, offset_direction) with defaults."""
    return (
        normalize_anchor_type(anchor_type),
        normalize_anchor_key(anchor_key),
        normalize_offset_direction(offset_direction),
    )


def is_absolute_config(*, absolute_scheduled_at: datetime | None) -> bool:
    return absolute_scheduled_at is not None


def validate_relative_scheduling(
    *,
    offset_value: int | None,
    offset_unit: str | None,
    time_of_day: time | None,
    absolute_scheduled_at: datetime | None,
) -> tuple[int, str]:
    if absolute_scheduled_at is not None:
        raise ReminderSchedulingValidationError(
            "relative reminder cannot include scheduled_at"
        )
    if offset_value is None:
        raise ReminderSchedulingValidationError("relative reminder requires offset_value")
    if offset_unit is None or not str(offset_unit).strip():
        raise ReminderSchedulingValidationError("relative reminder requires offset_unit")
    normalized_unit = str(offset_unit).strip().lower()
    if normalized_unit not in {"hours", "days", "weeks", "months"}:
        raise ReminderSchedulingValidationError(
            "offset_unit must be one of: hours, days, weeks, months"
        )
    if int(offset_value) < 0:
        raise ReminderSchedulingValidationError("offset_value must be >= 0")
    return int(offset_value), normalized_unit


def validate_absolute_scheduling(
    *,
    offset_value: int | None,
    offset_unit: str | None,
    time_of_day: time | None,
    absolute_scheduled_at: datetime | None,
) -> datetime:
    if absolute_scheduled_at is None:
        raise ReminderSchedulingValidationError("absolute reminder requires scheduled_at")
    if offset_value is not None:
        raise ReminderSchedulingValidationError(
            "absolute reminder cannot include offset_value"
        )
    if time_of_day is not None:
        raise ReminderSchedulingValidationError(
            "absolute reminder cannot include time_of_day"
        )
    return absolute_scheduled_at


def validate_scheduling_fields(
    *,
    offset_value: int | None,
    offset_unit: str | None,
    time_of_day: time | None,
    absolute_scheduled_at: datetime | None,
) -> tuple[str, int | None, str | None, time | None, datetime | None]:
    """
    Validate that exactly one scheduling mode is configured.

    Returns (mode, offset_value, offset_unit, time_of_day, absolute_scheduled_at).
    mode is 'relative' or 'absolute'.
    """
    has_absolute = absolute_scheduled_at is not None
    has_relative_hint = offset_value is not None or (offset_unit is not None and offset_unit != "days")

    if has_absolute and has_relative_hint:
        raise ReminderSchedulingValidationError(
            "reminder must use either relative offsets or scheduled_at, not both"
        )

    if has_absolute:
        return (
            "absolute",
            None,
            None,
            None,
            validate_absolute_scheduling(
                offset_value=offset_value,
                offset_unit=offset_unit,
                time_of_day=time_of_day,
                absolute_scheduled_at=absolute_scheduled_at,
            ),
        )

    if offset_value is None:
        raise ReminderSchedulingValidationError(
            "reminder requires either offset_value or scheduled_at"
        )

    resolved_offset, resolved_unit = validate_relative_scheduling(
        offset_value=offset_value,
        offset_unit=offset_unit or "days",
        time_of_day=time_of_day,
        absolute_scheduled_at=absolute_scheduled_at,
    )
    return ("relative", resolved_offset, resolved_unit, time_of_day, None)
