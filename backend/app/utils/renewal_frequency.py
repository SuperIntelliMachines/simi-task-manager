"""Allowed renewal frequency values for insurance policies."""

from __future__ import annotations

RENEWAL_FREQUENCY_MONTHLY = "monthly"
RENEWAL_FREQUENCY_QUARTERLY = "quarterly"
RENEWAL_FREQUENCY_HALF_YEARLY = "half_yearly"
RENEWAL_FREQUENCY_YEARLY = "yearly"

RENEWAL_FREQUENCY_DEFAULT = RENEWAL_FREQUENCY_YEARLY

RENEWAL_FREQUENCY_VALUES = frozenset(
    {
        RENEWAL_FREQUENCY_MONTHLY,
        RENEWAL_FREQUENCY_QUARTERLY,
        RENEWAL_FREQUENCY_HALF_YEARLY,
        RENEWAL_FREQUENCY_YEARLY,
    }
)

RENEWAL_FREQUENCY_LABELS = {
    RENEWAL_FREQUENCY_MONTHLY: "Monthly",
    RENEWAL_FREQUENCY_QUARTERLY: "Quarterly",
    RENEWAL_FREQUENCY_HALF_YEARLY: "Half-Yearly",
    RENEWAL_FREQUENCY_YEARLY: "Yearly",
}


def validate_renewal_frequency(value: str | None) -> str:
    if value is None or not str(value).strip():
        raise ValueError("renewal frequency is required")
    normalized = str(value).strip().lower()
    if normalized not in RENEWAL_FREQUENCY_VALUES:
        raise ValueError("invalid renewal frequency")
    return normalized


def renewal_frequency_label(value: str | None) -> str:
    if value is None or not str(value).strip():
        return RENEWAL_FREQUENCY_LABELS[RENEWAL_FREQUENCY_DEFAULT]
    normalized = str(value).strip().lower()
    return RENEWAL_FREQUENCY_LABELS.get(normalized, value)
