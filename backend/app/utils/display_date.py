"""Strict DD-MM-YYYY date parsing and validation."""

from __future__ import annotations

import re
from datetime import datetime

from app.utils.datetime_utils import normalize_to_utc_naive

DISPLAY_DATE_PATTERN = re.compile(r"^(\d{2})-(\d{2})-(\d{4})$")
MIN_YEAR = 1900
MAX_YEAR = 2100


def _is_valid_calendar_date(day: int, month: int, year: int) -> bool:
    if month < 1 or month > 12 or day < 1 or day > 31:
        return False
    candidate = datetime(year, month, day, 12, 0, 0)
    return candidate.year == year and candidate.month == month and candidate.day == day


def parse_display_date(value: str) -> datetime:
    """Parse DD-MM-YYYY into a UTC-naive datetime at noon."""
    trimmed = (value or "").strip()
    match = DISPLAY_DATE_PATTERN.fullmatch(trimmed)
    if not match:
        partial = re.fullmatch(r"(\d{2})-(\d{2})-(\d+)", trimmed)
        if partial and len(partial.group(3)) != 4:
            raise ValueError("Year must be exactly 4 digits. Use DD-MM-YYYY format.")
        raise ValueError("Invalid date format. Use DD-MM-YYYY.")

    day = int(match.group(1))
    month = int(match.group(2))
    year = int(match.group(3))

    if year < MIN_YEAR or year > MAX_YEAR:
        raise ValueError(f"Year must be between {MIN_YEAR} and {MAX_YEAR}.")

    if not _is_valid_calendar_date(day, month, year):
        raise ValueError("Invalid calendar date.")

    return datetime(year, month, day, 12, 0, 0)


def validate_expiry_datetime(value: datetime) -> datetime:
    """Normalize and ensure expiry datetime has a supported 4-digit year."""
    normalized = normalize_to_utc_naive(value)
    if normalized is None:
        raise ValueError("Expiry date is required.")
    if normalized.year < MIN_YEAR or normalized.year > MAX_YEAR:
        raise ValueError(f"Year must be between {MIN_YEAR} and {MAX_YEAR}.")
    return normalized
