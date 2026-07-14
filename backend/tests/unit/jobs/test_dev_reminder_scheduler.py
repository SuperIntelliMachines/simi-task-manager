import asyncio
import logging

import pytest

from app.jobs import dev_reminder_scheduler as scheduler


@pytest.mark.asyncio
async def test_run_dev_reminder_cycle_logs_counts(monkeypatch, caplog):
    class FakeSession:
        pass

    class FakeSessionCtx:
        async def __aenter__(self):
            return FakeSession()

        async def __aexit__(self, *args):
            return None

    async def fake_generate(session):
        return 1

    async def fake_policy(session):
        return {"processed": 2, "sent": 2, "failed": 0}

    async def fake_lead(session):
        return 3

    monkeypatch.setattr(scheduler, "AsyncSessionLocal", lambda: FakeSessionCtx())
    monkeypatch.setattr(scheduler, "generate_reminder_instances_all", fake_generate)
    monkeypatch.setattr(scheduler, "process_due_reminder_instances_all", fake_policy)
    monkeypatch.setattr(scheduler, "process_due_reminders_all", fake_lead)

    with caplog.at_level(logging.INFO):
        generated, policy_count, lead_count = await scheduler.run_dev_reminder_cycle()

    assert generated == 1
    assert policy_count == 2
    assert lead_count == 3
    assert "Generated 1 reminder instances" in caplog.text


@pytest.mark.asyncio
async def test_dev_reminder_scheduler_loop_continues_after_exception(monkeypatch, caplog):
    calls = {"count": 0}
    stop_event = asyncio.Event()

    async def flaky_cycle():
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("db unavailable")
        stop_event.set()
        return 0, 0, 0

    monkeypatch.setattr(scheduler, "run_dev_reminder_cycle", flaky_cycle)
    monkeypatch.setattr(scheduler, "DEV_REMINDER_INTERVAL_SECONDS", 0.01)

    task = asyncio.create_task(scheduler.dev_reminder_scheduler_loop(stop_event))

    with caplog.at_level(logging.INFO):
        await task

    assert calls["count"] == 2
    assert "[ReminderScheduler] Reminder cycle failed; continuing" in caplog.text
