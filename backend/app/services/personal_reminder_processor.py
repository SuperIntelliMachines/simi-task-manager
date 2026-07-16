"""Processor for Personal Reminders — independent of the Generic Reminder Engine."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.core import User
from app.models.personal_reminder import (
    PERSONAL_REMINDER_STATUS_FAILED,
    PERSONAL_REMINDER_STATUS_PENDING,
    PERSONAL_REMINDER_STATUS_SENT,
    PersonalReminder,
)
from app.models.reminder_template import ReminderTemplate
from app.models.reminder_history import (
    REMINDER_HISTORY_STATUS_FAILED,
    REMINDER_HISTORY_STATUS_SENT,
    REMINDER_HISTORY_STATUS_SKIPPED,
)
from app.services.channel_service import ChannelService
from app.services.reminder_history_service import ReminderHistoryService
from app.services.reminder_template_service import ReminderTemplateService
from app.utils.reminder_query_time import fetch_db_now

logger = logging.getLogger(__name__)

IN_APP_CHANNEL = "in_app"
PERSONAL_REMINDER_SENDER_NAME = "SIMI AI Task Manager"
PERSONAL_REMINDER_DATE_FORMAT = "%d %b %Y %I:%M %p"
# Meta-style numbered placeholders → named runtime context keys.
_NUMBERED_PLACEHOLDER_KEYS = (
    "customer_name",
    "policy_name",
    "reminder_date",
    "company_name",
)


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class PersonalReminderProcessorService:
    """Send due personal reminders via ChannelService."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def process_due_reminders(self) -> dict[str, int]:
        """Process all due PENDING personal reminders across organizations."""
        logger.info("[PersonalReminderProcessor] Processor started")

        # Same strategy as ReminderProcessorService: compare against DB clock,
        # not Python UTC — scheduled_at is stored as application wall-clock.
        now = await fetch_db_now(self.session)
        bind = self.session.get_bind()
        if bind.dialect.name == "postgresql":
            due_cutoff = func.now()
        else:
            due_cutoff = now

        result = await self.session.execute(
            select(PersonalReminder)
            .where(
                PersonalReminder.status == PERSONAL_REMINDER_STATUS_PENDING,
                PersonalReminder.is_active.is_(True),
                PersonalReminder.scheduled_at <= due_cutoff,
            )
            .order_by(PersonalReminder.scheduled_at.asc())
            .with_for_update(skip_locked=True)
        )
        reminders = list(result.scalars())

        logger.info(
            "[PersonalReminderProcessor] Due reminders found count=%s",
            len(reminders),
        )

        channel_service = ChannelService(self.session)
        history_service = ReminderHistoryService(self.session)
        sent = 0
        failed = 0

        for reminder in reminders:
            reminder_id = reminder.id
            logger.info(
                "[PersonalReminderProcessor] Reminder ID=%s org_id=%s channels=%s",
                reminder_id,
                reminder.organization_id,
                reminder.channels,
            )
            try:
                if not reminder.is_active:
                    await self._record_history(
                        history_service,
                        reminder=reminder,
                        channel="-",
                        recipient="-",
                        status=REMINDER_HISTORY_STATUS_SKIPPED,
                        error_message="Reminder is inactive",
                        executed_at=now,
                    )
                    continue

                channels = self._normalize_channels(reminder.channels)
                if not channels:
                    await self._record_history(
                        history_service,
                        reminder=reminder,
                        channel="-",
                        recipient="-",
                        status=REMINDER_HISTORY_STATUS_SKIPPED,
                        error_message="Reminder has no channels configured",
                        executed_at=now,
                    )
                    raise ValueError("reminder has no channels configured")

                definition_name = await self._resolve_definition_name(reminder)

                for channel in channels:
                    logger.info(
                        "[PersonalReminderProcessor] Sending channel=%s reminder_id=%s",
                        channel,
                        reminder_id,
                    )
                    channel_template: ReminderTemplate | None = None
                    try:
                        recipient = self._recipient_for_channel(reminder, channel)
                    except ValueError as recipient_error:
                        await self._record_history(
                            history_service,
                            reminder=reminder,
                            channel=channel,
                            recipient="-",
                            status=REMINDER_HISTORY_STATUS_SKIPPED,
                            error_message=str(recipient_error),
                            executed_at=now,
                        )
                        raise

                    try:
                        channel_message, channel_template = await self._resolve_channel_content(
                            reminder=reminder,
                            channel=channel,
                            definition_name=definition_name,
                        )
                        outbound = await self._send_channel(
                            channel_service=channel_service,
                            reminder=reminder,
                            channel=channel,
                            message=channel_message,
                            template=channel_template,
                            recipient=recipient,
                        )
                    except Exception as send_exc:  # noqa: BLE001
                        await self._record_history(
                            history_service,
                            reminder=reminder,
                            channel=channel,
                            recipient=recipient,
                            status=REMINDER_HISTORY_STATUS_FAILED,
                            template_id=(
                                channel_template.id if channel_template is not None else reminder.template_id
                            ),
                            error_message=str(send_exc),
                            executed_at=now,
                        )
                        raise

                    if outbound.status != "sent":
                        provider_error = getattr(outbound, "provider_error", None)
                        error_message = provider_error or (
                            f"channel send failed with status={outbound.status}"
                        )
                        await self._record_history(
                            history_service,
                            reminder=reminder,
                            channel=channel,
                            recipient=recipient,
                            status=REMINDER_HISTORY_STATUS_FAILED,
                            template_id=(
                                channel_template.id if channel_template is not None else reminder.template_id
                            ),
                            provider_message_id=getattr(
                                outbound, "external_provider_message_id", None
                            ),
                            error_message=error_message,
                            executed_at=now,
                        )
                        raise RuntimeError(error_message)

                    await self._record_history(
                        history_service,
                        reminder=reminder,
                        channel=channel,
                        recipient=recipient,
                        status=REMINDER_HISTORY_STATUS_SENT,
                        template_id=(
                            channel_template.id if channel_template is not None else reminder.template_id
                        ),
                        provider_message_id=getattr(
                            outbound, "external_provider_message_id", None
                        ),
                        executed_at=now,
                    )

                reminder.status = PERSONAL_REMINDER_STATUS_SENT
                reminder.sent_at = now
                reminder.updated_at = now
                await self.session.commit()
                sent += 1
                logger.info(
                    "[PersonalReminderProcessor] Success reminder_id=%s",
                    reminder_id,
                )
            except Exception as exc:  # noqa: BLE001
                row = await self.session.get(PersonalReminder, reminder_id)
                if row is None or row.status != PERSONAL_REMINDER_STATUS_PENDING:
                    logger.warning(
                        "[PersonalReminderProcessor] Reminder ID=%s skipped after failure",
                        reminder_id,
                    )
                    continue

                row.status = PERSONAL_REMINDER_STATUS_FAILED
                row.updated_at = now
                await self.session.commit()
                failed += 1
                logger.error(
                    "[PersonalReminderProcessor] Failure reason reminder_id=%s error=%s",
                    reminder_id,
                    exc,
                )
                logger.exception(
                    "[PersonalReminderProcessor] Failed reminder_id=%s",
                    reminder_id,
                )

        processed = sent + failed
        logger.info(
            "[PersonalReminderProcessor] Processor finished processed=%s sent=%s failed=%s",
            processed,
            sent,
            failed,
        )
        return {"processed": processed, "sent": sent, "failed": failed}

    async def _record_history(
        self,
        history_service: ReminderHistoryService,
        *,
        reminder: PersonalReminder,
        channel: str,
        recipient: str,
        status: str,
        executed_at: datetime,
        provider_message_id: str | None = None,
        error_message: str | None = None,
        template_id: uuid.UUID | None = None,
    ) -> None:
        try:
            await history_service.record_attempt(
                organization_id=int(reminder.organization_id),
                reminder_id=reminder.id,
                template_id=template_id if template_id is not None else reminder.template_id,
                created_by=int(reminder.created_by),
                reminder_title=reminder.title or "Reminder",
                channel=channel,
                recipient=recipient,
                status=status,
                provider_message_id=provider_message_id,
                error_message=error_message,
                executed_at=executed_at,
            )
        except Exception:  # noqa: BLE001
            logger.exception(
                "[PersonalReminderProcessor] History logging failed reminder_id=%s channel=%s",
                reminder.id,
                channel,
            )

    async def _resolve_definition_name(self, reminder: PersonalReminder) -> str | None:
        """Logical definition name from the stored template_id (any channel variant)."""
        if reminder.template_id is None:
            return None
        anchor = await self._load_template(
            organization_id=int(reminder.organization_id),
            template_id=reminder.template_id,
        )
        name = (anchor.name or "").strip()
        return name or None

    async def _resolve_channel_content(
        self,
        *,
        reminder: PersonalReminder,
        channel: str,
        definition_name: str | None,
    ) -> tuple[str, ReminderTemplate | None]:
        """Resolve channel-specific template content for one delivery channel.

        Never reuses another channel's body. WhatsApp Meta templates keep raw
        placeholders; other channels get fully rendered text.
        """
        organization_id = int(reminder.organization_id)
        custom_message = (reminder.custom_message or "").strip()
        context = await self._build_runtime_context(reminder)

        if definition_name:
            template_service = ReminderTemplateService(self.session)
            channel_template = await template_service.find_channel_variant(
                organization_id=organization_id,
                definition_name=definition_name,
                channel=channel,
                require_active=True,
            )
            if channel_template is None:
                raise ValueError(
                    f"No {channel} template content found for reminder template "
                    f"'{definition_name}'"
                )
            body = (channel_template.body or "").strip()
            if not body:
                raise ValueError(
                    f"template body is empty for channel={channel} "
                    f"definition='{definition_name}'"
                )
            # WhatsApp Meta templates are rendered by Meta using template_variables.
            if channel == "whatsapp" and self._uses_meta_whatsapp_template(channel_template):
                return body, channel_template
            return self._render_text_content(body, context), channel_template

        if not custom_message:
            raise ValueError("custom_message is required when no template is configured")
        return self._render_text_content(custom_message, context), None

    @staticmethod
    def _uses_meta_whatsapp_template(template: ReminderTemplate) -> bool:
        if (template.channel or "").strip().lower() != "whatsapp":
            return False
        approval = (template.approval_status or "").strip().lower()
        template_name = (template.whatsapp_template_name or "").strip()
        return approval == "approved" and bool(template_name)

    @staticmethod
    def _render_text_content(body: str, context: dict[str, str]) -> str:
        """Render named and numbered placeholders for non-Meta channels."""
        rendered = body
        for key, value in context.items():
            rendered = rendered.replace("{" + key + "}", value)
            rendered = rendered.replace("{{" + key + "}}", value)
        for index, key in enumerate(_NUMBERED_PLACEHOLDER_KEYS, start=1):
            rendered = rendered.replace("{{" + str(index) + "}}", context.get(key, ""))
        return rendered

    async def _load_template(
        self,
        *,
        organization_id: int,
        template_id: uuid.UUID,
    ) -> ReminderTemplate:
        template = await self.session.get(ReminderTemplate, template_id)
        if template is None or int(template.organization_id) != int(organization_id):
            raise ValueError(f"template {template_id} not found")
        if not template.is_active:
            raise ValueError(f"template {template_id} is inactive")
        return template

    @staticmethod
    def _normalize_channels(channels: list[str] | None) -> list[str]:
        if not channels:
            return []
        normalized: list[str] = []
        seen: set[str] = set()
        for raw in channels:
            channel = (raw or "").strip().lower()
            if not channel or channel in seen:
                continue
            seen.add(channel)
            normalized.append(channel)
        return normalized

    @staticmethod
    def _recipient_for_channel(reminder: PersonalReminder, channel: str) -> str:
        if channel == "email":
            recipient = (reminder.email or "").strip()
            if not recipient:
                raise ValueError("email is required for email channel")
            return recipient
        if channel == "sms":
            recipient = (reminder.mobile_number or "").strip()
            if not recipient:
                raise ValueError("mobile_number is required for sms channel")
            return recipient
        if channel == "whatsapp":
            recipient = (reminder.whatsapp_number or "").strip()
            if not recipient:
                raise ValueError("whatsapp_number is required for whatsapp channel")
            return recipient
        if channel == "telegram":
            recipient = (reminder.telegram_chat_id or "").strip()
            if not recipient:
                raise ValueError("telegram_chat_id is required for telegram channel")
            return recipient
        if channel == IN_APP_CHANNEL:
            return str(int(reminder.created_by))
        raise ValueError(f"unsupported channel: {channel}")

    async def _send_channel(
        self,
        *,
        channel_service: ChannelService,
        reminder: PersonalReminder,
        channel: str,
        message: str,
        template: ReminderTemplate | None,
        recipient: str | None = None,
    ):
        if recipient is None:
            recipient = self._recipient_for_channel(reminder, channel)
        organization_id = int(reminder.organization_id)
        send_kwargs: dict[str, Any] = {
            "organization_id": organization_id,
            "channel": channel,
            "recipient": recipient,
            "text": message,
        }

        if channel == "email":
            subject = reminder.title
            if template and template.subject:
                subject = template.subject
            context = await self._build_runtime_context(reminder)
            send_kwargs["connection_settings"] = {
                "subject": self._render_text_content(subject, context),
            }

        elif channel == IN_APP_CHANNEL:
            title = reminder.title
            if template and template.title:
                title = template.title
            context = await self._build_runtime_context(reminder)
            send_kwargs["connection_settings"] = {
                "organization_id": organization_id,
                "entity_type": "personal_reminder",
                "entity_id": 0,
                "title": self._render_text_content(title, context),
                "priority": "normal",
                "metadata": {"personal_reminder_id": str(reminder.id)},
                "created_by": int(reminder.created_by),
            }

        elif channel == "whatsapp":
            settings = get_settings()
            use_meta_template = False
            if template and template.channel == "whatsapp":
                approval = (template.approval_status or "").strip().lower()
                template_name = (template.whatsapp_template_name or "").strip()
                if approval == "approved" and template_name:
                    use_meta_template = True
                    template_variables = await self._build_whatsapp_template_variables(
                        reminder=reminder,
                        template=template,
                    )
                    send_kwargs["connection_settings"] = {
                        "use_whatsapp_session_text": False,
                        # Personal Reminder Meta body param keys (pos {{1}}..{{4}}).
                        # Override without changing shared KNOWN_TEMPLATE_LAYOUTS.
                        "templateLayout": {
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
                        },
                    }
                    send_kwargs["template_name"] = template_name
                    send_kwargs["template_language"] = (
                        settings.whatsapp_template_language or "en_US"
                    ).strip() or "en_US"
                    send_kwargs["template_variables"] = template_variables
            if not use_meta_template:
                send_kwargs["connection_settings"] = {"use_whatsapp_session_text": True}

        return await channel_service.send_outbound_message(**send_kwargs)

    async def _build_whatsapp_template_variables(
        self,
        *,
        reminder: PersonalReminder,
        template: ReminderTemplate,
    ) -> dict[str, str]:
        """Build named runtime vars for the approved Meta template body.

        policy_renewal_reminder placeholders:
          {{1}} customer_name, {{2}} policy_name,
          {{3}} reminder_date, {{4}} company_name
        """
        _ = template  # template row selected; variable values come from the reminder
        return await self._build_runtime_context(reminder)

    async def _build_runtime_context(self, reminder: PersonalReminder) -> dict[str, str]:
        customer_name = await self._resolve_customer_name(reminder)
        reminder_date = ""
        if reminder.scheduled_at is not None:
            reminder_date = reminder.scheduled_at.strftime(PERSONAL_REMINDER_DATE_FORMAT)
        policy_name = (reminder.title or "").strip() or "Reminder"
        return {
            "customer_name": customer_name,
            "policy_name": policy_name,
            "reminder_date": reminder_date,
            "company_name": PERSONAL_REMINDER_SENDER_NAME,
        }

    async def _resolve_customer_name(self, reminder: PersonalReminder) -> str:
        user = await self.session.get(User, int(reminder.created_by))
        if user is None:
            return "User"
        email = (user.email or "").strip()
        if not email:
            return "User"
        local = email.split("@", 1)[0].strip()
        if not local:
            return "User"
        # Prefer a readable display from the email local-part (User has no display_name).
        return local.replace(".", " ").replace("_", " ").strip().title() or "User"
