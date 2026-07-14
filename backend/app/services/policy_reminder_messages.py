"""Unified automatic policy renewal reminder message template."""

from __future__ import annotations

from datetime import datetime

from app.utils.datetime_utils import normalize_to_utc_naive

POLICY_RENEWAL_REMINDER_TEMPLATE = (
    "Dear {customer_name},\n\n"
    "Your policy renewal is due soon.\n\n"
    "Policy: {policy_number}\n"
    "Renewal Date: {renewal_date}\n\n"
    "Please complete your renewal before the policy expiry date to avoid any interruption in coverage.\n\n"
    "Kindly ignore this message if payment has already been made.\n\n"
    "Thank you,\n"
    "{agent_name}"
)


def format_policy_renewal_date(value: datetime | str | None) -> str:
    """Format policy expiry/renewal date for customer-facing messages (DD-MM-YYYY)."""
    if value is None:
        return "-"
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or "-"
    normalized = normalize_to_utc_naive(value)
    if normalized is None:
        return "-"
    return normalized.strftime("%d-%m-%Y")


def build_policy_reminder_message(
    *,
    reminder_type: str | None = None,
    customer_name: str,
    policy_number: str,
    renewal_date: datetime | str | None,
    agent_name: str | None = None,
    logged_in_user_name: str | None = None,
) -> str:
    """Build the outbound message for an automatic policy reminder send.

    Default stage types (DUE_30_DAYS, UPCOMING_10_DAYS, …), EXPIRY_DAY, and
    PERSONALIZED all use the same unified customer template.
    """
    _ = reminder_type
    resolved_agent = (agent_name or logged_in_user_name or "SIMI Insurance").strip() or "SIMI Insurance"
    return POLICY_RENEWAL_REMINDER_TEMPLATE.format(
        customer_name=customer_name or "Customer",
        policy_number=policy_number or "-",
        renewal_date=format_policy_renewal_date(renewal_date),
        agent_name=resolved_agent,
    )
