"""Service layer for generic in-app notifications."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import (
    NOTIFICATION_STATUS_UNREAD,
    Notification,
)
from app.repositories.notification_repository import NotificationRepository, utcnow_naive


class NotificationService:
    def __init__(self, session: AsyncSession, repository: NotificationRepository | None = None):
        self.session = session
        self.repository = repository or NotificationRepository(session)

    async def create_notification(
        self,
        *,
        organization_id: int,
        user_id: int,
        entity_type: str,
        entity_id: int,
        title: str,
        message: str,
        priority: str = "normal",
        reminder_instance_id: int | None = None,
        metadata: dict[str, Any] | None = None,
        created_by: int | None = None,
    ) -> Notification:
        row = Notification(
            organization_id=int(organization_id),
            user_id=int(user_id),
            entity_type=(entity_type or "").strip().lower(),
            entity_id=int(entity_id),
            reminder_instance_id=reminder_instance_id,
            title=(title or "").strip() or "Reminder",
            message=(message or "").strip() or "",
            priority=(priority or "normal").strip().lower() or "normal",
            status=NOTIFICATION_STATUS_UNREAD,
            metadata_json=dict(metadata or {}),
            created_at=utcnow_naive(),
            read_at=None,
            created_by=created_by,
        )
        return await self.repository.create(row)

    async def list_notifications(
        self,
        *,
        organization_id: int,
        user_id: int,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Notification]:
        return await self.repository.list_for_user(
            organization_id=organization_id,
            user_id=user_id,
            status=status,
            limit=limit,
            offset=offset,
        )

    async def unread_count(self, *, organization_id: int, user_id: int) -> int:
        return await self.repository.unread_count(organization_id=organization_id, user_id=user_id)

    async def mark_as_read(
        self,
        *,
        organization_id: int,
        user_id: int,
        notification_id: int,
    ) -> Notification:
        row = await self.repository.mark_read(
            organization_id=organization_id,
            user_id=user_id,
            notification_id=notification_id,
        )
        if row is None:
            raise ValueError("notification not found")
        return row

    async def mark_all_as_read(self, *, organization_id: int, user_id: int) -> int:
        return await self.repository.mark_all_read(organization_id=organization_id, user_id=user_id)

    async def delete_notification(
        self,
        *,
        organization_id: int,
        user_id: int,
        notification_id: int,
    ) -> None:
        deleted = await self.repository.delete_for_user(
            organization_id=organization_id,
            user_id=user_id,
            notification_id=notification_id,
        )
        if not deleted:
            raise ValueError("notification not found")
