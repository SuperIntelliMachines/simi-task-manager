from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db_session
from app.main import app


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def seed_org(async_session):
    from app.models.core import Organization

    org = Organization(
        name=f"Followup Org {uuid4().hex[:8]}",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(org)
    await async_session.flush()
    return org


async def seed_user(async_session, organization_id: int):
    from app.models.core import User

    user = User(
        organization_id=organization_id,
        email=f"followup-agent-{uuid4().hex[:8]}@example.com",
        hashed_password="x",
        is_active=True,
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(user)
    await async_session.flush()
    return user


@pytest.fixture
async def followup_client(async_session) -> AsyncGenerator[AsyncClient, None]:
    async def override_session():
        yield async_session

    app.dependency_overrides[get_db_session] = override_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_followup_related_policy_and_assigned_agent_persist(followup_client, async_session):
    org = await seed_org(async_session)
    agent = await seed_user(async_session, org.id)
    await async_session.commit()

    # create a policy via API so a contact exists
    expiry_iso = (utcnow_naive() + timedelta(days=30)).replace(tzinfo=UTC).isoformat()
    create_resp = await followup_client.post(
        "/api/v1/insurance/policies",
        json={
            "organization_id": org.id,
            "actor_user_id": agent.id,
            "policyholder_name": "Followup Holder",
            "premium": 5000,
            "policy_type": "home",
            "carrier": "CarrierY",
            "assigned_agent_user_id": agent.id,
            "preferred_channel": "email",
            "expiry_date": expiry_iso,
        },
    )
    assert create_resp.status_code == 200
    policy = create_resp.json()
    policy_id = policy["id"]
    policyholder_id = policy["policyholder_id"]

    # create followup referencing the policy and assigned agent
    follow_resp = await followup_client.post(
        f"/api/v1/insurance/followups?organization_id={org.id}",
        json={
            "related_policy_id": policy_id,
            "contact_id": policyholder_id,
            "assigned_agent_id": agent.id,
            "status": "open",
        },
    )
    assert follow_resp.status_code == 201
    body = follow_resp.json()
    assert body["related_policy_id"] == policy_id
    # schema exposes assigned_agent_user_id now
    assert body.get("assigned_agent_user_id") == agent.id
*** End Patch