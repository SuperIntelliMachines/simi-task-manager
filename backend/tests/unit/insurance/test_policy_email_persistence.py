from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.core import Contact, Organization
from app.models.verticals import InsurancePolicy
from app.services.insurance_service import InsuranceService


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def test_insurance_policy_model_includes_email_column():
    now = utcnow_naive()
    policy = InsurancePolicy(
        id=9104,
        organization_id=1,
        policyholder_id=9101,
        policy_number="POL-EMAIL-DB-001",
        premium=0,
        policy_type=None,
        carrier=None,
        assigned_agent_user_id=None,
        preferred_channel=None,
        mobile_number="9876543210",
        email="test@gmail.com",
        document_name=None,
        document_path=None,
        expiry_date=now,
        status="active",
        created_at=now,
        updated_at=now,
    )

    assert policy.email == "test@gmail.com"


@pytest.mark.asyncio
async def test_update_policy_syncs_email_to_policy_and_contact(async_session):
    org = Organization(
        name=f"Update Email Org {uuid4().hex[:8]}",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(org)
    await async_session.flush()

    now = utcnow_naive()
    contact = Contact(
        id=9102,
        organization_id=org.id,
        name="Update Holder",
        email="old@example.com",
        phone="9876543210",
        created_at=now,
        updated_at=now,
    )
    async_session.add(contact)
    await async_session.flush()

    policy = InsurancePolicy(
        id=9103,
        organization_id=org.id,
        policyholder_id=contact.id,
        policy_number="POL-UPDATE-EMAIL",
        premium=1000,
        policy_type="Health",
        carrier="HDFC Ergo",
        assigned_agent_user_id=None,
        preferred_channel=None,
        mobile_number="9876543210",
        email="old@example.com",
        document_name=None,
        document_path=None,
        expiry_date=now + timedelta(days=30),
        status="active",
        created_at=now,
        updated_at=now,
    )
    async_session.add(policy)
    await async_session.commit()

    service = InsuranceService(async_session)
    updated = await service.update_policy(policy.id, {"email": "test@gmail.com"})

    assert updated.email == "test@gmail.com"

    stored_policy = (
        await async_session.execute(select(InsurancePolicy).where(InsurancePolicy.id == policy.id))
    ).scalar_one()
    assert stored_policy.email == "test@gmail.com"

    stored_contact = (
        await async_session.execute(select(Contact).where(Contact.id == contact.id))
    ).scalar_one()
    assert stored_contact.email == "test@gmail.com"
