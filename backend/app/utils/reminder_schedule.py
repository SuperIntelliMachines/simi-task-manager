"""Shared reminder schedule calculations for the generic reminder engine."""

from __future__ import annotations

from calendar import monthrange
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.core.enums import ReminderOffsetDirection
from app.utils.datetime_utils import REMINDER_SEND_TIMEZONE, normalize_to_utc_naive


def _shift_months(anchor_date: datetime, months: int) -> datetime:
    """Shift ``anchor_date`` by ``months`` (negative = earlier)."""
    year = anchor_date.year
    month = anchor_date.month + months
    while month <= 0:
        month += 12
        year -= 1
    while month > 12:
        month -= 12
        year += 1
    day = min(anchor_date.day, monthrange(year, month)[1])
    return anchor_date.replace(year=year, month=month, day=day)


def scheduled_at_for_offset(
    *,
    anchor_date: datetime,
    offset_value: int,
    offset_unit: str,
    offset_direction: str = ReminderOffsetDirection.BEFORE.value,
) -> datetime:
    """Return reminder send time by applying offset before/after ``anchor_date``."""
    direction = (offset_direction or ReminderOffsetDirection.BEFORE.value).strip().lower()
    sign = -1 if direction == ReminderOffsetDirection.BEFORE.value else 1
    amount = int(offset_value) * sign

    if offset_unit == "hours":
        return anchor_date + timedelta(hours=amount)
    if offset_unit == "days":
        return anchor_date + timedelta(days=amount)
    if offset_unit == "weeks":
        return anchor_date + timedelta(weeks=amount)
    if offset_unit == "months":
        return _shift_months(anchor_date, amount)
    raise ValueError(f"unsupported offset_unit: {offset_unit}")


def get_default_reminder_timezone() -> ZoneInfo:
    from app.core.config import get_settings

    settings = get_settings()
    try:
        return ZoneInfo(settings.default_reminder_timezone)
    except Exception:
        return REMINDER_SEND_TIMEZONE


def get_default_reminder_time_of_day() -> time:
    from app.core.config import get_settings
    from app.utils.policy_reminder_settings import parse_time_hhmm

    settings = get_settings()
    parsed = parse_time_hhmm(settings.default_reminder_time, field_name="default_reminder_time")
    return parsed or time(9, 0)


def apply_time_of_day_on_date(
    *,
    reference: datetime,
    send_time: time,
) -> datetime:
    """
    Set wall-clock send time on the calendar date of ``reference``.

    Both custom ``time_of_day`` and the default send time use naive wall-clock
    values on the offset date (no timezone conversion).
    """
    utc_naive = normalize_to_utc_naive(reference)
    if utc_naive is None:
        raise ValueError("reference datetime is required")
    return utc_naive.replace(
        hour=send_time.hour,
        minute=send_time.minute,
        second=send_time.second,
        microsecond=0,
    )


def scheduled_at_for_relative_config(
    *,
    anchor_date: datetime,
    offset_value: int,
    offset_unit: str,
    time_of_day: time | None = None,
    offset_direction: str = ReminderOffsetDirection.BEFORE.value,
) -> datetime:
    """
    Compute instance scheduled_at for a relative reminder config.

    For day/week/month offsets, when time_of_day is omitted, applies
    DEFAULT_REMINDER_TIME (09:00 by default) as wall-clock time on the offset date.

    For hour offsets, preserves the exact computed instant unless time_of_day is set.
    """
    offset_date = scheduled_at_for_offset(
        anchor_date=anchor_date,
        offset_value=offset_value,
        offset_unit=offset_unit,
        offset_direction=offset_direction,
    )
    unit = (offset_unit or "days").strip().lower()
    if unit == "hours" and time_of_day is None:
        normalized = normalize_to_utc_naive(offset_date)
        if normalized is None:
            raise ValueError("anchor_date is required")
        return normalized

    send_time = time_of_day if time_of_day is not None else get_default_reminder_time_of_day()
    return apply_time_of_day_on_date(reference=offset_date, send_time=send_time)


def scheduled_at_for_absolute_config(*, absolute_scheduled_at: datetime) -> datetime:
    normalized = normalize_to_utc_naive(absolute_scheduled_at)
    if normalized is None:
        raise ValueError("scheduled_at is required for absolute reminders")
    return normalized
