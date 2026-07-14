from __future__ import annotations

import re

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def validate_policy_email(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if not EMAIL_PATTERN.match(normalized):
        raise ValueError("email must be a valid email address")
    return normalized.lower()
