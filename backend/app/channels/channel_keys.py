"""Canonical reminder channel keys used by ChannelService adapters.

Keep a single definition so metadata APIs and ChannelService cannot drift.
"""

from __future__ import annotations

# Order matches Reminder Management / metadata API expectations.
SUPPORTED_REMINDER_CHANNELS: tuple[str, ...] = (
    "in_app",
    "email",
    "sms",
    "whatsapp",
    "telegram",
)


def list_supported_reminder_channels() -> list[str]:
    return list(SUPPORTED_REMINDER_CHANNELS)
