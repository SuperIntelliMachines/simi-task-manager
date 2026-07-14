import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.jobs import celery_app
from app.jobs.reminder_engine_jobs import (
    generate_reminder_instances,
    generate_reminder_instances_all,
    process_due_reminder_instances,
    process_due_reminder_instances_all,
    run_reminder_engine_cycle,
)
from app.jobs.reminder_jobs import (
    escalate_overdue_tasks,
    process_due_reminders,
    process_due_reminders_all,
    retry_failed_reminder_attempts,
)
from app.jobs.renewal_escalation_jobs import (
    process_renewal_escalations,
    process_renewal_escalations_all,
)


async def _run_with_session(coro):
    async with AsyncSessionLocal() as session:  # type: AsyncSession
        return await coro(session)


@celery_app.task(name="process_due_reminders")
def process_due_reminders_task(organization_id: int | None = None) -> int:
    async def run(session: AsyncSession) -> int:
        if organization_id is not None:
            return await process_due_reminders(session, organization_id)
        return await process_due_reminders_all(session)

    return asyncio.run(_run_with_session(run))


@celery_app.task(name="retry_failed_reminder_attempts")
def retry_failed_reminder_attempts_task(organization_id: int) -> int:
    return asyncio.run(
        _run_with_session(lambda session: retry_failed_reminder_attempts(session, organization_id))
    )


@celery_app.task(name="escalate_overdue_tasks")
def escalate_overdue_tasks_task(organization_id: int) -> int:
    return asyncio.run(_run_with_session(lambda session: escalate_overdue_tasks(session, organization_id)))


@celery_app.task(name="process_due_policy_reminders")
def process_due_policy_reminders_task(organization_id: int | None = None) -> int:
    async def run(session: AsyncSession) -> int:
        if organization_id is not None:
            stats = await process_due_reminder_instances(session, organization_id)
            return int(stats.get("sent", 0))
        stats = await process_due_reminder_instances_all(session)
        return int(stats.get("sent", 0))

    return asyncio.run(_run_with_session(run))


@celery_app.task(name="generate_daily_policy_reminders")
def generate_daily_policy_reminders_task(organization_id: int | None = None) -> int:
    async def run(session: AsyncSession) -> int:
        return await generate_reminder_instances(session, organization_id=organization_id)

    return asyncio.run(_run_with_session(run))


@celery_app.task(name="generate_reminder_instances")
def generate_reminder_instances_task(organization_id: int | None = None) -> int:
    async def run(session: AsyncSession) -> int:
        return await generate_reminder_instances(session, organization_id=organization_id)

    return asyncio.run(_run_with_session(run))


@celery_app.task(name="process_due_reminder_instances")
def process_due_reminder_instances_task(organization_id: int | None = None) -> int:
    async def run(session: AsyncSession) -> int:
        if organization_id is not None:
            stats = await process_due_reminder_instances(session, organization_id)
            return int(stats.get("sent", 0))
        stats = await process_due_reminder_instances_all(session)
        return int(stats.get("sent", 0))

    return asyncio.run(_run_with_session(run))


@celery_app.task(name="run_reminder_engine_cycle")
def run_reminder_engine_cycle_task() -> dict[str, int]:
    return asyncio.run(_run_with_session(run_reminder_engine_cycle))


@celery_app.task(name="run_daily_policy_reminder_cycle")
def run_daily_policy_reminder_cycle_task() -> dict[str, int]:
    return asyncio.run(_run_with_session(run_reminder_engine_cycle))


@celery_app.task(name="process_renewal_escalations")
def process_renewal_escalations_task(organization_id: int | None = None) -> dict[str, int]:
    async def run(session: AsyncSession) -> dict[str, int]:
        if organization_id is not None:
            return await process_renewal_escalations(session, organization_id)
        return await process_renewal_escalations_all(session)

    return asyncio.run(_run_with_session(run))
