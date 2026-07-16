"""Validation helpers for recurring reminders and stop conditions."""

from __future__ import annotations

from typing import Any

from app.core.enums import (
    DEFAULT_REMINDER_STOP_CONDITION,
    REMINDER_OFFSET_UNITS,
    ReminderStopCondition,
)
from app.utils.reminder_config_validation import ReminderSchedulingValidationError


def normalize_stop_condition(value: str | ReminderStopCondition | None) -> str:
    if value is None or (isinstance(value, str) and not value.strip()):
        return DEFAULT_REMINDER_STOP_CONDITION
    normalized = (
        value.value if isinstance(value, ReminderStopCondition) else str(value).strip().lower()
    )
    allowed = {item.value for item in ReminderStopCondition}
    if normalized not in allowed:
        raise ReminderSchedulingValidationError(
            f"stop_condition must be one of: {', '.join(sorted(allowed))}"
        )
    return normalized


def normalize_repeat_frequency_unit(value: str | None) -> str | None:
    if value is None or not str(value).strip():
        return None
    normalized = str(value).strip().lower()
    if normalized not in REMINDER_OFFSET_UNITS:
        raise ReminderSchedulingValidationError(
            f"repeat_frequency_unit must be one of: {', '.join(sorted(REMINDER_OFFSET_UNITS))}"
        )
    return normalized


def validate_recurrence_fields(
    *,
    repeat_enabled: bool | None = None,
    repeat_frequency_value: int | None = None,
    repeat_frequency_unit: str | None = None,
    max_attempts: int | None = None,
    stop_condition: str | ReminderStopCondition | None = None,
    stop_condition_config: dict[str, Any] | None = None,
) -> tuple[bool, int | None, str | None, int | None, str, dict[str, Any] | None]:
    """Return normalized recurrence/stop fields with sensible defaults."""
    enabled = bool(repeat_enabled)
    normalized_stop = normalize_stop_condition(stop_condition)
    normalized_config = dict(stop_condition_config) if stop_condition_config else None

    normalized_max: int | None
    if max_attempts is None:
        normalized_max = None
    else:
        normalized_max = int(max_attempts)
        if normalized_max < 1:
            raise ReminderSchedulingValidationError("max_attempts must be >= 1 when provided")

    if not enabled:
        return False, None, None, normalized_max, normalized_stop, normalized_config

    if repeat_frequency_value is None:
        raise ReminderSchedulingValidationError(
            "repeat_frequency_value is required when repeat_enabled is true"
        )
    normalized_value = int(repeat_frequency_value)
    if normalized_value < 1:
        raise ReminderSchedulingValidationError("repeat_frequency_value must be >= 1")

    normalized_unit = normalize_repeat_frequency_unit(repeat_frequency_unit)
    if normalized_unit is None:
        raise ReminderSchedulingValidationError(
            "repeat_frequency_unit is required when repeat_enabled is true"
        )

    return (
        True,
        normalized_value,
        normalized_unit,
        normalized_max,
        normalized_stop,
        normalized_config,
    )
