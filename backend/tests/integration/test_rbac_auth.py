"""Integration tests for RBAC and auth security."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db_session
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models.core import Organization, User
from tests.helpers.auth import auth_header, seed_authenticated_context, utcnow_naive


@pytest.fixture
async def rbac_client(async_session):
    async def override_session():
        yield async_session

    app.dependency_overrides[get_db_session] = override_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_login_returns_access_and_refresh_token(rbac_client, async_session):
    org = Organization(name="RBAC Org", created_at=utcnow_naive(), updated_at=utcnow_naive())
    async_session.add(org)
    await async_session.flush()
    user = User(
        organization_id=org.id,
        email="rbac-login@test.com",
        hashed_password=get_password_hash("secret123"),
        is_active=True,
        role="tenant_user",
        failed_login_attempts=0,
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(user)
    await async_session.commit()

    response = await rbac_client.post(
        "/api/v1/auth/token",
        json={"email": "rbac-login@test.com", "password": "secret123"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["refresh_token"]


@pytest.mark.asyncio
async def test_swagger_oauth2_form_login_accepts_username_as_email(rbac_client, async_session):
    """Swagger Authorize uses OAuth2PasswordRequestForm (username/password form)."""
    org = Organization(name="Swagger Auth Org", created_at=utcnow_naive(), updated_at=utcnow_naive())
    async_session.add(org)
    await async_session.flush()
    user = User(
        organization_id=org.id,
        email="swagger-login@test.com",
        hashed_password=get_password_hash("secret123"),
        is_active=True,
        role="tenant_user",
        failed_login_attempts=0,
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(user)
    await async_session.commit()

    # JSON body against the OAuth2 form endpoint must fail validation (422),
    # matching the original Swagger mismatch against /auth/token.
    json_mismatch = await rbac_client.post(
        "/api/v1/auth/token/swagger",
        json={"email": "swagger-login@test.com", "password": "secret123"},
    )
    assert json_mismatch.status_code == 422

    response = await rbac_client.post(
        "/api/v1/auth/token/swagger",
        data={"username": "swagger-login@test.com", "password": "secret123"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"

    me = await rbac_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == "swagger-login@test.com"


@pytest.mark.asyncio
async def test_me_returns_permissions(rbac_client, async_session):
    _org, user, headers = await seed_authenticated_context(async_session, role="viewer")
    response = await rbac_client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "viewer"
    assert "insurance:view" in body["permissions"]
    assert "insurance:create" not in body["permissions"]


@pytest.mark.asyncio
async def test_viewer_forbidden_on_insurance_create(rbac_client, async_session):
    org, user, headers = await seed_authenticated_context(async_session, role="viewer")
    response = await rbac_client.post(
        "/api/v1/insurance/policies",
        headers=headers,
        json={
            "organization_id": org.id,
            "policyholder_name": "Test",
            "policy_number": "POL-1",
            "expiry_date": "2027-01-01",
            "premium": "1000",
            "policy_type": "motor",
            "carrier": "Test Carrier",
        },
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_request_returns_401(rbac_client):
    response = await rbac_client.get("/api/v1/tasks?organization_id=1")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_rotation(rbac_client, async_session):
    org = Organization(name="Refresh Org", created_at=utcnow_naive(), updated_at=utcnow_naive())
    async_session.add(org)
    await async_session.flush()
    user = User(
        organization_id=org.id,
        email="refresh@test.com",
        hashed_password=get_password_hash("secret123"),
        is_active=True,
        role="platform_admin",
        failed_login_attempts=0,
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(user)
    await async_session.commit()

    login = await rbac_client.post(
        "/api/v1/auth/token",
        json={"email": "refresh@test.com", "password": "secret123"},
    )
    refresh_token = login.json()["refresh_token"]
    refreshed = await rbac_client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"]
    assert refreshed.json()["refresh_token"] != refresh_token


@pytest.mark.asyncio
async def test_organization_isolation_on_tasks(rbac_client, async_session):
    org_a, user_a, headers_a = await seed_authenticated_context(async_session, role="manager")
    org_b = Organization(name="Other Org", created_at=utcnow_naive(), updated_at=utcnow_naive())
    async_session.add(org_b)
    await async_session.commit()

    response = await rbac_client.get(
        f"/api/v1/tasks?organization_id={org_b.id}",
        headers=headers_a,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_org_admin_can_create_admin_console_user_with_users_permissions(rbac_client, async_session):
    org, _user, headers = await seed_authenticated_context(async_session, role="org_admin")
    response = await rbac_client.post(
        "/api/v1/admin/users",
        headers=headers,
        json={
            "email": "new-admin-console-user@test.com",
            "password": "secret123",
            "organization_id": org.id,
            "role": "tenant_user",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "new-admin-console-user@test.com"
    assert body["organization_id"] == org.id
    assert body["role"] == "tenant_user"
