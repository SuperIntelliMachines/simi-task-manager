"""Customer Telegram bot onboarding for insurance policy reminder delivery."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.verticals import InsurancePolicy
from app.utils.policy_mobile import mobile_policy_lookup_values
logger = logging.getLogger(__name__)


class CustomerTelegramOnboardingService:
    """Handles customer onboarding messages from the customer-facing Telegram bot."""

    def __init__(self) -> None:
        self._awaiting_mobile_by_chat: set[str] = set()

    @staticmethod
    def _extract_message(payload: dict[str, Any]) -> tuple[str | None, str | None, str | None, str | None]:
        message = payload.get("message") or {}
        text = str(message.get("text") or "").strip()
        from_user = message.get("from") or {}
        chat = message.get("chat") or {}
        chat_id = str(chat.get("id") or "").strip() or None
        username = str(from_user.get("username") or "").strip() or None
        first_name = str(from_user.get("first_name") or "").strip() or None
        return text or None, chat_id, username, first_name

    @staticmethod
    def _is_greeting(text: str) -> bool:
        normalized = text.strip().lower()
        return normalized in {"/start", "hi", "hello", "hey"}

    async def handle_payload(
        self,
        *,
        session: AsyncSession,
        payload: dict[str, Any],
    ) -> str | None:
        text, chat_id, username, first_name = self._extract_message(payload)
        if not text or not chat_id:
            return None

        if self._is_greeting(text):
            self._awaiting_mobile_by_chat.add(chat_id)
            name = first_name or "there"
            return (
                f"Hi {name}! Please reply with your registered mobile number "
                "(for example: +919876543210)."
            )

        if chat_id not in self._awaiting_mobile_by_chat:
            return (
                "Please send /start or hi first, then share your registered mobile number "
                "to link your policy reminders."
            )

        lookup_values = mobile_policy_lookup_values(text)
        if not lookup_values:
            return "Please enter a valid mobile number (10-15 digits, optional leading +)."

        result = await session.execute(
            select(InsurancePolicy).where(InsurancePolicy.mobile_number.in_(lookup_values))
        )
        policies = list(result.scalars())
        if not policies:
            logger.warning(
                "[CustomerTelegramOnboarding] no policy match chat_id=%s username=%s mobile=%s",
                chat_id,
                username,
                text,
            )
            return (
                "Policy not found for that mobile number. "
                "Please verify and send the same number used during policy registration."
            )

        for policy in policies:
            policy.telegram_chat_id = int(chat_id)
            policy.telegram_username = username
        await session.commit()
        self._awaiting_mobile_by_chat.discard(chat_id)
        logger.info(
            "[CustomerTelegramOnboarding] linked chat_id=%s username=%s policy_count=%s",
            chat_id,
            username,
            len(policies),
        )
        return "Thanks! Your Telegram chat is linked. You will now receive policy reminders here."
