from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models.verticals import InsurancePolicy
from app.schemas.insurance import PolicyCreate, PolicyResponse, PolicyUpdate
from app.schemas.atm007 import InsurancePolicyCreateBody, InsurancePolicyPatchBody


def test_policy_response_includes_mobile_number():
    now = datetime.now(UTC).replace(tzinfo=None)
    policy = InsurancePolicy(
        id=1,
        organization_id=10,
        policyholder_id=20,
        policy_number="POL-001",
        premium=1000,
        policy_type="Health",
        carrier="CarrierA",
        assigned_agent_user_id=None,
        preferred_channel=["telegram"],
        mobile_number="9876543210",
        document_name=None,
        document_path=None,
        expiry_date=now,
        status="active",
        created_at=now,
        updated_at=now,
    )

    response = PolicyResponse.model_validate(policy)

    assert response.mobile_number == "9876543210"


def test_policy_create_and_update_accept_mobile_number():
    now = datetime.now(UTC).replace(tzinfo=None)

    create = PolicyCreate(
        policyholder_name="Ravi",
        policy_number="POL-002",
        expiry_date=now,
        mobile_number="+919876543210",
    )
    assert create.mobile_number == "+919876543210"

    update = PolicyUpdate(mobile_number="9876543210")
    assert update.mobile_number == "9876543210"


def test_policy_response_defaults_mobile_number_to_none():
    now = datetime.now(UTC).replace(tzinfo=None)
    policy = InsurancePolicy(
        id=2,
        organization_id=10,
        policyholder_id=20,
        policy_number="POL-003",
        premium=500,
        policy_type=None,
        carrier=None,
        assigned_agent_user_id=None,
        preferred_channel=None,
        mobile_number=None,
        document_name=None,
        document_path=None,
        expiry_date=now,
        status="active",
        created_at=now,
        updated_at=now,
    )

    response = PolicyResponse.model_validate(policy)

    assert response.mobile_number is None


@pytest.mark.parametrize(
    "mobile_number",
    [
        "98765abcde",
        "123456789",
        "1234567890123456",
    ],
)
def test_policy_create_rejects_invalid_mobile_number(mobile_number: str):
    now = datetime.now(UTC).replace(tzinfo=None)
    with pytest.raises(ValidationError):
        PolicyCreate(
            policyholder_name="Ravi",
            policy_number="POL-004",
            expiry_date=now,
            mobile_number=mobile_number,
        )


@pytest.mark.parametrize(
    "mobile_number",
    [
        "98765abcde",
    ],
)
def test_policy_update_rejects_invalid_mobile_number(mobile_number: str):
    with pytest.raises(ValidationError):
        PolicyUpdate(mobile_number=mobile_number)


def test_insurance_policy_create_body_accepts_international_mobile_number():
    now = datetime.now(UTC).replace(tzinfo=None)
    body = InsurancePolicyCreateBody(
        organization_id=1,
        policyholder_name="Ravi",
        policy_number="POL-005",
        expiry_date=now,
        mobile_number="+919876543210",
    )
    assert body.mobile_number == "+919876543210"


def test_insurance_policy_create_body_validates_mobile_number():
    now = datetime.now(UTC).replace(tzinfo=None)
    body = InsurancePolicyCreateBody(
        organization_id=1,
        policyholder_name="Ravi",
        policy_number="POL-005",
        expiry_date=now,
        mobile_number="9876543210",
    )
    assert body.mobile_number == "9876543210"


def test_insurance_policy_patch_body_rejects_invalid_mobile_number():
    with pytest.raises(ValidationError):
        InsurancePolicyPatchBody(mobile_number="98765abcde")


def test_insurance_policy_patch_body_normalizes_dashed_mobile_number():
    body = InsurancePolicyPatchBody(mobile_number="98-7654-3210")
    assert body.mobile_number == "9876543210"
