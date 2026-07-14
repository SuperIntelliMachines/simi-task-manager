from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.integrations.telegram.customer_onboarding import CustomerTelegramOnboardingService
from app.models.core import Contact, Organization
from app.models.verticals import InsurancePolicy


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@pytest.mark.asyncio
async def test_customer_onboarding_start_prompts_for_mobile(async_session):
    service = CustomerTelegramOnboardingService()
    reply = await service.handle_payload(
        session=async_session,
        payload={
            "message": {
                "text": "/start",
                "chat": {"id": 12345},
                "from": {"first_name": "Asha", "username": "asha_customer"},
            }
        },
    )
    assert reply is not None
    assert "registered mobile number" in reply


@pytest.mark.asyncio
async def test_customer_onboarding_links_policy_by_mobile(async_session):
    org = Organization(
        name=f"Customer TG Org {uuid4().hex[:8]}",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(org)
    await async_session.flush()

    contact = Contact(
        id=9101,
        organization_id=org.id,
        name="Customer One",
        email="customer@example.com",
        phone="+919876543210",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(contact)
    await async_session.flush()

    policy = InsurancePolicy(
        id=9201,
        organization_id=org.id,
        policyholder_id=contact.id,
        policy_number=f"POL-CUST-{uuid4().hex[:4]}",
        premium=1000,
        policy_type="health",
        carrier="Carrier",
        preferred_channel=["telegram"],
        mobile_number="919876543210",
        expiry_date=utcnow_naive() + timedelta(days=30),
        status="active",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(policy)
    await async_session.commit()

    service = CustomerTelegramOnboardingService()
    await service.handle_payload(
        session=async_session,
        payload={"message": {"text": "hi", "chat": {"id": 9876543}, "from": {"username": "cust_user"}}},
    )
    reply = await service.handle_payload(
        session=async_session,
        payload={
            "message": {
                "text": "+91 98765 43210",
                "chat": {"id": 9876543},
                "from": {"username": "cust_user"},
            }
        },
    )

    assert reply == "Thanks! Your Telegram chat is linked. You will now receive policy reminders here."
    updated = (
        await async_session.execute(select(InsurancePolicy).where(InsurancePolicy.id == policy.id))
    ).scalar_one()
    assert updated.telegram_chat_id == 9876543
    assert updated.telegram_username == "cust_user"


@pytest.mark.asyncio
async def test_customer_onboarding_normalizes_mobile_formats(async_session):
    org = Organization(
        name=f"Customer TG Org {uuid4().hex[:8]}",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(org)
    await async_session.flush()

    contact = Contact(
        id=9102,
        organization_id=org.id,
        name="Customer Two",
        email="customer2@example.com",
        phone="+919121529697",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(contact)
    await async_session.flush()

    policy = InsurancePolicy(
        id=9202,
        organization_id=org.id,
        policyholder_id=contact.id,
        policy_number=f"POL-CUST-{uuid4().hex[:4]}",
        premium=1000,
        policy_type="health",
        carrier="Carrier",
        preferred_channel=["telegram"],
        mobile_number="919121529697",
        expiry_date=utcnow_naive() + timedelta(days=30),
        status="active",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(policy)
    await async_session.commit()

    service = CustomerTelegramOnboardingService()
    await service.handle_payload(
        session=async_session,
        payload={"message": {"text": "/start", "chat": {"id": 88776655}, "from": {"username": "cust_user_2"}}},
    )
    reply = await service.handle_payload(
        session=async_session,
        payload={
            "message": {
                "text": "09121529697",
                "chat": {"id": 88776655},
                "from": {"username": "cust_user_2"},
            }
        },
    )

    assert reply == "Thanks! Your Telegram chat is linked. You will now receive policy reminders here."
