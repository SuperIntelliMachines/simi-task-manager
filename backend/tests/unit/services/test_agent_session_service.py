from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.models.core import Organization
from app.services.agent_session_service import AgentSessionService


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def seed_org(async_session):
    org = Organization(name=f"Org A {uuid4().hex[:8]}", created_at=utcnow_naive(), updated_at=utcnow_naive())
    async_session.add(org)
    await async_session.commit()
    return org


@pytest.mark.asyncio
async def test_create_and_resume_session(async_session):
    org = await seed_org(async_session)
    service = AgentSessionService(async_session)

    session = await service.create_clarification_session(
        organization_id=org.id,
        missing_fields=["expiry_date"],
        collected_fields={"policyholder": "John"},
    )

    resumed = await service.resume_session_on_reply(
        session_id=session.id,
        user_reply="expiry is 2026-12-30",
        extracted_fields={"expiry_date": "2026-12-30"},
    )

    assert resumed.status == "resolved"
    assert resumed.collected_fields["expiry_date"] == "2026-12-30"


@pytest.mark.asyncio
async def test_expire_stale_sessions(async_session):
    org = await seed_org(async_session)
    service = AgentSessionService(async_session)

    session = await service.create_clarification_session(
        organization_id=org.id,
        missing_fields=["expiry_date"],
    )

    session.expires_at = utcnow_naive() - timedelta(minutes=1)
    await async_session.commit()

    expired_count = await service.expire_stale_sessions(org.id)
    assert expired_count == 1
