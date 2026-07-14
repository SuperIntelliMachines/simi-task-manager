"""In-memory pending policy renewal context per Telegram user."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class PendingPolicyRenewal:
    external_user_id: str
    organization_id: int
    policy_id: int
    customer_name: str
    policy_number: str
    previous_status: str
    current_expiry: datetime


class RenewalContextStore:
    """Stores one pending renewal conversation per Telegram user."""

    def __init__(self) -> None:
        self._pending: dict[str, PendingPolicyRenewal] = {}

    def get(self, external_user_id: str) -> PendingPolicyRenewal | None:
        return self._pending.get(external_user_id)

    def set(self, external_user_id: str, context: PendingPolicyRenewal) -> None:
        self._pending[external_user_id] = context
        logger.info(
            "Telegram renewal context stored user=%s policy_id=%s customer=%s policy_number=%s",
            external_user_id,
            context.policy_id,
            context.customer_name,
            context.policy_number,
        )

    def clear(self, external_user_id: str) -> None:
        if external_user_id in self._pending:
            logger.info("Telegram renewal context cleared user=%s", external_user_id)
            del self._pending[external_user_id]


renewal_context_store = RenewalContextStore()


def format_renewal_prompt(context: PendingPolicyRenewal) -> str:
    return (
        "🔄 Policy Renewal Request\n\n"
        f"Customer: {context.customer_name}\n"
        f"Policy Number: {context.policy_number}\n"
        f"Current Expiry: {context.current_expiry.strftime('%d-%b-%Y')}\n\n"
        "Please provide the new expiry date.\n"
        "Example: 03-Jun-2027"
    )


def format_invalid_renewal_date_prompt(context: PendingPolicyRenewal) -> str:
    return (
        "❌ Invalid date format.\n\n"
        "Please provide the new expiry date.\n"
        "Example: 03-Jun-2027\n\n"
        f"{format_renewal_prompt(context)}"
    )
