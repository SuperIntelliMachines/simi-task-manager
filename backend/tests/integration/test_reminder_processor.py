from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.atm017 import OutboundMessage
from app.models.core import Organization, Reminder, Task, User
from app.jobs.reminder_jobs import process_due_reminders
from app.services.channel_adapter import set_channel_adapter


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class FakeChannelAdapter:
    def __init__(self):
        self.counter = 0

    async def send_message(self, *, channel: str, recipient: str, body: str) -> str:
        self.counter += 1
        return f"provider-{self.counter}"


async def seed_org_task(async_session):
    org = Organization(
        name=f"Org A {uuid4().hex[:8]}",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
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
        id=9001,
        organization_id=org.id,
        title="Due reminder task",
        description=None,
        domain="general",
        status="open",
        due_at=utcnow_naive() - timedelta(minutes=1),
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(task)
    await async_session.flush()

    now = utcnow_naive()
    reminder = Reminder(
        id=9002,
        organization_id=org.id,
        task_id=task.id,
        dedupe_key="due-reminder-1",
        status="pending",
        scheduled_for=now - timedelta(minutes=2),
        created_at=now,
        updated_at=now,
    )
    async_session.add(reminder)
    await async_session.commit()
    return org, user, task


@pytest.mark.asyncio
async def test_due_reminder_processed_once(async_session, monkeypatch):
    org, user, task = await seed_org_task(async_session)

    async def noop_audit(*_args, **_kwargs):
        return None

    monkeypatch.setattr("app.jobs.reminder_jobs.write_audit_event", noop_audit)
    set_channel_adapter(FakeChannelAdapter())

    processed_first = await process_due_reminders(async_session, org.id)
    processed_second = await process_due_reminders(async_session, org.id)

    assert processed_first == 1
    assert processed_second == 0

    outbounds = await async_session.execute(select(OutboundMessage))
    rows = list(outbounds.scalars())
    assert len(rows) == 1
    assert rows[0].status == "sent"
