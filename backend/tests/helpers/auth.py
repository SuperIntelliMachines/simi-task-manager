"""Auth helpers for backend tests."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.core.security import create_access_token
from app.models.core import Organization, User
from app.seeds.rbac_seed import seed_rbac


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def seed_org(async_session, *, name: str | None = None) -> Organization:
    org = Organization(
        name=name or f"Test Org {uuid4().hex[:8]}",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(org)
    await async_session.flush()
    return org


async def seed_user(
    async_session,
    *,
    organization_id: int,
    email: str | None = None,
    role: str = "platform_admin",
) -> User:
    user = User(
        organization_id=organization_id,
        email=email or f"user-{uuid4().hex[:8]}@test.com",
        hashed_password="x",
        is_active=True,
        role=role,
        failed_login_attempts=0,
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(user)
    await async_session.flush()
    return user


async def seed_rbac_if_needed(async_session) -> None:
    await seed_rbac(async_session)


def auth_header(user_id: int) -> dict[str, str]:
    token = create_access_token(str(user_id))
    return {"Authorization": f"Bearer {token}"}


async def seed_authenticated_context(
    async_session,
    *,
    role: str = "platform_admin",
) -> tuple[Organization, User, dict[str, str]]:
    await seed_rbac_if_needed(async_session)
    org = await seed_org(async_session)
    user = await seed_user(async_session, organization_id=org.id, role=role)
    await async_session.commit()
    return org, user, auth_header(user.id)
