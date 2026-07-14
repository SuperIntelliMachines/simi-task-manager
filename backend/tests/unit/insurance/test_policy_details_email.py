from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.api.v1.endpoints.insurance import _attach_contact_fields
from app.models.core import Contact, Organization
from app.models.verticals import InsurancePolicy
from app.schemas.insurance import PolicyResponse


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _sample_policy(*, policyholder_id: int, email: str | None = None) -> InsurancePolicy:
    now = utcnow_naive()
    return InsurancePolicy(
        id=1001,
        organization_id=10,
        policyholder_id=policyholder_id,
        policy_number="pol-1432",
        premium=1000,
        policy_type="Health",
        carrier="HDFC Ergo",
        assigned_agent_user_id=None,
        preferred_channel=["email"],
        mobile_number="9121529697",
        email=email,
        document_name=None,
        document_path=None,
        expiry_date=now,
        status="active",
        created_at=now,
        updated_at=now,
    )


def test_policy_response_includes_email_from_policy_column():
    policy = _sample_policy(policyholder_id=20, email="kanithiudaykumar324@gmail.com")
    setattr(policy, "policyholder_name", "Kuday")

    response = PolicyResponse.model_validate(policy)

    assert response.email == "kanithiudaykumar324@gmail.com"
    assert response.policyholder_name == "Kuday"


def test_policy_response_email_defaults_to_none_without_contact():
    policy = _sample_policy(policyholder_id=20)

    response = PolicyResponse.model_validate(policy)

    assert response.email is None


@pytest.mark.asyncio
async def test_attach_contact_fields_sets_policyholder_email(async_session):
    org = Organization(
        name=f"Policy Email Org {uuid4().hex[:8]}",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(org)
    await async_session.flush()

    now = utcnow_naive()
    contact = Contact(
        id=8001,
        organization_id=org.id,
        name="Kuday",
        email="kanithiudaykumar324@gmail.com",
        phone="9121529697",
        created_at=now,
        updated_at=now,
    )
    async_session.add(contact)
    await async_session.flush()

    policy = InsurancePolicy(
        id=8002,
        organization_id=org.id,
        policyholder_id=contact.id,
        policy_number="pol-1432",
        premium=1000,
        policy_type="Health",
        carrier="HDFC Ergo",
        assigned_agent_user_id=None,
        preferred_channel=["email"],
        mobile_number="9121529697",
        email="kanithiudaykumar324@gmail.com",
        document_name=None,
        document_path=None,
        expiry_date=now,
        status="active",
        created_at=now,
        updated_at=now,
    )
    async_session.add(policy)
    await async_session.commit()

    await _attach_contact_fields(async_session, policy)

    assert policy.policyholder_name == "Kuday"
    assert policy.email == "kanithiudaykumar324@gmail.com"
    assert policy.mobile == "9121529697"

    response = PolicyResponse.model_validate(policy)
    assert response.email == "kanithiudaykumar324@gmail.com"


@pytest.mark.asyncio
async def test_attach_contact_fields_leaves_email_none_when_contact_has_no_email(async_session):
    org = Organization(
        name=f"No Email Policy Org {uuid4().hex[:8]}",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(org)
    await async_session.flush()

    now = utcnow_naive()
    contact = Contact(
        id=8003,
        organization_id=org.id,
        name="No Email Holder",
        email=None,
        phone="9121529697",
        created_at=now,
        updated_at=now,
    )
    async_session.add(contact)
    await async_session.flush()

    policy = InsurancePolicy(
        id=8004,
        organization_id=org.id,
        policyholder_id=contact.id,
        policy_number="pol-1433",
        premium=500,
        policy_type=None,
        carrier=None,
        assigned_agent_user_id=None,
        preferred_channel=None,
        mobile_number="9121529697",
        document_name=None,
        document_path=None,
        expiry_date=now,
        status="active",
        created_at=now,
        updated_at=now,
    )
    async_session.add(policy)
    await async_session.commit()

    await _attach_contact_fields(async_session, policy)

    assert getattr(policy, "email", None) is None
    response = PolicyResponse.model_validate(policy)
    assert response.email is None
