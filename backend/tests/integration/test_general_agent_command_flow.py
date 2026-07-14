from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.ai.domain_classifier import DomainClassifier
from app.ai.fake_llm_provider import FakeLLMProvider
from app.ai.registry import AgentRegistry
from app.ai.validator import StructuredOutputValidator
from app.models.core import Contact, Organization, OrganizationMembership, Reminder, Task, TaskAssignment, User
from app.schemas.atm012 import AgentCommandInput
from app.services.agent_orchestrator import AgentOrchestrator


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def build_orchestrator(async_session):
    return AgentOrchestrator(
        session=async_session,
        registry=AgentRegistry(),
        classifier=DomainClassifier(FakeLLMProvider()),
        llm_provider=FakeLLMProvider(),
        validator=StructuredOutputValidator(),
    )


async def seed_org(async_session, *, name_prefix: str = "Org General") -> Organization:
    org = Organization(
        name=f"{name_prefix} {uuid4().hex[:8]}",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(org)
    await async_session.flush()
    return org


async def seed_user(async_session, *, organization_id: int, email: str) -> User:
    user = User(
        organization_id=organization_id,
        email=email,
        hashed_password="x",
        is_active=True,
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(user)
    await async_session.flush()
    return user


async def seed_contact(async_session, *, organization_id: int, name: str) -> Contact:
    contact = Contact(
        organization_id=organization_id,
        name=name,
        email=f"{name.lower()}@example.com",
        phone="+1000",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(contact)
    await async_session.flush()
    return contact


@pytest.mark.asyncio
async def test_remind_me_to_call_creates_task_and_reminder(async_session):
    org = await seed_org(async_session)
    await async_session.commit()
    orchestrator = await build_orchestrator(async_session)

    result = await orchestrator.process_command(
        AgentCommandInput(
            organization_id=org.id,
            actor_user_id=None,
            command_text="Remind me to call Suresh tomorrow morning",
            context={},
        )
    )

    assert result.agent_key == "general_task_agent"
    assert result.status == "executed"
    assert {entity.type for entity in result.created_entities} == {"task", "reminder"}

    tasks = await async_session.execute(select(Task).where(Task.organization_id == org.id))
    reminders = await async_session.execute(select(Reminder).where(Reminder.organization_id == org.id))
    task_rows = list(tasks.scalars())
    reminder_rows = list(reminders.scalars())
    assert len(task_rows) == 1
    assert task_rows[0].title == "Call Suresh"
    assert len(reminder_rows) == 1
    assert reminder_rows[0].task_id == task_rows[0].id


@pytest.mark.asyncio
async def test_assignment_command_creates_task_and_assignment(async_session):
    org = await seed_org(async_session)
    actor = await seed_user(async_session, organization_id=org.id, email="owner@test.local")
    await seed_contact(async_session, organization_id=org.id, name="Priya")
    await async_session.commit()
    orchestrator = await build_orchestrator(async_session)

    result = await orchestrator.process_command(
        AgentCommandInput(
            organization_id=org.id,
            actor_user_id=actor.id,
            command_text="Assign Priya to submit report by Friday",
            context={},
        )
    )

    assert result.status == "executed"
    assert {entity.type for entity in result.created_entities} == {"task", "task_assignment"}

    task_rows = list((await async_session.execute(select(Task).where(Task.organization_id == org.id))).scalars())
    assignment_rows = list((await async_session.execute(select(TaskAssignment).where(TaskAssignment.organization_id == org.id))).scalars())
    assert len(task_rows) == 1
    assert task_rows[0].title == "Submit report"
    assert len(assignment_rows) == 1
    assert assignment_rows[0].contact_id is not None


@pytest.mark.asyncio
async def test_snooze_with_context_updates_active_task(async_session):
    org = await seed_org(async_session)
    task = Task(
        organization_id=org.id,
        title="Follow up tomorrow",
        description=None,
        domain="general",
        status="open",
        due_at=None,
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(task)
    await async_session.commit()
    orchestrator = await build_orchestrator(async_session)

    result = await orchestrator.process_command(
        AgentCommandInput(
            organization_id=org.id,
            actor_user_id=None,
            command_text="Snooze this to Monday",
            context={"task_id": task.id},
        )
    )

    await async_session.refresh(task)
    assert result.status == "executed"
    assert task.status == "snoozed"
    assert task.due_at is not None


@pytest.mark.asyncio
async def test_complete_task_with_multiple_matches_requests_clarification(async_session):
    org = await seed_org(async_session)
    async_session.add_all(
        [
            Task(
                organization_id=org.id,
                title="The report draft",
                description=None,
                domain="general",
                status="open",
                due_at=None,
                created_at=utcnow_naive(),
                updated_at=utcnow_naive(),
            ),
            Task(
                organization_id=org.id,
                title="The report final",
                description=None,
                domain="general",
                status="open",
                due_at=None,
                created_at=utcnow_naive(),
                updated_at=utcnow_naive(),
            ),
        ]
    )
    await async_session.commit()
    orchestrator = await build_orchestrator(async_session)

    result = await orchestrator.process_command(
        AgentCommandInput(
            organization_id=org.id,
            actor_user_id=None,
            command_text="Complete the report task",
            context={},
        )
    )

    assert result.status == "needs_clarification"
    assert result.clarification is not None
    assert "multiple tasks" in result.clarification.question.lower()


@pytest.mark.asyncio
async def test_staff_cannot_complete_other_users_task_without_permission(async_session):
    org = await seed_org(async_session)
    owner = await seed_user(async_session, organization_id=org.id, email="owner@test.local")
    staff = await seed_user(async_session, organization_id=org.id, email="staff@test.local")
    task = Task(
        organization_id=org.id,
        title="Quarterly report",
        description=None,
        domain="general",
        status="open",
        due_at=None,
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(task)
    await async_session.flush()
    async_session.add(
        TaskAssignment(
            organization_id=org.id,
            task_id=task.id,
            user_id=owner.id,
            contact_id=None,
            status="assigned",
            assigned_at=utcnow_naive(),
            created_at=utcnow_naive(),
            updated_at=utcnow_naive(),
        )
    )
    await async_session.commit()
    orchestrator = await build_orchestrator(async_session)

    result = await orchestrator.process_command(
        AgentCommandInput(
            organization_id=org.id,
            actor_user_id=staff.id,
            command_text="Complete quarterly report task",
            context={},
        )
    )

    await async_session.refresh(task)
    assert result.status == "failed"
    assert "do not have permission" in (result.user_message or "").lower()
    assert task.status == "open"


@pytest.mark.asyncio
async def test_agent_does_not_act_across_tenant_boundaries(async_session):
    org_a = await seed_org(async_session, name_prefix="Org A")
    org_b = await seed_org(async_session, name_prefix="Org B")
    foreign_task = Task(
        organization_id=org_b.id,
        title="Foreign task",
        description=None,
        domain="general",
        status="open",
        due_at=None,
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(foreign_task)
    await async_session.commit()
    orchestrator = await build_orchestrator(async_session)

    result = await orchestrator.process_command(
        AgentCommandInput(
            organization_id=org_a.id,
            actor_user_id=None,
            command_text="Snooze this to Monday",
            context={"task_id": foreign_task.id},
        )
    )

    await async_session.refresh(foreign_task)
    assert result.status == "failed"
    assert foreign_task.status == "open"
