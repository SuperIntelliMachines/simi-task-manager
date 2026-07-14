from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.jobs.policy_reminder_jobs import process_due_policy_reminders
from app.models.core import Contact, Organization, Task, User
from app.models.insurance import PolicyReminder
from app.models.verticals import InsurancePolicy
from app.services.insurance_service import InsuranceService
from tests.helpers.sqlite_task import patch_task_service_for_sqlite


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@pytest.mark.asyncio
async def test_trigger_renewal_escalation_creates_task_and_sets_status(async_session, monkeypatch):
    org = Organization(
        name=f"Escalation Org {uuid4().hex[:8]}",
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
        id=1201,
        organization_id=org.id,
        name="Ravi",
        phone="+919876543210",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(contact)
    await async_session.flush()

    now = utcnow_naive()
    policy = InsurancePolicy(
        id=2201,
        organization_id=org.id,
        policyholder_id=contact.id,
        policy_number="POL-ESC-001",
        premium=2500,
        policy_type="life",
        carrier="LIC",
        assigned_agent_user_id=agent.id,
        preferred_channel=["sms"],
        expiry_date=now - timedelta(days=1),
        status="active",
        created_at=now,
        updated_at=now,
    )
    async_session.add(policy)
    await async_session.commit()

    async def noop_audit(*_args, **_kwargs):
        return None

    monkeypatch.setattr("app.services.insurance_service.write_audit_event", noop_audit)
    monkeypatch.setattr("app.services.task_service.write_audit_event", noop_audit)
    patch_task_service_for_sqlite(monkeypatch, start_id=4200)

    service = InsuranceService(async_session)
    result = await service.trigger_renewal_escalation(policy=policy, actor_user_id=agent.id)
    await async_session.commit()

    assert result["result"] == "created"
    assert result["task_id"] is not None
    assert result["assigned_agent_user_id"] == agent.id

    refreshed = await async_session.get(InsurancePolicy, policy.id)
    assert refreshed is not None
    assert refreshed.status == "escalated"

    task = await async_session.get(Task, result["task_id"])
    assert task is not None
    assert task.title == "Escalate renewal for POL-ESC-001"
    assert task.description == "Policy has not been renewed after expiry. Immediate follow-up required."
    assert task.status == "open"
    assert task.domain == "insurance"


@pytest.mark.asyncio
async def test_trigger_renewal_escalation_is_idempotent(async_session, monkeypatch):
    org = Organization(
        name=f"Escalation Org {uuid4().hex[:8]}",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(org)
    await async_session.flush()

    contact = Contact(
        id=1202,
        organization_id=org.id,
        name="Meera",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(contact)
    await async_session.flush()

    now = utcnow_naive()
    policy = InsurancePolicy(
        id=2202,
        organization_id=org.id,
        policyholder_id=contact.id,
        policy_number="POL-ESC-002",
        premium=1800,
        policy_type="health",
        carrier="Star",
        assigned_agent_user_id=None,
        preferred_channel=["email"],
        expiry_date=now - timedelta(days=1),
        status="active",
        created_at=now,
        updated_at=now,
    )
    async_session.add(policy)
    await async_session.commit()

    async def noop_audit(*_args, **_kwargs):
        return None

    monkeypatch.setattr("app.services.insurance_service.write_audit_event", noop_audit)
    monkeypatch.setattr("app.services.task_service.write_audit_event", noop_audit)
    patch_task_service_for_sqlite(monkeypatch, start_id=4300)

    service = InsuranceService(async_session)
    first = await service.trigger_renewal_escalation(policy=policy)
    await async_session.commit()
    await async_session.refresh(policy)
    second = await service.trigger_renewal_escalation(policy=policy)
    await async_session.commit()

    tasks = list(
        (
            await async_session.execute(
                select(Task).where(
                    Task.organization_id == org.id,
                    Task.title == "Escalate renewal for POL-ESC-002",
                )
            )
        ).scalars()
    )

    assert first["result"] == "created"
    assert second["result"] == "skipped"
    assert len(tasks) == 1


@pytest.mark.skip(reason="Legacy policy_reminders ESCALATION rows no longer processed by policy_reminder_jobs")
@pytest.mark.asyncio
async def test_process_due_stage_one_triggers_escalation(async_session, monkeypatch):
    org = Organization(
        name=f"Escalation Org {uuid4().hex[:8]}",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(org)
    await async_session.flush()

    contact = Contact(
        id=1203,
        organization_id=org.id,
        name="Anita",
        email="anita@example.com",
        phone="+919111222333",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(contact)
    await async_session.flush()

    now = utcnow_naive()
    policy = InsurancePolicy(
        id=2203,
        organization_id=org.id,
        policyholder_id=contact.id,
        policy_number="POL-ESC-003",
        premium=1500,
        policy_type="auto",
        carrier="Carrier",
        assigned_agent_user_id=None,
        preferred_channel=["email"],
        expiry_date=now - timedelta(days=1),
        status="active",
        created_at=now,
        updated_at=now,
    )
    async_session.add(policy)
    await async_session.flush()

    async_session.add(
        PolicyReminder(
            id=3203,
            policy_id=policy.id,
            organization_id=org.id,
            reminder_at=now - timedelta(minutes=5),
            stage=-1,
            reminder_type="ESCALATION",
            channel="email",
            status="PENDING",
            attempt_count=0,
        )
    )
    await async_session.commit()

    async def fake_send(*_args, **_kwargs):
        return True, None

    async def noop_audit(*_args, **_kwargs):
        return None

    monkeypatch.setattr("app.jobs.policy_reminder_jobs.send_policy_channel_message", fake_send)
    monkeypatch.setattr("app.jobs.policy_reminder_jobs.write_audit_event", noop_audit)
    monkeypatch.setattr("app.services.insurance_service.write_audit_event", noop_audit)
    monkeypatch.setattr("app.services.task_service.write_audit_event", noop_audit)
    patch_task_service_for_sqlite(monkeypatch, start_id=4400)

    processed = (await process_due_policy_reminders(async_session, org.id)).processed
    assert processed == 1

    refreshed = await async_session.get(InsurancePolicy, policy.id)
    assert refreshed is not None
    assert refreshed.status == "escalated"

    tasks = list(
        (
            await async_session.execute(
                select(Task).where(
                    Task.organization_id == org.id,
                    Task.title == "Escalate renewal for POL-ESC-003",
                )
            )
        ).scalars()
    )
    assert len(tasks) == 1


@pytest.mark.asyncio
async def test_mark_policy_renewed_cancels_stage_one_escalation_task(async_session, monkeypatch):
    org = Organization(
        name=f"Escalation Org {uuid4().hex[:8]}",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(org)
    await async_session.flush()

    contact = Contact(
        id=1204,
        organization_id=org.id,
        name="Kiran",
        phone="+919222333444",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(contact)
    await async_session.flush()

    now = utcnow_naive()
    policy = InsurancePolicy(
        id=2204,
        organization_id=org.id,
        policyholder_id=contact.id,
        policy_number="POL-ESC-004",
        premium=1500,
        policy_type="auto",
        carrier="Carrier",
        assigned_agent_user_id=None,
        preferred_channel=["sms"],
        expiry_date=now - timedelta(days=1),
        status="escalated",
        created_at=now,
        updated_at=now,
    )
    async_session.add(policy)
    await async_session.flush()

    task = Task(
        id=4204,
        organization_id=org.id,
        title="Escalate renewal for POL-ESC-004",
        description="Policy has not been renewed after expiry. Immediate follow-up required.",
        domain="insurance",
        status="open",
        priority="medium",
        due_at=now,
        created_at=now,
        updated_at=now,
    )
    async_session.add(task)
    await async_session.commit()

    async def fake_send(*_args, **_kwargs):
        return True, None

    async def noop_audit(*_args, **_kwargs):
        return None

    monkeypatch.setattr("app.services.insurance_service.send_policy_channel_message", fake_send)
    monkeypatch.setattr("app.services.insurance_service.write_audit_event", noop_audit)
    monkeypatch.setattr("app.services.task_service.write_audit_event", noop_audit)

    service = InsuranceService(async_session)
    updated = await service.mark_policy_renewed(policy_id=policy.id, actor_user_id=None)

    assert updated.status == "renewed"
    cancelled = await async_session.get(Task, task.id)
    assert cancelled is not None
    assert cancelled.status == "canceled"
