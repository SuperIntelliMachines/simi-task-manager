"""Normalize reminder config recipient_data to a list of recipient objects."""

from __future__ import annotations

from typing import Any


class RecipientDataValidationError(ValueError):
    """Raised when recipient_data cannot be normalized."""


# Channel → preferred address keys on a recipient object (first match wins).
CHANNEL_RECIPIENT_ADDRESS_KEYS: dict[str, tuple[str, ...]] = {
    "whatsapp": ("whatsapp", "whatsapp_number", "phone", "mobile"),
    "sms": ("phone", "mobile", "whatsapp", "whatsapp_number"),
    "email": ("email",),
    "telegram": ("telegram_chat_id", "telegram"),
    "in_app": (
        "user_id",
        "recipient_user_id",
        "assigned_user_id",
        "assigned_agent_user_id",
        "owner_user_id",
        "created_by",
        "agent_id",
        "simi_user_id",
    ),
}


def normalize_recipient_data(value: object) -> list[dict[str, Any]]:
    """
    Normalize recipient_data to ``list[dict]``.

    Backward compatible:
    - ``None`` → ``[]``
    - ``{...}`` → ``[{...}]`` (legacy single-recipient object)
    - ``{"recipients": [ {...}, ... ], ...}`` → the nested list (legacy Claims shape)
    - ``[{...}, ...]`` → validated list
    """
    if value is None:
        return []

    if isinstance(value, list):
        normalized: list[dict[str, Any]] = []
        for index, item in enumerate(value):
            if not isinstance(item, dict):
                raise RecipientDataValidationError(
                    f"recipient_data[{index}] must be a JSON object"
                )
            normalized.append(dict(item))
        return normalized

    if isinstance(value, dict):
        nested = value.get("recipients")
        if isinstance(nested, list):
            return normalize_recipient_data(nested)
        # Legacy empty object means "no explicit recipients" (resolver fallback).
        if not value:
            return []
        return [dict(value)]

    raise RecipientDataValidationError(
        "recipient_data must be a JSON array of recipient objects "
        "or a legacy JSON object"
    )


def recipient_address_for_channel(
    recipient: dict[str, Any],
    channel: str,
) -> str:
    """Extract the outbound address for a channel from one recipient object."""
    keys = CHANNEL_RECIPIENT_ADDRESS_KEYS.get((channel or "").strip().lower(), ())
    for key in keys:
        raw = recipient.get(key)
        if raw is None or raw == "":
            continue
        return str(raw).strip()
    return ""
