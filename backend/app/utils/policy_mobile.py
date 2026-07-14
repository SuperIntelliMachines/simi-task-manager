from __future__ import annotations

import re

MOBILE_NUMBER_PATTERN = re.compile(r"^\+?[0-9]{10,15}$")


def normalize_mobile_number(value: str) -> str:
    """Remove spaces and keep an optional leading '+' with digits only."""
    stripped = value.strip()
    if not stripped:
        return ""
    compact = "".join(stripped.split())
    if compact.count("+") > 1 or "+" in compact[1:]:
        return compact
    if compact.startswith("+"):
        digits = "".join(char for char in compact[1:] if char.isdigit())
        return f"+{digits}" if digits else "+"
    return "".join(char for char in compact if char.isdigit())


def validate_mobile_number(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = normalize_mobile_number(value)
    if not normalized or normalized == "+":
        return None
    if not MOBILE_NUMBER_PATTERN.match(normalized):
        raise ValueError(
            "mobile_number must be 10 to 15 digits, with an optional leading '+'"
        )
    return normalized


def normalize_mobile_for_policy_lookup(raw_mobile: str) -> str:
    """Normalize mobile to digits-only lookup format (e.g. 919121529697)."""
    compact = str(raw_mobile or "").strip().replace(" ", "")
    if not compact:
        return ""
    compact = compact.replace("+", "")
    compact = compact.lstrip("0")
    if len(compact) == 10:
        compact = f"91{compact}"
    return "".join(ch for ch in compact if ch.isdigit())


def mobile_policy_lookup_values(raw_mobile: str | None) -> list[str]:
    """Return distinct stored-value variants for matching insurance_policies.mobile_number."""
    normalized = normalize_mobile_for_policy_lookup(raw_mobile or "")
    if not normalized:
        return []
    values = {normalized, f"+{normalized}"}
    if len(normalized) == 12 and normalized.startswith("91"):
        values.add(normalized[2:])
    stripped = str(raw_mobile or "").strip()
    if stripped:
        values.add(stripped)
    return list(values)


def normalize_whatsapp_recipient(phone: str) -> str:
    """Meta Cloud API expects E.164 digits without '+' prefix."""
    normalized = normalize_mobile_number(phone)
    digits = normalized[1:] if normalized.startswith("+") else normalized
    digits = "".join(char for char in digits if char.isdigit())
    # Indian mobiles are often stored as 10 digits without country code.
    if len(digits) == 10 and digits[0] in "6789":
        return f"91{digits}"
    return digits
