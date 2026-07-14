"""In-app notification channel adapter for the Generic Reminder Engine."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.base import ChannelAdapter, NormalizedInboundMessage
from app.services.notification_service import NotificationService


class InAppAdapter(ChannelAdapter):
    """Creates inbox Notification rows instead of sending external messages."""

    channel_name = "in_app"

    def __init__(self, session: AsyncSession, service: NotificationService | None = None):
        self.session = session
        self.service = service or NotificationService(session)

    def normalize_inbound_payload(
        self,
        payload: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> NormalizedInboundMessage:
        return NormalizedInboundMessage(
            channel=self.channel_name,
            external_message_id=str(payload.get("id", "in-app")),
            external_user_id=str(payload.get("user_id", "0")),
            external_chat_id=None,
            text=payload.get("text"),
            message_type="text",
            raw_payload=payload,
        )

    async def send_outbound_message(
        self,
        *,
        connection_settings: dict[str, Any],
        recipient: str,
        text: str,
        template_name: str | None = None,
        template_language: str | None = None,
        template_variables: dict[str, str] | None = None,
    ) -> str:
        _ = template_name, template_language, template_variables
        settings = connection_settings or {}
        try:
            user_id = int(str(recipient).strip())
        except (TypeError, ValueError) as exc:
            raise ValueError("in_app recipient must be a numeric user_id") from exc

        organization_id = settings.get("organization_id")
        if organization_id is None:
            raise ValueError("in_app connection_settings.organization_id is required")

        entity_type = str(settings.get("entity_type") or "reminder").strip().lower()
        entity_id = int(settings.get("entity_id") or 0)
        title = str(settings.get("title") or "Reminder").strip() or "Reminder"
        priority = str(settings.get("priority") or "normal").strip().lower() or "normal"
        reminder_instance_id = settings.get("reminder_instance_id")
        created_by = settings.get("created_by")
        metadata = settings.get("metadata") if isinstance(settings.get("metadata"), dict) else {}

        notification = await self.service.create_notification(
            organization_id=int(organization_id),
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            title=title,
            message=text,
            priority=priority,
            reminder_instance_id=int(reminder_instance_id) if reminder_instance_id is not None else None,
            metadata=metadata,
            created_by=int(created_by) if created_by is not None else None,
        )
        return f"in-app-{notification.id}"

    def verify_webhook(
        self,
        *,
        method: str,
        query_params: dict[str, str],
        headers: dict[str, str],
        body: bytes,
    ) -> tuple[bool, str | None]:
        return True, None

    def resolve_identity(self, normalized: NormalizedInboundMessage) -> dict[str, str | None]:
        return {
            "external_user_id": normalized.external_user_id,
            "external_chat_id": normalized.external_chat_id,
        }

    def map_provider_error(self, error: Exception) -> dict[str, str]:
        return {"code": "in_app_error", "message": str(error)}
