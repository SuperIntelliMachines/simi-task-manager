from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db_session
from app.core.security import create_access_token
from app.main import app
from app.models.core import Organization, Task, User
from app.services.task_service import TaskService
from tests.helpers.sqlite_task import SQLITE_BIGINT_PK_TABLES, patch_sqlite_session_bigint_ids


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def seed_org(async_session, *, name: str) -> Organization:
    org = Organization(name=name, created_at=utcnow_naive(), updated_at=utcnow_naive())
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


async def seed_task(async_session, *, organization_id: int, title: str, domain: str) -> Task:
    now = utcnow_naive()
    task = Task(
        organization_id=organization_id,
        title=title,
        description=None,
        domain=domain,
        status="open",
        priority="medium",
        due_at=None,
        created_at=now,
        updated_at=now,
    )
    async_session.add(task)
    await async_session.flush()
    return task


@pytest.fixture
async def tasks_client(async_session) -> AsyncGenerator[AsyncClient, None]:
    patch_sqlite_session_bigint_ids(
        async_session,
        start_id=9100 + (uuid4().int % 1_000_000),
        table_names=SQLITE_BIGINT_PK_TABLES,
    )

    async def override_session():
        yield async_session

    app.dependency_overrides[get_db_session] = override_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.clear()


def auth_header(user_id: int) -> dict[str, str]:
    token = create_access_token(str(user_id))
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_list_tasks_api_isolates_organizations(tasks_client, async_session):
    general_org = await seed_org(async_session, name=f"General Org {uuid4().hex[:8]}")
    insurance_org = await seed_org(async_session, name=f"Insurance Org {uuid4().hex[:8]}")
    general_user = await seed_user(async_session, organization_id=general_org.id, email=f"general-{uuid4().hex[:6]}@test.com")
    insurance_user = await seed_user(async_session, organization_id=insurance_org.id, email=f"insurance-{uuid4().hex[:6]}@test.com")
    await seed_task(async_session, organization_id=general_org.id, title="General task", domain="general")
    await seed_task(async_session, organization_id=insurance_org.id, title="Lead follow-up", domain="insurance")
    await seed_task(async_session, organization_id=insurance_org.id, title="Policy renewal", domain="insurance")
    await async_session.commit()

    general_response = await tasks_client.get(
        f"/api/v1/tasks?organization_id={general_org.id}",
        headers=auth_header(general_user.id),
    )
    assert general_response.status_code == 200
    general_titles = {row["title"] for row in general_response.json()}
    assert general_titles == {"General task"}

    insurance_response = await tasks_client.get(
        f"/api/v1/tasks?organization_id={insurance_org.id}",
        headers=auth_header(insurance_user.id),
    )
    assert insurance_response.status_code == 200
    insurance_titles = {row["title"] for row in insurance_response.json()}
    assert insurance_titles == {"Lead follow-up", "Policy renewal"}

    cross_tenant_response = await tasks_client.get(
        f"/api/v1/tasks?organization_id={insurance_org.id}",
        headers=auth_header(general_user.id),
    )
    assert cross_tenant_response.status_code == 403


@pytest.mark.asyncio
async def test_list_tasks_api_requires_authentication(tasks_client, async_session):
    org = await seed_org(async_session, name=f"Org {uuid4().hex[:8]}")
    await async_session.commit()

    response = await tasks_client.get(f"/api/v1/tasks?organization_id={org.id}")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_task_mutations_reject_cross_organization_access(async_session):
    patch_sqlite_session_bigint_ids(
        async_session,
        start_id=9200,
        table_names=SQLITE_BIGINT_PK_TABLES,
    )
    general_org = await seed_org(async_session, name=f"General Org {uuid4().hex[:8]}")
    insurance_org = await seed_org(async_session, name=f"Insurance Org {uuid4().hex[:8]}")
    insurance_task = await seed_task(
        async_session,
        organization_id=insurance_org.id,
        title="Policy renewal",
        domain="insurance",
    )
    await async_session.commit()

    service = TaskService(async_session)
    with pytest.raises(ValueError, match="cross-tenant"):
        await service.complete_task(insurance_task.id, organization_id=general_org.id)

    with pytest.raises(ValueError, match="cross-tenant"):
        await service.update_task(
            insurance_task.id,
            {"status": "canceled"},
            organization_id=general_org.id,
        )

    with pytest.raises(ValueError, match="cross-tenant"):
        await service.snooze_task(
            insurance_task.id,
            due_at=utcnow_naive(),
            organization_id=general_org.id,
        )


@pytest.mark.asyncio
async def test_list_tasks_service_isolates_organizations(async_session):
    patch_sqlite_session_bigint_ids(
        async_session,
        start_id=9300,
        table_names=SQLITE_BIGINT_PK_TABLES,
    )
    general_org = await seed_org(async_session, name=f"General Org {uuid4().hex[:8]}")
    insurance_org = await seed_org(async_session, name=f"Insurance Org {uuid4().hex[:8]}")
    await seed_task(async_session, organization_id=general_org.id, title="General task", domain="general")
    await seed_task(async_session, organization_id=insurance_org.id, title="Lead follow-up", domain="insurance")
    await async_session.commit()

    service = TaskService(async_session)
    general_tasks = await service.list_tasks(organization_id=general_org.id)
    insurance_tasks = await service.list_tasks(organization_id=insurance_org.id, domain="insurance")

    assert {task.title for task in general_tasks} == {"General task"}
    assert {task.title for task in insurance_tasks} == {"Lead follow-up"}
