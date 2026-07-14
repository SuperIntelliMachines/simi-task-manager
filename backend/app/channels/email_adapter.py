from typing import Any
import smtplib

from app.channels.base import ChannelAdapter, NormalizedInboundMessage
from app.services.email_service import EmailDeliveryError, EmailService


class EmailAdapter(ChannelAdapter):
    channel_name = "email"

    def __init__(self, email_service: EmailService | None = None):
        self.email_service = email_service or EmailService.from_settings()

    def normalize_inbound_payload(
        self,
        payload: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> NormalizedInboundMessage:
        return NormalizedInboundMessage(
            channel=self.channel_name,
            external_message_id=str(payload.get("id", "email-inbound")),
            external_user_id=str(payload.get("from", "email-user")),
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
        template_variables: dict[str, str] | None = None,
    ) -> str:
        settings = connection_settings or {}
        subject = str(settings.get("subject") or "Insurance Reminder")
        html = settings.get("html")
        html_text = str(html) if html is not None else None
        return await self.email_service.send_email(
            to=recipient,
            subject=subject,
            text=text,
            html=html_text,
        )

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
        if isinstance(error, EmailDeliveryError):
            return {"code": "email_delivery_error", "message": str(error)}
        if isinstance(error, smtplib.SMTPException):
            return {"code": "smtp_error", "message": str(error)}
        return {"code": "email_error", "message": str(error)}
