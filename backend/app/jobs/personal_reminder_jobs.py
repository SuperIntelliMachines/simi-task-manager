"""Scheduler jobs for Personal Reminders (independent module)."""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.personal_reminder_processor import PersonalReminderProcessorService

logger = logging.getLogger(__name__)


async def process_due_personal_reminders(session: AsyncSession) -> dict[str, int]:
    stats = await PersonalReminderProcessorService(session).process_due_reminders()
    logger.info(
        "[PersonalReminderJob] completed processed=%s sent=%s failed=%s",
        stats.get("processed", 0),
        stats.get("sent", 0),
        stats.get("failed", 0),
    )
    return stats
