from app.utils.policy_reminder_stages import (
    normalize_row_reminder_type,
    row_reminder_type_is_escalation,
    row_reminder_type_is_personalized,
)


def test_normalize_row_reminder_type_is_case_insensitive():
    assert normalize_row_reminder_type("personalized") == "PERSONALIZED"
    assert normalize_row_reminder_type("PERSONALIZED") == "PERSONALIZED"
    assert normalize_row_reminder_type("  due_30_days ") == "DUE_30_DAYS"


def test_row_reminder_type_is_personalized():
    assert row_reminder_type_is_personalized("PERSONALIZED") is True
    assert row_reminder_type_is_personalized("personalized") is True
    assert row_reminder_type_is_personalized("DUE_30_DAYS") is False


def test_row_reminder_type_is_escalation():
    assert row_reminder_type_is_escalation("ESCALATION") is True
    assert row_reminder_type_is_escalation("escalation") is True
    assert row_reminder_type_is_personalized("ESCALATION") is False
