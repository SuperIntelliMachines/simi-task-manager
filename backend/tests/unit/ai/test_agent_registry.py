from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.ai.registry import AgentRegistry
from app.models.atm012 import AgentDefinition
from app.models.core import Organization


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@pytest.mark.asyncio
async def test_registry_exposes_all_initial_agents():
    registry = AgentRegistry()
    enabled = registry.list_enabled_agents()
    keys = {agent.key for agent in enabled}

    assert keys == {
        "general_task_agent",
        "insurance_agent",
        "construction_agent",
        "doctors_office_agent",
    }


@pytest.mark.asyncio
async def test_registry_loads_persisted_agent_definitions(async_session):
    now = utcnow_naive()
    org = Organization(
        name=f"Org Registry {uuid4().hex[:8]}",
        created_at=now,
        updated_at=now,
    )
    async_session.add(org)
    await async_session.flush()

    async_session.add(
        AgentDefinition(
            organization_id=org.id,
            key="insurance_agent",
            name="Insurance Agent Override",
            domain="insurance",
            description="Disabled for this org",
            system_prompt="",
            tool_policy={},
            guardrail_policy={},
            status="active",
            is_enabled=False,
            config={},
            created_at=now,
            updated_at=now,
        )
    )
    await async_session.commit()

    registry = AgentRegistry()
    await registry.load_persisted_definitions(async_session, organization_id=org.id)

    insurance_agents = registry.list_enabled_agents(organization_id=org.id, domain="insurance")
    assert insurance_agents == []

    general = registry.resolve_agent_for_domain("insurance", organization_id=org.id)
    assert general == "general_task_agent"
