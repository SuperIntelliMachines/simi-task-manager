"""Schemas for General Reminder Definition CRUD (platform feature).

Validates structure only — no module-specific allowlists (Insurance, Claims, etc.).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

TriggerType = Literal["date", "workflow"]
OffsetUnit = Literal["minutes", "hours", "days", "weeks", "months"]
OffsetDirection = Literal["before", "after"]

ALLOWED_TRIGGER_TYPES = frozenset({"date", "workflow"})
ALLOWED_OFFSET_UNITS = frozenset({"minutes", "hours", "days", "weeks", "months"})
ALLOWED_DIRECTIONS = frozenset({"before", "after"})


class TriggerPayload(BaseModel):
    type: str = Field(..., min_length=1, max_length=20)
    key: str = Field(..., min_length=1, max_length=100)

    @field_validator("type")
    @classmethod
    def validate_trigger_type(cls, value: str) -> str:
        normalized = (value or "").strip().lower()
        if normalized not in ALLOWED_TRIGGER_TYPES:
            raise ValueError("trigger.type must be one of: date, workflow")
        return normalized

    @field_validator("key")
    @classmethod
    def validate_trigger_key(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("trigger.key is required")
        return cleaned


class SchedulePayload(BaseModel):
    offset_value: int = Field(..., ge=0)
    offset_unit: str = Field(..., min_length=1, max_length=20)
    direction: str = Field(..., min_length=1, max_length=20)

    @field_validator("offset_unit")
    @classmethod
    def validate_offset_unit(cls, value: str) -> str:
        normalized = (value or "").strip().lower()
        if normalized not in ALLOWED_OFFSET_UNITS:
            raise ValueError(
                "schedule.offset_unit must be one of: minutes, hours, days, weeks, months"
            )
        return normalized

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, value: str) -> str:
        normalized = (value or "").strip().lower()
        if normalized not in ALLOWED_DIRECTIONS:
            raise ValueError("schedule.direction must be one of: before, after")
        return normalized


class RecipientPayload(BaseModel):
    type: str = Field(..., min_length=1, max_length=50)
    value: list[Any] = Field(default_factory=list)

    @field_validator("type")
    @classmethod
    def validate_recipient_type(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("recipient.type is required")
        return cleaned

    @field_validator("value", mode="before")
    @classmethod
    def coerce_value_list(cls, value: Any) -> list[Any]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("recipient.value must be a list")
        return value


class GeneralReminderCreateRequest(BaseModel):
    module_key: str = Field(..., min_length=1, max_length=50)
    reminder_name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    trigger: TriggerPayload
    schedule: SchedulePayload
    recipient: RecipientPayload
    channels: list[str] = Field(..., min_length=1)
    template_key: str | None = Field(default=None, max_length=100)
    is_active: bool = True

    @field_validator("module_key")
    @classmethod
    def validate_module_key(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("module_key is required")
        return cleaned

    @field_validator("reminder_name")
    @classmethod
    def validate_reminder_name(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("reminder_name is required")
        return cleaned

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
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

    @field_validator("template_key")
    @classmethod
    def normalize_template_key(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class GeneralReminderUpdateRequest(BaseModel):
    """Partial update — only provided fields are applied."""

    model_config = ConfigDict(extra="forbid")

    module_key: str | None = Field(default=None, min_length=1, max_length=50)
    reminder_name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    trigger: TriggerPayload | None = None
    schedule: SchedulePayload | None = None
    recipient: RecipientPayload | None = None
    channels: list[str] | None = None
    template_key: str | None = Field(default=None, max_length=100)
    is_active: bool | None = None

    @model_validator(mode="after")
    def at_least_one_field(self) -> GeneralReminderUpdateRequest:
        if not self.model_dump(exclude_unset=True):
            raise ValueError("At least one field must be provided for update")
        return self

    @field_validator("module_key")
    @classmethod
    def validate_module_key(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("module_key cannot be empty")
        return cleaned

    @field_validator("reminder_name")
    @classmethod
    def validate_reminder_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("reminder_name cannot be empty")
        return cleaned

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
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

    @field_validator("template_key")
    @classmethod
    def normalize_template_key(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class GeneralReminderResponse(BaseModel):
    id: UUID
    organization_id: int
    module_key: str
    reminder_name: str
    description: str | None
    trigger: TriggerPayload
    schedule: SchedulePayload
    recipient: RecipientPayload
    channels: list[str]
    template_key: str | None
    is_active: bool
    created_by: int | None
    created_at: datetime
    updated_at: datetime


class GeneralReminderListResponse(BaseModel):
    items: list[GeneralReminderResponse]
    total: int
    limit: int
    offset: int
