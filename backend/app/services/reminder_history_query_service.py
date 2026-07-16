"""Read service for Reminder History (Reminder Management)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.personal_reminder import PersonalReminder
from app.models.reminder_history import ReminderHistory
from app.models.reminder_template import ReminderTemplate


class ReminderHistoryQueryService:
    """Org-scoped queries over reminder_history."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_history(
        self,
        *,
        organization_id: int,
        status: str | None = None,
        channel: str | None = None,
        executed_from: datetime | None = None,
        executed_to: datetime | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[ReminderHistory], int]:
        filters = [ReminderHistory.organization_id == int(organization_id)]

        if status:
            filters.append(ReminderHistory.status == status.strip().upper())
        if channel:
            filters.append(ReminderHistory.channel == channel.strip().lower())
        if executed_from is not None:
            filters.append(ReminderHistory.executed_at >= executed_from)
        if executed_to is not None:
            filters.append(ReminderHistory.executed_at <= executed_to)
        if search:
            pattern = f"%{search.strip()}%"
            filters.append(
                or_(
                    ReminderHistory.reminder_title.ilike(pattern),
                    ReminderHistory.recipient.ilike(pattern),
                )
            )

        page = max(1, int(page))
        page_size = max(1, min(int(page_size), 200))
        offset = (page - 1) * page_size

        items_stmt: Select[tuple[ReminderHistory]] = (
            select(ReminderHistory)
            .where(*filters)
            .order_by(ReminderHistory.executed_at.desc(), ReminderHistory.id.desc())
            .limit(page_size)
            .offset(offset)
        )
        items = list((await self.session.execute(items_stmt)).scalars().all())

        count_stmt = select(func.count()).select_from(ReminderHistory).where(*filters)
        total = int((await self.session.execute(count_stmt)).scalar_one())
        return items, total

    async def get_history(
        self,
        *,
        organization_id: int,
        history_id: uuid.UUID,
    ) -> ReminderHistory:
        row = await self.session.scalar(
            select(ReminderHistory).where(
                ReminderHistory.id == history_id,
                ReminderHistory.organization_id == int(organization_id),
            )
        )
        if row is None:
            raise ValueError("Reminder history not found")
        return row

    async def load_reminder(
        self,
        *,
        organization_id: int,
        reminder_id: uuid.UUID | None,
    ) -> PersonalReminder | None:
        if reminder_id is None:
            return None
        return await self.session.scalar(
            select(PersonalReminder).where(
                PersonalReminder.id == reminder_id,
                PersonalReminder.organization_id == int(organization_id),
            )
        )

    async def load_template(
        self,
        *,
        organization_id: int,
        template_id: uuid.UUID | None,
    ) -> ReminderTemplate | None:
        if template_id is None:
            return None
        return await self.session.scalar(
            select(ReminderTemplate).where(
                ReminderTemplate.id == template_id,
                ReminderTemplate.organization_id == int(organization_id),
            )
        )
