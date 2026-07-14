from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.core import Organization, Reminder, Task, WorkflowRun
from app.models.verticals import InsuranceLead
from app.services.insurance_service import InsuranceService


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def seed_org(async_session) -> Organization:
    org = Organization(
        name=f"Lead Org {uuid4().hex[:8]}",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(org)
    await async_session.flush()
    return org


@pytest.mark.asyncio
async def test_demo_logged_creates_followup_reminder(async_session):
    org = await seed_org(async_session)
    await async_session.commit()
    service = InsuranceService(async_session)

    lead = await service.create_lead(
        organization_id=org.id,
        contact_name="Priya",
        actor_user_id=None,
        source="demo",
        notes="Demo completed",
        demo_logged_at=utcnow_naive(),
    )
    result = await service.start_lead_followup_workflow(
        lead_id=lead.id,
        actor_user_id=None,
        days_until_followup=3,
    )

    assert result["lead"].status == "follow_up_pending"
    reminders = list((await async_session.execute(select(Reminder).where(Reminder.organization_id == org.id))).scalars())
    assert len(reminders) == 1
    assert reminders[0].task_id == result["task"].id


@pytest.mark.asyncio
async def test_lead_marked_not_interested_closes_lead_cycle(async_session):
    org = await seed_org(async_session)
    await async_session.commit()
    service = InsuranceService(async_session)

    lead = await service.create_lead(
        organization_id=org.id,
        contact_name="Arjun",
        actor_user_id=None,
        source="demo",
        notes="Initial conversation",
        demo_logged_at=utcnow_naive(),
    )
    await service.start_lead_followup_workflow(lead_id=lead.id, actor_user_id=None)
    updated = await service.update_lead(lead.id, {"status": "not_interested"}, actor_user_id=None)

    tasks = list((await async_session.execute(select(Task).where(Task.organization_id == org.id))).scalars())
    reminders = list((await async_session.execute(select(Reminder).where(Reminder.organization_id == org.id))).scalars())
    runs = list((await async_session.execute(select(WorkflowRun).where(WorkflowRun.organization_id == org.id))).scalars())

    assert updated.status == "not_interested"
    assert tasks[0].status == "completed"
    assert reminders[0].status == "canceled"
    assert runs[0].status == "completed"


@pytest.mark.asyncio
async def test_follow_up_later_reschedules_reminder(async_session):
    org = await seed_org(async_session)
    await async_session.commit()
    service = InsuranceService(async_session)

    lead = await service.create_lead(
        organization_id=org.id,
        contact_name="Neha",
        actor_user_id=None,
        source="demo",
        notes="Asked to circle back later",
        demo_logged_at=utcnow_naive(),
    )
    await service.start_lead_followup_workflow(lead_id=lead.id, actor_user_id=None)
    new_due = utcnow_naive() + timedelta(days=10)
    updated = await service.update_lead(
        lead.id,
        {"status": "follow_up_later", "followup_due_at": new_due},
        actor_user_id=None,
    )

    lead_row = (await async_session.execute(select(InsuranceLead).where(InsuranceLead.id == lead.id))).scalar_one()
    reminder = (await async_session.execute(select(Reminder).where(Reminder.organization_id == org.id))).scalar_one()
    task = (await async_session.execute(select(Task).where(Task.organization_id == org.id))).scalar_one()

    assert updated.status == "follow_up_later"
    assert lead_row.followup_due_at == new_due
    assert reminder.scheduled_for == new_due
    assert task.due_at == new_due
    assert task.status == "snoozed"


@pytest.mark.asyncio
async def test_renewed_status_requires_policy_module_context(async_session):
    org = await seed_org(async_session)
    await async_session.commit()
    service = InsuranceService(async_session)

    lead = await service.create_lead(
        organization_id=org.id,
        contact_name="Ravi",
        actor_user_id=None,
        source="demo",
        notes="Awaiting decision",
        demo_logged_at=utcnow_naive(),
    )

    with pytest.raises(ValueError, match="Policy module"):
        await service.update_lead(lead.id, {"status": "renewed"}, actor_user_id=None)
