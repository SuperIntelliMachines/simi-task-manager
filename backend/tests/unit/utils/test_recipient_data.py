"""Unit tests for recipient_data normalization helpers."""

import pytest

from app.utils.recipient_data import (
    RecipientDataValidationError,
    normalize_recipient_data,
    recipient_address_for_channel,
)


def test_normalize_none_and_empty():
    assert normalize_recipient_data(None) == []
    assert normalize_recipient_data([]) == []
    assert normalize_recipient_data({}) == []


def test_normalize_legacy_object_wraps_to_array():
    payload = {"email": "a@example.com", "phone": "+911"}
    assert normalize_recipient_data(payload) == [payload]


def test_normalize_array_of_recipients():
    payload = [
        {"recipient_type": "customer", "email": "a@example.com"},
        {"recipient_type": "manager", "phone": "+911"},
    ]
    assert normalize_recipient_data(payload) == payload


def test_normalize_legacy_nested_recipients_key():
    assert normalize_recipient_data(
        {"recipients": [{"email": "a@example.com"}], "user_id": 1}
    ) == [{"email": "a@example.com"}]


def test_normalize_invalid_array_entry():
    with pytest.raises(RecipientDataValidationError, match="must be a JSON object"):
        normalize_recipient_data(["bad"])


def test_normalize_invalid_scalar():
    with pytest.raises(RecipientDataValidationError, match="must be a JSON array"):
        normalize_recipient_data("not-valid")


@pytest.mark.parametrize(
    "channel,recipient,expected",
    [
        ("email", {"email": "a@x.com", "phone": "+1"}, "a@x.com"),
        ("sms", {"phone": "+911", "email": "a@x.com"}, "+911"),
        ("whatsapp", {"whatsapp_number": "+922", "phone": "+911"}, "+922"),
        ("telegram", {"telegram_chat_id": "99"}, "99"),
        ("in_app", {"user_id": 42}, "42"),
        ("sms", {"email": "only@x.com"}, ""),
    ],
)
def test_recipient_address_for_channel(channel, recipient, expected):
    assert recipient_address_for_channel(recipient, channel) == expected
