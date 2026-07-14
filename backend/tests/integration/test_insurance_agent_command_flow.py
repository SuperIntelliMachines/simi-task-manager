from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.ai.domain_classifier import DomainClassifier
from app.ai.fake_llm_provider import FakeLLMProvider
from app.ai.registry import AgentRegistry
from app.ai.validator import StructuredOutputValidator
from app.models.atm017 import ApprovalRequest
from app.models.core import Contact, Organization, Reminder, Task, User, WorkflowRun, WorkflowTemplate
from app.models.verticals import InsurancePolicy
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


async def seed_org(async_session, *, name_prefix: str = "Org Insurance") -> Organization:
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
        phone="+15550001",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(contact)
    await async_session.flush()
    return contact


@pytest.mark.asyncio
async def test_create_policy_command_creates_policy_and_workflow(async_session):
    org = await seed_org(async_session)
    actor = await seed_user(async_session, organization_id=org.id, email=f"owner-{uuid4().hex[:6]}@test.local")
    await async_session.commit()
    orchestrator = await build_orchestrator(async_session)

    result = await orchestrator.process_command(
        AgentCommandInput(
            organization_id=org.id,
            actor_user_id=actor.id,
            command_text="Create auto policy for Ravi expiring June 25 2099 and remind him on WhatsApp",
            context={},
        )
    )

    assert result.agent_key == "insurance_agent"
    assert result.status == "executed"
    assert {entity.type for entity in result.created_entities} >= {
        "contact",
        "insurance_policy",
        "workflow_template",
        "workflow_run",
        "task",
        "reminder",
    }

    policy_rows = list((await async_session.execute(select(InsurancePolicy).where(InsurancePolicy.organization_id == org.id))).scalars())
    template_rows = list((await async_session.execute(select(WorkflowTemplate).where(WorkflowTemplate.organization_id == org.id))).scalars())
    run_rows = list((await async_session.execute(select(WorkflowRun).where(WorkflowRun.organization_id == org.id))).scalars())
    reminder_rows = list((await async_session.execute(select(Reminder).where(Reminder.organization_id == org.id))).scalars())

    assert len(policy_rows) == 1
    assert policy_rows[0].preferred_channel == ["whatsapp"]
    assert len(template_rows) == 1
    assert len(run_rows) == 1
    assert len(reminder_rows) == 5


@pytest.mark.asyncio
async def test_policy_workflow_skips_past_stages(async_session):
    org = await seed_org(async_session)
    await async_session.commit()
    orchestrator = await build_orchestrator(async_session)
    expiry = utcnow_naive() + timedelta(days=2)

    result = await orchestrator.process_command(
        AgentCommandInput(
            organization_id=org.id,
            actor_user_id=None,
            command_text=f"Create auto policy for Ravi expiring {expiry.strftime('%B %d %Y')} and remind him on WhatsApp",
            context={},
        )
    )

    assert result.status == "executed"
    reminder_rows = list((await async_session.execute(select(Reminder).where(Reminder.organization_id == org.id))).scalars())
    assert len(reminder_rows) == 2


@pytest.mark.asyncio
async def test_mark_policy_renewed_cancels_remaining_reminders(async_session):
    org = await seed_org(async_session)
    await async_session.commit()
    orchestrator = await build_orchestrator(async_session)

    create_result = await orchestrator.process_command(
        AgentCommandInput(
            organization_id=org.id,
            actor_user_id=None,
            command_text="Create auto policy for Ravi expiring June 25 2099 and remind him on WhatsApp",
            context={},
        )
    )
    assert create_result.status == "executed"

    renew_result = await orchestrator.process_command(
        AgentCommandInput(
            organization_id=org.id,
            actor_user_id=None,
            command_text="Renewed Ravi's policy",
            context={},
        )
    )

    assert renew_result.status == "executed"
    policy = (await async_session.execute(select(InsurancePolicy).where(InsurancePolicy.organization_id == org.id))).scalar_one()
    reminders = list((await async_session.execute(select(Reminder).where(Reminder.organization_id == org.id))).scalars())
    task = (await async_session.execute(select(Task).where(Task.organization_id == org.id))).scalar_one()

    assert policy.status == "renewed"
    assert all(reminder.status == "canceled" for reminder in reminders)
    assert task.status == "completed"


