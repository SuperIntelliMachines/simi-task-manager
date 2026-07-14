from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.main import app


@pytest.fixture
def scheduler_secret(monkeypatch):
    monkeypatch.setenv("SCHEDULER_SECRET", "test-scheduler-secret")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_generate_internal_reminders_requires_secret(scheduler_secret):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/api/v1/internal/reminders/generate",
            json={
                "organization_id": 1,
                "entity_type": "policy",
                "entity_id": 10,
                "anchor_date": datetime(2026, 8, 1, 9, 0, 0).isoformat(),
            },
        )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_generate_internal_reminders_success(scheduler_secret):
    generated = [object(), object(), object()]
    with patch(
        "app.api.v1.endpoints.internal_reminders.ReminderGeneratorService.generate_instances",
        new=AsyncMock(return_value=generated),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.post(
                "/api/v1/internal/reminders/generate",
                headers={"X-Scheduler-Secret": "test-scheduler-secret"},
                json={
                    "organization_id": 7,
                    "entity_type": "invoice",
                    "entity_id": 99,
                    "anchor_date": datetime(2026, 8, 1, 9, 0, 0).isoformat(),
                },
            )

    assert response.status_code == 200
    assert response.json() == {"generated": 3}


@pytest.mark.asyncio
async def test_process_internal_reminders_requires_secret(scheduler_secret):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/api/v1/internal/reminders/process",
            json={"organization_id": 1},
        )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_process_internal_reminders_success(scheduler_secret):
    summary = {"processed": 5, "sent": 4, "failed": 1}
    with patch(
        "app.api.v1.endpoints.internal_reminders.ReminderProcessorService.process_due_reminders",
        new=AsyncMock(return_value=summary),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.post(
                "/api/v1/internal/reminders/process",
                headers={"X-Scheduler-Secret": "test-scheduler-secret"},
                json={"organization_id": 12},
            )

    assert response.status_code == 200
    assert response.json() == summary


@pytest.mark.asyncio
async def test_generate_all_internal_reminders_success(scheduler_secret):
    generated = [object(), object()]
    with patch(
        "app.api.v1.endpoints.internal_reminders.ReminderGeneratorService.generate_from_active_configs",
        new=AsyncMock(return_value=generated),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.post(
                "/api/v1/internal/reminders/generate-all",
                headers={"X-Scheduler-Secret": "test-scheduler-secret"},
                json={"organization_id": 607},
            )

    assert response.status_code == 200
    assert response.json() == {"generated": 2}


@pytest.mark.asyncio
async def test_generate_internal_reminders_org_only_uses_scheduler(scheduler_secret):
    generated = [object()]
    with patch(
        "app.api.v1.endpoints.internal_reminders.ReminderGeneratorService.generate_from_active_configs",
        new=AsyncMock(return_value=generated),
    ) as mock_generate:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.post(
                "/api/v1/internal/reminders/generate",
                headers={"X-Scheduler-Secret": "test-scheduler-secret"},
                json={"organization_id": 607},
            )

    assert response.status_code == 200
    assert response.json() == {"generated": 1}
    mock_generate.assert_awaited_once_with(organization_id=607)
