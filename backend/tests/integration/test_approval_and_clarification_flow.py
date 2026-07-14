from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.atm017 import AuditEvent, OutboundMessage
from app.models.core import Organization, User
from app.services.agent_session_service import AgentSessionService
from app.services.approval_service import ApprovalService


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def seed_org_user(async_session):
    org = Organization(
        name=f"Org A {uuid4().hex[:8]}",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
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
    await async_session.commit()
    return org, user


@pytest.mark.asyncio
async def test_approval_and_clarification_flow(async_session):
    org, user = await seed_org_user(async_session)

    approval_service = ApprovalService(async_session)
    request = await approval_service.create_request(
        organization_id=org.id,
        requested_by_user_id=user.id,
        reason="bulk insurance reminder",
        proposed_action={
            "action_type": "send_bulk_reminder",
            "payload": {"recipients": ["+1001", "+1002"], "body": "Renew now"},
        },
    )

    approved = await approval_service.approve_request(request.id, user.id)
    assert approved.status == "approved"

    outbounds = await async_session.execute(select(OutboundMessage))
    assert len(list(outbounds.scalars())) == 2

    audits = await async_session.execute(select(AuditEvent).where(AuditEvent.entity_id == str(request.id)))
    assert len(list(audits.scalars())) >= 2

    session_service = AgentSessionService(async_session)
    session = await session_service.create_clarification_session(
        organization_id=org.id,
        missing_fields=["expiry_date"],
        collected_fields={"policyholder": "John"},
    )

    resumed = await session_service.resume_session_on_reply(
        session_id=session.id,
        user_reply="expiry is 2026-12-30",
        extracted_fields={"expiry_date": "2026-12-30"},
    )
    assert resumed.status == "resolved"
    assert resumed.collected_fields["expiry_date"] == "2026-12-30"
