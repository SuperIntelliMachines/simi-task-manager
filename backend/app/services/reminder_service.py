from datetime import UTC, datetime
from app.utils.datetime_utils import normalize_to_utc_naive, utcnow_naive

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import Reminder
from app.services.audit_service import write_audit_event



# utcnow_naive imported from utils


class ReminderService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_reminder(
        self,
        *,
        organization_id: int,
        task_id: int,
        dedupe_key: str,
        scheduled_for: datetime,
        actor_user_id: int | None = None,
    ) -> Reminder:
        scheduled_for = normalize_to_utc_naive(scheduled_for)
        item = Reminder(
            organization_id=organization_id,
            task_id=task_id,
            dedupe_key=dedupe_key,
            status="pending",
            scheduled_for=scheduled_for,
            created_at=utcnow_naive(),
            updated_at=utcnow_naive(),
        )
        self.session.add(item)
        await self.session.flush()
        await write_audit_event(
            session=self.session,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            event_type="reminder.created",
            entity_type="reminder",
            entity_id=str(item.id),
            payload={"dedupe_key": dedupe_key},
        )
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def cancel_reminder(self, reminder_id: int, actor_user_id: int | None = None) -> Reminder:
        item = await self.session.get(Reminder, reminder_id)
        if item is None:
            raise ValueError("reminder not found")

        item.status = "canceled"
        item.canceled_at = utcnow_naive()
        item.updated_at = utcnow_naive()

        await write_audit_event(
            session=self.session,
            organization_id=item.organization_id,
            actor_user_id=actor_user_id,
            event_type="reminder.canceled",
            entity_type="reminder",
            entity_id=str(item.id),
            payload={},
        )
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def acknowledge_reminder(self, reminder_id: int, actor_user_id: int | None = None) -> Reminder:
        item = await self.session.get(Reminder, reminder_id)
        if item is None:
            raise ValueError("reminder not found")

        item.status = "acknowledged"
        item.acknowledged_at = utcnow_naive()
        item.updated_at = utcnow_naive()

        await write_audit_event(
            session=self.session,
            organization_id=item.organization_id,
            actor_user_id=actor_user_id,
            event_type="reminder.acknowledged",
            entity_type="reminder",
            entity_id=str(item.id),
            payload={},
        )
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def snooze_reminder(
        self,
        reminder_id: int,
        scheduled_for: datetime,
        actor_user_id: int | None = None,
    ) -> Reminder:
        item = await self.session.get(Reminder, reminder_id)
        if item is None:
            raise ValueError("reminder not found")

        item.status = "pending"
        item.scheduled_for = scheduled_for
        item.updated_at = utcnow_naive()

        await write_audit_event(
            session=self.session,
            organization_id=item.organization_id,
            actor_user_id=actor_user_id,
            event_type="reminder.snoozed",
            entity_type="reminder",
            entity_id=str(item.id),
            payload={"scheduled_for": scheduled_for.isoformat()},
        )
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def list_pending_reminders(self, organization_id: int) -> list[Reminder]:
        result = await self.session.execute(
            select(Reminder).where(
                Reminder.organization_id == organization_id,
                Reminder.status == "pending",
            )
        )
        return list(result.scalars())

    async def find_due_reminders(self, organization_id: int, now: datetime | None = None) -> list[Reminder]:
        now = now or utcnow_naive()
        result = await self.session.execute(
            select(Reminder).where(
                Reminder.organization_id == organization_id,
                Reminder.status == "pending",
                Reminder.scheduled_for <= now,
            )
        )
        return list(result.scalars())
