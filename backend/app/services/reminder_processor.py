from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import Organization
from app.models.reminder_config import ReminderConfig
from app.models.reminder_instance import ReminderInstance
from app.core.config import get_settings
from app.services.channel_service import ChannelService
from app.services.reminder_resolvers import (
    ReminderEntityResolver,
    ReminderEntitySnapshot,
    ReminderResolverFactory,
    UnsupportedReminderEntityTypeError,
    get_reminder_resolver_factory,
)
from app.utils.reminder_query_time import fetch_db_now

logger = logging.getLogger(__name__)

IN_APP_CHANNEL = "in_app"


class ReminderProcessorService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        resolver_factory: ReminderResolverFactory | None = None,
    ):
        self.session = session
        self._resolver_factory = resolver_factory or get_reminder_resolver_factory()

    async def resolve_entity(self, instance: ReminderInstance) -> ReminderEntitySnapshot:
        entity_type = (instance.entity_type or "").strip().lower()
        try:
            resolver = self._resolver_factory.resolve(entity_type)
        except UnsupportedReminderEntityTypeError as exc:
            raise ValueError(f"unsupported entity type: {entity_type}") from exc

        entity = await resolver.get_entity(
            self.session,
            instance.organization_id,
            instance.entity_id,
        )
        if entity is None:
            raise ValueError("entity not found")
        return entity

    def _resolve_entity_label(self, config: ReminderConfig, resolver: ReminderEntityResolver) -> str:
        label = (config.entity_label or "").strip()
        if label:
            return label
        return resolver.get_default_entity_label()

    async def _resolve_sender_name(
        self,
        config: ReminderConfig,
        organization_id: int,
        resolver: ReminderEntityResolver,
    ) -> str:
        sender = (config.sender_name or "").strip()
        if sender:
            return sender
        org = await self.session.get(Organization, organization_id)
        if org is not None and (org.name or "").strip():
            return org.name.strip()
        return resolver.get_default_sender_name()

    async def process_due_reminders(self, organization_id: int) -> dict[str, int]:
        # Use database current time instead of datetime.utcnow()
        # to avoid timezone drift between app server and stored scheduled_at timestamps.
        logger.info(f"Processing due reminders for organization {organization_id}")

        now = await fetch_db_now(self.session)

        try:
            raw = await self.session.execute(
                text("""
                    SELECT id
                    FROM reminder_instances
                    WHERE organization_id = :org_id
                      AND status = 'PENDING'
                      AND scheduled_at <= NOW()
                """),
                {"org_id": organization_id},
            )
        except Exception:  # noqa: BLE001 — SQLite has no NOW()
            raw = await self.session.execute(
                text("""
                    SELECT id
                    FROM reminder_instances
                    WHERE organization_id = :org_id
                      AND status = 'PENDING'
                      AND scheduled_at <= :now
                """),
                {"org_id": organization_id, "now": now},
            )

        instance_ids = [row[0] for row in raw.fetchall()]

        instances: list[ReminderInstance] = []
        if instance_ids:
            result = await self.session.execute(
                select(ReminderInstance).where(
                    ReminderInstance.id.in_(instance_ids),
                )
            )
            instances = result.scalars().all()

        channel_service = ChannelService(self.session)

        sent = 0
        failed = 0

        for instance in instances:
            logger.info(f"Processing reminder instance {instance.id}")
            try:
                config = await self.session.get(ReminderConfig, instance.config_id)
                if config is None:
                    raise ValueError("reminder config not found")

                entity_type = (instance.entity_type or "").strip().lower()
                try:
                    resolver = self._resolver_factory.resolve(entity_type)
                except UnsupportedReminderEntityTypeError as exc:
                    raise ValueError(f"unsupported entity type: {entity_type}") from exc

                entity = await resolver.get_entity(
                    self.session,
                    instance.organization_id,
                    instance.entity_id,
                )
                if entity is None:
                    raise ValueError("entity not found")

                if resolver.should_cancel_instance(entity):
                    instance.status = "CANCELED"
                    instance.updated_at = now
                    continue

                entity_label = self._resolve_entity_label(config, resolver)
                sender_name = await self._resolve_sender_name(config, organization_id, resolver)
                channel = (config.channel or "").strip().lower()
                message = resolver.build_text_message(
                    entity,
                    entity_label=entity_label,
                    scheduled_at=instance.scheduled_at,
                    now=now,
                )

                if channel == IN_APP_CHANNEL:
                    outbound = await self._send_in_app(
                        channel_service=channel_service,
                        organization_id=organization_id,
                        instance=instance,
                        resolver=resolver,
                        entity=entity,
                        entity_label=entity_label,
                        message=message,
                    )
                else:
                    outbound = await self._send_outbound_channel(
                        channel_service=channel_service,
                        organization_id=organization_id,
                        config=config,
                        channel=channel,
                        resolver=resolver,
                        entity=entity,
                        entity_label=entity_label,
                        sender_name=sender_name,
                        message=message,
                        scheduled_at=instance.scheduled_at,
                    )

                if outbound.status != "sent":
                    provider_error = getattr(outbound, "provider_error", None)
                    raise RuntimeError(provider_error or f"channel send failed with status={outbound.status}")

                instance.status = "SENT"
                instance.sent_at = now
                instance.updated_at = now
                sent += 1
                logger.info(f"Reminder sent successfully for instance {instance.id}")
            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    f"Unexpected error while processing instance {instance.id}"
                )
                logger.error(
                    f"Reminder failed for instance {instance.id}: {exc}"
                )
                instance.status = "FAILED"
                instance.attempt_count = (instance.attempt_count or 0) + 1
                instance.last_error = str(exc)
                instance.updated_at = now
                failed += 1

        if instances:
            await self.session.commit()

        processed = len(instances)
        logger.info(
            f"Reminder processing completed: processed={processed}, sent={sent}, failed={failed}"
        )

        return {
            "processed": processed,
            "sent": sent,
            "failed": failed,
        }

    async def _send_in_app(
        self,
        *,
        channel_service: ChannelService,
        organization_id: int,
        instance: ReminderInstance,
        resolver: ReminderEntityResolver,
        entity: ReminderEntitySnapshot,
        entity_label: str,
        message: str,
    ):
        user_id = resolver.get_recipient_user_id(entity)
        if user_id is None:
            raise ValueError("missing recipient user id for in_app channel")

        return await channel_service.send_outbound_message(
            organization_id=organization_id,
            channel=IN_APP_CHANNEL,
            recipient=str(int(user_id)),
            text=message,
            connection_settings={
                "organization_id": organization_id,
                "entity_type": instance.entity_type,
                "entity_id": instance.entity_id,
                "reminder_instance_id": instance.id,
                "title": entity_label,
                "priority": "normal",
                "metadata": {
                    "reference_id": resolver.get_reference(entity),
                    "customer_name": resolver.get_customer_name(entity),
                },
            },
        )

    async def _send_outbound_channel(
        self,
        *,
        channel_service: ChannelService,
        organization_id: int,
        config: ReminderConfig,
        channel: str,
        resolver: ReminderEntityResolver,
        entity: ReminderEntitySnapshot,
        entity_label: str,
        sender_name: str,
        message: str,
        scheduled_at: datetime,
    ):
        phone_number = (resolver.get_recipient(entity) or "").strip()
        if not phone_number:
            raise ValueError("missing recipient phone number")

        send_kwargs: dict[str, object] = {
            "organization_id": organization_id,
            "channel": config.channel,
            "recipient": phone_number,
            "text": message,
        }
        settings = get_settings()
        template_name = (settings.whatsapp_template_name or "").strip()
        template_language = (settings.whatsapp_template_language or "en_US").strip() or "en_US"
        if channel == "whatsapp" and template_name:
            send_kwargs["connection_settings"] = {"use_whatsapp_session_text": False}
            send_kwargs["template_name"] = template_name
            send_kwargs["template_language"] = template_language
            send_kwargs["template_variables"] = resolver.build_template_context(
                entity,
                entity_label=entity_label,
                sender_name=sender_name,
                scheduled_at=scheduled_at,
            )

        return await channel_service.send_outbound_message(**send_kwargs)
