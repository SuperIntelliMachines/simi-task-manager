"""Validation helpers for per-policy renewal reminder configuration."""

from __future__ import annotations

import re
from datetime import datetime, time

REMINDER_TYPE_DEFAULT = "default"
REMINDER_TYPE_PERSONALIZED = "personalized"
REMINDER_TYPES = {REMINDER_TYPE_DEFAULT, REMINDER_TYPE_PERSONALIZED}

REMINDER_UNITS = {"hours", "days", "weeks", "months"}

_TIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)(?::([0-5]\d))?$")


def normalize_reminder_type(value: str | None) -> str:
    normalized = (value or REMINDER_TYPE_DEFAULT).strip().lower()
    if normalized not in REMINDER_TYPES:
        raise ValueError("reminder_type must be 'default' or 'personalized'")
    return normalized


def normalize_reminder_unit(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized not in REMINDER_UNITS:
        raise ValueError("reminder_unit must be one of: hours, days, weeks, months")
    return normalized


def parse_time_hhmm(value: str | time | datetime | None, *, field_name: str) -> time | None:
    if value is None:
        return None
    if isinstance(value, time):
        return value
    if isinstance(value, datetime):
        return value.time()
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        if not _TIME_PATTERN.match(stripped):
            raise ValueError(f"{field_name} must use HH:MM format")
        for fmt in ("%H:%M", "%H:%M:%S"):
            try:
                return datetime.strptime(stripped, fmt).time()
            except ValueError:
                continue
        raise ValueError(f"{field_name} must use HH:MM format")
    raise ValueError(f"{field_name} must use HH:MM format")


def validate_time_hhmm(value: str | time | datetime | None, *, field_name: str) -> time | None:
    return parse_time_hhmm(value, field_name=field_name)


def validate_policy_reminder_settings(
    *,
    reminder_type: str | None,
    reminder_unit: str | None,
    reminder_value: int | None,
    dnd_start_time: str | time | datetime | None,
    dnd_end_time: str | time | datetime | None,
    has_custom_reminders: bool = False,
) -> dict[str, str | int | time | None]:
    normalized_type = normalize_reminder_type(reminder_type)
    normalized_unit = normalize_reminder_unit(reminder_unit)
    normalized_start = validate_time_hhmm(dnd_start_time, field_name="dnd_start_time")
    normalized_end = validate_time_hhmm(dnd_end_time, field_name="dnd_end_time")

    if normalized_type == REMINDER_TYPE_DEFAULT:
        return {
            "reminder_type": normalized_type,
            "reminder_unit": None,
            "reminder_value": None,
            "dnd_start_time": None,
            "dnd_end_time": None,
        }

    if has_custom_reminders:
        if not normalized_start or not normalized_end:
            raise ValueError(
                "dnd_start_time and dnd_end_time are required for personalized custom reminders"
            )
        if normalized_start == normalized_end:
            raise ValueError("dnd_start_time and dnd_end_time must be different")
        return {
            "reminder_type": normalized_type,
            "reminder_unit": None,
            "reminder_value": None,
            "dnd_start_time": normalized_start,
            "dnd_end_time": normalized_end,
        }

    if normalized_unit is None:
        raise ValueError("reminder_unit is required when reminder_type is personalized")
    if reminder_value is None or int(reminder_value) <= 0:
        raise ValueError("reminder_value must be a positive integer for personalized reminders")
    if not normalized_start or not normalized_end:
        raise ValueError("dnd_start_time and dnd_end_time are required for personalized reminders")
    if normalized_start == normalized_end:
        raise ValueError("dnd_start_time and dnd_end_time must be different")

    return {
        "reminder_type": normalized_type,
        "reminder_unit": normalized_unit,
        "reminder_value": int(reminder_value),
        "dnd_start_time": normalized_start,
        "dnd_end_time": normalized_end,
    }
