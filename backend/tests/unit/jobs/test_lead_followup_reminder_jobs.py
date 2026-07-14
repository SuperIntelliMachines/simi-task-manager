from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.channels.mock_adapter import MockAdapter
from app.jobs.reminder_jobs import process_due_reminders
from app.models.core import Contact, Organization, Reminder, Task, User
from app.models.verticals import InsuranceLead
from app.services.channel_service import ChannelService
from app.services.insurance_service import build_agent_follow_up_message


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def noop_audit(*_args, **_kwargs):
    return None


def _channel_service_factory(email_adapter: MockAdapter):
    def factory(session, **kwargs):
        return ChannelService(
            session,
            telegram_adapter=kwargs.get("telegram_adapter") or MockAdapter("telegram"),
            whatsapp_adapter=kwargs.get("whatsapp_adapter") or MockAdapter("whatsapp"),
            email_adapter=email_adapter,
        )

    return factory


@pytest.mark.asyncio
async def test_process_due_lead_followup_reminder_sends_agent_message(async_session, monkeypatch):
    org = Organization(
        name=f"Lead Reminder Org {uuid4().hex[:8]}",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(org)
    await async_session.flush()

    agent = User(
        organization_id=org.id,
        email=f"agent-{uuid4().hex[:8]}@example.com",
        hashed_password="x",
        is_active=True,
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(agent)
    await async_session.flush()

    contact = Contact(
        id=5101,
        organization_id=org.id,
        name="Priya Sharma",
        phone="+919876543210",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(contact)
    await async_session.flush()

    now = utcnow_naive()
    lead = InsuranceLead(
        id=6101,
        organization_id=org.id,
        contact_id=contact.id,
        assigned_agent_user_id=agent.id,
        source="demo",
        status="follow_up_pending",
        notes="Policy Type: Health\nDemo completed",
        demo_logged_at=now,
        followup_due_at=now - timedelta(minutes=1),
        created_at=now,
        updated_at=now,
    )
    async_session.add(lead)
    await async_session.flush()

    task = Task(
        id=7101,
        organization_id=org.id,
        title="Demo follow-up with Priya Sharma",
        description=lead.notes,
        domain="insurance",
        status="open",
        priority="medium",
        due_at=now,
        created_at=now,
        updated_at=now,
    )
    async_session.add(task)
    await async_session.flush()

    reminder = Reminder(
        id=8101,
        organization_id=org.id,
        task_id=task.id,
        dedupe_key=f"lead-followup:{lead.id}",
        status="pending",
        scheduled_for=now - timedelta(minutes=2),
        created_at=now,
        updated_at=now,
    )
    async_session.add(reminder)
    await async_session.commit()

    expected_message = build_agent_follow_up_message(
        customer_name="Priya Sharma",
        policy_type="health",
    )

    async def fake_send_lead_followup(*_args, **kwargs):
        assert kwargs["message"] == expected_message
        return True, None, "email", "agent@example.com"

    monkeypatch.setattr("app.jobs.reminder_jobs.send_lead_followup_agent_reminder", fake_send_lead_followup)
    monkeypatch.setattr("app.jobs.reminder_jobs.write_audit_event", noop_audit)

    processed = await process_due_reminders(async_session, org.id)
    assert processed == 1

    refreshed = await async_session.get(Reminder, reminder.id)
    assert refreshed is not None
    assert refreshed.status == "sent"
    assert refreshed.sent_at is not None


@pytest.mark.asyncio
async def test_process_multiple_due_lead_reminders_survives_outbound_commit(async_session, monkeypatch):
    org = Organization(
        name=f"Lead Reminder Org {uuid4().hex[:8]}",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(org)
    await async_session.flush()

    agent = User(
        organization_id=org.id,
        email=f"agent-{uuid4().hex[:8]}@example.com",
        hashed_password="x",
        is_active=True,
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(agent)
    await async_session.flush()

    now = utcnow_naive()
    reminder_ids: list[int] = []
    base = int(uuid4().hex[:8], 16) % 900000 + 100000

    for index, name in enumerate(["Priya Sharma", "Ravi Kumar"]):
        contact = Contact(
            id=base + index,
            organization_id=org.id,
            name=name,
            phone=f"+91987654321{index}",
            created_at=now,
            updated_at=now,
        )
        async_session.add(contact)
        await async_session.flush()

        lead = InsuranceLead(
            id=base + 100 + index,
            organization_id=org.id,
            contact_id=contact.id,
            assigned_agent_user_id=agent.id,
            source="demo",
            status="follow_up_pending",
            notes="Policy Type: Health\nDemo completed",
            demo_logged_at=now,
            followup_due_at=now - timedelta(minutes=1),
            created_at=now,
            updated_at=now,
        )
        async_session.add(lead)
        await async_session.flush()

        task = Task(
            id=base + 200 + index,
            organization_id=org.id,
            title=f"Demo follow-up with {name}",
            description=lead.notes,
            domain="insurance",
            status="open",
            priority="medium",
            due_at=now,
            created_at=now,
            updated_at=now,
        )
        async_session.add(task)
        await async_session.flush()

        reminder = Reminder(
            id=base + 300 + index,
            organization_id=org.id,
            task_id=task.id,
            dedupe_key=f"lead-followup:{lead.id}",
            status="pending",
            scheduled_for=now - timedelta(minutes=2),
            created_at=now,
            updated_at=now,
        )
        async_session.add(reminder)
        reminder_ids.append(reminder.id)

    await async_session.commit()

    email_adapter = MockAdapter("email")
    monkeypatch.setattr(
        "app.services.insurance_messaging.ChannelService",
        _channel_service_factory(email_adapter),
    )
    monkeypatch.setattr("app.services.channel_service.write_audit_event", noop_audit)
    monkeypatch.setattr("app.jobs.reminder_jobs.write_audit_event", noop_audit)

    processed = await process_due_reminders(async_session, org.id)
    assert processed == 2
    assert len(email_adapter.sent) == 2

    rows = list(
        (
            await async_session.execute(
                select(Reminder).where(Reminder.id.in_(reminder_ids)).order_by(Reminder.id)
            )
        ).scalars()
    )
    assert len(rows) == 2
    assert all(row.status == "sent" for row in rows)
    assert all(row.sent_at is not None for row in rows)
