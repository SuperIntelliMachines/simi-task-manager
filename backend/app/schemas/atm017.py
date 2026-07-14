from typing import Any

from pydantic import BaseModel, Field


class ApproveRejectBody(BaseModel):
    actor_user_id: int | None = None
    notes: str | None = None


class AgentSessionReplyBody(BaseModel):
    user_reply: str
    extracted_fields: dict[str, Any] = Field(default_factory=dict)


class MessageTemplateCreateBody(BaseModel):
    organization_id: int
    name: str
    channel: str
    purpose: str
    body: str
    required_variables: list[str] = Field(default_factory=list)
    provider_template_name: str | None = None


class MessageTemplatePatchBody(BaseModel):
    name: str | None = None
    channel: str | None = None
    purpose: str | None = None
    body: str | None = None
    required_variables: list[str] | None = None
    provider_template_name: str | None = None
    status: str | None = None


class TemplateApproveBody(BaseModel):
    approver_user_id: int | None = None


class NotificationPreferenceUpdateBody(BaseModel):
    preferred_channel: str | None = None
    fallback_channel: str | None = None
    opt_out: bool | None = None
    quiet_hours_start: int | None = None
    quiet_hours_end: int | None = None
