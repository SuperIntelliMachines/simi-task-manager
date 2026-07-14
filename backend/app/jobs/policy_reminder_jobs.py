"""
Process due policy reminders via the generic reminder engine.

DEPRECATED: policy_reminders is no longer processed for new schedules.
Due sends are handled through reminder_instances + ReminderProcessorService.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reminder_instance import ReminderInstance
from app.services.policy_generic_reminder_service import PolicyGenericReminderService
from app.utils.reminder_query_time import fetch_db_now

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PolicyReminderJobResult:
    processed: int = 0
    fetched: int = 0
    failed: int = 0
    due_total: int = 0
    skipped: int = 0
    sent: int = 0


def _to_job_result(stats: dict[str, int]) -> PolicyReminderJobResult:
    processed = int(stats.get("sent", 0)) + int(stats.get("failed", 0))
    failed = int(stats.get("failed", 0))
    return PolicyReminderJobResult(
        processed=processed,
        fetched=int(stats.get("processed", 0)),
        failed=failed,
        due_total=int(stats.get("processed", 0)),
        skipped=0,
        sent=int(stats.get("sent", 0)),
    )


async def _org_ids_with_due_instances(session: AsyncSession) -> list[int]:
    now = await fetch_db_now(session)
    result = await session.execute(
        select(ReminderInstance.organization_id)
        .where(
            ReminderInstance.status == "PENDING",
            ReminderInstance.scheduled_at <= now,
        )
        .distinct()
    )
    return list(result.scalars())


async def process_due_policy_reminders(
    session: AsyncSession,
    organization_id: int,
) -> PolicyReminderJobResult:
    service = PolicyGenericReminderService(session)
    stats = await service.process_due_reminders(organization_id)
    result = _to_job_result(stats)
    logger.info(
        "[PolicyReminderJob] generic processor org_id=%s processed=%s sent=%s failed=%s",
        organization_id,
        stats.get("processed"),
        stats.get("sent"),
        stats.get("failed"),
    )
    return result


async def process_due_policy_reminders_all(session: AsyncSession) -> PolicyReminderJobResult:
    org_ids = await _org_ids_with_due_instances(session)
    if not org_ids:
        return PolicyReminderJobResult()

    service = PolicyGenericReminderService(session)
    totals = {"processed": 0, "sent": 0, "failed": 0}
    for org_id in org_ids:
        stats = await service.process_due_reminders(org_id)
        for key in totals:
            totals[key] += int(stats.get(key, 0))

    result = _to_job_result(totals)
    logger.info(
        "[PolicyReminderJob] generic processor all orgs=%s processed=%s sent=%s failed=%s",
        len(org_ids),
        totals["processed"],
        totals["sent"],
        totals["failed"],
    )
    return result
