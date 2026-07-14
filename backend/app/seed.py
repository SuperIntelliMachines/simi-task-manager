from sqlalchemy.ext.asyncio import AsyncSession
from app.models.core import Organization, User
from datetime import UTC, datetime


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)

async def seed_data(session: AsyncSession):
    # Create organization
    organization = Organization(
        name="SIMI",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    session.add(organization)
    await session.flush()

    # Create admin user
    admin_user = User(
        organization_id=organization.id,
        email="admin@example.com",
        hashed_password="hashed_password_here",
        is_active=True,
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    session.add(admin_user)
    await session.commit()