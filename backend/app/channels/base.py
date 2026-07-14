from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class NormalizedInboundMessage:
    channel: str
    external_message_id: str
    external_user_id: str
    external_chat_id: str | None
    text: str | None
    message_type: str = "text"
    action: str | None = None
    action_payload: dict[str, Any] | None = None
    raw_payload: dict[str, Any] | None = None


class ChannelAdapter(Protocol):
    channel_name: str

    def normalize_inbound_payload(
        self,
        payload: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> NormalizedInboundMessage: ...

    async def send_outbound_message(
        self,
        *,
        connection_settings: dict[str, Any],
        recipient: str,
        text: str,
        template_name: str | None = None,
        template_language: str | None = None,
        template_variables: dict[str, str] | None = None,
    ) -> str: ...

    def verify_webhook(
        self,
        *,
        method: str,
        query_params: dict[str, str],
        headers: dict[str, str],
        body: bytes,
    ) -> tuple[bool, str | None]: ...

    def resolve_identity(self, normalized: NormalizedInboundMessage) -> dict[str, str | None]: ...

    def map_provider_error(self, error: Exception) -> dict[str, str]: ...
