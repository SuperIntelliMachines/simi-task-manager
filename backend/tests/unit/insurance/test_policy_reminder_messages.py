from datetime import datetime

import pytest

from app.services.policy_reminder_messages import (
    POLICY_RENEWAL_REMINDER_TEMPLATE,
    build_policy_reminder_message,
    format_policy_renewal_date,
)
from app.utils.policy_reminder_stages import (
    EXPIRY_DAY_REMINDER_TYPE,
    PERSONALIZED_REMINDER_TYPE,
    REMINDER_STAGE_TYPES,
)


def test_format_policy_renewal_date():
    assert format_policy_renewal_date(datetime(2026, 7, 18, 12, 0, 0)) == "18-07-2026"
    assert format_policy_renewal_date("18-07-2026") == "18-07-2026"
    assert format_policy_renewal_date(None) == "-"


@pytest.mark.parametrize("reminder_type", sorted(set(REMINDER_STAGE_TYPES.values())))
def test_all_default_stages_use_unified_template(reminder_type: str):
    message = build_policy_reminder_message(
        reminder_type=reminder_type,
        customer_name="John Doe",
        policy_number="POL-2027-001",
        renewal_date=datetime(2026, 7, 18, 12, 0, 0),
        agent_name="Uday Kumar",
    )
    assert message == build_policy_reminder_message(
        reminder_type="DUE_30_DAYS",
        customer_name="John Doe",
        policy_number="POL-2027-001",
        renewal_date=datetime(2026, 7, 18, 12, 0, 0),
        agent_name="Uday Kumar",
    )


def test_build_policy_reminder_message_uses_exact_unified_format():
    message = build_policy_reminder_message(
        reminder_type=EXPIRY_DAY_REMINDER_TYPE,
        customer_name="John Doe",
        policy_number="POL-2027-001",
        renewal_date=datetime(2026, 7, 18, 12, 0, 0),
        agent_name="Uday Kumar",
    )
    expected = POLICY_RENEWAL_REMINDER_TEMPLATE.format(
        customer_name="John Doe",
        policy_number="POL-2027-001",
        renewal_date="18-07-2026",
        agent_name="Uday Kumar",
    )
    assert message == expected
    assert "Your policy renewal is due soon." in message
    assert "Policy: POL-2027-001" in message
    assert "Renewal Date: 18-07-2026" in message
    assert "Thank you,\nUday Kumar" in message


def test_personalized_reminder_uses_same_template():
    default_message = build_policy_reminder_message(
        reminder_type="DUE_30_DAYS",
        customer_name="Jane",
        policy_number="POL-001",
        renewal_date=datetime(2026, 12, 31, 12, 0, 0),
        agent_name="Agent",
    )
    personalized_message = build_policy_reminder_message(
        reminder_type=PERSONALIZED_REMINDER_TYPE,
        customer_name="Jane",
        policy_number="POL-001",
        renewal_date=datetime(2026, 12, 31, 12, 0, 0),
        agent_name="Agent",
    )
    assert personalized_message == default_message


def test_unknown_reminder_type_uses_unified_template():
    message = build_policy_reminder_message(
        reminder_type="LEGACY_UNKNOWN",
        customer_name="Jane",
        policy_number="POL-001",
        renewal_date=datetime(2026, 6, 1, 12, 0, 0),
        logged_in_user_name="Agent",
    )
    assert "Your policy renewal is due soon." in message
    assert "Policy: POL-001" in message
    assert "Renewal Date: 01-06-2026" in message
    assert "Thank you,\nAgent" in message
