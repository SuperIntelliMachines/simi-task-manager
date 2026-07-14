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
async def test_process_renewal_escalations_requires_secret(scheduler_secret):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post("/api/v1/internal/jobs/process-renewal-escalations")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_process_renewal_escalations_success(scheduler_secret):
    mock_stats = {"processed": 2, "escalated": 1, "skipped": 1}
    with patch(
        "app.api.v1.endpoints.scheduler_jobs.process_renewal_escalations_all",
        new=AsyncMock(return_value=mock_stats),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.post(
                "/api/v1/internal/jobs/process-renewal-escalations",
                headers={"X-Scheduler-Secret": "test-scheduler-secret"},
            )
    assert response.status_code == 200
    assert response.json() == {"success": True, **mock_stats}


@pytest.mark.asyncio
async def test_generate_policy_reminders_requires_secret(scheduler_secret):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post("/api/v1/internal/jobs/generate-policy-reminders")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_generate_policy_reminders_only_generates(scheduler_secret):
    generate_mock = AsyncMock(return_value=3)
    process_mock = AsyncMock(return_value={"processed": 2, "sent": 2, "failed": 0})
    with (
        patch(
            "app.api.v1.endpoints.scheduler_jobs.generate_reminder_instances_all",
            new=generate_mock,
        ),
        patch(
            "app.api.v1.endpoints.scheduler_jobs.process_due_reminder_instances_all",
            new=process_mock,
        ),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.post(
                "/api/v1/internal/jobs/generate-policy-reminders",
                headers={"X-Scheduler-Secret": "test-scheduler-secret"},
            )
    assert response.status_code == 200
    assert response.json() == {"success": True}
    generate_mock.assert_awaited_once()
    process_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_policy_reminders_only_processes(scheduler_secret):
    generate_mock = AsyncMock(return_value=3)
    process_mock = AsyncMock(return_value={"processed": 2, "sent": 2, "failed": 0})
    with (
        patch(
            "app.api.v1.endpoints.scheduler_jobs.generate_reminder_instances_all",
            new=generate_mock,
        ),
        patch(
            "app.api.v1.endpoints.scheduler_jobs.process_due_reminder_instances_all",
            new=process_mock,
        ),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.post(
                "/api/v1/internal/jobs/process-policy-reminders",
                headers={"X-Scheduler-Secret": "test-scheduler-secret"},
            )
    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "processed": 2,
        "fetched": 2,
        "failed": 0,
        "due_total": 2,
    }
    process_mock.assert_awaited_once()
    generate_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_policy_reminder_cycle_generates_and_processes(scheduler_secret):
    cycle_mock = AsyncMock(return_value={"generated": 3, "processed": 2, "sent": 2, "failed": 0})
    with patch(
        "app.api.v1.endpoints.scheduler_jobs.run_reminder_engine_cycle",
        new=cycle_mock,
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.post(
                "/api/v1/internal/jobs/policy-reminder-cycle",
                headers={"X-Scheduler-Secret": "test-scheduler-secret"},
            )
    assert response.status_code == 200
    assert response.json() == {"success": True}
    cycle_mock.assert_awaited_once()
