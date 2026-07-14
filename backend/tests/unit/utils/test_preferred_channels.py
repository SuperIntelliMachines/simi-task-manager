from __future__ import annotations

import pytest

from app.utils.preferred_channels import (
    coerce_preferred_channel_input,
    describe_preferred_channel,
    normalize_preferred_channel,
    parse_postgres_text_array_literal,
    resolve_policy_reminder_channels,
    validate_preferred_channel,
)


def test_normalize_preferred_channel_deduplicates_and_lowercases():
    assert normalize_preferred_channel(["SMS", "email", "sms"]) == ["sms", "email"]


def test_coerce_preferred_channel_input_accepts_legacy_string():
    assert coerce_preferred_channel_input("email") == ["email"]
    assert validate_preferred_channel("email") == ["email"]


def test_validate_preferred_channel_accepts_in_app():
    assert validate_preferred_channel(["in_app", "whatsapp"]) == ["in_app", "whatsapp"]


def test_resolve_policy_reminder_channels_defaults_to_whatsapp():
    assert resolve_policy_reminder_channels(None) == ["whatsapp"]
    assert normalize_preferred_channel([]) is None


def test_parse_postgres_text_array_literal_supports_telegram_format():
    assert parse_postgres_text_array_literal("{telegram}") == ["telegram"]
    assert parse_postgres_text_array_literal("{telegram,email}") == ["telegram", "email"]


def test_resolve_policy_reminder_channels_accepts_postgres_array_literal_string():
    assert resolve_policy_reminder_channels("{telegram}") == ["telegram"]
    assert resolve_policy_reminder_channels('["telegram"]') == ["telegram"]


def test_describe_preferred_channel_reports_postgres_literal():
    debug = describe_preferred_channel("{telegram}")
    assert debug["resolved_channels"] == ["telegram"]
    assert debug["postgres_literal_detected"] is True
