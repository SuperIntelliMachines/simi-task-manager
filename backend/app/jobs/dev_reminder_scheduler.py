from __future__ import annotations

import asyncio
import logging

from app.core.database import AsyncSessionLocal
from app.jobs.personal_reminder_jobs import process_due_personal_reminders
from app.jobs.reminder_engine_jobs import (
    generate_reminder_instances_all,
    process_due_reminder_instances_all,
)
from app.jobs.reminder_jobs import process_due_reminders_all

logger = logging.getLogger(__name__)

DEV_REMINDER_INTERVAL_SECONDS = 60


async def run_dev_reminder_cycle() -> tuple[int, int, int, dict[str, int]]:
    async with AsyncSessionLocal() as session:
        generated = await generate_reminder_instances_all(session)
        engine_stats = await process_due_reminder_instances_all(session)
        lead_count = await process_due_reminders_all(session)
        personal_stats = await process_due_personal_reminders(session)
    logger.info(
        "[ReminderScheduler] Generated %s reminder instances; processed %s engine sends; "
        "%s lead reminders; personal processed=%s sent=%s failed=%s",
        generated,
        engine_stats.get("sent", 0),
        lead_count,
        personal_stats.get("processed", 0),
        personal_stats.get("sent", 0),
        personal_stats.get("failed", 0),
    )
    return generated, int(engine_stats.get("sent", 0)), lead_count, personal_stats


async def dev_reminder_scheduler_loop(stop_event: asyncio.Event) -> None:
    logger.info(
        "[ReminderScheduler] Dev reminder scheduler started (interval=%ss)",
        DEV_REMINDER_INTERVAL_SECONDS,
    )
    while not stop_event.is_set():
        try:
            await run_dev_reminder_cycle()
        except Exception:
            logger.exception("[ReminderScheduler] Reminder cycle failed; continuing")

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=DEV_REMINDER_INTERVAL_SECONDS)
            break
        except asyncio.TimeoutError:
            continue

    logger.info("[ReminderScheduler] Dev reminder scheduler stopped")


def start_dev_reminder_scheduler() -> tuple[asyncio.Task[None], asyncio.Event]:
    stop_event = asyncio.Event()
    task = asyncio.create_task(dev_reminder_scheduler_loop(stop_event), name="dev-reminder-scheduler")
    return task, stop_event
