import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.core import Organization, User
from datetime import UTC, datetime


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)

@pytest.mark.asyncio
async def test_create_organization(async_session: AsyncSession):
    organization = Organization(
        name="Test Organization",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(organization)
    await async_session.commit()

    assert organization.id is not None

@pytest.mark.asyncio
async def test_create_user(async_session: AsyncSession):
    organization = Organization(
        name="Test Organization",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(organization)
    await async_session.flush()

    user = User(
        organization_id=organization.id,
        email="user@example.com",
        hashed_password="hashed_password_here",
        is_active=True,
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(user)
    await async_session.commit()

    assert user.id is not None