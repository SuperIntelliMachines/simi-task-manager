"""Telegram bot token resolution for channel adapters (no integrations package imports)."""

from __future__ import annotations

from typing import Any

from app.core.config import get_settings


def resolve_telegram_agent_bot_token(
    connection_settings: dict[str, Any] | None = None,
) -> str | None:
    """Resolve agent bot token from connection settings or TELEGRAM_AGENT_BOT_TOKEN."""
    settings = connection_settings or {}
    for key in ("bot_token", "botToken"):
        value = settings.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    env_token = get_settings().telegram_agent_bot_token
    return env_token.strip() if env_token else None


def resolve_telegram_customer_bot_token() -> str | None:
    """Resolve customer-facing bot token from TELEGRAM_CUSTOMER_BOT_TOKEN."""
    env_token = get_settings().telegram_customer_bot_token
    return env_token.strip() if env_token else None


def resolve_telegram_bot_token(connection_settings: dict[str, Any] | None = None) -> str | None:
    """Backward-compatible alias used by the agent bot flow."""
    return resolve_telegram_agent_bot_token(connection_settings)


def normalize_telegram_connection_settings(connection_settings: dict[str, Any] | None = None) -> dict[str, Any]:
    """Normalize UI/API settings keys for TelegramAdapter."""
    settings = dict(connection_settings or {})
    token = resolve_telegram_agent_bot_token(settings)
    if token:
        settings["bot_token"] = token
    return settings
