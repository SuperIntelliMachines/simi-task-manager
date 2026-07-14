"""Policy reminder stage metadata (direction/unit/value)."""

from __future__ import annotations

from datetime import datetime

import pytest

from app.utils.policy_reminder_stages import (
    ESCALATION_REMINDER_TYPE,
    EXPIRY_DAY_REMINDER_TYPE,
    PERSONALIZED_REMINDER_TYPE,
    STAGE_DIRECTION_AFTER,
    STAGE_DIRECTION_BEFORE,
    STAGE_DIRECTION_ON,
    build_multi_custom_reminder_schedule,
    build_policy_reminder_schedule,
    build_renewal_reminder_schedule,
    escalation_metadata,
    expiry_day_metadata,
    personalized_reminder_metadata,
    personalized_reminder_stage,
)


def _entry_map(schedule):
    return {
        (entry.stage_direction, entry.stage_unit, entry.stage_value): entry
        for entry in schedule
    }


def test_personalized_reminder_metadata_examples():
    assert personalized_reminder_metadata("months", 1) == (30, STAGE_DIRECTION_BEFORE, "months", 1)
    assert personalized_reminder_metadata("weeks", 3) == (21, STAGE_DIRECTION_BEFORE, "weeks", 3)
    assert personalized_reminder_metadata("days", 4) == (4, STAGE_DIRECTION_BEFORE, "days", 4)
    assert personalized_reminder_metadata("hours", 14) == (14, STAGE_DIRECTION_BEFORE, "hours", 14)


def test_personalized_reminder_stage_is_always_positive():
    assert personalized_reminder_stage("hours", 12) == 12
    assert personalized_reminder_stage("days", 7) == 7
    assert personalized_reminder_stage("weeks", 2) == 14
    assert personalized_reminder_stage("months", 1) == 30


def test_system_reminder_metadata():
    assert expiry_day_metadata() == (0, STAGE_DIRECTION_ON, "day", 0)
    assert escalation_metadata() == (1, STAGE_DIRECTION_AFTER, "days", 1)


def test_build_renewal_schedule_uses_positive_escalation_stage():
    expiry = datetime(2026, 7, 1, 12, 0, 0)
    schedule = build_renewal_reminder_schedule(expiry)
    stages = [entry.stage for entry in schedule]
    assert all(stage >= 0 for stage in stages)
    assert stages[-1] == 1
    escalation = schedule[-1]
    assert escalation.reminder_type == ESCALATION_REMINDER_TYPE
    assert escalation.stage_direction == STAGE_DIRECTION_AFTER
    assert escalation.stage_unit == "days"
    assert escalation.stage_value == 1


def test_build_multi_custom_schedule_metadata():
    expiry = datetime(2026, 7, 30, 12, 0, 0)
    custom = [
        {"reminder_unit": "months", "reminder_value": 1},
        {"reminder_unit": "weeks", "reminder_value": 1},
        {"reminder_unit": "days", "reminder_value": 1},
        {"reminder_unit": "hours", "reminder_value": 5},
    ]
    schedule = build_multi_custom_reminder_schedule(expiry, custom)
    by_key = _entry_map(schedule)

    month = by_key[(STAGE_DIRECTION_BEFORE, "months", 1)]
    assert month.reminder_type == PERSONALIZED_REMINDER_TYPE
    assert month.stage == 30

    hours = by_key[(STAGE_DIRECTION_BEFORE, "hours", 5)]
    assert hours.stage == 5

    assert (STAGE_DIRECTION_ON, "day", 0) not in by_key

    escalation = by_key[(STAGE_DIRECTION_AFTER, "days", 1)]
    assert escalation.reminder_type == ESCALATION_REMINDER_TYPE
    assert escalation.stage == 1


