from app.channels.whatsapp_template_specs import (
    EXPECTED_PLACEHOLDER_COUNT,
    POLICY_RENEWAL_REMINDER_BODY,
    POLICY_RENEWAL_REMINDER_BODY_EXAMPLES,
    POLICY_RENEWAL_REMINDER_PARAM_KEYS,
    POLICY_RENEWAL_REMINDER_PREVIEW_BODY,
    POLICY_RENEWAL_REMINDER_TEMPLATE_NAME,
)


def test_policy_renewal_reminder_phase_a_body_has_four_placeholders():
    assert POLICY_RENEWAL_REMINDER_BODY.count("{{") == EXPECTED_PLACEHOLDER_COUNT
    assert "Kindly take note" in POLICY_RENEWAL_REMINDER_BODY
    assert "Kindily" not in POLICY_RENEWAL_REMINDER_BODY


def test_policy_renewal_reminder_param_keys_and_examples_align():
    assert len(POLICY_RENEWAL_REMINDER_PARAM_KEYS) == EXPECTED_PLACEHOLDER_COUNT
    assert len(POLICY_RENEWAL_REMINDER_BODY_EXAMPLES[0]) == EXPECTED_PLACEHOLDER_COUNT


def test_policy_renewal_reminder_preview_body_formats():
    sample = {
        "customer_name": "Ravi Kumar",
        "entity_label": "Policy Renewal",
        "reminder_date": "18-07-2026",
        "sender_name": "SIMI Insurance",
    }
    rendered = POLICY_RENEWAL_REMINDER_PREVIEW_BODY.format(**sample)
    assert "Ravi Kumar" in rendered
    assert "Policy Renewal" in rendered
    assert "Kindly take note" in rendered
    assert POLICY_RENEWAL_REMINDER_TEMPLATE_NAME == "policy_renewal_reminder"
