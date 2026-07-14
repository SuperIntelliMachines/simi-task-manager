from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.database import get_db_session
from app.main import app
from app.models.core import Organization, User
from app.models.verticals import InsuranceLead, InsurancePolicy
from tests.helpers.sqlite_task import SQLITE_BIGINT_PK_TABLES, patch_sqlite_session_bigint_ids


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def seed_org(async_session) -> Organization:
    org = Organization(
        name=f"API Insurance Org {uuid4().hex[:8]}",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(org)
    await async_session.flush()
    return org


async def seed_user(async_session, organization_id: int) -> User:
    user = User(
        organization_id=organization_id,
        email=f"api-agent-{uuid4().hex[:8]}@example.com",
        hashed_password="x",
        is_active=True,
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(user)
    await async_session.flush()
    return user


@pytest.fixture
async def insurance_client(async_session) -> AsyncGenerator[AsyncClient, None]:
    patch_sqlite_session_bigint_ids(
        async_session,
        start_id=8800 + (uuid4().int % 1_000_000),
        table_names=SQLITE_BIGINT_PK_TABLES,
    )

    async def override_session():
        yield async_session

    app.dependency_overrides[get_db_session] = override_session
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_insurance_policy_crud_and_workflow_api(insurance_client, async_session):
    org = await seed_org(async_session)
    agent = await seed_user(async_session, org.id)
    await async_session.commit()

    create_response = await insurance_client.post(
        "/api/v1/insurance/policies",
        json={
            "organization_id": org.id,
            "actor_user_id": agent.id,
            "policyholder_name": "Ravi",
            "premium": 3200,
            "policy_type": "auto",
            "carrier": "carrier-a",
            "assigned_agent_user_id": agent.id,
            "preferred_channel": ["whatsapp"],
            "expiry_date": (utcnow_naive() + timedelta(days=20)).isoformat(),
        },
    )
    assert create_response.status_code == 200
    policy_id = create_response.json()["id"]

    list_response = await insurance_client.get(f"/api/v1/insurance/policies?organization_id={org.id}")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    patch_response = await insurance_client.patch(
        f"/api/v1/insurance/policies/{policy_id}",
        json={"status": "active", "premium": 3500},
    )
    assert patch_response.status_code == 200
    assert int(patch_response.json()["premium"]) == 3500

    workflow_response = await insurance_client.post(
        f"/api/v1/insurance/policies/{policy_id}/renewal-workflow",
        json={"actor_user_id": agent.id},
    )
    assert workflow_response.status_code == 200
    assert len(workflow_response.json()["reminders"]) == 0

    policy = (await async_session.execute(select(InsurancePolicy).where(InsurancePolicy.id == policy_id))).scalar_one()
    assert policy.preferred_channel == ["whatsapp"]


@pytest.mark.asyncio
async def test_create_policy_duplicate_policy_number_returns_409(insurance_client, async_session):
    org = await seed_org(async_session)
    agent = await seed_user(async_session, org.id)
    await async_session.commit()

    policy_number = f"POL-DUP-{uuid4().hex[:8]}"
    payload = {
        "organization_id": org.id,
        "actor_user_id": agent.id,
        "policyholder_name": "Duplicate Holder",
        "policy_number": policy_number,
        "mobile_number": "9876543210",
        "premium": 1000,
        "policy_type": "auto",
        "carrier": "carrier-a",
        "expiry_date": (utcnow_naive() + timedelta(days=20)).isoformat(),
    }

    first = await insurance_client.post("/api/v1/insurance/policies", json=payload)
    assert first.status_code == 200

    second = await insurance_client.post("/api/v1/insurance/policies", json=payload)
    assert second.status_code == 409
    assert second.json()["detail"] == "Policy number already exists."

    policies = list(
        (await async_session.execute(select(InsurancePolicy).where(InsurancePolicy.policy_number == policy_number))).scalars()
    )
    assert len(policies) == 1


@pytest.mark.asyncio
async def test_insurance_lead_followup_and_dashboard_api(insurance_client, async_session):
    org = await seed_org(async_session)
    agent = await seed_user(async_session, org.id)
    await async_session.commit()

    expired_policy_response = await insurance_client.post(
        "/api/v1/insurance/policies",
        json={
            "organization_id": org.id,
            "actor_user_id": agent.id,
            "policyholder_name": "Expired Customer",
            "premium": 1000,
            "policy_type": "health",
            "carrier": "carrier-b",
            "preferred_channel": ["telegram"],
            "expiry_date": (utcnow_naive() - timedelta(days=1)).isoformat(),
        },
    )
    assert expired_policy_response.status_code == 200

    due_policy_response = await insurance_client.post(
        "/api/v1/insurance/policies",
        json={
            "organization_id": org.id,
            "actor_user_id": agent.id,
            "policyholder_name": "Due Customer",
            "premium": 1200,
            "policy_type": "auto",
            "carrier": "carrier-c",
            "preferred_channel": ["whatsapp"],
            "expiry_date": (utcnow_naive() + timedelta(days=5)).isoformat(),
        },
    )
    assert due_policy_response.status_code == 200

    lead_response = await insurance_client.post(
        "/api/v1/insurance/leads",
        json={
            "organization_id": org.id,
            "actor_user_id": agent.id,
            "contact_name": "Priya",
            "assigned_agent_user_id": agent.id,
            "source": "demo",
            "notes": "Interested after demo",
        },
    )
    assert lead_response.status_code == 200
    lead_id = lead_response.json()["id"]

    followup_response = await insurance_client.post(
        f"/api/v1/insurance/leads/{lead_id}/follow-up-workflow",
        json={"actor_user_id": agent.id, "days_until_followup": 3},
    )
    assert followup_response.status_code == 200
    assert followup_response.json()["lead"]["status"] == "follow_up_pending"

    reschedule_at = utcnow_naive() + timedelta(days=7)
    reschedule_response = await insurance_client.patch(
        f"/api/v1/insurance/leads/{lead_id}",
        json={"actor_user_id": agent.id, "status": "follow_up_later", "followup_due_at": reschedule_at.isoformat()},
    )
    assert reschedule_response.status_code == 200
    assert reschedule_response.json()["status"] == "follow_up_later"

    dashboard_response = await insurance_client.get(f"/api/v1/insurance/dashboard?organization_id={org.id}")
    assert dashboard_response.status_code == 200
    payload = dashboard_response.json()
    assert payload["counts"]["due_renewals"] == 1
    assert payload["counts"]["expired_policies"] == 1
    assert payload["counts"]["pending_followups"] == 1
    assert payload["counts"]["due_followups"] == 0
    assert payload["counts"]["overdue_followups"] == 0

    close_response = await insurance_client.patch(
        f"/api/v1/insurance/leads/{lead_id}",
        json={"actor_user_id": agent.id, "status": "not_interested"},
    )
    assert close_response.status_code == 200
    lead = (await async_session.execute(select(InsuranceLead).where(InsuranceLead.id == lead_id))).scalar_one()
    assert lead.status == "not_interested"
