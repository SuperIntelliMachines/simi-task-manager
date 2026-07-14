from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.atm017 import MessageTemplate
from app.models.core import Contact, Organization, User, WorkflowRun
from app.models.insurance import PolicyReminder
from app.models.verticals import InsurancePolicy
from app.services.insurance_service import INSURANCE_TEMPLATE_DEFINITIONS, InsuranceService
from tests.helpers.sqlite_task import patch_sqlite_session_bigint_ids, patch_task_service_for_sqlite


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def seed_org(async_session) -> Organization:
    org = Organization(
        name=f"Insurance Org {uuid4().hex[:8]}",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(org)
    await async_session.flush()
    return org


async def seed_user(async_session, organization_id: int) -> User:
    user = User(
        organization_id=organization_id,
        email=f"agent-{uuid4().hex[:8]}@example.com",
        hashed_password="x",
        is_active=True,
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(user)
    await async_session.flush()
    return user


@pytest.mark.asyncio
async def test_start_policy_renewal_workflow_does_not_pre_create_policy_reminders(async_session, monkeypatch):
    org = await seed_org(async_session)
    agent = await seed_user(async_session, org.id)
    now = utcnow_naive()
    contact = Contact(
        id=9701,
        organization_id=org.id,
        name="Ravi",
        phone="+919876543210",
        created_at=now,
        updated_at=now,
    )
    async_session.add(contact)
    await async_session.flush()

    policy = InsurancePolicy(
        id=9702,
        organization_id=org.id,
        policyholder_id=contact.id,
        policy_number="POL-20DAY",
        premium=2500,
        policy_type="auto",
        carrier="carrier-a",
        assigned_agent_user_id=agent.id,
        preferred_channel=["whatsapp"],
        expiry_date=now + timedelta(days=20),
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
    patch_task_service_for_sqlite(monkeypatch, start_id=9800)
    patch_sqlite_session_bigint_ids(async_session, start_id=9900)

    service = InsuranceService(async_session)
    result = await service.start_policy_renewal_workflow(policy_id=policy.id, actor_user_id=agent.id)

    reminders = list(
        (await async_session.execute(select(PolicyReminder).where(PolicyReminder.policy_id == policy.id))).scalars()
    )
    templates = list(
        (await async_session.execute(select(MessageTemplate).where(MessageTemplate.organization_id == org.id))).scalars()
    )

    assert result["reminders"] == []
    assert reminders == []
    assert len(templates) == len(INSURANCE_TEMPLATE_DEFINITIONS)
    workflow_runs = list(
        (await async_session.execute(select(WorkflowRun).where(WorkflowRun.organization_id == org.id))).scalars()
    )
    assert len(workflow_runs) == 1


@pytest.mark.asyncio
async def test_renewal_status_cancels_pending_policy_reminders(async_session, monkeypatch):
    org = await seed_org(async_session)
    now = utcnow_naive()
    contact = Contact(
        id=9703,
        organization_id=org.id,
        name="Meera",
        phone="+919111222333",
        created_at=now,
        updated_at=now,
    )
    async_session.add(contact)
    await async_session.flush()

    policy = InsurancePolicy(
        id=9704,
        organization_id=org.id,
        policyholder_id=contact.id,
        policy_number="POL-RENEW",
        premium=1500,
        policy_type="auto",
        carrier="carrier-c",
        assigned_agent_user_id=None,
        preferred_channel=["whatsapp"],
        expiry_date=now + timedelta(days=15),
        status="active",
        created_at=now,
        updated_at=now,
    )
    async_session.add(policy)
    await async_session.flush()
    async_session.add(
        PolicyReminder(
            id=9705,
            policy_id=policy.id,
            organization_id=org.id,
            reminder_at=now,
            stage=15,
            reminder_type="DUE_15_DAYS",
            channel="whatsapp",
            status="PENDING",
            attempt_count=0,
        )
    )
    await async_session.commit()

    async def noop_audit(*_args, **_kwargs):
        return None

    monkeypatch.setattr("app.services.insurance_service.write_audit_event", noop_audit)

    async def fake_send(*_args, **_kwargs):
        return False, None

    monkeypatch.setattr(InsuranceService, "_send_renewal_confirmation", fake_send)

    service = InsuranceService(async_session)
    updated = await service.mark_policy_renewed(policy_id=policy.id, actor_user_id=None)
    reminders = list(
        (await async_session.execute(select(PolicyReminder).where(PolicyReminder.policy_id == policy.id))).scalars()
    )

    assert updated.status == "renewed"
    assert reminders
    assert all(reminder.status == "CANCELED" for reminder in reminders)
