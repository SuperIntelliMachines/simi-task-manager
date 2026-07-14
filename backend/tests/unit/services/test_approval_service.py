from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.atm017 import ApprovalRequest, AuditEvent, OutboundMessage
from app.models.core import Organization, User
from app.services.approval_service import ApprovalService


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def seed_org_user(async_session):
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
    await async_session.commit()
    return org, user


@pytest.mark.asyncio
async def test_bulk_action_creates_pending_request(async_session):
    org, user = await seed_org_user(async_session)
    service = ApprovalService(async_session)

    request = await service.create_request(
        organization_id=org.id,
        requested_by_user_id=user.id,
        reason="bulk insurance reminder",
        proposed_action={
            "action_type": "send_bulk_reminder",
            "payload": {"recipients": ["+1001", "+1002"], "body": "Renew now"},
        },
    )

    assert request.status == "pending"
    result = await async_session.execute(select(OutboundMessage))
    assert list(result.scalars()) == []


@pytest.mark.asyncio
async def test_approval_executes_once_and_writes_audit(async_session):
    org, user = await seed_org_user(async_session)
    service = ApprovalService(async_session)

    request = await service.create_request(
        organization_id=org.id,
        requested_by_user_id=user.id,
        reason="bulk insurance reminder",
        proposed_action={
            "action_type": "send_bulk_reminder",
            "payload": {"recipients": ["+1001", "+1002"], "body": "Renew now"},
        },
    )

    approved = await service.approve_request(request.id, user.id)
    assert approved.status == "approved"

    result = await async_session.execute(select(OutboundMessage))
    assert len(list(result.scalars())) == 2

    audits = await async_session.execute(select(AuditEvent).where(AuditEvent.entity_id == str(request.id)))
    assert len(list(audits.scalars())) >= 2

    # Re-approve should not duplicate outbound messages.
    await service.approve_request(request.id, user.id)
    result = await async_session.execute(select(OutboundMessage))
    assert len(list(result.scalars())) == 2


@pytest.mark.asyncio
async def test_reject_does_not_execute(async_session):
    org, user = await seed_org_user(async_session)
    service = ApprovalService(async_session)

    request = await service.create_request(
        organization_id=org.id,
        requested_by_user_id=user.id,
        reason="bulk insurance reminder",
        proposed_action={
            "action_type": "send_bulk_reminder",
            "payload": {"recipients": ["+1001"], "body": "Renew now"},
        },
    )

    rejected = await service.reject_request(request.id, user.id, "not now")
    assert rejected.status == "rejected"

    result = await async_session.execute(select(OutboundMessage))
    assert list(result.scalars()) == []
