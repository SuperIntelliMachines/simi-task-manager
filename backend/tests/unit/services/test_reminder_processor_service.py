from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.config import get_settings
from app.models.core import Contact, Organization
from app.models.reminder_config import ReminderConfig
from app.models.reminder_instance import ReminderInstance
from app.models.verticals import InsurancePolicy
from app.services.reminder_processor import ReminderProcessorService
from tests.helpers.sqlite_task import patch_sqlite_session_bigint_ids


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def seed_org(async_session):
    org = Organization(name=f"Org {uuid4().hex[:8]}", created_at=utcnow_naive(), updated_at=utcnow_naive())
    async_session.add(org)
    await async_session.commit()
    return org


async def seed_policy(async_session, *, org_id: int, mobile_number: str | None = "+919876543210") -> InsurancePolicy:
    patch_sqlite_session_bigint_ids(async_session, start_id=5000)
    contact = Contact(
        organization_id=org_id,
        name="Ravi Kumar",
        email="ravi@example.com",
        phone="+919876543210",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(contact)
    await async_session.flush()

    now = utcnow_naive()
    policy = InsurancePolicy(
        organization_id=org_id,
        policyholder_id=contact.id,
        policy_number="POL-GEN-001",
        premium=2500,
        policy_type="life",
        carrier="LIC",
        mobile_number=mobile_number,
        expiry_date=now + timedelta(days=10),
        status="ACTIVE",
        created_at=now,
        updated_at=now,
    )
    async_session.add(policy)
    await async_session.commit()
    return policy


async def _add_due_instance(
    async_session,
    *,
    org_id: int,
    entity_type: str,
    entity_id: int,
    channel: str = "whatsapp",
    scheduled_at: datetime | None = None,
    attempt_count: int = 0,
) -> ReminderInstance:
    config = ReminderConfig(
        organization_id=org_id,
        entity_type=entity_type,
        entity_id=entity_id,
        channel=channel,
        template_key=None,
        offset_value=1,
        offset_unit="days",
        is_active=True,
    )
    async_session.add(config)
    await async_session.flush()
    inst = ReminderInstance(
        config_id=config.id,
        organization_id=org_id,
        entity_type=entity_type,
        entity_id=entity_id,
        scheduled_at=scheduled_at or (utcnow_naive() - timedelta(minutes=5)),
        status="PENDING",
        attempt_count=attempt_count,
    )
    async_session.add(inst)
    await async_session.commit()
    return inst


@pytest.mark.asyncio
async def test_process_due_reminders_sends_due_whatsapp_template(async_session, monkeypatch):
    org = await seed_org(async_session)
    policy = await seed_policy(async_session, org_id=org.id)
    scheduled_at = utcnow_naive() - timedelta(minutes=5)
    inst = await _add_due_instance(
        async_session,
        org_id=org.id,
        entity_type="policy",
        entity_id=policy.id,
        channel="whatsapp",
        scheduled_at=scheduled_at,
    )
    config = await async_session.get(ReminderConfig, inst.config_id)
    assert config is not None
    config.entity_label = "Car Insurance Renewal"
    config.sender_name = "ABC Insurance"
    await async_session.commit()

    captured: dict[str, object] = {}

    async def _ok_send(self, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(status="sent")

    monkeypatch.setattr(
        "app.services.channel_service.ChannelService.send_outbound_message",
        _ok_send,
    )

    service = ReminderProcessorService(async_session)
    result = await service.process_due_reminders(org.id)
    assert result == {"processed": 1, "sent": 1, "failed": 0}
    assert captured["recipient"] == "+919876543210"
    settings = get_settings()
    assert captured["template_name"] == settings.whatsapp_template_name
    assert captured["template_language"] == settings.whatsapp_template_language
    template_variables = captured["template_variables"]
    assert template_variables == {
        "customer_name": "Ravi Kumar",
        "entity_label": "Car Insurance Renewal",
        "reminder_date": scheduled_at.strftime("%d-%m-%Y %I:%M %p"),
        "sender_name": "ABC Insurance",
    }

    refreshed = await async_session.get(ReminderInstance, inst.id)
    assert refreshed is not None
    assert refreshed.status == "SENT"


@pytest.mark.asyncio
async def test_process_due_reminders_whatsapp_defaults_entity_label_and_sender_name(async_session, monkeypatch):
    org = await seed_org(async_session)
    policy = await seed_policy(async_session, org_id=org.id)
    await _add_due_instance(
        async_session,
        org_id=org.id,
        entity_type="policy",
        entity_id=policy.id,
        channel="whatsapp",
    )

    captured: dict[str, object] = {}

    async def _ok_send(self, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(status="sent")

    monkeypatch.setattr(
        "app.services.channel_service.ChannelService.send_outbound_message",
        _ok_send,
    )

    service = ReminderProcessorService(async_session)
    await service.process_due_reminders(org.id)

    template_variables = captured["template_variables"]
    assert template_variables["entity_label"] == "Policy Renewal"
    assert template_variables["sender_name"] == org.name


@pytest.mark.asyncio
async def test_process_due_reminders_sends_due_non_whatsapp_text(async_session, monkeypatch):
    org = await seed_org(async_session)
    policy = await seed_policy(async_session, org_id=org.id)
    inst = await _add_due_instance(
        async_session,
        org_id=org.id,
        entity_type="policy",
        entity_id=policy.id,
        channel="telegram",
    )

    captured: dict[str, str] = {}

    async def _ok_send(self, **kwargs):
        captured["recipient"] = kwargs["recipient"]
        captured["text"] = kwargs["text"]
        return SimpleNamespace(status="sent")

    monkeypatch.setattr(
        "app.services.channel_service.ChannelService.send_outbound_message",
        _ok_send,
    )

    service = ReminderProcessorService(async_session)
    result = await service.process_due_reminders(org.id)
    assert result == {"processed": 1, "sent": 1, "failed": 0}
    assert captured["recipient"] == "+919876543210"
    assert "Ravi Kumar" in captured["text"]
    assert "POL-GEN-001" in captured["text"]

    refreshed = await async_session.get(ReminderInstance, inst.id)
    assert refreshed is not None
    assert refreshed.status == "SENT"
    assert refreshed.sent_at is not None


@pytest.mark.asyncio
async def test_process_due_reminders_ignores_future(async_session, monkeypatch):
    org = await seed_org(async_session)
    policy = await seed_policy(async_session, org_id=org.id)
    inst = await _add_due_instance(
        async_session,
        org_id=org.id,
        entity_type="policy",
        entity_id=policy.id,
        scheduled_at=utcnow_naive() + timedelta(hours=2),
    )

    async def _ok_send(self, **kwargs):
        return SimpleNamespace(status="sent")

    monkeypatch.setattr(
        "app.services.channel_service.ChannelService.send_outbound_message",
        _ok_send,
    )

    service = ReminderProcessorService(async_session)
    result = await service.process_due_reminders(org.id)
    assert result == {"processed": 0, "sent": 0, "failed": 0}

    refreshed = await async_session.get(ReminderInstance, inst.id)
    assert refreshed is not None
    assert refreshed.status == "PENDING"


@pytest.mark.asyncio
async def test_process_due_reminders_marks_failed_on_exception(async_session, monkeypatch):
    org = await seed_org(async_session)
    policy = await seed_policy(async_session, org_id=org.id)
    inst = await _add_due_instance(
        async_session,
        org_id=org.id,
        entity_type="policy",
        entity_id=policy.id,
        channel="whatsapp",
    )

    async def _boom(self, **kwargs):
        raise RuntimeError("provider down")

    monkeypatch.setattr(
        "app.services.channel_service.ChannelService.send_outbound_message",
        _boom,
    )

    service = ReminderProcessorService(async_session)
    result = await service.process_due_reminders(org.id)
    assert result == {"processed": 1, "sent": 0, "failed": 1}

    refreshed = await async_session.get(ReminderInstance, inst.id)
    assert refreshed is not None
    assert refreshed.status == "FAILED"
    assert refreshed.last_error == "provider down"


@pytest.mark.asyncio
async def test_process_due_reminders_increments_attempt_count(async_session, monkeypatch):
    org = await seed_org(async_session)
    policy = await seed_policy(async_session, org_id=org.id)
    inst = await _add_due_instance(
        async_session,
        org_id=org.id,
        entity_type="policy",
        entity_id=policy.id,
        channel="telegram",
        attempt_count=2,
    )

    async def _boom(self, **kwargs):
        raise RuntimeError("network error")

    monkeypatch.setattr(
        "app.services.channel_service.ChannelService.send_outbound_message",
        _boom,
    )

    service = ReminderProcessorService(async_session)
    await service.process_due_reminders(org.id)

    refreshed = await async_session.get(ReminderInstance, inst.id)
    assert refreshed is not None
    assert refreshed.attempt_count == 3


@pytest.mark.asyncio
async def test_process_due_reminders_cancels_renewed_policy(async_session, monkeypatch):
    org = await seed_org(async_session)
    policy = await seed_policy(async_session, org_id=org.id)
    policy.status = "renewed"
    await async_session.commit()

    inst = await _add_due_instance(
        async_session,
        org_id=org.id,
        entity_type="policy",
        entity_id=policy.id,
        channel="whatsapp",
    )

    async def _should_not_send(self, **kwargs):
        raise AssertionError("send should not be called for renewed policies")

    monkeypatch.setattr(
        "app.services.channel_service.ChannelService.send_outbound_message",
        _should_not_send,
    )

    service = ReminderProcessorService(async_session)
    result = await service.process_due_reminders(org.id)
    assert result == {"processed": 1, "sent": 0, "failed": 0}

    refreshed = await async_session.get(ReminderInstance, inst.id)
    assert refreshed is not None
    assert refreshed.status == "CANCELED"


@pytest.mark.asyncio
async def test_process_due_reminders_unsupported_entity_type(async_session):
    org = await seed_org(async_session)
    inst = await _add_due_instance(
        async_session,
        org_id=org.id,
        entity_type="unknown_module",
        entity_id=1,
    )

    service = ReminderProcessorService(async_session)
    result = await service.process_due_reminders(org.id)
    assert result == {"processed": 1, "sent": 0, "failed": 1}

    refreshed = await async_session.get(ReminderInstance, inst.id)
    assert refreshed is not None
    assert refreshed.status == "FAILED"
    assert "unsupported entity type" in (refreshed.last_error or "")


@pytest.mark.asyncio
async def test_resolve_entity_returns_policy_fields_via_resolver(async_session):
    org = await seed_org(async_session)
    policy = await seed_policy(async_session, org_id=org.id, mobile_number="919014757457")
    inst = ReminderInstance(
        config_id=1,
        organization_id=org.id,
        entity_type="policy",
        entity_id=policy.id,
        scheduled_at=utcnow_naive(),
        status="PENDING",
    )

    service = ReminderProcessorService(async_session)
    entity = await service.resolve_entity(inst)

    assert entity.customer_name == "Ravi Kumar"
    assert entity.recipient == "919014757457"
    assert entity.reference_id == "POL-GEN-001"
    assert entity.anchor_date == policy.expiry_date


@pytest.mark.asyncio
async def test_process_due_reminders_entity_not_found(async_session):
    org = await seed_org(async_session)
    inst = await _add_due_instance(
        async_session,
        org_id=org.id,
        entity_type="policy",
        entity_id=999999,
    )

    service = ReminderProcessorService(async_session)
    result = await service.process_due_reminders(org.id)
    assert result == {"processed": 1, "sent": 0, "failed": 1}

    refreshed = await async_session.get(ReminderInstance, inst.id)
    assert refreshed is not None
    assert refreshed.status == "FAILED"
    assert refreshed.last_error == "entity not found"


@pytest.mark.asyncio
async def test_process_due_reminders_missing_phone_number(async_session):
    org = await seed_org(async_session)
    policy = await seed_policy(async_session, org_id=org.id, mobile_number=None)
    inst = await _add_due_instance(
        async_session,
        org_id=org.id,
        entity_type="policy",
        entity_id=policy.id,
    )

    service = ReminderProcessorService(async_session)
    result = await service.process_due_reminders(org.id)
    assert result == {"processed": 1, "sent": 0, "failed": 1}

    refreshed = await async_session.get(ReminderInstance, inst.id)
    assert refreshed is not None
    assert refreshed.status == "FAILED"
    assert refreshed.last_error == "missing recipient phone number"


@pytest.mark.asyncio
async def test_process_due_reminders_uses_db_now_when_app_utc_is_stale(async_session, monkeypatch):
    """Due check must follow DB clock, not Python UTC, to avoid IST/UTC drift."""
    org = await seed_org(async_session)
    policy = await seed_policy(async_session, org_id=org.id)
    db_now = datetime(2026, 7, 4, 15, 0, 0)
    scheduled_at = db_now - timedelta(minutes=10)
    inst = await _add_due_instance(
        async_session,
        org_id=org.id,
        entity_type="policy",
        entity_id=policy.id,
        channel="telegram",
        scheduled_at=scheduled_at,
    )

    async def fake_db_now(_session):
        return db_now

    monkeypatch.setattr("app.services.reminder_processor.fetch_db_now", fake_db_now)
    monkeypatch.setattr(
        "app.utils.datetime_utils.utcnow_naive",
        lambda: db_now - timedelta(hours=6),
    )

    captured: dict[str, str] = {}

    async def _ok_send(self, **kwargs):
        captured["text"] = kwargs["text"]
        return SimpleNamespace(status="sent")

    monkeypatch.setattr(
        "app.services.channel_service.ChannelService.send_outbound_message",
        _ok_send,
    )

    service = ReminderProcessorService(async_session)
    result = await service.process_due_reminders(org.id)
    assert result == {"processed": 1, "sent": 1, "failed": 0}

    refreshed = await async_session.get(ReminderInstance, inst.id)
    assert refreshed is not None
    assert refreshed.status == "SENT"
    assert refreshed.sent_at == db_now


@pytest.mark.asyncio
async def test_process_due_reminders_ignores_future_relative_to_db_now(async_session, monkeypatch):
    org = await seed_org(async_session)
    policy = await seed_policy(async_session, org_id=org.id)
    db_now = datetime(2026, 7, 4, 15, 0, 0)
    await _add_due_instance(
        async_session,
        org_id=org.id,
        entity_type="policy",
        entity_id=policy.id,
        scheduled_at=db_now + timedelta(hours=1),
    )

    async def fake_db_now(_session):
        return db_now

    monkeypatch.setattr("app.services.reminder_processor.fetch_db_now", fake_db_now)

    async def _ok_send(self, **kwargs):
        return SimpleNamespace(status="sent")

    monkeypatch.setattr(
        "app.services.channel_service.ChannelService.send_outbound_message",
        _ok_send,
    )

    service = ReminderProcessorService(async_session)
    result = await service.process_due_reminders(org.id)
    assert result == {"processed": 0, "sent": 0, "failed": 0}
