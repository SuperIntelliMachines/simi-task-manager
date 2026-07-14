"""Preferred reminder channel validation and helpers."""

from __future__ import annotations

import json
import re

ALLOWED_POLICY_REMINDER_CHANNELS: frozenset[str] = frozenset(
    {"sms", "telegram", "whatsapp", "email", "in_app"}
)
DEFAULT_POLICY_REMINDER_CHANNELS: tuple[str, ...] = ("whatsapp",)
_POSTGRES_ARRAY_LITERAL = re.compile(r"^\{.*\}$", re.DOTALL)


def parse_postgres_text_array_literal(value: str) -> list[str]:
    """Parse PostgreSQL TEXT[] display form, e.g. ``{telegram}`` or ``{telegram,email}``."""
    stripped = value.strip()
    if not _POSTGRES_ARRAY_LITERAL.match(stripped):
        return []
    inner = stripped[1:-1].strip()
    if not inner:
        return []
    tokens: list[str] = []
    for part in inner.split(","):
        token = part.strip().strip('"').strip("'")
        if token:
            tokens.append(token)
    return tokens


def _expand_channel_tokens(raw: str) -> list[str]:
    stripped = (raw or "").strip()
    if not stripped:
        return []
    if _POSTGRES_ARRAY_LITERAL.match(stripped):
        return parse_postgres_text_array_literal(stripped)
    if stripped.startswith("[") and stripped.endswith("]"):
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            return [stripped]
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
    return [stripped]


def parse_stored_preferred_channel(value: str | list[str] | None) -> list[str] | None:
    """Normalize DB/API shapes (list, JSON string, PostgreSQL ``{telegram}`` literal)."""
    expanded = _expand_preferred_channel_input(value)
    return normalize_preferred_channel(expanded) if expanded else None


def _expand_preferred_channel_input(value: str | list[str] | None) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, list):
        expanded: list[str] = []
        for item in value:
            expanded.extend(_expand_channel_tokens(str(item)))
        return expanded or None
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        expanded = _expand_channel_tokens(stripped)
        return expanded or None
    raise ValueError("preferred_channel must be a string or list of strings")


def coerce_preferred_channel_input(value: str | list[str] | None) -> list[str] | None:
    """Accept legacy single-string values and normalize to a list."""
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        if _POSTGRES_ARRAY_LITERAL.match(stripped):
            return parse_postgres_text_array_literal(stripped)
        if stripped.startswith("[") and stripped.endswith("]"):
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                return [stripped]
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        return [stripped]
    if isinstance(value, list):
        expanded: list[str] = []
        for item in value:
            expanded.extend(_expand_channel_tokens(str(item)))
        return expanded or None
    raise ValueError("preferred_channel must be a string or list of strings")


def normalize_preferred_channel(channels: list[str] | None) -> list[str] | None:
    if not channels:
        return None

    normalized: list[str] = []
    seen: set[str] = set()
    for channel in channels:
        value = (channel or "").strip().lower()
        if not value or value not in ALLOWED_POLICY_REMINDER_CHANNELS or value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    return normalized or None


def validate_preferred_channel(channels: str | list[str] | None) -> list[str] | None:
    coerced = coerce_preferred_channel_input(channels)
    if coerced is None:
        return None

    invalid = [
        (channel or "").strip().lower()
        for channel in coerced
        if (channel or "").strip().lower() not in ALLOWED_POLICY_REMINDER_CHANNELS
    ]
    if invalid:
        allowed = ", ".join(sorted(ALLOWED_POLICY_REMINDER_CHANNELS))
        raise ValueError(f"Invalid preferred channel(s). Allowed values: {allowed}")

    normalized = normalize_preferred_channel(coerced)
    if not normalized:
        raise ValueError("Select at least one preferred reminder channel")
    return normalized


# Backward-compatible aliases used by older imports.
normalize_preferred_channels = normalize_preferred_channel
validate_preferred_channels = validate_preferred_channel


def resolve_policy_reminder_channels(channels: str | list[str] | None) -> list[str]:
    normalized = parse_stored_preferred_channel(channels)
    if normalized:
        return normalized
    return list(DEFAULT_POLICY_REMINDER_CHANNELS)


def describe_preferred_channel(value: str | list[str] | None) -> dict[str, object]:
    """Return raw + resolved channel values for scheduler diagnostics."""
    resolved = resolve_policy_reminder_channels(value)
    raw_type = type(value).__name__
    raw_repr = repr(value)
    if isinstance(value, list):
        raw_items = [repr(item) for item in value]
    else:
        raw_items = [raw_repr] if value is not None else []
    return {
        "raw_type": raw_type,
        "raw_repr": raw_repr,
        "raw_items": raw_items,
        "resolved_channels": resolved,
        "postgres_literal_detected": isinstance(value, str)
        and bool(_POSTGRES_ARRAY_LITERAL.match(str(value).strip())),
    }
