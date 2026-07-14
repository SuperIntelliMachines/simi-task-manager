"""Full schedule tests for generic policy reminder engine."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.jobs.policy_reminder_generator import generate_daily_policy_reminders
from app.models.core import Contact
from app.models.insurance import PolicyReminder
from app.models.reminder_config import ReminderConfig
from app.models.reminder_instance import ReminderInstance
from app.models.verticals import InsurancePolicy
from tests.unit.insurance.test_policy_reminder_generator import seed_org


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@pytest.mark.asyncio
async def test_policy_entering_window_creates_generic_schedule(async_session, monkeypatch):
    org = await seed_org(async_session)
    today = datetime(2026, 6, 1, 10, 0, 0)
    monkeypatch.setattr("app.utils.policy_reminder_stages.utcnow_naive", lambda: today)

    contact = Contact(
        id=9701,
        organization_id=org.id,
        name="Schedule Holder",
        phone="+919876543210",
        created_at=today,
        updated_at=today,
    )
    async_session.add(contact)
    await async_session.flush()

    policy = InsurancePolicy(
        id=9702,
        organization_id=org.id,
        policyholder_id=contact.id,
        policy_number="POL-FULL-SCHED",
        premium=1000,
        policy_type="life",
        carrier="LIC",
        preferred_channel=["whatsapp"],
        expiry_date=today + timedelta(days=30),
        status="active",
        created_at=today,
        updated_at=today,
    )
    async_session.add(policy)
    await async_session.commit()

    created = await generate_daily_policy_reminders(async_session, organization_id=org.id)
    assert created == 7

    config_count = await async_session.scalar(
        select(func.count())
        .select_from(ReminderConfig)
        .where(ReminderConfig.entity_id == policy.id, ReminderConfig.is_active.is_(True))
    )
    assert config_count == 7

    legacy_count = await async_session.scalar(
        select(func.count()).select_from(PolicyReminder).where(PolicyReminder.policy_id == policy.id)
    )
    assert legacy_count == 0


@pytest.mark.asyncio
async def test_full_schedule_generation_is_idempotent(async_session, monkeypatch):
    org = await seed_org(async_session)
    today = datetime(2026, 6, 1, 10, 0, 0)
    monkeypatch.setattr("app.utils.policy_reminder_stages.utcnow_naive", lambda: today)

    contact = Contact(
        id=9801,
        organization_id=org.id,
        name="Idempotent Holder",
        created_at=today,
        updated_at=today,
    )
    async_session.add(contact)
    await async_session.flush()

    policy = InsurancePolicy(
        id=9802,
        organization_id=org.id,
        policyholder_id=contact.id,
        policy_number="POL-IDEMP",
        premium=1000,
        policy_type="life",
        carrier="LIC",
        preferred_channel=["whatsapp"],
        expiry_date=today + timedelta(days=15),
        status="active",
        created_at=today,
        updated_at=today,
    )
    async_session.add(policy)
    await async_session.commit()

    first = await generate_daily_policy_reminders(async_session, organization_id=org.id)
    second = await generate_daily_policy_reminders(async_session, organization_id=org.id)
    assert first > 0
    assert second == 0

    instance_count = await async_session.scalar(
        select(func.count()).select_from(ReminderInstance).where(ReminderInstance.entity_id == policy.id)
    )
    assert instance_count == first
