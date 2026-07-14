from datetime import UTC, datetime
from decimal import Decimal

from app.models.verticals import InsurancePolicy
from app.schemas.insurance import PolicyCreate, PolicyResponse, PolicyUpdate


def test_policy_response_includes_document_fields():
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
        document_name="policy.pdf",
        document_path="/uploads/org-10/policy.pdf",
        expiry_date=now,
        status="active",
        created_at=now,
        updated_at=now,
    )

    response = PolicyResponse.model_validate(policy)

    assert response.document_name == "policy.pdf"
    assert response.document_path == "/uploads/org-10/policy.pdf"


def test_policy_create_and_update_accept_optional_document_fields():
    now = datetime.now(UTC).replace(tzinfo=None)

    create = PolicyCreate(
        policyholder_name="Ravi",
        policy_number="POL-002",
        expiry_date=now,
        document_name="cover.pdf",
        document_path="/uploads/cover.pdf",
    )
    assert create.document_name == "cover.pdf"
    assert create.document_path == "/uploads/cover.pdf"

    update = PolicyUpdate(document_name="updated.pdf", document_path="/uploads/updated.pdf")
    assert update.document_name == "updated.pdf"
    assert update.document_path == "/uploads/updated.pdf"


def test_policy_response_defaults_document_fields_to_none():
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
        document_name=None,
        document_path=None,
        expiry_date=now,
        status="active",
        created_at=now,
        updated_at=now,
    )

    response = PolicyResponse.model_validate(policy)

    assert response.document_name is None
    assert response.document_path is None
    assert response.premium == Decimal(500)