def test_personalized_schedule_excludes_expiry_day():
    expiry = datetime(2026, 7, 30, 12, 0, 0)
    custom = [{"reminder_unit": "hours", "reminder_value": 14}]
    schedule = build_multi_custom_reminder_schedule(expiry, custom)
    types = [entry.reminder_type for entry in schedule]
    assert PERSONALIZED_REMINDER_TYPE in types
    assert ESCALATION_REMINDER_TYPE in types
    assert EXPIRY_DAY_REMINDER_TYPE not in types


def test_default_schedule_includes_expiry_day_and_escalation():
    expiry = datetime(2026, 7, 1, 12, 0, 0)
    schedule = build_renewal_reminder_schedule(expiry)
    types = [entry.reminder_type for entry in schedule]
    assert EXPIRY_DAY_REMINDER_TYPE in types
    assert ESCALATION_REMINDER_TYPE in types


def test_build_policy_reminder_schedule_default_stages():
    expiry = datetime(2026, 7, 1, 12, 0, 0)
    schedule = build_policy_reminder_schedule(
        expiry,
        reminder_type="default",
        reminder_unit=None,
        reminder_value=None,
    )
    stages = [entry.stage for entry in schedule]
    assert stages == [30, 15, 10, 5, 2, 1, 0, 1]
    assert all(entry.stage >= 0 for entry in schedule)


def test_multi_custom_offsets_computed_independently_from_expiry():
    """Regression: weeks/days/hours must not chain from an earlier month anchor."""
    expiry = datetime(2026, 7, 30, 12, 0, 0)
    custom = [
        {"reminder_unit": "months", "reminder_value": 1},
        {"reminder_unit": "weeks", "reminder_value": 3},
        {"reminder_unit": "days", "reminder_value": 4},
        {"reminder_unit": "hours", "reminder_value": 8},
    ]
    schedule = build_multi_custom_reminder_schedule(expiry, custom)
    by_key = _entry_map(schedule)

    assert by_key[(STAGE_DIRECTION_BEFORE, "months", 1)].reminder_at == datetime(
        2026, 6, 30, 3, 30, 0
    )
    assert by_key[(STAGE_DIRECTION_BEFORE, "weeks", 3)].reminder_at == datetime(
        2026, 7, 9, 3, 30, 0
    )
    assert by_key[(STAGE_DIRECTION_BEFORE, "days", 4)].reminder_at == datetime(
        2026, 7, 26, 3, 30, 0
    )
    assert by_key[(STAGE_DIRECTION_BEFORE, "hours", 8)].reminder_at == datetime(
        2026, 7, 30, 3, 30, 0
    )


@pytest.mark.parametrize(
    "custom",
    [
        [
            {"reminder_unit": "months", "reminder_value": 1},
            {"reminder_unit": "weeks", "reminder_value": 3},
            {"reminder_unit": "days", "reminder_value": 4},
            {"reminder_unit": "hours", "reminder_value": 8},
        ],
        [
            {"reminder_unit": "hours", "reminder_value": 8},
            {"reminder_unit": "days", "reminder_value": 4},
            {"reminder_unit": "weeks", "reminder_value": 3},
            {"reminder_unit": "months", "reminder_value": 1},
        ],
    ],
)
def test_multi_custom_offsets_independent_of_input_order(custom):
    expiry = datetime(2026, 7, 30, 12, 0, 0)
    schedule = build_multi_custom_reminder_schedule(expiry, custom)
    by_key = _entry_map(schedule)

    assert by_key[(STAGE_DIRECTION_BEFORE, "months", 1)].reminder_at == datetime(
        2026, 6, 30, 3, 30, 0
    )
    assert by_key[(STAGE_DIRECTION_BEFORE, "weeks", 3)].reminder_at == datetime(
        2026, 7, 9, 3, 30, 0
    )
    assert by_key[(STAGE_DIRECTION_BEFORE, "days", 4)].reminder_at == datetime(
        2026, 7, 26, 3, 30, 0
    )
    assert by_key[(STAGE_DIRECTION_BEFORE, "hours", 8)].reminder_at == datetime(
        2026, 7, 30, 3, 30, 0
    )
