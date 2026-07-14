from typing import Any

from app.channels.base import ChannelAdapter, NormalizedInboundMessage


class TelegramAdapter(ChannelAdapter):
    channel_name = "telegram"

    def normalize_inbound_payload(
        self,
        payload: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> NormalizedInboundMessage:
        if "callback_query" in payload:
            cb = payload["callback_query"]
            msg = cb.get("message", {})
            from_user = cb.get("from", {})
            data = cb.get("data", "")
            action, action_payload = self._parse_callback_data(data)
            return NormalizedInboundMessage(
                channel=self.channel_name,
                external_message_id=str(cb.get("id") or payload.get("update_id")),
                external_user_id=str(from_user.get("id", "")),
                external_chat_id=str(msg.get("chat", {}).get("id")) if msg.get("chat") else None,
                text=cb.get("data"),
                message_type="callback",
                action=action,
                action_payload=action_payload,
                raw_payload=payload,
            )

        message = payload.get("message", {})
        from_user = message.get("from", {})
        return NormalizedInboundMessage(
            channel=self.channel_name,
            external_message_id=str(message.get("message_id") or payload.get("update_id")),
            external_user_id=str(from_user.get("id", "")),
            external_chat_id=str(message.get("chat", {}).get("id")) if message.get("chat") else None,
            text=message.get("text"),
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
        from app.channels.telegram_settings import resolve_telegram_bot_token
        from app.integrations.telegram.client import TelegramApiClient

        token = resolve_telegram_bot_token(connection_settings)
        if not token:
            raise ValueError("Telegram bot token is not configured")

        result = await TelegramApiClient(token).send_message(recipient, text)
        message_id = result.get("result", {}).get("message_id")
        return f"tg-{recipient}-{message_id}"

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
        return {"code": "telegram_error", "message": str(error)}

    def _parse_callback_data(self, raw_data: str) -> tuple[str | None, dict[str, Any] | None]:
        # Expected formats like: complete:task:12 or snooze:reminder:7
        parts = raw_data.split(":")
        if len(parts) < 3:
            return None, None
        action = parts[0]
        entity = parts[1]
        entity_id = parts[2]
        key = f"{entity}_id"
        return action, {key: int(entity_id)}
