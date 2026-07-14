"""Pydantic schemas for generic in-app notifications."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    user_id: int
    entity_type: str
    entity_id: int
    reminder_instance_id: int | None = None
    title: str
    message: str
    priority: str
    status: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    read_at: datetime | None = None
    created_by: int | None = None


class NotificationListResponse(BaseModel):
    notifications: list[NotificationResponse]


class UnreadCountResponse(BaseModel):
    unread_count: int


class MarkAllReadResponse(BaseModel):
    updated: int
