from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.models.core import Organization, Reminder, Task, User
from app.services.reminder_service import ReminderService
from app.services.task_service import TaskService


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def seed_org_task(async_session):
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

    task = Task(
        organization_id=org.id,
        title="Reminder task",
        description=None,
        domain="general",
        status="open",
        due_at=None,
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(task)
    await async_session.commit()
    return org, user, task


@pytest.mark.asyncio
async def test_create_and_acknowledge_reminder(async_session):
    org, user, task = await seed_org_task(async_session)
    service = ReminderService(async_session)

    reminder = await service.create_reminder(
        organization_id=org.id,
        task_id=task.id,
        dedupe_key="r1",
        scheduled_for=utcnow_naive() + timedelta(minutes=10),
        actor_user_id=user.id,
    )

    acked = await service.acknowledge_reminder(reminder.id, actor_user_id=user.id)
    assert acked.status == "acknowledged"
    assert acked.acknowledged_at is not None


@pytest.mark.asyncio
async def test_snooze_reminder_updates_scheduled_time(async_session):
    org, user, task = await seed_org_task(async_session)
    service = ReminderService(async_session)

    reminder = await service.create_reminder(
        organization_id=org.id,
        task_id=task.id,
        dedupe_key="r2",
        scheduled_for=utcnow_naive() + timedelta(minutes=1),
        actor_user_id=user.id,
    )

    new_time = utcnow_naive() + timedelta(hours=1)
    snoozed = await service.snooze_reminder(reminder.id, new_time, actor_user_id=user.id)
    assert snoozed.scheduled_for == new_time
    assert snoozed.status == "pending"


@pytest.mark.asyncio
async def test_duplicate_reminder_dedupe_key_fails(async_session):
    org, user, task = await seed_org_task(async_session)
    service = ReminderService(async_session)

    await service.create_reminder(
        organization_id=org.id,
        task_id=task.id,
        dedupe_key="dup-key",
        scheduled_for=utcnow_naive() + timedelta(minutes=5),
        actor_user_id=user.id,
    )

    with pytest.raises(Exception):
        await service.create_reminder(
            organization_id=org.id,
            task_id=task.id,
            dedupe_key="dup-key",
            scheduled_for=utcnow_naive() + timedelta(minutes=6),
            actor_user_id=user.id,
        )

    await async_session.rollback()
