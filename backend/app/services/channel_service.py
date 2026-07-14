from datetime import UTC, datetime
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.base import ChannelAdapter, NormalizedInboundMessage
from app.channels.channel_keys import SUPPORTED_REMINDER_CHANNELS, list_supported_reminder_channels
from app.channels.email_adapter import EmailAdapter
from app.channels.in_app_adapter import InAppAdapter
from app.channels.mock_adapter import MockAdapter
from app.channels.telegram_adapter import TelegramAdapter
from app.channels.whatsapp_adapter import WhatsAppAdapter
from app.models.atm005 import ChannelConnection, ContactChannelIdentity, InboundMessage
from app.models.atm017 import OutboundMessage
from app.models.core import Reminder, Task
from app.services.audit_service import write_audit_event
from app.services.email_service import EmailService
from app.services.reminder_service import ReminderService
from app.services.task_service import TaskService

logger = logging.getLogger(__name__)


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class ChannelService:
    """Outbound messaging facade. Adapter keys = SUPPORTED_REMINDER_CHANNELS."""

    SUPPORTED_CHANNELS: tuple[str, ...] = SUPPORTED_REMINDER_CHANNELS

    def __init__(
        self,
        session: AsyncSession,
        *,
        telegram_adapter: ChannelAdapter | None = None,
        whatsapp_adapter: ChannelAdapter | None = None,
        email_adapter: ChannelAdapter | None = None,
        email_service: EmailService | None = None,
    ):
        self.session = session
        resolved_email_service = email_service or EmailService.from_settings()
        self.adapters: dict[str, ChannelAdapter] = {
            "in_app": InAppAdapter(session),
            "email": email_adapter or EmailAdapter(resolved_email_service),
            "sms": MockAdapter("sms"),
            "whatsapp": whatsapp_adapter or WhatsAppAdapter(),
            "telegram": telegram_adapter or TelegramAdapter(),
        }

    @classmethod
    def supported_channels(cls) -> list[str]:
        """Channel keys Reminder Management / metadata APIs should advertise."""
        return list_supported_reminder_channels()

    def adapter_for(self, channel: str) -> ChannelAdapter:
        adapter = self.adapters.get(channel)
        if adapter is None:
            raise ValueError(f"unsupported channel: {channel}")
        return adapter

    async def _find_outbound_by_provider_message_id(
        self,
        *,
        channel: str,
        provider_id: str,
    ) -> OutboundMessage | None:
        return await self.session.scalar(
            select(OutboundMessage).where(
                OutboundMessage.channel == channel,
                OutboundMessage.external_provider_message_id == provider_id,
            )
        )

    async def _persist_sent_outbound_message(
        self,
        *,
        organization_id: int,
        channel: str,
        recipient: str,
        text: str,
        task_id: int | None,
        provider_id: str,
    ) -> tuple[OutboundMessage, bool]:
        existing = await self._find_outbound_by_provider_message_id(
            channel=channel,
            provider_id=provider_id,
        )
        if existing is not None:
            logger.info(
                "[ChannelService] duplicate outbound detected channel=%s provider_id=%s skipping insert",
                channel,
                provider_id,
            )
            return existing, True

        row = OutboundMessage(
            organization_id=organization_id,
            task_id=task_id,
            channel=channel,
            recipient=recipient,
            body=text,
            external_provider_message_id=provider_id,
            status="sent",
            created_at=utcnow_naive(),
            updated_at=utcnow_naive(),
        )
        try:
            async with self.session.begin_nested():
                self.session.add(row)
                await self.session.flush()
        except IntegrityError:
            existing = await self._find_outbound_by_provider_message_id(
                channel=channel,
                provider_id=provider_id,
            )
            if existing is None:
                raise
            logger.info(
                "[ChannelService] duplicate outbound detected channel=%s provider_id=%s skipping insert",
                channel,
                provider_id,
            )
            return existing, True

        return row, False

    async def list_connections(self, organization_id: int) -> list[ChannelConnection]:
        result = await self.session.execute(
            select(ChannelConnection).where(ChannelConnection.organization_id == organization_id)
        )
        return list(result.scalars())

    async def upsert_connection(
        self,
        *,
        organization_id: int,
        channel: str,
        status: str = "active",
        provider_reference: str | None = None,
        settings: dict[str, Any] | None = None,
    ) -> ChannelConnection:
        result = await self.session.execute(
            select(ChannelConnection).where(
                ChannelConnection.organization_id == organization_id,
                ChannelConnection.channel == channel,
            )
        )
        existing = result.scalar_one_or_none()

        now = utcnow_naive()
        if existing is None:
            existing = ChannelConnection(
                organization_id=organization_id,
                channel=channel,
                status=status,
                provider_reference=provider_reference,
                settings=settings or {},
                created_at=now,
                updated_at=now,
            )
            self.session.add(existing)
        else:
            existing.status = status
            existing.provider_reference = provider_reference
            existing.settings = settings or existing.settings
            existing.updated_at = now

        await self.session.commit()
        await self.session.refresh(existing)
        return existing

    async def test_message(
        self,
        *,
        connection_id: int,
        recipient: str,
        text: str,
    ) -> OutboundMessage:
        connection = await self.session.get(ChannelConnection, connection_id)
        if connection is None:
            raise ValueError("connection not found")

        return await self.send_outbound_message(
            organization_id=connection.organization_id,
            channel=connection.channel,
            recipient=recipient,
            text=text,
            connection_settings=connection.settings,
        )

    async def set_contact_preferred_channel(
        self,
        *,
        organization_id: int,
        contact_id: int,
        channel: str,
        external_user_id: str,
        external_chat_id: str | None,
        display_name: str | None,
    ) -> ContactChannelIdentity:
        result = await self.session.execute(
            select(ContactChannelIdentity).where(
                ContactChannelIdentity.organization_id == organization_id,
                ContactChannelIdentity.contact_id == contact_id,
                ContactChannelIdentity.channel == channel,
            )
        )
        row = result.scalar_one_or_none()
        now = utcnow_naive()
        if row is None:
            row = ContactChannelIdentity(
                organization_id=organization_id,
                contact_id=contact_id,
                user_id=None,
                channel=channel,
                external_user_id=external_user_id,
                external_chat_id=external_chat_id,
                display_name=display_name,
                is_opted_out=False,
                last_inbound_at=None,
                created_at=now,
                updated_at=now,
            )
            self.session.add(row)
        else:
            row.external_user_id = external_user_id
            row.external_chat_id = external_chat_id
            row.display_name = display_name
            row.updated_at = now

        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def process_webhook(
        self,
        *,
        channel: str,
        organization_id: int,
        payload: dict[str, Any],
        headers: dict[str, str],
        method: str = "POST",
        query_params: dict[str, str] | None = None,
        raw_body: bytes | None = None,
    ) -> dict[str, Any]:
        adapter = self.adapter_for(channel)
        query_params = query_params or {}
        verified, challenge = adapter.verify_webhook(
            method=method,
            query_params=query_params,
            headers=headers,
            body=raw_body or b"",
        )
        if not verified:
            raise ValueError("webhook verification failed")
        if challenge is not None:
            return {"challenge": challenge}

        normalized = adapter.normalize_inbound_payload(payload, headers)
        identity = await self._resolve_or_create_identity(organization_id=organization_id, normalized=normalized)
        inbound = await self._create_inbound_record(
            organization_id=organization_id,
            channel=channel,
            normalized=normalized,
            identity_id=identity.id if identity else None,
        )

        # STOP/opt-out handling
        if (normalized.text or "").strip().upper() == "STOP" and identity is not None:
            identity.is_opted_out = True
            identity.updated_at = utcnow_naive()

        # Inline button actions from Telegram
        await self._handle_inline_action(organization_id=organization_id, normalized=normalized)

        await self.session.commit()
        return {"stored": True, "inbound_message_id": inbound.id}

    async def send_outbound_message(
        self,
        *,
        organization_id: int,
        channel: str,
        recipient: str,
        text: str,
        task_id: int | None = None,
        connection_settings: dict[str, Any] | None = None,
        template_name: str | None = None,
        template_language: str | None = None,
        template_variables: dict[str, str] | None = None,
        contact_id: int | None = None,
    ) -> OutboundMessage:
        # enforce opt-out
        if contact_id is not None:
            pref_result = await self.session.execute(
                select(ContactChannelIdentity).where(
                    ContactChannelIdentity.organization_id == organization_id,
                    ContactChannelIdentity.contact_id == contact_id,
                    ContactChannelIdentity.channel == channel,
                )
            )
            identity = pref_result.scalar_one_or_none()
            if identity is not None and identity.is_opted_out:
                raise PermissionError("contact opted out")

        adapter = self.adapter_for(channel)
        try:
            provider_id = await adapter.send_outbound_message(
                connection_settings=connection_settings or {},
                recipient=recipient,
                text=text,
                template_name=template_name,
                template_language=template_language,
                template_variables=template_variables,
            )
            if not provider_id:
                raise RuntimeError(f"{channel} provider did not return message id")
            logger.info(
                "[ChannelService] outbound accepted channel=%s recipient=%s provider_message_id=%s",
                channel,
                recipient,
                provider_id,
            )
            row, is_duplicate = await self._persist_sent_outbound_message(
                organization_id=organization_id,
                channel=channel,
                recipient=recipient,
                text=text,
                task_id=task_id,
                provider_id=provider_id,
            )
        except Exception as exc:  # noqa: BLE001
            mapped = adapter.map_provider_error(exc)
            provider_error = mapped.get("message") or str(exc)
            logger.warning(
                "[ChannelService] outbound failed channel=%s recipient=%s error=%s",
                channel,
                recipient,
                provider_error,
            )
            row = OutboundMessage(
                organization_id=organization_id,
                task_id=task_id,
                channel=channel,
                recipient=recipient,
                body=text,
                external_provider_message_id=None,
                status="failed",
                created_at=utcnow_naive(),
                updated_at=utcnow_naive(),
            )
            self.session.add(row)
            await self.session.flush()
            await write_audit_event(
                session=self.session,
                organization_id=organization_id,
                actor_user_id=None,
                event_type="channel.outbound_failed",
                entity_type="outbound_message",
                entity_id=str(row.id),
                payload=mapped,
            )
            await self.session.commit()
            await self.session.refresh(row)
            row.provider_error = provider_error  # type: ignore[attr-defined]
            return row

        if not is_duplicate:
            await write_audit_event(
                session=self.session,
                organization_id=organization_id,
                actor_user_id=None,
                event_type="channel.outbound_sent",
                entity_type="outbound_message",
                entity_id=str(row.id),
                payload={"provider_message_id": row.external_provider_message_id},
            )
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def update_provider_status(self, outbound_id: int, status: str) -> OutboundMessage:
        row = await self.session.get(OutboundMessage, outbound_id)
        if row is None:
            raise ValueError("outbound message not found")

        row.status = status
        row.updated_at = utcnow_naive()
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def _resolve_or_create_identity(
        self,
        *,
        organization_id: int,
        normalized: NormalizedInboundMessage,
    ) -> ContactChannelIdentity | None:
        result = await self.session.execute(
            select(ContactChannelIdentity).where(
                ContactChannelIdentity.organization_id == organization_id,
                ContactChannelIdentity.channel == normalized.channel,
                ContactChannelIdentity.external_user_id == normalized.external_user_id,
            )
        )
        row = result.scalar_one_or_none()
        now = utcnow_naive()
        if row is None:
            row = ContactChannelIdentity(
                organization_id=organization_id,
                contact_id=None,
                user_id=None,
                channel=normalized.channel,
                external_user_id=normalized.external_user_id,
                external_chat_id=normalized.external_chat_id,
                display_name=None,
                is_opted_out=False,
                last_inbound_at=now,
                created_at=now,
                updated_at=now,
            )
            self.session.add(row)
            await self.session.flush()
            return row

        row.external_chat_id = normalized.external_chat_id
        row.last_inbound_at = now
        row.updated_at = now
        await self.session.flush()
        return row

    async def _create_inbound_record(
        self,
        *,
        organization_id: int,
        channel: str,
        normalized: NormalizedInboundMessage,
        identity_id: int | None,
    ) -> InboundMessage:
        existing_result = await self.session.execute(
            select(InboundMessage).where(
                InboundMessage.channel == channel,
                InboundMessage.external_message_id == normalized.external_message_id,
            )
        )
        existing = existing_result.scalar_one_or_none()
        if existing is not None:
            return existing

        row = InboundMessage(
            organization_id=organization_id,
            channel_connection_id=None,
            identity_id=identity_id,
            channel=channel,
            external_message_id=normalized.external_message_id,
            external_user_id=normalized.external_user_id,
            external_chat_id=normalized.external_chat_id,
            message_type=normalized.message_type,
            text=normalized.text,
            payload=normalized.raw_payload or {},
            created_at=utcnow_naive(),
            updated_at=utcnow_naive(),
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def _handle_inline_action(
        self,
        *,
        organization_id: int,
        normalized: NormalizedInboundMessage,
    ) -> None:
        if not normalized.action or not normalized.action_payload:
            return

        action = normalized.action
        payload = normalized.action_payload

        task_service = TaskService(self.session)
        reminder_service = ReminderService(self.session)

        if action == "complete" and payload.get("task_id"):
            await task_service.complete_task(int(payload["task_id"]))
        elif action == "snooze" and payload.get("reminder_id"):
            await reminder_service.snooze_reminder(
                int(payload["reminder_id"]),
                scheduled_for=utcnow_naive(),
            )
        elif action == "renewed" and payload.get("task_id"):
            await task_service.complete_task(int(payload["task_id"]))
        elif action == "follow_up_later" and payload.get("task_id"):
            task = await self.session.get(Task, int(payload["task_id"]))
            if task is not None:
                await task_service.snooze_task(task.id, due_at=utcnow_naive())
