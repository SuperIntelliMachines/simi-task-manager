from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

REMINDER_SEND_TIMEZONE = ZoneInfo("Asia/Kolkata")
REMINDER_SEND_HOUR = 9
REMINDER_SEND_MINUTE = 0


def normalize_to_utc_naive(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if getattr(dt, "tzinfo", None) is not None:
        return dt.astimezone(UTC).replace(tzinfo=None)
    return dt


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def expiry_ist_calendar_date(expiry_date: datetime) -> date:
    """Calendar date of the policy expiry instant in Asia/Kolkata."""
    utc_naive = normalize_to_utc_naive(expiry_date)
    if utc_naive is None:
        raise ValueError("expiry_date is required")
    return utc_naive.replace(tzinfo=UTC).astimezone(REMINDER_SEND_TIMEZONE).date()


def reminder_send_at_ist_date(ist_date: date) -> datetime:
    """Return 09:00 IST on ``ist_date`` as a UTC-naive timestamp for DB storage."""
    local = datetime(
        ist_date.year,
        ist_date.month,
        ist_date.day,
        REMINDER_SEND_HOUR,
        REMINDER_SEND_MINUTE,
        0,
        tzinfo=REMINDER_SEND_TIMEZONE,
    )
    return local.astimezone(UTC).replace(tzinfo=None)


def normalize_reminder_send_at(reference: datetime) -> datetime:
    """
    Snap a reference instant to 09:00 IST on its Asia/Kolkata calendar date.

    Used after day/hour offsets so sends do not inherit arbitrary expiry clock times.
    """
    utc_naive = normalize_to_utc_naive(reference)
    if utc_naive is None:
        raise ValueError("reference datetime is required")
    ist_date = utc_naive.replace(tzinfo=UTC).astimezone(REMINDER_SEND_TIMEZONE).date()
    return reminder_send_at_ist_date(ist_date)


def normalize_reminder_at(dt: datetime | None) -> datetime | None:
    """Normalize policy reminder timestamps to UTC-naive for storage and comparison."""
    return normalize_to_utc_naive(dt)
