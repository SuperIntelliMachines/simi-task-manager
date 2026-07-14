"""Canonical Meta WhatsApp template definitions for SIMI reminders (Phase A spec)."""

from __future__ import annotations

# Existing Meta template name — edit in Business Manager; do not register a new name.
POLICY_RENEWAL_REMINDER_TEMPLATE_NAME = "policy_renewal_reminder"
POLICY_RENEWAL_REMINDER_LANGUAGE = "en_US"
POLICY_RENEWAL_REMINDER_CATEGORY = "UTILITY"

# Maps to Meta {{1}}..{{4}} in order (Phase B code will use these keys in template_variables).
POLICY_RENEWAL_REMINDER_PARAM_KEYS: tuple[str, ...] = (
    "customer_name",
    "entity_label",
    "reminder_date",
    "sender_name",
)

POLICY_RENEWAL_REMINDER_PARAM_LABELS: tuple[str, ...] = (
    "Customer Name",
    "Reminder Title / Service Name",
    "Date / Time / Context",
    "Sender Name",
)

POLICY_RENEWAL_REMINDER_BODY = (
    "Hi {{1}}, this is a reminder for your {{2}} on {{3}}. Kindly take note.\n\n"
    "Thank you,\n"
    "{{4}}"
)

POLICY_RENEWAL_REMINDER_BODY_EXAMPLES: list[list[str]] = [
    ["Ravi Kumar", "Policy Renewal", "18-07-2026", "SIMI Insurance"],
]

# SIMI message_templates.body preview (Python format placeholders, not Meta {{n}}).
POLICY_RENEWAL_REMINDER_PREVIEW_BODY = (
    "Hi {customer_name}, this is a reminder for your {entity_label} on {reminder_date}. "
    "Kindly take note.\n\n"
    "Thank you,\n"
    "{sender_name}"
)

EXPECTED_PLACEHOLDER_COUNT = 4
