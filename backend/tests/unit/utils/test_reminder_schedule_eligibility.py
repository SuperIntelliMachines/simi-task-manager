"""Eligibility window for reminder schedule generation."""

from __future__ import annotations

from datetime import datetime

import pytest

from app.utils.policy_reminder_stages import (
    REMINDER_SCHEDULE_LOOKAHEAD_GRACE_DAYS,
    is_eligible_for_reminder_schedule,
    max_reminder_lookahead_days,
)


def test_max_reminder_lookahead_includes_one_month_custom_offset():
    custom = [
        {"reminder_unit": "months", "reminder_value": 1},
        {"reminder_unit": "weeks", "reminder_value": 1},
        {"reminder_unit": "hours", "reminder_value": 5},
    ]
    assert max_reminder_lookahead_days(
        reminder_type="personalized",
        reminder_unit=None,
        reminder_value=None,
        custom_reminders=custom,
    ) == 30


def test_policy_109_scenario_eligible_within_grace_window(monkeypatch):
    """31 days before expiry is eligible when max offset is 30 (calendar month variance)."""
    today = datetime(2026, 6, 29, 10, 0, 0)
    expiry = datetime(2026, 7, 30, 12, 0, 0)
    monkeypatch.setattr("app.utils.policy_reminder_stages.utcnow_naive", lambda: today)

    custom = [
        {"reminder_unit": "months", "reminder_value": 1},
        {"reminder_unit": "weeks", "reminder_value": 1},
        {"reminder_unit": "days", "reminder_value": 1},
        {"reminder_unit": "hours", "reminder_value": 5},
    ]
    assert is_eligible_for_reminder_schedule(
        status="active",
        expiry_date=expiry,
        reminder_type="personalized",
        custom_reminders=custom,
    )


def test_policy_outside_grace_window_not_eligible(monkeypatch):
    today = datetime(2026, 5, 1, 10, 0, 0)
    expiry = datetime(2026, 7, 30, 12, 0, 0)
    monkeypatch.setattr("app.utils.policy_reminder_stages.utcnow_naive", lambda: today)

    custom = [{"reminder_unit": "months", "reminder_value": 1}]
    assert not is_eligible_for_reminder_schedule(
        status="active",
        expiry_date=expiry,
        reminder_type="personalized",
        custom_reminders=custom,
    )


def test_grace_constant_covers_31_day_calendar_month():
    assert REMINDER_SCHEDULE_LOOKAHEAD_GRACE_DAYS >= 1
