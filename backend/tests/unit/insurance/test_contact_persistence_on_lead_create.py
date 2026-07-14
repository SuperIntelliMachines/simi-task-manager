from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.core import Contact, Organization
from app.services.insurance_service import InsuranceService


def utcnow_naive() -> datetime:
    from datetime import UTC

    return datetime.now(UTC).replace(tzinfo=None)


async def seed_org(async_session) -> Organization:
    org = Organization(
        name=f"Contact Org {uuid4().hex[:8]}",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(org)
    await async_session.flush()
    return org


@pytest.mark.asyncio
async def test_create_lead_persists_contact_name_phone_email(async_session):
    org = await seed_org(async_session)
    await async_session.commit()
    service = InsuranceService(async_session)

    await service.create_lead(
        organization_id=org.id,
        contact_name="Sanju",
        actor_user_id=None,
        source="demo",
        contact_phone="9876543210",
        contact_email="sanju@gmail.com",
        insurance_type="health",
        demo_logged_at=utcnow_naive(),
    )

    contact = (
        await async_session.execute(
            select(Contact).where(
                Contact.organization_id == org.id,
                Contact.name.ilike("Sanju"),
            )
        )
    ).scalar_one()

    assert contact.name == "Sanju"
    assert contact.phone == "9876543210"
    assert contact.email == "sanju@gmail.com"
