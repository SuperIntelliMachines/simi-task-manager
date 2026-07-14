"""Tests for generic-engine policy reminder processing."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.jobs.policy_reminder_jobs import process_due_policy_reminders
from app.models.core import Contact, Organization
from app.models.reminder_config import ReminderConfig
from app.models.reminder_instance import ReminderInstance
from app.models.verticals import InsurancePolicy
from app.services.policy_generic_reminder_service import PolicyGenericReminderService


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def seed_org(async_session) -> Organization:
    org = Organization(
        name=f"Org {uuid4().hex[:8]}",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(org)
    await async_session.flush()
    return org


@pytest.mark.asyncio
async def test_process_due_policy_reminders_sends_generic_instance(async_session, monkeypatch):
    org = await seed_org(async_session)
    now = utcnow_naive()
    contact = Contact(
        id=8001,
        organization_id=org.id,
        name="Ravi Kumar",
        phone="+919876543210",
        created_at=now,
        updated_at=now,
    )
    async_session.add(contact)
    await async_session.flush()

    policy = InsurancePolicy(
        id=8002,
        organization_id=org.id,
        policyholder_id=contact.id,
        policy_number="POL-REM-001",
        premium=1000,
        policy_type="life",
        carrier="LIC",
        mobile_number="+919876543210",
        preferred_channel=["whatsapp"],
        expiry_date=now + timedelta(days=10),
        status="active",
        created_at=now,
        updated_at=now,
    )
    async_session.add(policy)
    await async_session.flush()

    config = ReminderConfig(
        organization_id=org.id,
        entity_type="policy",
        entity_id=policy.id,
        channel="whatsapp",
        template_key="policy_renewal_reminder",
        entity_label="life Renewal",
        sender_name=org.name,
        offset_value=1,
        offset_unit="days",
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    async_session.add(config)
    await async_session.flush()

    instance = ReminderInstance(
        config_id=config.id,
        organization_id=org.id,
        entity_type="policy",
        entity_id=policy.id,
        scheduled_at=now - timedelta(minutes=5),
        status="PENDING",
    )
    async_session.add(instance)
    await async_session.commit()

    captured: dict[str, object] = {}

    async def _ok_send(self, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(status="sent")

    monkeypatch.setattr(
        "app.services.channel_service.ChannelService.send_outbound_message",
        _ok_send,
    )

    result = await process_due_policy_reminders(async_session, org.id)
    assert result.processed == 1
    assert result.failed == 0
    assert captured["template_variables"]["entity_label"] == "life Renewal"

    refreshed = await async_session.get(ReminderInstance, instance.id)
    assert refreshed is not None
    assert refreshed.status == "SENT"


@pytest.mark.asyncio
async def test_process_due_policy_reminders_no_due_instances(async_session):
    org = await seed_org(async_session)
    result = await process_due_policy_reminders(async_session, org.id)
    assert result.processed == 0
