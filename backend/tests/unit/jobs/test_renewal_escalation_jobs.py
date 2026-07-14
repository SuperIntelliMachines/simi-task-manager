from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.jobs.renewal_escalation_jobs import process_renewal_escalations
from app.models.core import Contact, Organization, Task, User
from app.models.verticals import InsurancePolicy
from tests.helpers.sqlite_task import patch_task_service_for_sqlite


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@pytest.mark.asyncio
async def test_process_renewal_escalations_escalates_expired_policy(async_session, monkeypatch):
    org = Organization(
        name=f"Escalation Job Org {uuid4().hex[:8]}",
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
        name="Ravi",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(contact)
    await async_session.flush()

    now = utcnow_naive()
    policy = InsurancePolicy(
        id=6101,
        organization_id=org.id,
        policyholder_id=contact.id,
        policy_number="POL-RE-001",
        premium=2500,
        policy_type="life",
        carrier="LIC",
        assigned_agent_user_id=agent.id,
        preferred_channel=["email"],
        expiry_date=now - timedelta(days=2),
        status="active",
        created_at=now,
        updated_at=now,
    )
    async_session.add(policy)
    await async_session.commit()

    async def noop_audit(*_args, **_kwargs):
        return None

    async def fake_email(*_args, **_kwargs):
        return True, None

    monkeypatch.setattr("app.services.insurance_service.write_audit_event", noop_audit)
    monkeypatch.setattr("app.services.task_service.write_audit_event", noop_audit)
    monkeypatch.setattr(
        "app.jobs.renewal_escalation_jobs.send_renewal_escalation_agent_notification",
        fake_email,
    )
    patch_task_service_for_sqlite(monkeypatch, start_id=7100)

    stats = await process_renewal_escalations(async_session, organization_id=org.id)

    assert stats == {"processed": 1, "escalated": 1, "skipped": 0}

    refreshed = await async_session.get(InsurancePolicy, policy.id)
    assert refreshed is not None
    assert refreshed.status == "escalated"

    tasks = list(
        (
            await async_session.execute(
                select(Task).where(
                    Task.organization_id == org.id,
                    Task.title == "Escalate renewal for POL-RE-001",
                )
            )
        ).scalars()
    )
    assert len(tasks) == 1


@pytest.mark.asyncio
async def test_process_renewal_escalations_skips_renewed_and_already_escalated(async_session, monkeypatch):
    org = Organization(
        name=f"Escalation Job Org {uuid4().hex[:8]}",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(org)
    await async_session.flush()

    contact = Contact(
        id=5102,
        organization_id=org.id,
        name="Meera",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(contact)
    await async_session.flush()

    now = utcnow_naive()
    renewed = InsurancePolicy(
        id=6102,
        organization_id=org.id,
        policyholder_id=contact.id,
        policy_number="POL-RE-002",
        premium=1800,
        policy_type="health",
        carrier="Star",
        assigned_agent_user_id=None,
        preferred_channel=["email"],
        expiry_date=now - timedelta(days=3),
        status="renewed",
        created_at=now,
        updated_at=now,
    )
    escalated = InsurancePolicy(
        id=6103,
        organization_id=org.id,
        policyholder_id=contact.id,
        policy_number="POL-RE-003",
        premium=1800,
        policy_type="health",
        carrier="Star",
        assigned_agent_user_id=None,
        preferred_channel=["email"],
        expiry_date=now - timedelta(days=4),
        status="escalated",
        created_at=now,
        updated_at=now,
    )
    async_session.add_all([renewed, escalated])
    await async_session.commit()

    stats = await process_renewal_escalations(async_session, organization_id=org.id)

    assert stats == {"processed": 0, "escalated": 0, "skipped": 0}


@pytest.mark.asyncio
async def test_process_renewal_escalations_is_idempotent(async_session, monkeypatch):
    org = Organization(
        name=f"Escalation Job Org {uuid4().hex[:8]}",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(org)
    await async_session.flush()

    contact = Contact(
        id=5103,
        organization_id=org.id,
        name="Anita",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(contact)
    await async_session.flush()

    now = utcnow_naive()
    policy = InsurancePolicy(
        id=6104,
        organization_id=org.id,
        policyholder_id=contact.id,
        policy_number="POL-RE-004",
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
    await async_session.commit()

    async def noop_audit(*_args, **_kwargs):
        return None

    monkeypatch.setattr("app.services.insurance_service.write_audit_event", noop_audit)
    monkeypatch.setattr("app.services.task_service.write_audit_event", noop_audit)
    patch_task_service_for_sqlite(monkeypatch, start_id=7200)

    first = await process_renewal_escalations(async_session, organization_id=org.id)
    second = await process_renewal_escalations(async_session, organization_id=org.id)

    assert first == {"processed": 1, "escalated": 1, "skipped": 0}
    assert second == {"processed": 0, "escalated": 0, "skipped": 0}

    tasks = list(
        (
            await async_session.execute(
                select(Task).where(
                    Task.organization_id == org.id,
                    Task.title == "Escalate renewal for POL-RE-004",
                )
            )
        ).scalars()
    )
    assert len(tasks) == 1
