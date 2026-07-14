"""Personalized reminder schedule uses IST-normalized 09:00 send times (UTC-naive)."""

from datetime import datetime

from app.utils.policy_reminder_stages import (
    ESCALATION_REMINDER_TYPE,
    EXPIRY_DAY_REMINDER_TYPE,
    PERSONALIZED_REMINDER_TYPE,
    build_multi_custom_reminder_schedule,
    build_personalized_reminder_schedule,
    escalation_reminder_at,
    scheduled_personalized_reminder_at,
)


def test_personalized_schedule_uses_ist_normalized_day_offsets():
    expiry = datetime(2026, 6, 25, 12, 0, 0)
    custom = [
        {"reminder_unit": "days", "reminder_value": 7},
        {"reminder_unit": "days", "reminder_value": 3},
        {"reminder_unit": "days", "reminder_value": 1},
    ]
    schedule = build_multi_custom_reminder_schedule(expiry, custom)
    by_stage = {entry.stage: entry.reminder_at for entry in schedule if entry.reminder_type == PERSONALIZED_REMINDER_TYPE}

    assert by_stage[7] == scheduled_personalized_reminder_at(expiry, 7)
    assert by_stage[3] == scheduled_personalized_reminder_at(expiry, 3)
    assert by_stage[1] == scheduled_personalized_reminder_at(expiry, 1)
    assert not any(entry.reminder_type == EXPIRY_DAY_REMINDER_TYPE for entry in schedule)
    escalation = next(entry for entry in schedule if entry.reminder_type == ESCALATION_REMINDER_TYPE)
    assert escalation.reminder_at == escalation_reminder_at(expiry)
    assert by_stage[7] == datetime(2026, 6, 18, 3, 30, 0)
    assert escalation.reminder_at == datetime(2026, 6, 26, 3, 30, 0)


def test_personalized_schedule_types_for_offsets():
    expiry = datetime(2026, 6, 25, 12, 0, 0)
    schedule = build_personalized_reminder_schedule(expiry, unit="days", value=7)
    types = [row.reminder_type for row in schedule]
    assert types == [PERSONALIZED_REMINDER_TYPE, ESCALATION_REMINDER_TYPE]


def test_personalized_hours_offset_normalizes_to_ist_send_time():
    expiry = datetime(2026, 7, 1, 12, 0, 0)
    custom = [{"reminder_unit": "hours", "reminder_value": 12}]
    schedule = build_multi_custom_reminder_schedule(expiry, custom)
    personalized = [row for row in schedule if row.reminder_type == PERSONALIZED_REMINDER_TYPE]
    assert len(personalized) == 1
    assert personalized[0].reminder_at == datetime(2026, 7, 1, 3, 30, 0)
    assert not any(row.reminder_type == EXPIRY_DAY_REMINDER_TYPE for row in schedule)
