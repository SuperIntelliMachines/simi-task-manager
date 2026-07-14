"""Tests for generic-engine policy reminder generation."""

import inspect

from app.services.insurance_service import InsuranceService


def test_create_policy_does_not_call_legacy_renewal_reminder_creation():
    source = inspect.getsource(InsuranceService.create_policy)
    assert "create_policy_renewal_reminders" not in source


def test_legacy_create_policy_renewal_reminders_method_removed():
    assert not hasattr(InsuranceService, "create_policy_renewal_reminders")


from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.jobs.policy_reminder_generator import generate_daily_policy_reminders
from app.models.core import Contact, Organization
from app.models.insurance import PolicyReminder
from app.models.reminder_config import ReminderConfig
from app.models.reminder_instance import ReminderInstance
from app.models.verticals import InsurancePolicy
from tests.helpers.reminder_configs import seed_policy_reminder_settings


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


def patch_sqlite_policy_reminder_ids(async_session, start_id: int = 9600):
    """Legacy no-op kept for tests that still import this helper."""
    return None


@pytest.mark.asyncio
async def test_daily_generator_creates_instances_for_matching_stage(async_session):
    org = await seed_org(async_session)
    now = utcnow_naive()
    contact = Contact(
        id=9501,
        organization_id=org.id,
        name="Ravi",
        phone="+919876543210",
        created_at=now,
        updated_at=now,
    )
    async_session.add(contact)
    await async_session.flush()

    policy = InsurancePolicy(
        id=9502,
        organization_id=org.id,
        policyholder_id=contact.id,
        policy_number="POL-30DAY",
        premium=2500,
        policy_type="life",
        carrier="LIC",
        assigned_agent_user_id=None,
        preferred_channel=["whatsapp"],
        expiry_date=now + timedelta(days=30),
        status="active",
        created_at=now,
        updated_at=now,
    )
    async_session.add(policy)
    await async_session.commit()

    await seed_policy_reminder_settings(
        async_session,
        organization_id=org.id,
        policy_id=policy.id,
        policy_type="life",
    )

    created = await generate_daily_policy_reminders(async_session, organization_id=org.id)
    assert created == 7

    configs = list(
        (
            await async_session.execute(
                select(ReminderConfig).where(
                    ReminderConfig.entity_type == "policy",
                    ReminderConfig.entity_id == policy.id,
                    ReminderConfig.is_active.is_(True),
                )
            )
        ).scalars()
    )
    assert len(configs) == 7
    assert all(config.template_key == "policy_renewal_reminder" for config in configs)
    assert all(config.entity_label == "life Renewal" for config in configs)

    instances = list(
        (
            await async_session.execute(
                select(ReminderInstance).where(
                    ReminderInstance.entity_type == "policy",
                    ReminderInstance.entity_id == policy.id,
                )
            )
        ).scalars()
    )
    assert len(instances) == 7
    assert all(instance.status == "PENDING" for instance in instances)

    legacy_rows = list(
        (await async_session.execute(select(PolicyReminder).where(PolicyReminder.policy_id == policy.id))).scalars()
    )
    assert len(legacy_rows) == 0


@pytest.mark.asyncio
async def test_generator_skips_policy_outside_30_day_window(async_session):
    org = await seed_org(async_session)
    now = utcnow_naive()
    contact = Contact(
        id=9521,
        organization_id=org.id,
        name="Vikram",
        created_at=now,
        updated_at=now,
    )
    async_session.add(contact)
    await async_session.flush()

    policy = InsurancePolicy(
        id=9522,
        organization_id=org.id,
        policyholder_id=contact.id,
        policy_number="POL-OUTSIDE-WINDOW",
        premium=2000,
        policy_type="life",
        carrier="LIC",
        preferred_channel=["whatsapp"],
        expiry_date=now + timedelta(days=45),
        status="active",
        created_at=now,
        updated_at=now,
    )
    async_session.add(policy)
    await async_session.commit()

    await seed_policy_reminder_settings(
        async_session,
        organization_id=org.id,
        policy_id=policy.id,
        policy_type="life",
    )

    created = await generate_daily_policy_reminders(async_session, organization_id=org.id)
    assert created == 0

    instances = list(
        (
            await async_session.execute(
                select(ReminderInstance).where(ReminderInstance.entity_id == policy.id)
            )
        ).scalars()
    )
    assert len(instances) == 0


@pytest.mark.asyncio
async def test_renewed_policy_does_not_regenerate_reminders(async_session):
    org = await seed_org(async_session)
    now = utcnow_naive()
    contact = Contact(
        id=9541,
        organization_id=org.id,
        name="Kiran",
        created_at=now,
        updated_at=now,
    )
    async_session.add(contact)
    await async_session.flush()

    policy = InsurancePolicy(
        id=9542,
        organization_id=org.id,
        policyholder_id=contact.id,
        policy_number="POL-NO-REGEN",
        premium=1800,
        policy_type="health",
        carrier="Star",
        expiry_date=now + timedelta(days=25),
        status="renewed",
        created_at=now,
        updated_at=now,
    )
    async_session.add(policy)
    await async_session.commit()

    created = await generate_daily_policy_reminders(async_session, organization_id=org.id)
    assert created == 0


@pytest.mark.asyncio
async def test_generator_deduplicates_instances(async_session):
    org = await seed_org(async_session)
    now = utcnow_naive()
    contact = Contact(
        id=9561,
        organization_id=org.id,
        name="Priya",
        created_at=now,
        updated_at=now,
    )
    async_session.add(contact)
    await async_session.flush()

    policy = InsurancePolicy(
        id=9562,
        organization_id=org.id,
        policyholder_id=contact.id,
        policy_number="POL-DEDUP",
        premium=1500,
        policy_type="life",
        carrier="LIC",
        preferred_channel=["whatsapp"],
        expiry_date=now + timedelta(days=10),
        status="active",
        created_at=now,
        updated_at=now,
    )
    async_session.add(policy)
    await async_session.commit()

    await seed_policy_reminder_settings(
        async_session,
        organization_id=org.id,
        policy_id=policy.id,
        policy_type="life",
    )

    first = await generate_daily_policy_reminders(async_session, organization_id=org.id)
    second = await generate_daily_policy_reminders(async_session, organization_id=org.id)
    assert first > 0
    assert second == 0

    instances = list(
        (
            await async_session.execute(
                select(ReminderInstance).where(ReminderInstance.entity_id == policy.id)
            )
        ).scalars()
    )
    assert len(instances) == first
