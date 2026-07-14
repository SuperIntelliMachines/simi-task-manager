from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.database import get_db_session
from app.main import app
from app.models.core import Organization, User, Reminder


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def seed_org(async_session) -> Organization:
    org = Organization(
        name=f"API Consistency Org {uuid4().hex[:8]}",
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
    async def override_session():
        yield async_session

    app.dependency_overrides[get_db_session] = override_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_premium_consistency_and_timezone_normalization(insurance_client, async_session):
    org = await seed_org(async_session)
    agent = await seed_user(async_session, org.id)
    await async_session.commit()

    # Create policy with premium in cents and timezone-aware expiry_date
    expiry_iso = (utcnow_naive() + timedelta(days=30)).replace(tzinfo=UTC).isoformat()
    create_resp = await insurance_client.post(
        "/api/v1/insurance/policies",
        json={
            "organization_id": org.id,
            "actor_user_id": agent.id,
            "policyholder_name": "Consistency Test",
            "premium": 5000,  # cents
            "policy_type": "auto",
            "carrier": "CarrierX",
            "assigned_agent_user_id": agent.id,
            "preferred_channel": ["whatsapp"],
            "expiry_date": expiry_iso,
        },
    )
    assert create_resp.status_code == 200
    body = create_resp.json()
    # API should return premium as user-facing decimal (5000 cents -> 50.00)
    assert float(body["premium"]) == 50.0
    policy_id = body["id"]

    # GET list
    list_resp = await insurance_client.get(f"/api/v1/insurance/policies?organization_id={org.id}")
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert len(items) >= 1
    assert float(items[0]["premium"]) == 50.0

    # GET single
    get_resp = await insurance_client.get(f"/api/v1/insurance/policies/{policy_id}")
    assert get_resp.status_code == 200
    got = get_resp.json()
    assert float(got["premium"]) == 50.0

    # expiry_date should be normalized (no timezone offset in returned ISO)
    returned_expiry = got["expiry_date"]
    assert returned_expiry.startswith(expiry_iso[:19])

    # Update premium via PUT using Decimal value (50.0) -> API accepts Decimal, PolicyService will convert
    put_resp = await insurance_client.put(
        f"/api/v1/insurance/policies/{policy_id}",
        params={"actor_user_id": agent.id},
        json={"premium": 75.0},
    )
    assert put_resp.status_code == 200
    updated = put_resp.json()
    assert float(updated["premium"]) == 75.0

    # Renew policy should return same premium
    renew_resp = await insurance_client.post(f"/api/v1/insurance/policies/{policy_id}/renew")
    assert renew_resp.status_code == 200
    renewed = renew_resp.json()
    assert float(renewed["premium"]) == 75.0
