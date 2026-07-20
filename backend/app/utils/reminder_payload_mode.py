"""Payload-driven reminder mode helpers (external module integrations)."""

from __future__ import annotations

from typing import Any

from app.core.enums import ReminderGenerationMode
from app.models.reminder_config import ReminderConfig
from app.utils.recipient_data import normalize_recipient_data, recipient_address_for_channel


class PayloadReminderValidationError(ValueError):
    """Raised when a payload-mode reminder request is invalid."""


def is_payload_config(config: ReminderConfig) -> bool:
    mode = getattr(config, "generation_mode", None) or ReminderGenerationMode.RESOLVER.value
    return str(mode).strip().lower() == ReminderGenerationMode.PAYLOAD.value


def is_payload_mode_request(
    *,
    definitions: list[Any],
    template_key: str | None,
    recipient_data: object,
    template_variables: dict[str, Any] | None,
) -> bool:
    """True when the caller supplied everything needed for payload-mode delivery."""
    if not (template_key or "").strip():
        return False
    if template_variables is None:
        return False
    if not normalize_recipient_data(recipient_data):
        return False
    if not definitions:
        return False
    for definition in definitions:
        scheduled_at = getattr(definition, "scheduled_at", None)
        if scheduled_at is None:
            return False
    return True


def validate_recipient_data_for_channels(
    recipient_data: list[dict[str, Any]],
    channels: list[str],
) -> None:
    normalized_channels = [
        (channel or "").strip().lower() for channel in channels if (channel or "").strip()
    ]
    for channel in normalized_channels:
        if any(recipient_address_for_channel(entry, channel) for entry in recipient_data):
            continue
        raise PayloadReminderValidationError(
            f"recipient_data has no address for channel '{channel}'"
        )


def collect_request_channels(definitions: list[Any]) -> list[str]:
    channels: list[str] = []
    seen: set[str] = set()
    for definition in definitions:
        for channel in getattr(definition, "channels", None) or []:
            normalized = (channel or "").strip().lower()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            channels.append(normalized)
    return channels
