from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.atm017 import AuditEvent
from app.models.core import Contact, Organization, Reminder, Task, User
from app.services.reminder_service import ReminderService
from app.services.task_service import TaskService


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def seed_org_user_contact(async_session):
    org = Organization(name=f"Org A {uuid4().hex[:8]}", created_at=utcnow_naive(), updated_at=utcnow_naive())
    async_session.add(org)
    await async_session.flush()

    user = User(
        organization_id=org.id,
        email="owner@orga.test",
        hashed_password="x",
        is_active=True,
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(user)
    await async_session.flush()

    contact = Contact(
        organization_id=org.id,
        name="John",
        email="john@example.com",
        phone="+1001",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(contact)
    await async_session.commit()
    return org, user, contact


@pytest.mark.asyncio
async def test_create_task_creates_audit_event(async_session):
    org, user, _ = await seed_org_user_contact(async_session)
    service = TaskService(async_session)

    task = await service.create_task(
        organization_id=org.id,
        title="Follow up renewal",
        description="Call customer",
        due_at=utcnow_naive() + timedelta(days=1),
        actor_user_id=user.id,
    )

    assert task.id is not None
    audits = await async_session.execute(
        select(AuditEvent).where(
            AuditEvent.event_type == "task.created",
            AuditEvent.entity_id == str(task.id),
        )
    )
    assert len(list(audits.scalars())) == 1


@pytest.mark.asyncio
async def test_assign_task_validates_assignee_belongs_to_tenant(async_session):
    org, user, _ = await seed_org_user_contact(async_session)
    service = TaskService(async_session)
    task = await service.create_task(
        organization_id=org.id,
        title="Assign me",
        description=None,
        due_at=None,
        actor_user_id=user.id,
    )

    other_org = Organization(name="Org B", created_at=utcnow_naive(), updated_at=utcnow_naive())
    async_session.add(other_org)
    await async_session.flush()
    outsider = User(
        organization_id=other_org.id,
        email="outsider@test",
        hashed_password="x",
        is_active=True,
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(outsider)
    await async_session.commit()

    with pytest.raises(ValueError):
        await service.assign_task(
            task_id=task.id,
            organization_id=org.id,
            user_id=outsider.id,
            contact_id=None,
            actor_user_id=user.id,
        )


@pytest.mark.asyncio
async def test_complete_task_cancels_future_reminders(async_session):
    org, user, _ = await seed_org_user_contact(async_session)
    task_service = TaskService(async_session)
    reminder_service = ReminderService(async_session)

    task = await task_service.create_task(
        organization_id=org.id,
        title="Complete me",
        description=None,
        due_at=None,
        actor_user_id=user.id,
    )

    await reminder_service.create_reminder(
        organization_id=org.id,
        task_id=task.id,
        dedupe_key="task-future-reminder",
        scheduled_for=utcnow_naive() + timedelta(hours=2),
        actor_user_id=user.id,
    )

    await task_service.complete_task(task.id, actor_user_id=user.id, cancel_future_reminders=True)

    reminders = await async_session.execute(select(Reminder).where(Reminder.task_id == task.id))
    rows = list(reminders.scalars())
    assert len(rows) == 1
    assert rows[0].status == "canceled"
