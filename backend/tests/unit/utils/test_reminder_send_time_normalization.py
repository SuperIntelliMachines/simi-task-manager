"""Reminder send times normalize to 09:00 IST, stored as UTC-naive."""

from datetime import date, datetime

from app.utils.datetime_utils import (
    expiry_ist_calendar_date,
    normalize_reminder_send_at,
    reminder_send_at_ist_date,
)
from app.utils.policy_reminder_stages import (
    ESCALATION_REMINDER_TYPE,
    EXPIRY_DAY_REMINDER_TYPE,
    PERSONALIZED_REMINDER_TYPE,
    build_multi_custom_reminder_schedule,
    build_renewal_reminder_schedule,
    escalation_reminder_at,
    expiry_day_reminder_at,
    scheduled_personalized_reminder_at,
    scheduled_reminder_at,
    scheduled_reminder_at_hours_before,
)


def _utc_naive(*args: int) -> datetime:
    return datetime(*args)


def test_reminder_send_at_ist_date_converts_to_utc_naive():
    # 2026-06-18 09:00 IST = 2026-06-18 03:30 UTC
    result = reminder_send_at_ist_date(date(2026, 6, 18))
    assert result == _utc_naive(2026, 6, 18, 3, 30, 0)
    assert result.tzinfo is None


def test_expiry_ist_calendar_date_uses_kolkata_wall_date():
    # 2026-06-25 20:00 UTC is 2026-06-26 01:30 IST
    expiry = _utc_naive(2026, 6, 25, 20, 0, 0)
    assert expiry_ist_calendar_date(expiry) == date(2026, 6, 26)


def test_normalize_reminder_send_at_snaps_to_0900_ist():
    reference = _utc_naive(2026, 6, 25, 12, 0, 0)
    assert normalize_reminder_send_at(reference) == _utc_naive(2026, 6, 25, 3, 30, 0)


def test_default_schedule_ignores_expiry_clock_time():
    expiry = _utc_naive(2026, 6, 25, 12, 0, 0)
    schedule = build_renewal_reminder_schedule(expiry)
    by_stage = {entry.stage: entry.reminder_at for entry in schedule if entry.stage != 1 or entry.stage_direction == "BEFORE"}

    assert by_stage[30] == _utc_naive(2026, 5, 26, 3, 30, 0)
    assert by_stage[0] == expiry_day_reminder_at(expiry)
    escalation = next(entry for entry in schedule if entry.reminder_type == ESCALATION_REMINDER_TYPE)
    assert escalation.reminder_at == escalation_reminder_at(expiry)
    assert by_stage[0] == _utc_naive(2026, 6, 25, 3, 30, 0)
    assert escalation.reminder_at == _utc_naive(2026, 6, 26, 3, 30, 0)


def test_personalized_day_offsets_match_default_normalization():
    expiry = _utc_naive(2026, 6, 25, 12, 0, 0)
    custom = [
        {"reminder_unit": "days", "reminder_value": 7},
        {"reminder_unit": "days", "reminder_value": 3},
        {"reminder_unit": "days", "reminder_value": 1},
    ]
    schedule = build_multi_custom_reminder_schedule(expiry, custom)
    by_stage = {entry.stage: entry.reminder_at for entry in schedule if entry.reminder_type == PERSONALIZED_REMINDER_TYPE}

    assert by_stage[7] == scheduled_personalized_reminder_at(expiry, 7)
    assert by_stage[7] == scheduled_reminder_at(expiry, 7)
    assert not any(entry.reminder_type == EXPIRY_DAY_REMINDER_TYPE for entry in schedule)
    escalation = next(entry for entry in schedule if entry.reminder_type == ESCALATION_REMINDER_TYPE)
    assert escalation.reminder_at == escalation_reminder_at(expiry)


def test_personalized_hours_offset_normalizes_send_time():
    expiry = _utc_naive(2026, 7, 1, 12, 0, 0)
    custom = [{"reminder_unit": "hours", "reminder_value": 12}]
    schedule = build_multi_custom_reminder_schedule(expiry, custom)
    personalized = [row for row in schedule if row.reminder_type == PERSONALIZED_REMINDER_TYPE]
    assert len(personalized) == 1
    expected = scheduled_reminder_at_hours_before(expiry, 12)
    assert personalized[0].reminder_at == expected
    assert expected == _utc_naive(2026, 7, 1, 3, 30, 0)


def test_personalized_schedule_has_escalation_not_expiry_day():
    expiry = _utc_naive(2026, 6, 25, 12, 0, 0)
    custom = [{"reminder_unit": "days", "reminder_value": 7}]
    schedule = build_multi_custom_reminder_schedule(expiry, custom)
    types = [row.reminder_type for row in schedule]
    assert types == [PERSONALIZED_REMINDER_TYPE, ESCALATION_REMINDER_TYPE]
    assert EXPIRY_DAY_REMINDER_TYPE not in types
