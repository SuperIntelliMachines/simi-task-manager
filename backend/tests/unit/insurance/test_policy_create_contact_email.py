from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from app.models.core import Contact, Organization
from app.schemas.atm007 import InsurancePolicyCreateBody
from app.schemas.insurance import PolicyCreate, PolicyUpdate
from app.services.insurance_service import InsuranceService
from app.services.policy_service import PolicyService


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def seed_org(async_session) -> Organization:
    org = Organization(
        name=f"Email Policy Org {uuid4().hex[:8]}",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(org)
    await async_session.flush()
    return org


@pytest.mark.asyncio
async def test_resolve_contact_persists_email_on_existing_contact(async_session):
    org = await seed_org(async_session)
    now = utcnow_naive()
    contact = Contact(
        id=9001,
        organization_id=org.id,
        name="Email Holder",
        email=None,
        phone="9876543210",
        created_at=now,
        updated_at=now,
    )
    async_session.add(contact)
    await async_session.commit()

    service = InsuranceService(async_session)
    resolved, created = await service._resolve_contact(
        organization_id=org.id,
        name="Email Holder",
        allow_create=True,
        phone="9876543210",
        email="holder@example.com",
    )

    assert created is False
    assert resolved.id == contact.id
    assert resolved.email == "holder@example.com"


@pytest.mark.asyncio
async def test_resolve_contact_leaves_email_null_when_not_provided(async_session):
    org = await seed_org(async_session)
    now = utcnow_naive()
    contact = Contact(
        id=9002,
        organization_id=org.id,
        name="No Email Holder",
        email=None,
        phone="9123456789",
        created_at=now,
        updated_at=now,
    )
    async_session.add(contact)
    await async_session.commit()

    service = InsuranceService(async_session)
    resolved, created = await service._resolve_contact(
        organization_id=org.id,
        name="No Email Holder",
        allow_create=True,
        phone="9123456789",
        email=None,
    )

    assert created is False
    assert resolved.email is None

    stored = (
        await async_session.execute(select(Contact).where(Contact.id == contact.id))
    ).scalar_one()
    assert stored.email is None


@pytest.mark.asyncio
async def test_policy_service_forwards_contact_email(async_session):
    service = PolicyService(async_session)
    now = utcnow_naive()
    mock_policy = MagicMock(premium=0)

    with patch.object(
        InsuranceService,
        "create_policy",
        new=AsyncMock(return_value=mock_policy),
    ) as create_policy:
        await service.create_policy(
            organization_id=1,
            policyholder_name="Email Holder",
            policy_number="POL-EMAIL-001",
            expiry_date=now + timedelta(days=30),
            contact_phone="9876543210",
            contact_email="holder@example.com",
        )

    create_policy.assert_awaited_once()
    assert create_policy.await_args.kwargs["contact_email"] == "holder@example.com"
    assert create_policy.await_args.kwargs["contact_phone"] == "9876543210"


def test_insurance_policy_create_body_accepts_optional_email():
    now = utcnow_naive()
    body = InsurancePolicyCreateBody(
        organization_id=1,
        policyholder_name="Ravi",
        policy_number="POL-EMAIL-002",
        expiry_date=now,
        email="ravi@example.com",
    )
    assert body.email == "ravi@example.com"


def test_insurance_policy_create_body_rejects_invalid_email():
    now = utcnow_naive()
    with pytest.raises(ValidationError):
        InsurancePolicyCreateBody(
            organization_id=1,
            policyholder_name="Ravi",
            policy_number="POL-EMAIL-003",
            expiry_date=now,
            email="invalid-email",
        )


def test_policy_create_and_update_accept_optional_email():
    now = utcnow_naive()

    create = PolicyCreate(
        policyholder_name="Ravi",
        policy_number="POL-EMAIL-004",
        expiry_date=now,
        email="ravi@example.com",
    )
    assert create.email == "ravi@example.com"

    update = PolicyUpdate(email="updated@example.com")
    assert update.email == "updated@example.com"
