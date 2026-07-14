"""Resolve organization and user context for Telegram chat users."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.atm005 import ContactChannelIdentity
from app.models.core import Organization, User

logger = logging.getLogger(__name__)


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@dataclass(frozen=True)
class TelegramUserContext:
    organization_id: int
    actor_user_id: int | None
    external_user_id: str
    external_chat_id: str | None
    display_name: str | None


class TelegramUserContextService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.settings = get_settings()

    async def resolve(
        self,
        *,
        external_user_id: str,
        external_chat_id: str | None,
        display_name: str | None = None,
        organization_id: int | None = None,
    ) -> TelegramUserContext:
        target_org_id = organization_id or await self._resolve_organization_id(external_user_id)
        identity = await self._find_identity(external_user_id)
        actor_user_id = identity.user_id if identity else None

        if identity is None:
            await self._create_identity(
                organization_id=target_org_id,
                external_user_id=external_user_id,
                external_chat_id=external_chat_id,
                display_name=display_name,
            )
        else:
            if identity.organization_id != target_org_id:
                logger.warning(
                    "Telegram identity org mismatch user=%s stored_org=%s target_org=%s — updating",
                    external_user_id,
                    identity.organization_id,
                    target_org_id,
                )
                identity.organization_id = target_org_id
                identity.user_id = await self._default_actor_user_id(target_org_id)
            await self._touch_identity(identity, external_chat_id, display_name)

        logger.info(
            "Telegram user context resolved user=%s organization_id=%s actor_user_id=%s",
            external_user_id,
            target_org_id,
            actor_user_id,
        )

        return TelegramUserContext(
            organization_id=target_org_id,
            actor_user_id=actor_user_id,
            external_user_id=external_user_id,
            external_chat_id=external_chat_id,
            display_name=display_name,
        )

    async def _resolve_organization_id(self, external_user_id: str) -> int:
        configured = self.settings.telegram_default_organization_id
        if configured:
            logger.info(
                "Telegram org resolution user=%s source=TELEGRAM_DEFAULT_ORGANIZATION_ID org=%s",
                external_user_id,
                configured,
            )
            return int(configured)

        identity = await self._find_identity(external_user_id)
        if identity is not None:
            logger.info(
                "Telegram org resolution user=%s source=existing_identity org=%s",
                external_user_id,
                identity.organization_id,
            )
            return int(identity.organization_id)

        org_result = await self.session.execute(select(Organization.id).order_by(Organization.id).limit(1))
        org_id = org_result.scalar_one_or_none()
        if org_id is None:
            raise ValueError("No organization configured for Telegram integration")
        logger.warning(
            "Telegram org resolution user=%s source=first_organization org=%s — set TELEGRAM_DEFAULT_ORGANIZATION_ID",
            external_user_id,
            org_id,
        )
        return int(org_id)

    async def _find_identity(self, external_user_id: str) -> ContactChannelIdentity | None:
        result = await self.session.execute(
            select(ContactChannelIdentity).where(
                ContactChannelIdentity.channel == "telegram",
                ContactChannelIdentity.external_user_id == external_user_id,
            )
        )
        return result.scalar_one_or_none()

    async def _create_identity(
        self,
        *,
        organization_id: int,
        external_user_id: str,
        external_chat_id: str | None,
        display_name: str | None,
    ) -> None:
        now = utcnow_naive()
        row = ContactChannelIdentity(
            organization_id=organization_id,
            contact_id=None,
            user_id=await self._default_actor_user_id(organization_id),
            channel="telegram",
            external_user_id=external_user_id,
            external_chat_id=external_chat_id,
            display_name=display_name,
            is_opted_out=False,
            last_inbound_at=now,
            created_at=now,
            updated_at=now,
        )
        self.session.add(row)
        await self.session.commit()

    async def _touch_identity(
        self,
        identity: ContactChannelIdentity,
        external_chat_id: str | None,
        display_name: str | None,
    ) -> None:
        now = utcnow_naive()
        identity.last_inbound_at = now
        identity.updated_at = now
        if external_chat_id:
            identity.external_chat_id = external_chat_id
        if display_name:
            identity.display_name = display_name
        await self.session.commit()

    async def _default_actor_user_id(self, organization_id: int) -> int | None:
        result = await self.session.execute(
            select(User.id).where(User.organization_id == organization_id, User.is_active.is_(True)).limit(1)
        )
        user_id = result.scalar_one_or_none()
        return int(user_id) if user_id is not None else None
