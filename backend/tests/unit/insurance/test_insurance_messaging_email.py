from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.channels.mock_adapter import MockAdapter
from app.jobs.policy_reminder_jobs import process_due_policy_reminders
from app.models.core import Contact, Organization
from app.models.insurance import PolicyReminder
from app.models.verticals import InsurancePolicy
from app.services.channel_service import ChannelService
from app.services.insurance_messaging import send_policy_channel_message


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def noop_audit(*_args, **_kwargs):
    return None


async def fake_telegram_connection(*_args, **_kwargs):
    return type(
        "Conn",
        (),
        {"settings": {"botToken": "test-token"}, "channel": "telegram", "status": "active"},
    )()


def _channel_service_factory(email_adapter: MockAdapter):
    def factory(session, **kwargs):
        return ChannelService(
            session,
            telegram_adapter=kwargs.get("telegram_adapter") or MockAdapter("telegram"),
            whatsapp_adapter=kwargs.get("whatsapp_adapter") or MockAdapter("whatsapp"),
            email_adapter=email_adapter,
        )

    return factory


@pytest.mark.asyncio
async def test_send_policy_channel_message_uses_email_when_channel_is_email(async_session, monkeypatch):
    org = Organization(
        name=f"Email Messaging Org {uuid4().hex[:8]}",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(org)
    await async_session.flush()

    contact = Contact(
        id=7101,
        organization_id=org.id,
        name="Email Holder",
        email="holder@example.com",
        phone="+919999999999",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(contact)
    await async_session.flush()

    now = utcnow_naive()
    policy = InsurancePolicy(
        id=7201,
        organization_id=org.id,
        policyholder_id=contact.id,
        policy_number="POL-EMAIL-001",
        premium=1000,
        policy_type="health",
        carrier="Carrier",
        preferred_channel=["whatsapp"],
        expiry_date=now + timedelta(days=10),
        status="active",
        created_at=now,
        updated_at=now,
    )
    async_session.add(policy)
    await async_session.commit()

    email_adapter = MockAdapter("email")
    monkeypatch.setattr(
        "app.services.insurance_messaging.ChannelService",
        _channel_service_factory(email_adapter),
    )
    monkeypatch.setattr("app.services.channel_service.write_audit_event", noop_audit)

    success, error = await send_policy_channel_message(
        async_session,
        organization_id=org.id,
        policy=policy,
        contact=contact,
        channel="email",
        message="Premium due message",
    )

    assert success is True
    assert error is None
    assert len(email_adapter.sent) == 1
    assert email_adapter.sent[0]["recipient"] == "holder@example.com"
    assert email_adapter.sent[0]["text"] == "Premium due message"


@pytest.mark.asyncio
async def test_send_policy_channel_message_returns_failure_when_whatsapp_unavailable(
    async_session, monkeypatch
):
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "")
    from app.core.config import get_settings
    get_settings.cache_clear()

    org = Organization(
        name=f"Email Fallback Org {uuid4().hex[:8]}",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(org)
    await async_session.flush()

    contact = Contact(
        id=7102,
        organization_id=org.id,
        name="Fallback Holder",
        email="fallback@example.com",
        phone="+919888888888",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(contact)
    await async_session.flush()

    now = utcnow_naive()
    policy = InsurancePolicy(
        id=7202,
        organization_id=org.id,
        policyholder_id=contact.id,
        policy_number="POL-FALLBACK-001",
        premium=1000,
        policy_type="auto",
        carrier="Carrier",
        preferred_channel=["whatsapp"],
        expiry_date=now + timedelta(days=10),
        status="active",
        created_at=now,
        updated_at=now,
    )
    async_session.add(policy)
    await async_session.commit()

    email_adapter = MockAdapter("email")
    monkeypatch.setattr(
        "app.services.insurance_messaging.ChannelService",
        _channel_service_factory(email_adapter),
    )
    monkeypatch.setattr("app.services.channel_service.write_audit_event", noop_audit)

    success, error = await send_policy_channel_message(
        async_session,
        organization_id=org.id,
        policy=policy,
        contact=contact,
        channel="whatsapp",
        message="Premium due message",
    )

    assert success is False
    assert error == "no active whatsapp connection"
    assert len(email_adapter.sent) == 0
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_process_due_policy_reminder_email_channel_updates_sent_status(async_session, monkeypatch):
    org = Organization(
        name=f"Email Reminder Org {uuid4().hex[:8]}",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(org)
    await async_session.flush()

    contact = Contact(
        id=7103,
        organization_id=org.id,
        name="Reminder Email Holder",
        email="reminder@example.com",
        phone="+919777777777",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(contact)
    await async_session.flush()

    now = utcnow_naive()
    policy = InsurancePolicy(
        id=7203,
        organization_id=org.id,
        policyholder_id=contact.id,
        policy_number="POL-EMAIL-REM",
        premium=1500,
        policy_type="life",
        carrier="LIC",
        preferred_channel=["email"],
        expiry_date=now + timedelta(days=8),
        status="active",
        created_at=now,
        updated_at=now,
    )
    async_session.add(policy)
    await async_session.flush()

    reminder = PolicyReminder(
        id=7303,
        policy_id=policy.id,
        organization_id=org.id,
        reminder_at=now - timedelta(minutes=2),
        stage=-5,
        channel="email",
        status="PENDING",
        attempt_count=0,
    )
    async_session.add(reminder)
    await async_session.commit()

    email_adapter = MockAdapter("email")
    monkeypatch.setattr(
        "app.services.insurance_messaging.ChannelService",
        _channel_service_factory(email_adapter),
    )
    monkeypatch.setattr("app.services.channel_service.write_audit_event", noop_audit)
    monkeypatch.setattr("app.jobs.policy_reminder_jobs.write_audit_event", noop_audit)

    processed = (await process_due_policy_reminders(async_session, org.id)).processed

    assert processed == 1
    assert len(email_adapter.sent) == 1
    assert email_adapter.sent[0]["recipient"] == "reminder@example.com"

    row = (
        await async_session.execute(select(PolicyReminder).where(PolicyReminder.id == reminder.id))
    ).scalar_one()
    assert row.status == "SENT"
    assert row.sent_at is not None
    assert row.attempt_count == 1
    assert row.last_error is None


@pytest.mark.asyncio
async def test_process_multiple_due_policy_reminders_survives_outbound_commit(async_session, monkeypatch):
    org = Organization(
        name=f"Email Reminder Org {uuid4().hex[:8]}",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(org)
    await async_session.flush()

    contact = Contact(
        id=7104,
        organization_id=org.id,
        name="Multi Reminder Holder",
        email="multi@example.com",
        phone="+919666666666",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(contact)
    await async_session.flush()

    now = utcnow_naive()
    policy = InsurancePolicy(
        id=7204,
        organization_id=org.id,
        policyholder_id=contact.id,
        policy_number="POL-MULTI-REM",
        premium=1500,
        policy_type="life",
        carrier="LIC",
        preferred_channel=["email"],
        expiry_date=now + timedelta(days=8),
        status="active",
        created_at=now,
        updated_at=now,
    )
    async_session.add(policy)
    await async_session.flush()

    reminder_ids = []
    for index, (reminder_id, stage, reminder_type) in enumerate(
        [
            (7304, 30, "DUE_30_DAYS"),
            (7305, 10, "UPCOMING_10_DAYS"),
        ]
    ):
        async_session.add(
            PolicyReminder(
                id=reminder_id,
                policy_id=policy.id,
                organization_id=org.id,
                reminder_at=now - timedelta(minutes=1),
                stage=stage,
                reminder_type=reminder_type,
                channel="email",
                status="PENDING",
                attempt_count=0,
            )
        )
        reminder_ids.append(reminder_id)
    await async_session.commit()

    email_adapter = MockAdapter("email")
    monkeypatch.setattr(
        "app.services.insurance_messaging.ChannelService",
        _channel_service_factory(email_adapter),
    )
    monkeypatch.setattr("app.services.channel_service.write_audit_event", noop_audit)
    monkeypatch.setattr("app.jobs.policy_reminder_jobs.write_audit_event", noop_audit)

    processed = (await process_due_policy_reminders(async_session, org.id)).processed

    assert processed == 2
    assert len(email_adapter.sent) == 2

    rows = list(
        (
            await async_session.execute(
                select(PolicyReminder).where(PolicyReminder.id.in_(reminder_ids)).order_by(PolicyReminder.id)
            )
        ).scalars()
    )
    assert len(rows) == 2
    assert all(row.status == "SENT" for row in rows)
    assert all(row.sent_at is not None for row in rows)


@pytest.mark.asyncio
async def test_send_policy_channel_message_uses_telegram_adapter(async_session, monkeypatch):
    monkeypatch.setenv("TELEGRAM_CUSTOMER_BOT_TOKEN", "customer-test-token")
    monkeypatch.setenv("TELEGRAM_AGENT_BOT_TOKEN", "")
    from app.core.config import get_settings
    get_settings.cache_clear()

    org = Organization(
        name=f"Telegram Messaging Org {uuid4().hex[:8]}",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(org)
    await async_session.flush()

    contact = Contact(
        id=7105,
        organization_id=org.id,
        name="Telegram Holder",
        email="telegram@example.com",
        phone="+919555555555",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(contact)
    await async_session.flush()

    now = utcnow_naive()
    policy = InsurancePolicy(
        id=7205,
        organization_id=org.id,
        policyholder_id=contact.id,
        policy_number="POL-TG-001",
        premium=1000,
        policy_type="health",
        carrier="Carrier",
        preferred_channel=["telegram"],
        telegram_chat_id=123456789,
        expiry_date=now + timedelta(days=10),
        status="active",
        created_at=now,
        updated_at=now,
    )
    async_session.add(policy)
    await async_session.commit()

    telegram_adapter = MockAdapter("telegram")
    email_adapter = MockAdapter("email")

    def factory(session, **kwargs):
        return ChannelService(
            session,
            telegram_adapter=telegram_adapter,
            whatsapp_adapter=kwargs.get("whatsapp_adapter") or MockAdapter("whatsapp"),
            email_adapter=email_adapter,
        )

    monkeypatch.setattr("app.services.insurance_messaging.ChannelService", factory)
    monkeypatch.setattr("app.services.channel_service.write_audit_event", noop_audit)
    success, error = await send_policy_channel_message(
        async_session,
        organization_id=org.id,
        policy=policy,
        contact=contact,
        channel="telegram",
        message="Telegram premium due message",
    )

    assert success is True
    assert error is None
    assert len(telegram_adapter.sent) == 1
    assert telegram_adapter.sent[0]["recipient"] == "123456789"
    assert telegram_adapter.sent[0]["text"] == "Telegram premium due message"
    assert telegram_adapter.sent[0]["connection_settings"]["bot_token"] == "customer-test-token"

    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_process_due_policy_reminder_telegram_channel_updates_sent_status(async_session, monkeypatch):
    monkeypatch.setenv("TELEGRAM_CUSTOMER_BOT_TOKEN", "customer-test-token")
    monkeypatch.setenv("TELEGRAM_AGENT_BOT_TOKEN", "")
    from app.core.config import get_settings
    get_settings.cache_clear()

    org = Organization(
        name=f"Telegram Reminder Org {uuid4().hex[:8]}",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(org)
    await async_session.flush()

    contact = Contact(
        id=7106,
        organization_id=org.id,
        name="Telegram Reminder Holder",
        email="tg-reminder@example.com",
        phone="+919444444444",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(contact)
    await async_session.flush()

    now = utcnow_naive()
    policy = InsurancePolicy(
        id=7206,
        organization_id=org.id,
        policyholder_id=contact.id,
        policy_number="POL-TG-REM",
        premium=1500,
        policy_type="life",
        carrier="LIC",
        preferred_channel=["telegram"],
        telegram_chat_id=987654321,
        expiry_date=now + timedelta(days=8),
        status="active",
        created_at=now,
        updated_at=now,
    )
    async_session.add(policy)
    await async_session.flush()

    reminder = PolicyReminder(
        id=7306,
        policy_id=policy.id,
        organization_id=org.id,
        reminder_at=now - timedelta(minutes=2),
        stage=8,
        reminder_type="UPCOMING_10_DAYS",
        channel="telegram",
        status="PENDING",
        attempt_count=0,
    )
    async_session.add(reminder)
    await async_session.commit()

    telegram_adapter = MockAdapter("telegram")
    email_adapter = MockAdapter("email")

    def factory(session, **kwargs):
        return ChannelService(
            session,
            telegram_adapter=telegram_adapter,
            whatsapp_adapter=kwargs.get("whatsapp_adapter") or MockAdapter("whatsapp"),
            email_adapter=email_adapter,
        )

    monkeypatch.setattr("app.services.insurance_messaging.ChannelService", factory)
    monkeypatch.setattr("app.services.channel_service.write_audit_event", noop_audit)
    monkeypatch.setattr("app.jobs.policy_reminder_jobs.write_audit_event", noop_audit)
    processed = (await process_due_policy_reminders(async_session, org.id)).processed

    assert processed == 1
    assert len(telegram_adapter.sent) == 1
    assert telegram_adapter.sent[0]["recipient"] == "987654321"
    assert telegram_adapter.sent[0]["connection_settings"]["bot_token"] == "customer-test-token"

    row = (
        await async_session.execute(select(PolicyReminder).where(PolicyReminder.id == reminder.id))
    ).scalar_one()
    assert row.status == "SENT"
    assert row.sent_at is not None
    assert row.channel == "telegram"

    get_settings.cache_clear()
