"""Schemas for Reminder Template CRUD."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ReminderTemplateChannel = Literal["email", "in_app", "sms", "telegram", "whatsapp"]
WhatsAppApprovalStatus = Literal["draft", "pending_approval", "approved", "rejected"]

ALLOWED_CHANNELS = frozenset({"email", "in_app", "sms", "telegram", "whatsapp"})
ALLOWED_APPROVAL_STATUSES = frozenset({"draft", "pending_approval", "approved", "rejected"})


class ReminderTemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    channel: str = Field(..., min_length=1, max_length=32)
    subject: str | None = Field(default=None, max_length=255)
    title: str | None = Field(default=None, max_length=255)
    body: str = Field(..., min_length=1)
    variables: list[str] = Field(default_factory=list)
    is_active: bool = True
    whatsapp_template_name: str | None = Field(default=None, max_length=255)

    @field_validator("name", "subject", "title", "body", "whatsapp_template_name")
    @classmethod
    def strip_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str:
        if not value:
            raise ValueError("name is required")
        return value

    @field_validator("body")
    @classmethod
    def validate_body(cls, value: str | None) -> str:
        if not value:
            raise ValueError("body is required")
        return value

    @field_validator("channel")
    @classmethod
    def validate_channel(cls, value: str) -> str:
        normalized = (value or "").strip().lower()
        if normalized not in ALLOWED_CHANNELS:
            raise ValueError("channel must be one of: email, in_app, sms, telegram, whatsapp")
        return normalized

    @field_validator("variables")
    @classmethod
    def normalize_variables(cls, value: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for item in value:
            token = (item or "").strip()
            if not token or token in seen:
                continue
            seen.add(token)
            cleaned.append(token)
        return cleaned

    @model_validator(mode="after")
    def validate_channel_fields(self) -> ReminderTemplateCreate:
        channel = self.channel
        if channel == "email" and not self.subject:
            raise ValueError("subject is required for email templates")
        if channel == "in_app" and not self.title:
            raise ValueError("title is required for in_app templates")
        if channel == "whatsapp" and not self.whatsapp_template_name:
            self.whatsapp_template_name = self.name
        return self


class ReminderTemplateUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    channel: str | None = Field(default=None, min_length=1, max_length=32)
    subject: str | None = Field(default=None, max_length=255)
    title: str | None = Field(default=None, max_length=255)
    body: str | None = Field(default=None, min_length=1)
    variables: list[str] | None = None
    is_active: bool | None = None
    whatsapp_template_name: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def at_least_one_field(self) -> ReminderTemplateUpdate:
        if not self.model_dump(exclude_unset=True):
            raise ValueError("At least one field must be provided for update")
        return self

    @field_validator("name", "subject", "title", "body", "whatsapp_template_name")
    @classmethod
    def strip_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("channel")
    @classmethod
    def validate_channel(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if normalized not in ALLOWED_CHANNELS:
            raise ValueError("channel must be one of: email, in_app, sms, telegram, whatsapp")
        return normalized

    @field_validator("variables")
    @classmethod
    def normalize_variables(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        cleaned: list[str] = []
        seen: set[str] = set()
        for item in value:
            token = (item or "").strip()
            if not token or token in seen:
                continue
            seen.add(token)
            cleaned.append(token)
        return cleaned


class ReminderTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: int
    created_by: int | None
    name: str
    channel: str
    subject: str | None
    title: str | None
    body: str
    variables: list[str]
    is_active: bool
    whatsapp_template_name: str | None
    approval_status: str | None
    meta_template_id: str | None
    approved_at: datetime | None
    rejection_reason: str | None
    created_at: datetime
    updated_at: datetime


class ReminderTemplateListResponse(BaseModel):
    items: list[ReminderTemplateResponse]
    total: int
    limit: int
    offset: int


class ReminderTemplateDefinitionResponse(BaseModel):
    """Logical reminder template definition (one name, many channel variants)."""

    id: UUID
    name: str
    channels: list[str]
    template_ids: list[UUID]
    is_active: bool = True


class ReminderTemplateDefinitionListResponse(BaseModel):
    items: list[ReminderTemplateDefinitionResponse]
    total: int
