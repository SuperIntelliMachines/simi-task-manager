import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.core import Organization, Reminder, Task
from datetime import UTC, datetime


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)

@pytest.mark.asyncio
async def test_reminder_dedupe_constraint(async_session: AsyncSession):
    organization = Organization(
        name="Test Organization",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(organization)
    await async_session.flush()

    task = Task(
        organization_id=organization.id,
        title="Test Task",
        status="pending",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(task)
    await async_session.flush()

    reminder = Reminder(
        organization_id=organization.id,
        task_id=task.id,
        dedupe_key="renewal:policy-1:day-10",
        status="pending",
        scheduled_for=utcnow_naive(),
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(reminder)
    await async_session.flush()

    duplicate_reminder = Reminder(
        organization_id=organization.id,
        task_id=task.id,
        dedupe_key="renewal:policy-1:day-10",
        status="pending",
        scheduled_for=utcnow_naive(),
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(duplicate_reminder)

    with pytest.raises(IntegrityError):
        await async_session.commit()