"""Integration tests for insurance + generic reminder engine (UI-driven configs)."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.jobs.policy_reminder_generator import generate_daily_policy_reminders
from app.jobs.policy_reminder_jobs import process_due_policy_reminders
from app.models.core import Contact, Organization
from app.models.insurance import PolicyReminder
from app.models.reminder_config import ReminderConfig
from app.models.reminder_instance import ReminderInstance
from app.models.verticals import InsurancePolicy
from app.services.insurance_service import InsuranceService
from app.services.policy_legacy_reminder_sync import PolicyLegacyReminderSyncService
from app.services.reminder_config_service import ReminderConfigService, ReminderOffsetSetting
from tests.helpers.reminder_configs import seed_policy_reminder_settings
from tests.helpers.sqlite_task import patch_sqlite_session_bigint_ids
from unittest.mock import AsyncMock


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@pytest.mark.asyncio
async def test_insurance_create_policy_does_not_auto_create_reminder_configs(async_session, monkeypatch):
    patch_sqlite_session_bigint_ids(async_session, start_id=11000)
    org = Organization(name=f"Mig Org {uuid4().hex[:6]}", created_at=utcnow_naive(), updated_at=utcnow_naive())
    async_session.add(org)
    await async_session.flush()

    monkeypatch.setattr("app.services.insurance_service.utcnow_naive", utcnow_naive)
    monkeypatch.setattr("app.services.insurance_service.InsuranceService.ensure_default_templates", AsyncMock())
    monkeypatch.setattr("app.services.insurance_service.InsuranceService._ensure_notification_preference", AsyncMock())

    service = InsuranceService(async_session)
    expiry = utcnow_naive() + timedelta(days=20)
    policy = await service.create_policy(
        organization_id=org.id,
        policyholder_name="Migration Holder",
        policy_number=f"MIG-{uuid4().hex[:6]}",
        expiry_date=expiry,
        actor_user_id=None,
        policy_type="health",
        preferred_channel=["whatsapp"],
    )

    configs = list(
        (
            await async_session.execute(
                select(ReminderConfig).where(
                    ReminderConfig.entity_type == "policy",
                    ReminderConfig.entity_id == policy.id,
                )
            )
        ).scalars()
    )
    assert len(configs) == 0

    legacy = list(
        (await async_session.execute(select(PolicyReminder).where(PolicyReminder.policy_id == policy.id))).scalars()
    )
    assert len(legacy) == 0


@pytest.mark.asyncio
async def test_insurance_end_to_end_generate_and_process_whatsapp(async_session, monkeypatch):
    org = Organization(name="ABC Insurance", created_at=utcnow_naive(), updated_at=utcnow_naive())
    async_session.add(org)
    await async_session.flush()

    now = utcnow_naive()
    contact = Contact(
        id=11101,
        organization_id=org.id,
        name="Ravi Kumar",
        phone="+919876543210",
        created_at=now,
        updated_at=now,
    )
    async_session.add(contact)
    await async_session.flush()

    policy = InsurancePolicy(
        id=11102,
        organization_id=org.id,
        policyholder_id=contact.id,
        policy_number="MIG-E2E-001",
        premium=1000,
        policy_type="life",
        carrier="LIC",
        mobile_number="+919876543210",
        preferred_channel=["whatsapp"],
        expiry_date=now + timedelta(days=7),
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
        channels=["whatsapp"],
        offsets=[7],
        sender_name="ABC Insurance",
    )

    async def fake_db_now(_session):
        return now

    monkeypatch.setattr("app.utils.policy_reminder_stages.utcnow_naive", lambda: now)
    monkeypatch.setattr("app.services.reminder_processor.fetch_db_now", fake_db_now)

    created = await generate_daily_policy_reminders(async_session, organization_id=org.id)
    assert created >= 1

    due_count = await async_session.scalar(
        select(func.count())
        .select_from(ReminderInstance)
        .where(
            ReminderInstance.entity_id == policy.id,
            ReminderInstance.status == "PENDING",
            ReminderInstance.scheduled_at <= now,
        )
    )
    assert due_count >= 1

    captured: dict[str, object] = {}

    async def _ok_send(self, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(status="sent")

    monkeypatch.setattr(
        "app.services.channel_service.ChannelService.send_outbound_message",
        _ok_send,
    )

    result = await process_due_policy_reminders(async_session, org.id)
    assert result.processed >= 1
    assert captured.get("template_name") == "policy_renewal_reminder"
    template_variables = captured.get("template_variables") or {}
    assert template_variables.get("customer_name") == "Ravi Kumar"
    assert list(template_variables.keys()) == [
        "customer_name",
        "entity_label",
        "reminder_date",
        "sender_name",
    ]

    new_legacy = list(
        (
            await async_session.execute(
                select(PolicyReminder).where(PolicyReminder.policy_id == policy.id)
            )
        ).scalars()
    )
    assert len(new_legacy) == 0


@pytest.mark.asyncio
async def test_save_entity_settings_creates_active_configs(async_session):
    patch_sqlite_session_bigint_ids(async_session, start_id=13000)

    org = Organization(name=f"UI Org {uuid4().hex[:6]}", created_at=utcnow_naive(), updated_at=utcnow_naive())
    async_session.add(org)
    await async_session.flush()

    service = ReminderConfigService(async_session)
    configs = await service.save_entity_settings(
        organization_id=org.id,
        entity_type="policy",
        entity_id=13002,
        channels=["whatsapp"],
        offsets=[
            ReminderOffsetSetting(offset_value=30, offset_unit="days"),
            ReminderOffsetSetting(offset_value=7, offset_unit="days"),
        ],
        template_key="policy_renewal_reminder",
        entity_label="Motor Renewal",
        sender_name="ABC Insurance",
    )

    assert len(configs) == 2
    assert all(config.is_active is True for config in configs)


@pytest.mark.asyncio
async def test_legacy_sync_policy_reminder_configs_still_available(async_session):
    """Legacy migration path remains for repair jobs."""
    patch_sqlite_session_bigint_ids(async_session, start_id=12000)

    org = Organization(name=f"Legacy Org {uuid4().hex[:6]}", created_at=utcnow_naive(), updated_at=utcnow_naive())
    async_session.add(org)
    await async_session.flush()

    now = utcnow_naive()
    contact = Contact(
        id=12001,
        organization_id=org.id,
        name="Legacy Holder",
        phone="+919999999999",
        created_at=now,
        updated_at=now,
    )
    async_session.add(contact)
    await async_session.flush()

    policy = InsurancePolicy(
        id=12002,
        organization_id=org.id,
        policyholder_id=contact.id,
        policy_number=f"LEGACY-{uuid4().hex[:6]}",
        premium=1000,
        policy_type="health",
        preferred_channel=["whatsapp"],
        expiry_date=now + timedelta(days=30),
        status="active",
        created_at=now,
        updated_at=now,
    )
    async_session.add(policy)
    await async_session.flush()

    configs = await PolicyLegacyReminderSyncService(async_session).sync_policy_reminder_configs(policy)
    await async_session.commit()

    assert len(configs) == 7
    assert all(config.is_active is True for config in configs)
