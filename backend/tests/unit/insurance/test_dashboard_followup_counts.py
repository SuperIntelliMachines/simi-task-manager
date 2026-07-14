from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.core import Contact, Organization
from app.models.verticals import InsuranceLead
from app.services.insurance_service import InsuranceService, OPEN_LEAD_STATUSES


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def _seed_org(session) -> Organization:
    org = Organization(
        name=f"Dashboard Followups {uuid4().hex[:8]}",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    session.add(org)
    await session.flush()
    return org


async def _seed_contact(session, org_id: int, contact_id: int, name: str) -> Contact:
    contact = Contact(
        id=contact_id,
        organization_id=org_id,
        name=name,
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    session.add(contact)
    await session.flush()
    return contact


async def _seed_lead(
    session,
    *,
    lead_id: int,
    org_id: int,
    contact_id: int,
    status: str,
    followup_due_at,
) -> InsuranceLead:
    lead = InsuranceLead(
        id=lead_id,
        organization_id=org_id,
        contact_id=contact_id,
        status=status,
        followup_due_at=followup_due_at,
        source="demo",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    session.add(lead)
    await session.flush()
    return lead


@pytest.mark.asyncio
async def test_dashboard_counts_due_and_overdue_followups(async_session):
    org = await _seed_org(async_session)
    now = utcnow_naive()
    today = now.date()

    due_today_contact = await _seed_contact(async_session, org.id, 9401, "Due Today")
    overdue_contact = await _seed_contact(async_session, org.id, 9402, "Overdue")
    closed_contact = await _seed_contact(async_session, org.id, 9403, "Closed Overdue")
    future_contact = await _seed_contact(async_session, org.id, 9404, "Future")

    await _seed_lead(
        async_session,
        lead_id=9501,
        org_id=org.id,
        contact_id=due_today_contact.id,
        status="follow_up_pending",
        followup_due_at=now.replace(hour=12, minute=0, second=0, microsecond=0),
    )
    await _seed_lead(
        async_session,
        lead_id=9502,
        org_id=org.id,
        contact_id=overdue_contact.id,
        status="interested",
        followup_due_at=now - timedelta(days=2),
    )
    await _seed_lead(
        async_session,
        lead_id=9503,
        org_id=org.id,
        contact_id=closed_contact.id,
        status="not_interested",
        followup_due_at=now - timedelta(days=5),
    )
    await _seed_lead(
        async_session,
        lead_id=9504,
        org_id=org.id,
        contact_id=future_contact.id,
        status="follow_up_later",
        followup_due_at=now + timedelta(days=4),
    )
    await async_session.commit()

    service = InsuranceService(async_session)
    dashboard = await service.get_dashboard(org.id)
    counts = dashboard["counts"]

    assert counts["due_followups"] == 1
    assert counts["overdue_followups"] == 1
    assert counts["pending_followups"] == 3

    leads = (
        await async_session.execute(select(InsuranceLead).where(InsuranceLead.organization_id == org.id))
    ).scalars()
    open_due_today = [
        lead
        for lead in leads
        if lead.status in OPEN_LEAD_STATUSES
        and lead.followup_due_at is not None
        and lead.followup_due_at.date() == today
    ]
    assert len(open_due_today) == 1
