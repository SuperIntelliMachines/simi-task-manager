from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.core import Contact, Organization, User
from app.models.insurance import PolicyReminder
from app.models.verticals import InsurancePolicy
from app.services.insurance_service import InsuranceService
from app.services.policy_service import PolicyService


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def seed_org(async_session) -> Organization:
    org = Organization(
        name=f"PolicyRenew Org {uuid4().hex[:8]}",
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
async def test_policy_service_renewal_cancels_pending_policy_reminders(async_session, monkeypatch):
    org = await seed_org(async_session)
    agent = await seed_user(async_session, org.id)
    now = utcnow_naive()

    contact = Contact(
        id=9100,
        organization_id=org.id,
        name="Test",
        phone="+919876543210",
        created_at=now,
        updated_at=now,
    )
    async_session.add(contact)
    await async_session.flush()

    policy = InsurancePolicy(
        id=9102,
        organization_id=org.id,
        policyholder_id=contact.id,
        policy_number="POL-TEST",
        premium=1000,
        policy_type="auto",
        carrier="carrier-x",
        assigned_agent_user_id=agent.id,
        preferred_channel=["whatsapp"],
        expiry_date=now + timedelta(days=10),
        status="active",
        created_at=now,
        updated_at=now,
    )
    async_session.add(policy)
    await async_session.flush()

    async_session.add(
        PolicyReminder(
            id=9101,
            policy_id=policy.id,
            organization_id=org.id,
            reminder_at=now,
            stage=10,
            reminder_type="UPCOMING_10_DAYS",
            channel="whatsapp",
            status="PENDING",
            attempt_count=0,
        )
    )
    await async_session.commit()

    async def noop_audit(*_args, **_kwargs):
        return None

    async def fake_send(*_args, **_kwargs):
        return False, None

    monkeypatch.setattr("app.services.insurance_service.write_audit_event", noop_audit)
    monkeypatch.setattr(InsuranceService, "_send_renewal_confirmation", fake_send)

    ps = PolicyService(async_session)
    updated = await ps.renew_policy(policy.id, actor_user_id=agent.id)

    assert updated.status == "renewed"

    reminders_after = list(
        (await async_session.execute(select(PolicyReminder).where(PolicyReminder.policy_id == policy.id))).scalars()
    )
    assert len(reminders_after) == 1
    assert reminders_after[0].status == "CANCELED"
