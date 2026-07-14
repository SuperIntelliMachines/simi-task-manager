from datetime import UTC, datetime

from app.channels.base import ChannelAdapter, NormalizedInboundMessage


class MockAdapter(ChannelAdapter):
    def __init__(self, channel_name: str):
        self.channel_name = channel_name
        self.sent: list[dict] = []
        self._send_counter = 0

    def normalize_inbound_payload(self, payload, headers=None):
        return NormalizedInboundMessage(
            channel=self.channel_name,
            external_message_id=str(payload.get("id", "mock-id")),
            external_user_id=str(payload.get("from", "mock-user")),
            external_chat_id=str(payload.get("chat_id", "mock-chat")),
            text=payload.get("text"),
            message_type="text",
            raw_payload=payload,
        )

    async def send_outbound_message(
        self,
        *,
        connection_settings,
        recipient,
        text,
        template_name=None,
        template_variables=None,
    ):
        self.sent.append(
            {
                "recipient": recipient,
                "text": text,
                "template_name": template_name,
                "template_variables": template_variables,
                "connection_settings": connection_settings,
            }
        )
        self._send_counter += 1
        now = int(datetime.now(UTC).timestamp() * 1000)
        return f"mock-{self.channel_name}-{recipient}-{now}-{self._send_counter}"

    def verify_webhook(self, *, method, query_params, headers, body):
        return True, None

    def resolve_identity(self, normalized):
        return {
            "external_user_id": normalized.external_user_id,
            "external_chat_id": normalized.external_chat_id,
        }

    def map_provider_error(self, error: Exception):
        return {"code": "mock_error", "message": str(error)}
