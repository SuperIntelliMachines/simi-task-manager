"""Schemas for Reminder History read APIs."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ReminderHistoryListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: int
    reminder_id: UUID | None
    template_id: UUID | None
    created_by: int
    reminder_title: str
    channel: str
    recipient: str
    status: str
    provider_message_id: str | None
    error_message: str | None
    executed_at: datetime


class ReminderHistoryListResponse(BaseModel):
    items: list[ReminderHistoryListItem]
    total: int
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1)


class ReminderHistoryReminderSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    status: str
    scheduled_at: datetime
    is_active: bool


class ReminderHistoryTemplateSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    channel: str
    is_active: bool


class ReminderHistoryDetailResponse(BaseModel):
    """Full execution details for a single history row."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: int
    reminder_id: UUID | None
    template_id: UUID | None
    created_by: int
    reminder_title: str
    channel: str
    recipient: str
    status: str
    provider_message_id: str | None
    error_message: str | None
    executed_at: datetime
    created_at: datetime
    reminder: ReminderHistoryReminderSummary | None = None
    template: ReminderHistoryTemplateSummary | None = None
