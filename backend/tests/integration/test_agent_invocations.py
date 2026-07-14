from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.ai.domain_classifier import DomainClassifier
from app.ai.fake_llm_provider import FakeLLMProvider
from app.ai.registry import AgentRegistry
from app.ai.validator import StructuredOutputValidator
from app.models.atm012 import AgentInvocation
from app.models.core import Organization
from app.schemas.atm012 import AgentCommandInput
from app.services.agent_orchestrator import AgentOrchestrator


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@pytest.mark.asyncio
async def test_agent_invocations_are_persisted(async_session):
    now = utcnow_naive()
    organization = Organization(
        name=f"Org Invocations {uuid4().hex[:8]}",
        created_at=now,
        updated_at=now,
    )
    async_session.add(organization)
    await async_session.commit()

    orchestrator = AgentOrchestrator(
        session=async_session,
        registry=AgentRegistry(),
        classifier=DomainClassifier(FakeLLMProvider()),
        llm_provider=FakeLLMProvider(),
        validator=StructuredOutputValidator(),
    )

    command = AgentCommandInput(
        organization_id=organization.id,
        actor_user_id=None,
        command_text="Create policy renewal for Ravi",
        context={},
    )
    result = await orchestrator.process_command(command)

    assert result.agent_key == "insurance_agent"
    assert result.status == "executed"

    rows = await async_session.execute(
        select(AgentInvocation).where(AgentInvocation.organization_id == organization.id)
    )
    invocation = rows.scalar_one()

    assert invocation.agent == "insurance_agent"
    assert invocation.domain == "insurance"
    assert invocation.intent == "create_lead_followup"
    assert invocation.guardrail_result == "passed"
    assert invocation.tool_calls == ["create_lead_followup"]
