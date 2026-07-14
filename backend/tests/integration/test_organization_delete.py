"""Integration tests for organization delete behavior."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db_session
from app.main import app
from app.models.core import Contact, Organization, User
from tests.helpers.auth import seed_authenticated_context, utcnow_naive


@pytest.fixture
async def admin_client(async_session):
    org, _user, headers = await seed_authenticated_context(async_session, role="platform_admin")

    async def override_session():
        yield async_session

    app.dependency_overrides[get_db_session] = override_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client, async_session, headers, org
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_delete_organization_with_no_users_succeeds(admin_client):
    client, session, headers, _admin_org = admin_client

    empty_org = Organization(
        name="Empty Org For Delete",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    session.add(empty_org)
    await session.commit()
    await session.refresh(empty_org)

    response = await client.delete(f"/api/v1/admin/customers/{empty_org.id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["detail"] == "Organization deleted"

    remaining = await session.get(Organization, empty_org.id)
    assert remaining is None


@pytest.mark.asyncio
async def test_delete_organization_with_related_contacts_returns_structured_409(admin_client):
    client, session, headers, _admin_org = admin_client

    org = Organization(
        name="Org With Contacts",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    session.add(org)
    await session.flush()
    session.add(
        Contact(
            id=9001,
            organization_id=org.id,
            name="Blocking Contact",
            email="contact@example.com",
            created_at=utcnow_naive(),
            updated_at=utcnow_naive(),
        )
    )
    await session.commit()
    await session.refresh(org)

    response = await client.delete(f"/api/v1/admin/customers/{org.id}", headers=headers)
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["error"] == "organization_has_dependencies"
    assert "related business data" in detail["message"].lower()
    assert detail["dependencies"] == [{"label": "Contacts", "count": 1}]
    assert "contacts" not in str(detail["dependencies"])

    remaining = await session.get(Organization, org.id)
    assert remaining is not None


@pytest.mark.asyncio
async def test_delete_organization_with_users_returns_structured_409(admin_client):
    client, session, headers, _admin_org = admin_client

    org = Organization(
        name="Org With Users",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    session.add(org)
    await session.flush()
    session.add(
        User(
            organization_id=org.id,
            email="org-user@test.com",
            hashed_password="x",
            is_active=True,
            role="tenant_user",
            failed_login_attempts=0,
            created_at=utcnow_naive(),
            updated_at=utcnow_naive(),
        )
    )
    await session.commit()
    await session.refresh(org)

    response = await client.delete(f"/api/v1/admin/customers/{org.id}", headers=headers)
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["error"] == "organization_has_dependencies"
    assert detail["dependencies"] == [{"label": "Users", "count": 1}]
    assert "users" not in str(detail["dependencies"])
