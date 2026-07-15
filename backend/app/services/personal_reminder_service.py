"""Service for Personal Reminder CRUD.

Independent of the Generic Reminder Engine — stores and manages user-owned
reminder rows only (no generation, processing, or channel dispatch).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.personal_reminder import PersonalReminder
from app.schemas.personal_reminder import PersonalReminderCreate, PersonalReminderUpdate


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class PersonalReminderService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_reminder(
        self,
        *,
        organization_id: int,
        created_by: int,
        payload: PersonalReminderCreate,
    ) -> PersonalReminder:
        now = utcnow_naive()
        row = PersonalReminder(
            organization_id=int(organization_id),
            created_by=int(created_by),
            title=payload.title,
            description=payload.description,
            scheduled_at=payload.scheduled_at,
            channels=list(payload.channels),
            email=payload.email,
            mobile_number=payload.mobile_number,
            whatsapp_number=payload.whatsapp_number,
            telegram_chat_id=payload.telegram_chat_id,
            template_id=payload.template_id,
            custom_message=payload.custom_message,
            status=payload.status,
            is_active=payload.is_active,
            created_at=now,
            updated_at=now,
        )
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def get_reminder(
        self,
        *,
        organization_id: int,
        created_by: int,
        reminder_id: uuid.UUID,
    ) -> PersonalReminder:
        row = await self._get_owned(
            organization_id=organization_id,
            created_by=created_by,
            reminder_id=reminder_id,
        )
        if row is None:
            raise ValueError("Personal reminder not found")
        return row

    async def list_reminders(
        self,
        *,
        organization_id: int,
        created_by: int,
        status: str | None = None,
        is_active: bool | None = None,
        q: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[PersonalReminder], int]:
        filters = self._ownership_filters(
            organization_id=organization_id,
            created_by=created_by,
        )
        if status:
            filters.append(PersonalReminder.status == status.strip().upper())
        if is_active is not None:
            filters.append(PersonalReminder.is_active.is_(is_active))
        if q:
            pattern = f"%{q.strip()}%"
            filters.append(
                or_(
                    PersonalReminder.title.ilike(pattern),
                    PersonalReminder.description.ilike(pattern),
                )
            )

        items_stmt: Select[tuple[PersonalReminder]] = (
            select(PersonalReminder)
            .where(*filters)
            .order_by(PersonalReminder.scheduled_at.asc(), PersonalReminder.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        items = list((await self.session.execute(items_stmt)).scalars().all())

        count_stmt = select(func.count()).select_from(PersonalReminder).where(*filters)
        total = int((await self.session.execute(count_stmt)).scalar_one())
        return items, total

    async def update_reminder(
        self,
        *,
        organization_id: int,
        created_by: int,
        reminder_id: uuid.UUID,
        payload: PersonalReminderUpdate,
    ) -> PersonalReminder:
        row = await self.get_reminder(
            organization_id=organization_id,
            created_by=created_by,
            reminder_id=reminder_id,
        )
        data = payload.model_dump(exclude_unset=True)

        for field in (
            "title",
            "description",
            "scheduled_at",
            "email",
            "mobile_number",
            "whatsapp_number",
            "telegram_chat_id",
            "template_id",
            "custom_message",
            "status",
            "is_active",
        ):
            if field in data:
                setattr(row, field, data[field])

        if "channels" in data and data["channels"] is not None:
            row.channels = list(data["channels"])

        row.updated_at = utcnow_naive()
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def delete_reminder(
        self,
        *,
        organization_id: int,
        created_by: int,
        reminder_id: uuid.UUID,
    ) -> None:
        row = await self.get_reminder(
            organization_id=organization_id,
            created_by=created_by,
            reminder_id=reminder_id,
        )
        await self.session.delete(row)
        await self.session.flush()

    def _ownership_filters(self, *, organization_id: int, created_by: int) -> list:
        return [
            PersonalReminder.organization_id == int(organization_id),
            PersonalReminder.created_by == int(created_by),
        ]

    async def _get_owned(
        self,
        *,
        organization_id: int,
        created_by: int,
        reminder_id: uuid.UUID,
    ) -> PersonalReminder | None:
        stmt = select(PersonalReminder).where(
            PersonalReminder.id == reminder_id,
            *self._ownership_filters(
                organization_id=organization_id,
                created_by=created_by,
            ),
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()
