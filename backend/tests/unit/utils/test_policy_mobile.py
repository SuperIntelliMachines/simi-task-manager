import pytest

from app.utils.policy_mobile import (
    mobile_policy_lookup_values,
    normalize_mobile_for_policy_lookup,
    normalize_mobile_number,
    normalize_whatsapp_recipient,
    validate_mobile_number,
)


@pytest.mark.parametrize(
    "value",
    ["9876543210", "919876543210", "+919876543210", "+91 98765 43210"],
)
def test_validate_mobile_number_accepts_valid_values(value: str):
    expected = normalize_mobile_number(value)
    assert validate_mobile_number(value) == expected


def test_validate_mobile_number_preserves_optional_plus():
    assert validate_mobile_number("+919121529697") == "+919121529697"
    assert validate_mobile_number("919121529697") == "919121529697"


@pytest.mark.parametrize(
    "value",
    ["98765abcde", "123456789", "1234567890123456", "++919876543210"],
)
def test_validate_mobile_number_rejects_invalid_values(value: str):
    with pytest.raises(ValueError, match="mobile_number must be 10 to 15 digits"):
        validate_mobile_number(value)


def test_validate_mobile_number_normalizes_dashed_local_number():
    assert validate_mobile_number("98-7654-3210") == "9876543210"


def test_validate_mobile_number_allows_none():
    assert validate_mobile_number(None) is None


def test_normalize_whatsapp_recipient_strips_plus_and_spaces():
    assert normalize_whatsapp_recipient("+91 98765 43210") == "919876543210"


def test_normalize_whatsapp_recipient_adds_india_country_code_for_10_digit_mobile():
    assert normalize_whatsapp_recipient("9121529697") == "919121529697"
    assert normalize_whatsapp_recipient("+919121529697") == "919121529697"


def test_normalize_whatsapp_recipient_keeps_digits_only():
    assert normalize_whatsapp_recipient("919876543210") == "919876543210"


@pytest.mark.parametrize(
    "value,expected",
    [
        ("+91 98765 43210", "919876543210"),
        ("09121529697", "919121529697"),
        ("9121529697", "919121529697"),
    ],
)
def test_normalize_mobile_for_policy_lookup(value: str, expected: str):
    assert normalize_mobile_for_policy_lookup(value) == expected


def test_mobile_policy_lookup_values_includes_common_formats():
    values = mobile_policy_lookup_values("+919121529697")
    assert "919121529697" in values
    assert "+919121529697" in values
    assert "9121529697" in values


def test_mobile_policy_lookup_values_empty_for_blank():
    assert mobile_policy_lookup_values(None) == []
    assert mobile_policy_lookup_values("   ") == []
