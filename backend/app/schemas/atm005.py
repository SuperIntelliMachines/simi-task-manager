from typing import Any

from pydantic import BaseModel, Field


class ChannelConnectionBody(BaseModel):
    organization_id: int
    channel: str
    status: str = "active"
    provider_reference: str | None = None
    settings: dict[str, Any] = Field(default_factory=dict)


class ChannelTestMessageBody(BaseModel):
    recipient: str
    text: str


class ContactPreferredChannelBody(BaseModel):
    organization_id: int
    channel: str
    external_user_id: str
    external_chat_id: str | None = None
    display_name: str | None = None


class WebhookEnvelope(BaseModel):
    organization_id: int
    payload: dict[str, Any]
