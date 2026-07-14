from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.models.core import Contact, Organization
from app.models.verticals import InsurancePolicy
from app.services.insurance_messaging import send_policy_channel_message


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@pytest.mark.asyncio
async def test_send_policy_channel_message_whatsapp_uses_four_template_params(async_session, monkeypatch):
    org = Organization(
        name="ABC Insurance",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(org)
    await async_session.flush()

    contact = Contact(
        id=9101,
        organization_id=org.id,
        name="Ravi Kumar",
        email="ravi@example.com",
        phone="919876543210",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(contact)
    await async_session.flush()

    reminder_date = utcnow_naive() + timedelta(days=10)
    policy = InsurancePolicy(
        id=9201,
        organization_id=org.id,
        policyholder_id=contact.id,
        policy_number="POL-WA-001",
        premium=1000,
        policy_type="health",
        carrier="Carrier",
        preferred_channel=["whatsapp"],
        mobile_number="919876543210",
        expiry_date=reminder_date,
        status="active",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(policy)
    await async_session.commit()

    captured: dict[str, object] = {}

    class FakeChannelService:
        def __init__(self, session):
            self.session = session

        async def list_connections(self, organization_id):
            return [
                SimpleNamespace(
                    id=1,
                    channel="whatsapp",
                    status="active",
                    settings={},
                )
            ]

        async def send_outbound_message(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(status="sent")

    monkeypatch.setattr(
        "app.services.insurance_messaging.ChannelService",
        FakeChannelService,
    )
    monkeypatch.setattr(
        "app.services.insurance_messaging._whatsapp_delivery_available",
        lambda connection: True,
    )

    success, error = await send_policy_channel_message(
        async_session,
        organization_id=org.id,
        policy=policy,
        contact=contact,
        channel="whatsapp",
        message="fallback text",
        sender_name="Agent Name",
        reminder_date=reminder_date,
    )

    assert success is True
    assert error is None
    assert captured["template_name"] == "policy_renewal_reminder"
    assert captured["template_language"] == "en_US"
    assert captured["template_variables"] == {
        "customer_name": "Ravi Kumar",
        "entity_label": "Policy Renewal",
        "reminder_date": reminder_date.strftime("%d-%m-%Y %I:%M %p"),
        "sender_name": "Agent Name",
    }

    body_params = captured["template_variables"]
    assert list(body_params.keys()) == [
        "customer_name",
        "entity_label",
        "reminder_date",
        "sender_name",
    ]
