from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import Organization
from app.models.reminder_config import ReminderConfig
from app.models.reminder_instance import ReminderInstance
from app.channels.whatsapp_template_layout import (
    build_template_components,
    resolve_template_language,
    resolve_template_layout,
)
from app.core.config import get_settings
from app.services.channel_service import ChannelService
from app.services.reminder_payload_delivery import (
    load_channel_template,
    render_template_body,
    uses_meta_whatsapp_template,
)
from app.services.reminder_resolvers import (
    ReminderEntityResolver,
    ReminderEntitySnapshot,
    ReminderResolverFactory,
    UnsupportedReminderEntityTypeError,
    get_reminder_resolver_factory,
)
from app.utils.recipient_data import (
    normalize_recipient_data,
    recipient_address_for_channel,
)
from app.utils.reminder_payload_mode import is_payload_config
from app.utils.reminder_query_time import fetch_db_now
from app.utils.reminder_recurrence import count_sent_instances, schedule_next_recurrence

logger = logging.getLogger(__name__)

IN_APP_CHANNEL = "in_app"

# Meta policy_renewal_reminder body placeholders {{1}}..{{4}} for payload-mode callers.
_PAYLOAD_WHATSAPP_TEMPLATE_LAYOUT: dict[str, object] = {
    "components": [
        {
            "type": "body",
            "param_keys": [
                "customer_name",
                "policy_name",
                "reminder_date",
                "company_name",
            ],
        }
    ]
}


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

                if is_payload_config(config):
                    await self._process_payload_instance(
                        instance=instance,
                        config=config,
                        organization_id=organization_id,
                        channel_service=channel_service,
                        now=now,
                    )
                    if instance.status == "SENT":
                        sent += 1
                        logger.info(
                            "Payload-mode reminder sent successfully for instance %s",
                            instance.id,
                        )
                    continue

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

                sent_count = await count_sent_instances(
                    self.session,
                    config_id=int(config.id),
                    entity_id=int(instance.entity_id),
                )

                if not config.is_active:
                    instance.status = "CANCELED"
                    instance.updated_at = now
                    continue

                max_attempts = getattr(config, "max_attempts", None)
                if max_attempts is not None and sent_count >= int(max_attempts):
                    instance.status = "CANCELED"
                    instance.updated_at = now
                    continue

                if resolver.should_stop_reminder(
                    entity,
                    config,
                    sent_count=sent_count,
                    now=now,
                ):
                    instance.status = "CANCELED"
                    instance.updated_at = now
                    continue

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

                recipients = normalize_recipient_data(
                    getattr(config, "recipient_data", None)
                )
                # Empty list → one resolver-backed delivery (legacy behavior).
                delivery_targets: list[dict[str, object] | None] = (
                    list(recipients) if recipients else [None]
                )

                send_errors: list[str] = []
                sent_to_any = False
                for target in delivery_targets:
                    try:
                        if channel == IN_APP_CHANNEL:
                            outbound = await self._send_in_app(
                                channel_service=channel_service,
                                organization_id=organization_id,
                                config=config,
                                instance=instance,
                                resolver=resolver,
                                entity=entity,
                                entity_label=entity_label,
                                message=message,
                                recipient_entry=target,
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
                                recipient_entry=target,
                            )

                        if outbound.status != "sent":
                            provider_error = getattr(outbound, "provider_error", None)
                            raise RuntimeError(
                                provider_error
                                or f"channel send failed with status={outbound.status}"
                            )
                        sent_to_any = True
                    except Exception as recipient_exc:  # noqa: BLE001
                        logger.exception(
                            "Reminder recipient delivery failed instance=%s channel=%s recipient=%s",
                            instance.id,
                            channel,
                            target,
                        )
                        send_errors.append(str(recipient_exc))

                if not sent_to_any:
                    raise RuntimeError(
                        "; ".join(send_errors) or "all recipient deliveries failed"
                    )

                if send_errors:
                    instance.last_error = (
                        "partial recipient failures: " + "; ".join(send_errors)
                    )

                instance.status = "SENT"
                instance.sent_at = now
                instance.updated_at = now
                sent += 1
                logger.info(f"Reminder sent successfully for instance {instance.id}")

                if bool(getattr(config, "repeat_enabled", False)):
                    next_sent_count = sent_count + 1
                    max_attempts = getattr(config, "max_attempts", None)
                    should_continue = max_attempts is None or next_sent_count < int(max_attempts)
                    if should_continue and not resolver.should_stop_reminder(
                        entity,
                        config,
                        sent_count=next_sent_count,
                        now=now,
                    ):
                        await schedule_next_recurrence(
                            self.session,
                            config=config,
                            organization_id=organization_id,
                            entity_type=instance.entity_type,
                            entity_id=int(instance.entity_id),
                            from_time=now,
                        )
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

    async def _resolve_payload_sender_name(
        self,
        config: ReminderConfig,
        organization_id: int,
    ) -> str:
        sender = (config.sender_name or "").strip()
        if sender:
            return sender
        org = await self.session.get(Organization, organization_id)
        if org is not None and (org.name or "").strip():
            return org.name.strip()
        return "SIMI"

    @staticmethod
    def _resolve_payload_entity_label(config: ReminderConfig) -> str:
        label = (config.entity_label or "").strip()
        return label or "Reminder"

    async def _build_payload_message(
        self,
        *,
        config: ReminderConfig,
        organization_id: int,
        channel: str,
    ) -> tuple[str, object | None]:
        template_key = (config.template_key or "").strip()
        if not template_key:
            raise ValueError("template_key is required for payload-mode delivery")

        variables = dict(getattr(config, "template_variables", None) or {})
        channel_template = await load_channel_template(
            self.session,
            organization_id=organization_id,
            template_key=template_key,
            channel=channel,
        )
        body = (channel_template.body or "").strip()
        if channel == "whatsapp" and uses_meta_whatsapp_template(channel_template):
            return body, channel_template
        return render_template_body(body, variables), channel_template

    async def _process_payload_instance(
        self,
        *,
        instance: ReminderInstance,
        config: ReminderConfig,
        organization_id: int,
        channel_service: ChannelService,
        now: datetime,
    ) -> None:
        if not config.is_active:
            instance.status = "CANCELED"
            instance.updated_at = now
            return

        sent_count = await count_sent_instances(
            self.session,
            config_id=int(config.id),
            entity_id=int(instance.entity_id),
        )
        max_attempts = getattr(config, "max_attempts", None)
        if max_attempts is not None and sent_count >= int(max_attempts):
            instance.status = "CANCELED"
            instance.updated_at = now
            return

        recipients = normalize_recipient_data(getattr(config, "recipient_data", None))
        if not recipients:
            raise ValueError("recipient_data is required for payload-mode delivery")

        entity_label = self._resolve_payload_entity_label(config)
        sender_name = await self._resolve_payload_sender_name(config, organization_id)
        channel = (config.channel or "").strip().lower()
        message, channel_template = await self._build_payload_message(
            config=config,
            organization_id=organization_id,
            channel=channel,
        )
        template_variables = dict(getattr(config, "template_variables", None) or {})
        string_template_variables = {
            key: "" if value is None else str(value) for key, value in template_variables.items()
        }

        send_errors: list[str] = []
        sent_to_any = False
        for target in recipients:
            try:
                if channel == IN_APP_CHANNEL:
                    outbound = await self._send_in_app_payload(
                        channel_service=channel_service,
                        organization_id=organization_id,
                        config=config,
                        instance=instance,
                        entity_label=entity_label,
                        message=message,
                        channel_template=channel_template,
                        recipient_entry=target,
                    )
                else:
                    outbound = await self._send_outbound_payload(
                        channel_service=channel_service,
                        organization_id=organization_id,
                        config=config,
                        channel=channel,
                        entity_label=entity_label,
                        sender_name=sender_name,
                        message=message,
                        scheduled_at=instance.scheduled_at,
                        channel_template=channel_template,
                        template_variables=string_template_variables,
                        recipient_entry=target,
                    )

                if outbound.status != "sent":
                    provider_error = getattr(outbound, "provider_error", None)
                    raise RuntimeError(
                        provider_error
                        or f"channel send failed with status={outbound.status}"
                    )
                sent_to_any = True
            except Exception as recipient_exc:  # noqa: BLE001
                logger.exception(
                    "Payload reminder delivery failed instance=%s channel=%s recipient=%s",
                    instance.id,
                    channel,
                    target,
                )
                send_errors.append(str(recipient_exc))

        if not sent_to_any:
            raise RuntimeError(
                "; ".join(send_errors) or "all recipient deliveries failed"
            )

        if send_errors:
            instance.last_error = "partial recipient failures: " + "; ".join(send_errors)

        instance.status = "SENT"
        instance.sent_at = now
        instance.updated_at = now

    async def _send_in_app_payload(
        self,
        *,
        channel_service: ChannelService,
        organization_id: int,
        config: ReminderConfig,
        instance: ReminderInstance,
        entity_label: str,
        message: str,
        channel_template: object | None,
        recipient_entry: dict[str, object],
    ):
        user_id = self._recipient_user_id_from_entry(recipient_entry)
        if user_id is None or int(user_id) <= 0:
            raise ValueError(
                "missing recipient user id for in_app payload-mode delivery "
                f"(recipient_entry={recipient_entry!r})"
            )

        variables = dict(getattr(config, "template_variables", None) or {})
        title = entity_label
        if channel_template is not None:
            template_title = getattr(channel_template, "title", None)
            if isinstance(template_title, str) and template_title.strip():
                title = render_template_body(template_title.strip(), variables)

        connection_settings = {
            "organization_id": organization_id,
            "entity_type": instance.entity_type,
            "entity_id": instance.entity_id,
            "reminder_instance_id": instance.id,
            "title": title,
            "priority": "normal",
            "metadata": {
                "reference_id": str(variables.get("reference_id") or ""),
                "customer_name": str(variables.get("customer_name") or "Customer"),
                "recipient_type": recipient_entry.get("recipient_type"),
            },
        }
        return await channel_service.send_outbound_message(
            organization_id=organization_id,
            channel=IN_APP_CHANNEL,
            recipient=str(int(user_id)),
            text=message,
            connection_settings=connection_settings,
        )

    async def _send_outbound_payload(
        self,
        *,
        channel_service: ChannelService,
        organization_id: int,
        config: ReminderConfig,
        channel: str,
        entity_label: str,
        sender_name: str,
        message: str,
        scheduled_at: datetime,
        channel_template: object | None,
        template_variables: dict[str, str],
        recipient_entry: dict[str, object],
    ):
        recipient = recipient_address_for_channel(recipient_entry, channel)
        if not recipient:
            missing_by_channel = {
                "whatsapp": "missing recipient phone number",
                "sms": "missing recipient phone number",
                "email": "missing recipient email",
                "telegram": "missing recipient telegram chat id",
            }
            raise ValueError(
                missing_by_channel.get(channel, "missing recipient for channel delivery")
            )

        send_kwargs: dict[str, object] = {
            "organization_id": organization_id,
            "channel": config.channel,
            "recipient": recipient,
            "text": message,
            "template_variables": template_variables,
        }

        connection_settings: dict[str, object] = {}
        if channel == "email" and channel_template is not None:
            subject = getattr(channel_template, "subject", None)
            if isinstance(subject, str) and subject.strip():
                connection_settings["subject"] = render_template_body(
                    subject.strip(),
                    dict(getattr(config, "template_variables", None) or {}),
                )
        if connection_settings:
            send_kwargs["connection_settings"] = connection_settings

        if channel == "whatsapp" and channel_template is not None:
            settings = get_settings()
            if uses_meta_whatsapp_template(channel_template):
                template_name = (getattr(channel_template, "whatsapp_template_name", None) or "").strip()
                if template_name:
                    send_kwargs["connection_settings"] = {
                        "use_whatsapp_session_text": False,
                        "templateLayout": _PAYLOAD_WHATSAPP_TEMPLATE_LAYOUT,
                    }
                    send_kwargs["template_name"] = template_name
                    send_kwargs["template_language"] = (
                        settings.whatsapp_template_language or "en_US"
                    ).strip() or "en_US"
            else:
                template_name = (settings.whatsapp_template_name or "").strip()
                template_language = (
                    settings.whatsapp_template_language or "en_US"
                ).strip() or "en_US"
                if template_name:
                    send_kwargs["connection_settings"] = {"use_whatsapp_session_text": False}
                    send_kwargs["template_name"] = template_name
                    send_kwargs["template_language"] = template_language

        if channel == "whatsapp" and send_kwargs.get("template_name"):
            connection_settings = send_kwargs.get("connection_settings")
            layout_settings = (
                connection_settings if isinstance(connection_settings, dict) else {}
            )
            template_name = str(send_kwargs["template_name"])
            language_code = resolve_template_language(
                template_name,
                layout_settings,
                template_language=str(send_kwargs.get("template_language") or ""),
            )
            layout = resolve_template_layout(template_name, layout_settings)
            components = build_template_components(layout, template_variables)
            whatsapp_payload: dict[str, object] = {
                "messaging_product": "whatsapp",
                "to": recipient,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {"code": language_code},
                },
            }
            if components:
                whatsapp_payload["template"]["components"] = components
            logger.info(
                "[ReminderProcessor] payload-mode WhatsApp request body=%s",
                whatsapp_payload,
            )

        return await channel_service.send_outbound_message(**send_kwargs)

    @staticmethod
    def _coerce_positive_user_id(value: object) -> int | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, int) and value > 0:
            return value
        if isinstance(value, str) and value.strip().isdigit():
            parsed = int(value.strip())
            if parsed > 0:
                return parsed
        return None

    def _recipient_user_id_from_entry(
        self,
        recipient_entry: dict[str, object] | None,
    ) -> int | None:
        if not isinstance(recipient_entry, dict) or not recipient_entry:
            return None
        address = recipient_address_for_channel(recipient_entry, IN_APP_CHANNEL)
        return self._coerce_positive_user_id(address) if address else None

    def _recipient_user_id_from_data(self, config: ReminderConfig) -> int | None:
        for entry in normalize_recipient_data(getattr(config, "recipient_data", None)):
            parsed = self._recipient_user_id_from_entry(entry)
            if parsed is not None:
                return parsed
        return None

    def _resolve_in_app_user_id(
        self,
        *,
        config: ReminderConfig,
        resolver: ReminderEntityResolver,
        entity: ReminderEntitySnapshot,
        recipient_entry: dict[str, object] | None = None,
    ) -> int | None:
        if recipient_entry is not None:
            return self._recipient_user_id_from_entry(recipient_entry)
        from_data = self._recipient_user_id_from_data(config)
        if from_data is not None:
            return from_data
        return resolver.get_recipient_user_id(entity)

    def _missing_in_app_user_id_error(
        self,
        *,
        config: ReminderConfig,
        entity: ReminderEntitySnapshot,
        recipient_entry: dict[str, object] | None = None,
    ) -> ValueError:
        entity_type = (entity.entity_type or "").strip().lower() or "unknown"
        recipient_data = getattr(config, "recipient_data", None)
        source = entity.source
        assigned = getattr(source, "assigned_agent_user_id", None) if source is not None else None

        if entity_type == "policy":
            return ValueError(
                "missing recipient user id for in_app channel: "
                f"policy id={entity.entity_id} has no assigned_agent_user_id "
                f"(got {assigned!r}) and recipient_data has no user id "
                f"(recipient_entry={recipient_entry!r}; recipient_data={recipient_data!r})"
            )
        return ValueError(
            "missing recipient user id for in_app channel: "
            f"entity_type={entity_type} entity_id={entity.entity_id} "
            "resolver did not provide recipient_user_id and recipient_data "
            f"has no user id (recipient_entry={recipient_entry!r}; "
            f"recipient_data={recipient_data!r})"
        )

    async def _send_in_app(
        self,
        *,
        channel_service: ChannelService,
        organization_id: int,
        config: ReminderConfig,
        instance: ReminderInstance,
        resolver: ReminderEntityResolver,
        entity: ReminderEntitySnapshot,
        entity_label: str,
        message: str,
        recipient_entry: dict[str, object] | None = None,
    ):
        user_id = self._resolve_in_app_user_id(
            config=config,
            resolver=resolver,
            entity=entity,
            recipient_entry=recipient_entry,
        )
        if user_id is None or int(user_id) <= 0:
            raise self._missing_in_app_user_id_error(
                config=config,
                entity=entity,
                recipient_entry=recipient_entry,
            )

        connection_settings = {
            "organization_id": organization_id,
            "entity_type": instance.entity_type,
            "entity_id": instance.entity_id,
            "reminder_instance_id": instance.id,
            "title": entity_label,
            "priority": "normal",
            "metadata": {
                "reference_id": resolver.get_reference(entity),
                "customer_name": resolver.get_customer_name(entity),
                "recipient_type": (
                    recipient_entry.get("recipient_type")
                    if isinstance(recipient_entry, dict)
                    else None
                ),
            },
        }
        logger.info(
            "[ReminderProcessor] in_app delivery entity_type=%s entity_id=%s "
            "recipient_user_id=%s recipient_entry=%s",
            entity.entity_type,
            entity.entity_id,
            user_id,
            recipient_entry,
        )
        return await channel_service.send_outbound_message(
            organization_id=organization_id,
            channel=IN_APP_CHANNEL,
            recipient=str(int(user_id)),
            text=message,
            connection_settings=connection_settings,
        )

    @staticmethod
    def _recipient_from_entry(
        recipient_entry: dict[str, object] | None,
        channel: str,
    ) -> str:
        if not isinstance(recipient_entry, dict) or not recipient_entry:
            return ""
        return recipient_address_for_channel(recipient_entry, channel)

    def _recipient_from_data(self, config: ReminderConfig, channel: str) -> str:
        for entry in normalize_recipient_data(getattr(config, "recipient_data", None)):
            address = self._recipient_from_entry(entry, channel)
            if address:
                return address
        return ""

    def _resolve_recipient(
        self,
        *,
        config: ReminderConfig,
        channel: str,
        resolver: ReminderEntityResolver,
        entity: ReminderEntitySnapshot,
        recipient_entry: dict[str, object] | None = None,
    ) -> str:
        if recipient_entry is not None:
            return self._recipient_from_entry(recipient_entry, channel)
        from_data = self._recipient_from_data(config, channel)
        if from_data:
            return from_data
        return (resolver.get_recipient(entity) or "").strip()

    def _resolve_template_variables(
        self,
        *,
        config: ReminderConfig,
        resolver: ReminderEntityResolver,
        entity: ReminderEntitySnapshot,
        entity_label: str,
        sender_name: str,
        scheduled_at: datetime,
    ) -> dict[str, object]:
        configured = getattr(config, "template_variables", None)
        if isinstance(configured, dict) and configured:
            return dict(configured)
        return resolver.build_template_context(
            entity,
            entity_label=entity_label,
            sender_name=sender_name,
            scheduled_at=scheduled_at,
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
        recipient_entry: dict[str, object] | None = None,
    ):
        recipient = self._resolve_recipient(
            config=config,
            channel=channel,
            resolver=resolver,
            entity=entity,
            recipient_entry=recipient_entry,
        )
        if not recipient:
            missing_by_channel = {
                "whatsapp": "missing recipient phone number",
                "sms": "missing recipient phone number",
                "email": "missing recipient email",
                "telegram": "missing recipient telegram chat id",
            }
            raise ValueError(
                missing_by_channel.get(channel, "missing recipient for channel delivery")
            )

        template_variables = self._resolve_template_variables(
            config=config,
            resolver=resolver,
            entity=entity,
            entity_label=entity_label,
            sender_name=sender_name,
            scheduled_at=scheduled_at,
        )

        send_kwargs: dict[str, object] = {
            "organization_id": organization_id,
            "channel": config.channel,
            "recipient": recipient,
            "text": message,
            "template_variables": template_variables,
        }
        settings = get_settings()
        template_name = (settings.whatsapp_template_name or "").strip()
        template_language = (settings.whatsapp_template_language or "en_US").strip() or "en_US"
        if channel == "whatsapp" and template_name:
            send_kwargs["connection_settings"] = {"use_whatsapp_session_text": False}
            send_kwargs["template_name"] = template_name
            send_kwargs["template_language"] = template_language

        return await channel_service.send_outbound_message(**send_kwargs)
