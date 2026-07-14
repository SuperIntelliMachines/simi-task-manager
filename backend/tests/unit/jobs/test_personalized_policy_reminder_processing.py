"""Ensure personalized policy reminders use the generic reminder engine."""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.jobs.policy_reminder_generator import generate_daily_policy_reminders
from app.jobs.policy_reminder_jobs import process_due_policy_reminders
from app.models.core import Contact
from app.models.reminder_config import ReminderConfig
from app.models.reminder_instance import ReminderInstance
from app.models.verticals import InsurancePolicy
from tests.helpers.reminder_configs import seed_entity_reminder_settings
from tests.unit.insurance.test_policy_reminder_generator import seed_org


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@pytest.mark.asyncio
async def test_process_due_personalized_reminders_via_generic_engine(async_session, monkeypatch):
    org = await seed_org(async_session)
    today = datetime(2026, 6, 25, 16, 0, 0)
    expiry = datetime(2026, 7, 2, 15, 30, 0)
    monkeypatch.setattr("app.utils.policy_reminder_stages.utcnow_naive", lambda: today)

    contact = Contact(
        id=8801,
        organization_id=org.id,
        name="Personalized Customer",
        email="personalized@example.com",
        phone="+919876543210",
        created_at=today,
        updated_at=today,
    )
    async_session.add(contact)
    await async_session.flush()

    policy = InsurancePolicy(
        id=8802,
        organization_id=org.id,
        policyholder_id=contact.id,
        policy_number=f"POL-PERS-{uuid4().hex[:4]}",
        premium=1500,
        policy_type="health",
        carrier="Star",
        preferred_channel=["email"],
        mobile_number="+919876543210",
        reminder_type="personalized",
        dnd_start_time=time(21, 0),
        dnd_end_time=time(8, 0),
        expiry_date=expiry,
        status="active",
        created_at=today,
        updated_at=today,
    )
    async_session.add(policy)
    await async_session.flush()

    custom = [{"reminder_unit": "days", "reminder_value": offset} for offset in (7, 2)]
    await seed_entity_reminder_settings(
        async_session,
        organization_id=org.id,
        entity_type="policy",
        entity_id=policy.id,
        channels=["email"],
        offsets=[7, 2],
        template_key="policy_renewal_reminder",
    )
    await async_session.commit()

    created = await generate_daily_policy_reminders(async_session, organization_id=org.id)
    assert created == 2

    instances = list(
        (
            await async_session.execute(
                select(ReminderInstance)
                .where(ReminderInstance.entity_id == policy.id)
                .order_by(ReminderInstance.scheduled_at.asc())
            )
        ).scalars()
    )
    assert len(instances) == 2

    due_instance = next(row for row in instances if row.scheduled_at <= today)
    assert due_instance.status == "PENDING"

    captured: dict[str, object] = {}

    async def _ok_send(self, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(status="sent")

    monkeypatch.setattr(
        "app.services.channel_service.ChannelService.send_outbound_message",
        _ok_send,
    )

    result = await process_due_policy_reminders(async_session, org.id)
    assert result.sent >= 1

    sent_instances = list(
        (
            await async_session.execute(
                select(ReminderInstance).where(
                    ReminderInstance.entity_id == policy.id,
                    ReminderInstance.status == "SENT",
                )
            )
        ).scalars()
    )
    assert len(sent_instances) >= 1


@pytest.mark.asyncio
async def test_process_due_personalized_reminder_records_error_on_send_exception(async_session, monkeypatch):
    org = await seed_org(async_session)
    today = datetime(2026, 6, 25, 16, 0, 0)
    monkeypatch.setattr("app.utils.policy_reminder_stages.utcnow_naive", lambda: today)

    contact = Contact(
        id=8901,
        organization_id=org.id,
        name="Error Customer",
        phone="+919876543210",
        created_at=today,
        updated_at=today,
    )
    async_session.add(contact)
    await async_session.flush()

    policy = InsurancePolicy(
        id=8902,
        organization_id=org.id,
        policyholder_id=contact.id,
        policy_number=f"POL-ERR-{uuid4().hex[:4]}",
        premium=1500,
        policy_type="health",
        carrier="Star",
        preferred_channel=["whatsapp"],
        mobile_number="+919876543210",
        expiry_date=today + timedelta(days=3),
        status="active",
        created_at=today,
        updated_at=today,
    )
    async_session.add(policy)
    await async_session.flush()

    config = ReminderConfig(
        organization_id=org.id,
        entity_type="policy",
        entity_id=policy.id,
        channel="whatsapp",
        template_key="policy_renewal_reminder",
        entity_label="health Renewal",
        sender_name=org.name,
        offset_value=1,
        offset_unit="days",
        is_active=True,
        created_at=today,
        updated_at=today,
    )
    async_session.add(config)
    await async_session.flush()

    instance = ReminderInstance(
        config_id=config.id,
        organization_id=org.id,
        entity_type="policy",
        entity_id=policy.id,
        scheduled_at=today - timedelta(minutes=1),
        status="PENDING",
    )
    async_session.add(instance)
    await async_session.commit()

    async def _boom(self, **kwargs):
        raise RuntimeError("provider down")

    monkeypatch.setattr(
        "app.services.channel_service.ChannelService.send_outbound_message",
        _boom,
    )

    result = await process_due_policy_reminders(async_session, org.id)
    assert result.failed == 1

    refreshed = await async_session.get(ReminderInstance, instance.id)
    assert refreshed is not None
    assert refreshed.status == "FAILED"
    assert refreshed.last_error == "provider down"
