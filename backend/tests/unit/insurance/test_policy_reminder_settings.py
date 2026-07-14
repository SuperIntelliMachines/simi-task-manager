from datetime import datetime, time

import pytest

from app.schemas.atm007 import InsurancePolicyCreateBody
from app.utils.policy_reminder_settings import (
    REMINDER_TYPE_DEFAULT,
    REMINDER_TYPE_PERSONALIZED,
    validate_policy_reminder_settings,
)
from app.utils.policy_reminder_dnd import is_within_dnd_window
from app.utils.policy_reminder_stages import (
    PERSONALIZED_REMINDER_TYPE,
    build_personalized_reminder_schedule,
    build_policy_reminder_schedule,
    get_policy_reminder_offsets,
    personalized_reminder_offset_days,
)


def test_default_reminder_settings_clear_personalized_fields():
    validated = validate_policy_reminder_settings(
        reminder_type="default",
        reminder_unit="days",
        reminder_value=7,
        dnd_start_time="21:00",
        dnd_end_time="08:00",
    )
    assert validated["reminder_type"] == REMINDER_TYPE_DEFAULT
    assert validated["reminder_unit"] is None
    assert validated["reminder_value"] is None
    assert validated["dnd_start_time"] is None
    assert validated["dnd_end_time"] is None


def test_personalized_reminder_settings_require_all_fields():
    with pytest.raises(ValueError, match="reminder_unit is required"):
        validate_policy_reminder_settings(
            reminder_type="personalized",
            reminder_unit=None,
            reminder_value=7,
            dnd_start_time="21:00",
            dnd_end_time="08:00",
        )


def test_personalized_reminder_settings_validate_success():
    validated = validate_policy_reminder_settings(
        reminder_type="personalized",
        reminder_unit="days",
        reminder_value=7,
        dnd_start_time="21:00",
        dnd_end_time="08:00",
    )
    assert validated["reminder_type"] == REMINDER_TYPE_PERSONALIZED
    assert validated["reminder_unit"] == "days"
    assert validated["reminder_value"] == 7
    assert validated["dnd_start_time"] == datetime.strptime("21:00", "%H:%M").time()
    assert validated["dnd_end_time"] == datetime.strptime("08:00", "%H:%M").time()


def test_custom_reminder_settings_require_and_preserve_dnd():
    validated = validate_policy_reminder_settings(
        reminder_type="personalized",
        reminder_unit=None,
        reminder_value=None,
        dnd_start_time="21:00",
        dnd_end_time="08:00",
        has_custom_reminders=True,
    )
    assert validated["reminder_type"] == REMINDER_TYPE_PERSONALIZED
    assert validated["reminder_unit"] is None
    assert validated["reminder_value"] is None
    assert validated["dnd_start_time"] == time(21, 0)
    assert validated["dnd_end_time"] == time(8, 0)


def test_custom_reminder_settings_require_dnd():
    with pytest.raises(ValueError, match="dnd_start_time and dnd_end_time are required"):
        validate_policy_reminder_settings(
            reminder_type="personalized",
            reminder_unit=None,
            reminder_value=None,
            dnd_start_time=None,
            dnd_end_time=None,
            has_custom_reminders=True,
        )


def test_insurance_policy_create_body_preserves_dnd_for_custom_reminders():
    body = InsurancePolicyCreateBody(
        organization_id=1,
        policyholder_name="Holder",
        expiry_date=datetime(2026, 12, 31, 12, 0, 0),
        custom_reminders=[{"reminder_unit": "days", "reminder_value": 7}],
        dnd_start_time="21:00",
        dnd_end_time="08:00",
    )
    assert body.dnd_start_time == time(21, 0)
    assert body.dnd_end_time == time(8, 0)


def test_build_policy_reminder_schedule_default_uses_standard_cycle():
    expiry = datetime(2026, 7, 1, 12, 0, 0)
    schedule = build_policy_reminder_schedule(
        expiry,
        reminder_type="default",
        reminder_unit=None,
        reminder_value=None,
    )
    stages = [entry.stage for entry in schedule]
    assert stages == [30, 15, 10, 5, 2, 1, 0, 1]


def test_personalized_reminder_offset_days_conversion():
    assert personalized_reminder_offset_days("days", 7) == 7
    assert personalized_reminder_offset_days("weeks", 2) == 14
    assert personalized_reminder_offset_days("months", 1) == 30
    assert get_policy_reminder_offsets(
        reminder_type="personalized",
        reminder_unit="days",
        reminder_value=7,
    ) == [7]
    assert get_policy_reminder_offsets(
        reminder_type="default",
        reminder_unit=None,
        reminder_value=None,
    ) == [30, 15, 10, 5, 2, 1, 0]


def test_build_personalized_reminder_schedule_single_offset():
    expiry = datetime(2026, 7, 31, 12, 0, 0)
    schedule = build_personalized_reminder_schedule(expiry, unit="days", value=7)
    personalized = [item for item in schedule if item.reminder_type == PERSONALIZED_REMINDER_TYPE]
    stages = [entry.stage for entry in personalized]
    assert stages == [7]


def test_is_within_dnd_window_supports_overnight_range():
    assert is_within_dnd_window(time(22, 0), time(21, 0), time(8, 0)) is True
    assert is_within_dnd_window(time(7, 30), time(21, 0), time(8, 0)) is True
    assert is_within_dnd_window(time(12, 0), time(21, 0), time(8, 0)) is False
    assert is_within_dnd_window(time(12, 0), None, time(8, 0)) is False
