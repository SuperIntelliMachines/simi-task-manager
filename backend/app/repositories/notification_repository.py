"""Repository for generic in-app notifications."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import (
    NOTIFICATION_STATUS_READ,
    NOTIFICATION_STATUS_UNREAD,
    Notification,
)


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class NotificationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, notification: Notification) -> Notification:
        self.session.add(notification)
        await self.session.flush()
        return notification

    async def get_for_user(
        self,
        *,
        organization_id: int,
        user_id: int,
        notification_id: int,
    ) -> Notification | None:
        result = await self.session.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.organization_id == organization_id,
                Notification.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self,
        *,
        organization_id: int,
        user_id: int,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Notification]:
        stmt = (
            select(Notification)
            .where(
                Notification.organization_id == organization_id,
                Notification.user_id == user_id,
            )
            .order_by(Notification.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if status:
            stmt = stmt.where(Notification.status == status)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def unread_count(self, *, organization_id: int, user_id: int) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.organization_id == organization_id,
                Notification.user_id == user_id,
                Notification.status == NOTIFICATION_STATUS_UNREAD,
            )
        )
        return int(result.scalar_one() or 0)

    async def mark_read(
        self,
        *,
        organization_id: int,
        user_id: int,
        notification_id: int,
    ) -> Notification | None:
        row = await self.get_for_user(
            organization_id=organization_id,
            user_id=user_id,
            notification_id=notification_id,
        )
        if row is None:
            return None
        if row.status != NOTIFICATION_STATUS_READ:
            row.status = NOTIFICATION_STATUS_READ
            row.read_at = utcnow_naive()
            await self.session.flush()
        return row

    async def mark_all_read(self, *, organization_id: int, user_id: int) -> int:
        now = utcnow_naive()
        result = await self.session.execute(
            update(Notification)
            .where(
                Notification.organization_id == organization_id,
                Notification.user_id == user_id,
                Notification.status == NOTIFICATION_STATUS_UNREAD,
            )
            .values(status=NOTIFICATION_STATUS_READ, read_at=now)
        )
        await self.session.flush()
        return int(result.rowcount or 0)

    async def delete_for_user(
        self,
        *,
        organization_id: int,
        user_id: int,
        notification_id: int,
    ) -> bool:
        row = await self.get_for_user(
            organization_id=organization_id,
            user_id=user_id,
            notification_id=notification_id,
        )
        if row is None:
            return False
        await self.session.delete(row)
        await self.session.flush()
        return True
