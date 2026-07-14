from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.channels.mock_adapter import MockAdapter
from app.models.atm005 import ContactChannelIdentity
from app.models.atm017 import OutboundMessage
from app.models.core import Contact, Organization
from app.services.channel_service import ChannelService


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def seed_org_contact(async_session):
    org = Organization(
        name=f"Org A {uuid4().hex[:8]}",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(org)
    await async_session.flush()

    contact = Contact(
        organization_id=org.id,
        name="John",
        email="john@example.com",
        phone="+1001",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(contact)
    await async_session.commit()
    return org, contact


@pytest.mark.asyncio
async def test_mock_adapter_can_be_used(async_session):
    org, _ = await seed_org_contact(async_session)
    service = ChannelService(
        async_session,
        telegram_adapter=MockAdapter("telegram"),
        whatsapp_adapter=MockAdapter("whatsapp"),
    )

    row = await service.send_outbound_message(
        organization_id=org.id,
        channel="telegram",
        recipient="123",
        text="hello",
    )
    assert row.status == "sent"


@pytest.mark.asyncio
async def test_outbound_send_failure_records_provider_error(async_session):
    org, _ = await seed_org_contact(async_session)

    class FailingAdapter(MockAdapter):
        async def send_outbound_message(self, **kwargs):
            raise RuntimeError("provider down")

    service = ChannelService(
        async_session,
        telegram_adapter=FailingAdapter("telegram"),
        whatsapp_adapter=MockAdapter("whatsapp"),
    )

    row = await service.send_outbound_message(
        organization_id=org.id,
        channel="telegram",
        recipient="123",
        text="hello",
    )
    assert row.status == "failed"


@pytest.mark.asyncio
async def test_opt_out_stops_future_external_reminders(async_session):
    org, contact = await seed_org_contact(async_session)
    service = ChannelService(
        async_session,
        telegram_adapter=MockAdapter("telegram"),
        whatsapp_adapter=MockAdapter("whatsapp"),
    )

    identity = ContactChannelIdentity(
        organization_id=org.id,
        contact_id=contact.id,
        user_id=None,
        channel="whatsapp",
        external_user_id="wa-user-1",
        external_chat_id="wa-user-1",
        display_name="John",
        is_opted_out=True,
        last_inbound_at=None,
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(identity)
    await async_session.commit()

    with pytest.raises(PermissionError):
        await service.send_outbound_message(
            organization_id=org.id,
            channel="whatsapp",
            recipient="wa-user-1",
            text="hello",
            contact_id=contact.id,
        )


class FixedProviderAdapter(MockAdapter):
    def __init__(self, channel_name: str, provider_id: str):
        super().__init__(channel_name)
        self.provider_id = provider_id

    async def send_outbound_message(self, **kwargs):
        await super().send_outbound_message(**kwargs)
        return self.provider_id


@pytest.mark.asyncio
async def test_duplicate_provider_message_id_skips_second_insert(async_session, monkeypatch):
    async def noop_audit(*_args, **_kwargs):
        return None

    monkeypatch.setattr("app.services.channel_service.write_audit_event", noop_audit)

    org = Organization(
        name=f"Org Dup {uuid4().hex[:8]}",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(org)
    await async_session.commit()
    provider_id = "wamid.duplicate-test-1"
    adapter = FixedProviderAdapter("whatsapp", provider_id)
    service = ChannelService(async_session, whatsapp_adapter=adapter)

    first = await service.send_outbound_message(
        organization_id=org.id,
        channel="whatsapp",
        recipient="919876543210",
        text="hello",
    )
    second = await service.send_outbound_message(
        organization_id=org.id,
        channel="whatsapp",
        recipient="919876543210",
        text="hello again",
    )

    assert first.status == "sent"
    assert second.status == "sent"
    assert first.id == second.id
    assert second.external_provider_message_id == provider_id

    count = await async_session.scalar(
        select(func.count())
        .select_from(OutboundMessage)
        .where(
            OutboundMessage.channel == "whatsapp",
            OutboundMessage.external_provider_message_id == provider_id,
        )
    )
    assert count == 1

