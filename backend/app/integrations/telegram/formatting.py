"""Telegram-friendly message formatting for insurance commands."""

from __future__ import annotations


def section(title: str) -> str:
    return f"{title}\n{'─' * 28}"


def bullet(label: str, value: str | int) -> str:
    return f"• {label}: {value}"


def numbered(index: int, *parts: str) -> str:
    return f"{index}. {' — '.join(parts)}"


def empty_state(title: str, message: str) -> str:
    return f"{title}\n\n{message}"
