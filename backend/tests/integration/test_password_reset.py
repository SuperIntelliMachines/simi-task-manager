"""Integration tests for password reset flow."""

from __future__ import annotations

from datetime import timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.database import get_db_session
from app.core.security import get_password_hash, verify_password
from app.main import app
from app.models.auth_security import PasswordResetToken
from app.models.core import Organization, User
from app.services.auth_security_service import AuthSecurityService, utcnow_naive
from tests.helpers.auth import utcnow_naive as helper_utcnow


@pytest.fixture
async def reset_client(async_session):
    async def override_session():
        yield async_session

    app.dependency_overrides[get_db_session] = override_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client, async_session
    app.dependency_overrides.clear()


async def _seed_user(session, *, email: str = "reset-user@test.com", password: str = "OldPass123") -> User:
    org = Organization(name=f"Reset Org {email}", created_at=helper_utcnow(), updated_at=helper_utcnow())
    session.add(org)
    await session.flush()
    user = User(
        organization_id=org.id,
        email=email,
        hashed_password=get_password_hash(password),
        is_active=True,
        role="tenant_user",
        failed_login_attempts=2,
        locked_until=helper_utcnow() + timedelta(minutes=5),
        created_at=helper_utcnow(),
        updated_at=helper_utcnow(),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_valid_password_reset_request_returns_dev_token(reset_client):
    client, session = reset_client
    await _seed_user(session, email="valid-reset@test.com")

    response = await client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "valid-reset@test.com"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "If the account exists" in body["detail"]
    assert body["reset_token"]
    assert body["reset_url"]
    assert "token=" in body["reset_url"]


@pytest.mark.asyncio
async def test_invalid_email_does_not_reveal_account(reset_client):
    client, _session = reset_client
    response = await client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "missing-user@test.com"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "If the account exists" in body["detail"]
    assert body.get("reset_token") is None
    assert body.get("reset_url") is None


@pytest.mark.asyncio
async def test_expired_token_is_rejected(reset_client):
    client, session = reset_client
    user = await _seed_user(session, email="expired-token@test.com")
    security = AuthSecurityService(session)
    raw = await security.create_password_reset_token(user)
    await session.commit()

    result = await session.execute(
        select(PasswordResetToken).where(PasswordResetToken.user_id == user.id)
    )
    token_row = result.scalar_one()
    token_row.expires_at = utcnow_naive() - timedelta(minutes=1)
    await session.commit()

    response = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": raw, "new_password": "NewPass123"},
    )
    assert response.status_code == 400
    assert "Invalid or expired" in response.json()["detail"]


@pytest.mark.asyncio
async def test_invalid_token_is_rejected(reset_client):
    client, _session = reset_client
    response = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": "not-a-real-token", "new_password": "NewPass123"},
    )
    assert response.status_code == 400
    assert "Invalid or expired" in response.json()["detail"]


@pytest.mark.asyncio
async def test_successful_password_reset_and_login(reset_client):
    client, session = reset_client
    user = await _seed_user(session, email="success-reset@test.com", password="OldPass123")

    request = await client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "success-reset@test.com"},
    )
    assert request.status_code == 200
    token = request.json()["reset_token"]
    assert token

    confirm = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": token, "new_password": "NewPass456"},
    )
    assert confirm.status_code == 200
    assert confirm.json()["detail"] == "Password reset successfully"

    await session.refresh(user)
    assert user.failed_login_attempts == 0
    assert user.locked_until is None
    assert verify_password("NewPass456", user.hashed_password)

    login_new = await client.post(
        "/api/v1/auth/token",
        json={"email": "success-reset@test.com", "password": "NewPass456"},
    )
    assert login_new.status_code == 200
    assert login_new.json()["access_token"]

    login_old = await client.post(
        "/api/v1/auth/token",
        json={"email": "success-reset@test.com", "password": "OldPass123"},
    )
    assert login_old.status_code == 401


@pytest.mark.asyncio
async def test_reset_token_is_single_use(reset_client):
    client, session = reset_client
    await _seed_user(session, email="single-use@test.com", password="OldPass123")

    request = await client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "single-use@test.com"},
    )
    token = request.json()["reset_token"]

    first = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": token, "new_password": "NewPass789"},
    )
    assert first.status_code == 200

    second = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": token, "new_password": "AnotherPass1"},
    )
    assert second.status_code == 400
