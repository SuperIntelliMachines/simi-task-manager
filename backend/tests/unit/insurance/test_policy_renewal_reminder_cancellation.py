from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.jobs.policy_reminder_generator import generate_daily_policy_reminders
from app.jobs.policy_reminder_jobs import process_due_policy_reminders
from app.models.core import Contact, Organization
from app.models.reminder_config import ReminderConfig
from app.models.reminder_instance import ReminderInstance
from app.models.verticals import InsurancePolicy
from app.services.insurance_service import InsuranceService


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def _seed_policy_with_generic_instances(
    async_session,
    *,
    scheduled_dates: list[datetime],
) -> tuple[Organization, InsurancePolicy, ReminderConfig]:
    suffix = int(uuid4().hex[:6], 16) % 1_000_000
    org = Organization(
        name=f"Renew Cancel Org {uuid4().hex[:8]}",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(org)
    await async_session.flush()

    contact = Contact(
        id=8_000_000 + suffix,
        organization_id=org.id,
        name="Customer",
        phone="+919876543210",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(contact)
    await async_session.flush()

    now = utcnow_naive()
    policy = InsurancePolicy(
        id=9_000_000 + suffix,
        organization_id=org.id,
        policyholder_id=contact.id,
        policy_number=f"POL-CANCEL-{uuid4().hex[:6]}",
        premium=2000,
        policy_type="health",
        carrier="LIC",
        mobile_number="+919876543210",
        preferred_channel=["whatsapp"],
        expiry_date=now + timedelta(days=30),
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
        entity_label="health Renewal",
        sender_name=org.name,
        offset_value=1,
        offset_unit="days",
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    async_session.add(config)
    await async_session.flush()

    for scheduled_at in scheduled_dates:
        async_session.add(
            ReminderInstance(
                config_id=config.id,
                organization_id=org.id,
                entity_type="policy",
                entity_id=policy.id,
                scheduled_at=scheduled_at,
                status="PENDING",
            )
        )
    await async_session.commit()
    return org, policy, config


@pytest.mark.asyncio
async def test_mark_policy_renewed_cancels_all_pending_future_instances(async_session, monkeypatch):
    now = utcnow_naive()
    future_dates = [now + timedelta(days=d) for d in (5, 10, 15, 20, 25)]
    _org, policy, _config = await _seed_policy_with_generic_instances(async_session, scheduled_dates=future_dates)

    async def noop_audit(*_args, **_kwargs):
        return None

    async def fake_send(*_args, **_kwargs):
        return False, None

    monkeypatch.setattr("app.services.insurance_service.write_audit_event", noop_audit)
    monkeypatch.setattr(InsuranceService, "_send_renewal_confirmation", fake_send)

    service = InsuranceService(async_session)
    await service.mark_policy_renewed(policy_id=policy.id, actor_user_id=None)

    instances = list(
        (
            await async_session.execute(
                select(ReminderInstance).where(ReminderInstance.entity_id == policy.id)
            )
        ).scalars()
    )
    assert len(instances) == 5
    assert all(instance.status == "CANCELED" for instance in instances)


@pytest.mark.asyncio
async def test_policy_reminder_cycle_skips_renewed_policies(async_session):
    now = utcnow_naive()
    _org, policy, _config = await _seed_policy_with_generic_instances(
        async_session,
        scheduled_dates=[now + timedelta(days=5)],
    )
    policy.status = "renewed"
    await async_session.commit()

    created = await generate_daily_policy_reminders(async_session, organization_id=policy.organization_id)
    assert created == 0


@pytest.mark.asyncio
async def test_process_policy_reminders_cancels_pending_for_renewed_policy(async_session, monkeypatch):
    now = utcnow_naive()
    due_dates = [now - timedelta(minutes=5), now + timedelta(days=5), now + timedelta(days=10)]
    org, policy, _config = await _seed_policy_with_generic_instances(async_session, scheduled_dates=due_dates)
    policy.status = "renewed"
    await async_session.commit()

    async def _ok_send(self, **kwargs):
        return SimpleNamespace(status="sent")

    monkeypatch.setattr(
        "app.services.channel_service.ChannelService.send_outbound_message",
        _ok_send,
    )

    result = await process_due_policy_reminders(async_session, org.id)
    assert result.sent == 0

    instances = list(
        (
            await async_session.execute(
                select(ReminderInstance).where(ReminderInstance.entity_id == policy.id)
            )
        ).scalars()
    )
    due_instance = next(row for row in instances if row.scheduled_at <= now)
    assert due_instance.status == "CANCELED"
    assert all(row.status == "PENDING" for row in instances if row.scheduled_at > now)
