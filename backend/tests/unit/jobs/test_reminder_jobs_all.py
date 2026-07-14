import pytest

from app.jobs.reminder_jobs import process_due_reminders_all


@pytest.mark.asyncio
async def test_process_due_reminders_all_does_not_raise_name_error(async_session):
    count = await process_due_reminders_all(async_session)
    assert count == 0
