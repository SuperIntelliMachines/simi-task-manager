from app.utils.policy_mobile import normalize_whatsapp_recipient


def test_normalize_whatsapp_recipient_strips_plus_and_spaces():
    assert normalize_whatsapp_recipient("+91 98765 43210") == "919876543210"


def test_normalize_whatsapp_recipient_adds_india_country_code_for_10_digit_mobile():
    assert normalize_whatsapp_recipient("9121529697") == "919121529697"


def test_normalize_whatsapp_recipient_keeps_digits_only():
    assert normalize_whatsapp_recipient("919876543210") == "919876543210"
