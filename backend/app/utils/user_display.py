from __future__ import annotations


def format_user_display_name(email_or_name: str | None) -> str:
    """Derive a human-readable name from an email address or plain name."""
    trimmed = (email_or_name or "").strip()
    if not trimmed:
        return "SIMI Insurance"

    local_part = trimmed.split("@", 1)[0] if "@" in trimmed else trimmed
    parts = [part for part in local_part.replace("-", ".").replace("_", ".").split(".") if part]
    if not parts:
        return "SIMI Insurance"

    return " ".join(part[:1].upper() + part[1:].lower() for part in parts if part)
