"""Schemas for Personal Reminder CRUD (independent of the Generic Reminder Engine)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

PersonalReminderStatus = Literal["PENDING", "SENT", "FAILED", "CANCELLED"]
ALLOWED_STATUSES = frozenset({"PENDING", "SENT", "FAILED", "CANCELLED"})


def _strip_tz(value: datetime) -> datetime:
    if value.tzinfo is not None:
        return value.replace(tzinfo=None)
    return value


class PersonalReminderCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    scheduled_at: datetime
    channels: list[str] = Field(..., min_length=1)
    email: str | None = Field(default=None, max_length=255)
    mobile_number: str | None = Field(default=None, max_length=20)
    whatsapp_number: str | None = Field(default=None, max_length=20)
    telegram_chat_id: str | None = Field(default=None, max_length=100)
    template_id: UUID | None = None
    custom_message: str | None = None
    status: PersonalReminderStatus = "PENDING"
    is_active: bool = True

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("title is required")
        return cleaned

    @field_validator("description", "custom_message", "email", "mobile_number", "whatsapp_number", "telegram_chat_id")
    @classmethod
    def normalize_optional_str(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("channels")
    @classmethod
    def validate_channels(cls, value: list[str]) -> list[str]:
        cleaned = [(c or "").strip().lower() for c in value if (c or "").strip()]
        if not cleaned:
            raise ValueError("channels must contain at least one channel")
        return cleaned

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        normalized = (value or "").strip().upper()
        if normalized not in ALLOWED_STATUSES:
            raise ValueError("status must be one of: PENDING, SENT, FAILED, CANCELLED")
        return normalized

    @field_validator("scheduled_at")
    @classmethod
    def normalize_scheduled_at(cls, value: datetime) -> datetime:
        return _strip_tz(value)


class PersonalReminderUpdate(BaseModel):
    """Partial update — only provided fields are applied."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    scheduled_at: datetime | None = None
    channels: list[str] | None = None
    email: str | None = Field(default=None, max_length=255)
    mobile_number: str | None = Field(default=None, max_length=20)
    whatsapp_number: str | None = Field(default=None, max_length=20)
    telegram_chat_id: str | None = Field(default=None, max_length=100)
    template_id: UUID | None = None
    custom_message: str | None = None
    status: PersonalReminderStatus | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def at_least_one_field(self) -> PersonalReminderUpdate:
        if not self.model_dump(exclude_unset=True):
            raise ValueError("At least one field must be provided for update")
        return self

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("title cannot be empty")
        return cleaned

    @field_validator("description", "custom_message", "email", "mobile_number", "whatsapp_number", "telegram_chat_id")
    @classmethod
    def normalize_optional_str(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("channels")
    @classmethod
    def validate_channels(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        cleaned = [(c or "").strip().lower() for c in value if (c or "").strip()]
        if not cleaned:
            raise ValueError("channels must contain at least one channel")
        return cleaned

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        if normalized not in ALLOWED_STATUSES:
            raise ValueError("status must be one of: PENDING, SENT, FAILED, CANCELLED")
        return normalized

    @field_validator("scheduled_at")
    @classmethod
    def normalize_scheduled_at(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return _strip_tz(value)


class PersonalReminderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: int
    created_by: int
    title: str
    description: str | None
    scheduled_at: datetime
    channels: list[str]
    email: str | None
    mobile_number: str | None
    whatsapp_number: str | None
    telegram_chat_id: str | None
    template_id: UUID | None
    custom_message: str | None
    status: str
    sent_at: datetime | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PersonalReminderListResponse(BaseModel):
    items: list[PersonalReminderResponse]
    total: int
    limit: int
    offset: int