@pytest.mark.asyncio
async def test_demo_followup_creates_task_and_reminder(async_session):
    org = await seed_org(async_session)
    actor = await seed_user(async_session, organization_id=org.id, email=f"agent-{uuid4().hex[:6]}@test.local")
    await async_session.commit()
    orchestrator = await build_orchestrator(async_session)

    result = await orchestrator.process_command(
        AgentCommandInput(
            organization_id=org.id,
            actor_user_id=actor.id,
            command_text="Follow up with Priya after demo in 3 days",
            context={},
        )
    )

    assert result.status == "executed"
    tasks = list((await async_session.execute(select(Task).where(Task.organization_id == org.id))).scalars())
    reminders = list((await async_session.execute(select(Reminder).where(Reminder.organization_id == org.id))).scalars())

    assert len(tasks) == 1
    assert tasks[0].title == "Demo follow-up with Priya"
    assert len(reminders) == 1
    assert reminders[0].task_id == tasks[0].id


@pytest.mark.asyncio
async def test_missing_expiry_requests_clarification(async_session):
    org = await seed_org(async_session)
    await async_session.commit()
    orchestrator = await build_orchestrator(async_session)

    result = await orchestrator.process_command(
        AgentCommandInput(
            organization_id=org.id,
            actor_user_id=None,
            command_text="Create auto policy for Ravi and remind him on WhatsApp",
            context={},
        )
    )

    assert result.status == "needs_clarification"
    assert result.clarification is not None
    assert "expire" in result.clarification.question.lower()


@pytest.mark.asyncio
async def test_bulk_campaign_creates_approval_request(async_session):
    org = await seed_org(async_session)
    actor = await seed_user(async_session, organization_id=org.id, email=f"owner-{uuid4().hex[:6]}@test.local")
    await async_session.commit()
    orchestrator = await build_orchestrator(async_session)

    result = await orchestrator.process_command(
        AgentCommandInput(
            organization_id=org.id,
            actor_user_id=actor.id,
            command_text="Send renewal reminders to all expiring customers",
            context={},
        )
    )

    assert result.status == "needs_approval"
    assert result.approval_request_id is not None
    approval_rows = list((await async_session.execute(select(ApprovalRequest).where(ApprovalRequest.organization_id == org.id))).scalars())
    assert len(approval_rows) == 1


@pytest.mark.asyncio
async def test_unknown_customer_requests_clarification(async_session):
    org = await seed_org(async_session)
    await async_session.commit()
    orchestrator = await build_orchestrator(async_session)

    result = await orchestrator.process_command(
        AgentCommandInput(
            organization_id=org.id,
            actor_user_id=None,
            command_text="Create auto policy for unknown expiring June 25 2099 and remind him on WhatsApp",
            context={},
        )
    )

    assert result.status == "needs_clarification"
    assert result.clarification is not None
    assert "contact details" in result.clarification.question.lower()


@pytest.mark.asyncio
async def test_multiple_matching_policies_request_clarification(async_session):
    org = await seed_org(async_session)
    contact = await seed_contact(async_session, organization_id=org.id, name="Ravi")
    async_session.add_all(
        [
            InsurancePolicy(
                organization_id=org.id,
                policyholder_id=contact.id,
                policy_number=f"POL-{uuid4().hex[:6]}",
                premium=1000,
                policy_type="auto",
                carrier="carrier-a",
                assigned_agent_user_id=None,
                preferred_channel=["whatsapp"],
                expiry_date=utcnow_naive() + timedelta(days=30),
                status="active",
                created_at=utcnow_naive(),
                updated_at=utcnow_naive(),
            ),
            InsurancePolicy(
                organization_id=org.id,
                policyholder_id=contact.id,
                policy_number=f"POL-{uuid4().hex[:6]}",
                premium=1200,
                policy_type="auto",
                carrier="carrier-b",
                assigned_agent_user_id=None,
                preferred_channel=["whatsapp"],
                expiry_date=utcnow_naive() + timedelta(days=60),
                status="active",
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
            command_text="Renewed Ravi's policy",
            context={},
        )
    )

    assert result.status == "needs_clarification"
    assert result.clarification is not None
    assert "multiple matching policies" in result.clarification.question.lower()
