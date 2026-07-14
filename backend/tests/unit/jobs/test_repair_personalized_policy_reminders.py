"""Repair personalized schedules via generic reminder resync."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.jobs.policy_reminder_generator import repair_personalized_policy_reminder_schedules
from app.models.core import Contact
from app.models.reminder_config import ReminderConfig
from app.models.reminder_instance import ReminderInstance
from app.models.verticals import InsurancePolicy
from app.services.policy_legacy_reminder_sync import PolicyLegacyReminderSyncService
from tests.unit.insurance.test_policy_reminder_generator import seed_org


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@pytest.mark.asyncio
async def test_repair_resyncs_personalized_configs_and_regenerates(async_session, monkeypatch):
    org = await seed_org(async_session)
    today = datetime(2026, 6, 10, 10, 0, 0)
    monkeypatch.setattr("app.utils.policy_reminder_stages.utcnow_naive", lambda: today)

    contact = Contact(
        id=8701,
        organization_id=org.id,
        name="Repair Holder",
        phone="+919876543210",
        created_at=today,
        updated_at=today,
    )
    async_session.add(contact)
    await async_session.flush()

    policy = InsurancePolicy(
        id=8702,
        organization_id=org.id,
        policyholder_id=contact.id,
        policy_number="POL-REPAIR-001",
        premium=1000,
        policy_type="health",
        carrier="Star",
        preferred_channel=["whatsapp"],
        reminder_type="personalized",
        expiry_date=today + timedelta(days=14),
        status="active",
        created_at=today,
        updated_at=today,
    )
    async_session.add(policy)
    await async_session.flush()

    custom = [{"reminder_unit": "days", "reminder_value": 7}]
    await PolicyLegacyReminderSyncService(async_session).sync_policy_reminder_configs(
        policy,
        custom_reminders=custom,
    )
    await async_session.commit()

    stats = await repair_personalized_policy_reminder_schedules(
        async_session,
        organization_id=org.id,
        policy_id=policy.id,
    )
    assert stats["policies_repaired"] >= 0

    config_count = await async_session.scalar(
        select(func.count())
        .select_from(ReminderConfig)
        .where(ReminderConfig.entity_id == policy.id, ReminderConfig.is_active.is_(True))
    )
    assert config_count == 1

    instance_count = await async_session.scalar(
        select(func.count()).select_from(ReminderInstance).where(ReminderInstance.entity_id == policy.id)
    )
    assert instance_count >= 1
