from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.models.core import Contact, Organization
from app.models.verticals import InsurancePolicy
from app.services.insurance_service import InsuranceService


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@pytest.mark.asyncio
async def test_send_policy_renewal_sms_whatsapp_routes_through_send_policy_channel_message(
    async_session, monkeypatch
):
    org = Organization(
        name=f"Renewal SMS Org {uuid4().hex[:8]}",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(org)
    await async_session.flush()

    contact = Contact(
        id=8101,
        organization_id=org.id,
        name="WhatsApp Holder",
        email="holder@example.com",
        phone="919014757457",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(contact)
    await async_session.flush()

    now = utcnow_naive()
    policy = InsurancePolicy(
        id=8201,
        organization_id=org.id,
        policyholder_id=contact.id,
        policy_number="POL-WA-001",
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

    calls: list[dict] = []

    async def fake_send(session, **kwargs):
        calls.append(kwargs)
        return True, None

    monkeypatch.setattr(
        "app.services.insurance_service.send_policy_channel_message",
        fake_send,
    )

    service = InsuranceService(async_session)
    result = await service.send_policy_renewal_sms(
        policy_id=policy.id,
        logged_in_user_name="Agent Name",
    )

    assert result["mode"] == "sent"
    assert len(calls) == 1
    assert calls[0]["channel"] == "whatsapp"
    assert calls[0]["policy"].id == policy.id
    assert calls[0]["contact"].id == contact.id
    assert "policy renewal is due soon" not in calls[0]["message"].lower()
    assert calls[0]["message"] == "Policy renewal reminder"
