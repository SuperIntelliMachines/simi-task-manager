from datetime import UTC, datetime
from app.utils.datetime_utils import normalize_to_utc_naive, utcnow_naive

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.atm017 import AuditEvent
from app.models.core import Contact, Reminder, Task, TaskAssignment, User
from app.services.audit_service import write_audit_event


# utcnow_naive imported from utils


class TaskService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _get_task_for_org(self, task_id: int, organization_id: int) -> Task:
        item = await self.session.get(Task, task_id)
        if item is None:
            raise ValueError("task not found")
        if item.organization_id != organization_id:
            raise ValueError("cross-tenant task access denied")
        return item

    async def create_task(
        self,
        *,
        organization_id: int,
        title: str,
        description: str | None,
        due_at: datetime | None,
        domain: str = "general",
        actor_user_id: int | None = None,
        priority: str | None = "medium",
    ) -> Task:
        now = utcnow_naive()
        due_at = normalize_to_utc_naive(due_at)
        item = Task(
            organization_id=organization_id,
            title=title,
            description=description,
            domain=domain,
            status="open",
            priority=priority or "medium",
            due_at=due_at,
            created_at=now,
            updated_at=now,
        )
        self.session.add(item)
        await self.session.flush()
        await write_audit_event(
            session=self.session,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            event_type="task.created",
            entity_type="task",
            entity_id=str(item.id),
            payload={"title": title},
        )
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def update_task(
        self,
        task_id: int,
        updates: dict,
        actor_user_id: int | None = None,
        organization_id: int | None = None,
    ) -> Task:
        if organization_id is None:
            item = await self.session.get(Task, task_id)
            if item is None:
                raise ValueError("task not found")
        else:
            item = await self._get_task_for_org(task_id, organization_id)

        for key, value in updates.items():
            if hasattr(item, key):
                setattr(item, key, value)
        item.updated_at = utcnow_naive()

        await write_audit_event(
            session=self.session,
            organization_id=item.organization_id,
            actor_user_id=actor_user_id,
            event_type="task.updated",
            entity_type="task",
            entity_id=str(item.id),
            payload=updates,
        )
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def assign_task(
        self,
        *,
        task_id: int,
        organization_id: int,
        user_id: int | None,
        contact_id: int | None,
        actor_user_id: int | None = None,
    ) -> TaskAssignment:
        item = await self.session.get(Task, task_id)
        if item is None:
            raise ValueError("task not found")
        if item.organization_id != organization_id:
            raise ValueError("cross-tenant task access denied")

        if (user_id is None and contact_id is None) or (user_id is not None and contact_id is not None):
            raise ValueError("exactly one assignee must be provided")

        if user_id is not None:
            user = await self.session.get(User, user_id)
            if user is None or user.organization_id != organization_id:
                raise ValueError("assignee user must belong to tenant")

        if contact_id is not None:
            contact = await self.session.get(Contact, contact_id)
            if contact is None or contact.organization_id != organization_id:
                raise ValueError("assignee contact must belong to tenant")

        now = utcnow_naive()
        assignment = TaskAssignment(
            organization_id=organization_id,
            task_id=item.id,
            user_id=user_id,
            contact_id=contact_id,
            status="assigned",
            assigned_at=now,
            created_at=now,
            updated_at=now,
        )
        self.session.add(assignment)

        await write_audit_event(
            session=self.session,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            event_type="task.assigned",
            entity_type="task",
            entity_id=str(item.id),
            payload={"user_id": user_id, "contact_id": contact_id},
        )

        await self.session.commit()
        await self.session.refresh(assignment)
        return assignment

    async def complete_task(
        self,
        task_id: int,
        actor_user_id: int | None = None,
        cancel_future_reminders: bool = True,
        organization_id: int | None = None,
    ) -> Task:
        if organization_id is None:
            item = await self.session.get(Task, task_id)
            if item is None:
                raise ValueError("task not found")
        else:
            item = await self._get_task_for_org(task_id, organization_id)

        now = utcnow_naive()
        item.status = "completed"
        item.updated_at = now

        if cancel_future_reminders:
            result = await self.session.execute(
                select(Reminder).where(
                    Reminder.task_id == item.id,
                    Reminder.status.in_(["pending", "processing"]),
                    Reminder.scheduled_for > now,
                )
            )
            reminders = list(result.scalars())
            for reminder in reminders:
                reminder.status = "canceled"
                reminder.canceled_at = now
                reminder.updated_at = now

        await write_audit_event(
            session=self.session,
            organization_id=item.organization_id,
            actor_user_id=actor_user_id,
            event_type="task.completed",
            entity_type="task",
            entity_id=str(item.id),
            payload={"cancel_future_reminders": cancel_future_reminders},
        )

        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def cancel_task(
        self,
        task_id: int,
        actor_user_id: int | None = None,
        organization_id: int | None = None,
    ) -> Task:
        if organization_id is None:
            item = await self.session.get(Task, task_id)
            if item is None:
                raise ValueError("task not found")
        else:
            item = await self._get_task_for_org(task_id, organization_id)

        item.status = "canceled"
        item.updated_at = utcnow_naive()
        await write_audit_event(
            session=self.session,
            organization_id=item.organization_id,
            actor_user_id=actor_user_id,
            event_type="task.canceled",
            entity_type="task",
            entity_id=str(item.id),
            payload={},
        )
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def snooze_task(
        self,
        task_id: int,
        due_at: datetime,
        actor_user_id: int | None = None,
        organization_id: int | None = None,
    ) -> Task:
        if organization_id is None:
            item = await self.session.get(Task, task_id)
            if item is None:
                raise ValueError("task not found")
        else:
            item = await self._get_task_for_org(task_id, organization_id)

        item.status = "snoozed"
        item.due_at = due_at
        item.updated_at = utcnow_naive()

        await write_audit_event(
            session=self.session,
            organization_id=item.organization_id,
            actor_user_id=actor_user_id,
            event_type="task.snoozed",
            entity_type="task",
            entity_id=str(item.id),
            payload={"due_at": due_at.isoformat()},
        )
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def list_tasks(
        self,
        *,
        organization_id: int,
        status: str | None = None,
        domain: str | None = None,
    ) -> list[Task]:
        query = select(Task).where(Task.organization_id == organization_id)
        if status is not None:
            query = query.where(Task.status == status)
        if domain is not None:
            query = query.where(Task.domain == domain)

        result = await self.session.execute(query.order_by(Task.created_at.desc()))
        return list(result.scalars())
