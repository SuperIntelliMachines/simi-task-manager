from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.models.atm017 import NotificationPreference
from app.models.core import Contact, Organization, User
from app.services.notification_preference_service import NotificationPreferenceService


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def seed_org_user_contact(async_session):
    org = Organization(name=f"Org A {uuid4().hex[:8]}", created_at=utcnow_naive(), updated_at=utcnow_naive())
    async_session.add(org)
    await async_session.flush()

    user = User(
        organization_id=org.id,
        email="owner@orga.test",
        hashed_password="x",
        is_active=True,
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(user)
    await async_session.flush()

    contact = Contact(
        organization_id=org.id,
        name="John",
        email="john@example.com",
        phone="+1999",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(contact)
    await async_session.flush()

    pref = NotificationPreference(
        organization_id=org.id,
        user_id=None,
        contact_id=contact.id,
        purpose="renewal",
        preferred_channel="whatsapp",
        fallback_channel="telegram",
        opt_out=False,
        quiet_hours_start=22,
        quiet_hours_end=6,
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(pref)
    await async_session.commit()

    return org, user, contact, pref


@pytest.mark.asyncio
async def test_contact_opt_out_prevents_external_reminder(async_session):
    org, _, contact, pref = await seed_org_user_contact(async_session)
    service = NotificationPreferenceService(async_session)

    await service.update_preference(pref.id, {"opt_out": True})
    channel = await service.choose_channel(
        organization_id=org.id,
        purpose="renewal",
        contact_id=contact.id,
        current_hour=10,
    )
    assert channel is None


@pytest.mark.asyncio
async def test_quiet_hours_delays_non_urgent_reminder(async_session):
    org, _, contact, _ = await seed_org_user_contact(async_session)
    service = NotificationPreferenceService(async_session)

    channel = await service.choose_channel(
        organization_id=org.id,
        purpose="renewal",
        contact_id=contact.id,
        current_hour=23,
        urgent=False,
    )
    assert channel == "telegram"
