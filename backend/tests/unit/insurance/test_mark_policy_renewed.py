from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.core import Organization
from app.models.insurance import PolicyReminder
from app.services.insurance_service import InsuranceService, build_renewal_confirmation_message


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@pytest.mark.asyncio
async def test_build_renewal_confirmation_message():
    message = build_renewal_confirmation_message(
        customer_name="Ravi",
        policy_number="POL-123",
    )
    assert "Dear Ravi," in message
    assert "POL-123" in message
    assert "renewed successfully" in message


@pytest.mark.asyncio
async def test_cancel_renewal_policy_reminders_handles_processing(async_session):
    org = Organization(
        name=f"Renew Org {uuid4().hex[:8]}",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(org)
    await async_session.flush()

    from app.models.core import Contact
    from app.models.verticals import InsurancePolicy

    contact = Contact(
        id=1101,
        organization_id=org.id,
        name="Anita",
        phone="+919999888777",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(contact)
    await async_session.flush()

    now = utcnow_naive()
    policy = InsurancePolicy(
        id=2101,
        organization_id=org.id,
        policyholder_id=contact.id,
        policy_number="POL-PROC",
        premium=1200,
        policy_type="auto",
        carrier="carrier-d",
        preferred_channel=["sms"],
        expiry_date=now + timedelta(days=15),
        status="active",
        created_at=now,
        updated_at=now,
    )
    async_session.add(policy)
    await async_session.flush()

    async_session.add(
        PolicyReminder(
            id=3101,
            policy_id=policy.id,
            organization_id=org.id,
            reminder_at=now + timedelta(days=5),
            stage=-5,
            channel="sms",
            status="PROCESSING",
            attempt_count=1,
        )
    )
    async_session.add(
        PolicyReminder(
            id=3102,
            policy_id=policy.id,
            organization_id=org.id,
            reminder_at=now - timedelta(days=1),
            stage=0,
            channel="sms",
            status="SENT",
            attempt_count=1,
            sent_at=now - timedelta(days=1),
        )
    )
    await async_session.commit()

    service = InsuranceService(async_session)
    cancelled = await service._cancel_renewal_policy_reminders(policy)
    await async_session.commit()

    assert cancelled == 1
    rows = list(
        (await async_session.execute(select(PolicyReminder).where(PolicyReminder.policy_id == policy.id))).scalars()
    )
    by_id = {row.id: row for row in rows}
    assert by_id[3101].status == "CANCELED"
    assert by_id[3102].status == "SENT"
