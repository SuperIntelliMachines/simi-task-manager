"""Generic reminder engine scheduler jobs (module-independent)."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reminder_config import ReminderConfig
from app.models.reminder_instance import ReminderInstance
from app.services.reminder_generator import ReminderGeneratorService
from app.services.reminder_processor import ReminderProcessorService
from app.utils.reminder_query_time import fetch_db_now

logger = logging.getLogger(__name__)


async def _org_ids_with_active_configs(session: AsyncSession) -> list[int]:
    result = await session.execute(
        select(ReminderConfig.organization_id)
        .where(ReminderConfig.is_active.is_(True))
        .distinct()
    )
    return list(result.scalars())


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


async def generate_reminder_instances(
    session: AsyncSession,
    *,
    organization_id: int | None = None,
) -> int:
    """
    Load active reminder_configs and create reminder_instances via resolvers.

    No module-specific logic — entity discovery is resolver-driven.
    """
    generator = ReminderGeneratorService(session)

    if organization_id is not None:
        created = await generator.generate_from_active_configs(organization_id=organization_id)
        return len(created)

    org_ids = await _org_ids_with_active_configs(session)
    if not org_ids:
        return 0

    total_created = 0
    for org_id in org_ids:
        created = await generator.generate_from_active_configs(
            organization_id=org_id,
            commit=False,
        )
        total_created += len(created)

    if total_created:
        await session.commit()

    logger.info(
        "[ReminderEngine] generated instances orgs=%s created=%s",
        len(org_ids),
        total_created,
    )
    return total_created


async def generate_reminder_instances_all(session: AsyncSession) -> int:
    return await generate_reminder_instances(session, organization_id=None)


async def process_due_reminder_instances(
    session: AsyncSession,
    organization_id: int,
) -> dict[str, int]:
    return await ReminderProcessorService(session).process_due_reminders(organization_id)


async def process_due_reminder_instances_all(session: AsyncSession) -> dict[str, int]:
    org_ids = await _org_ids_with_due_instances(session)
    totals = {"processed": 0, "sent": 0, "failed": 0}

    for org_id in org_ids:
        stats = await process_due_reminder_instances(session, org_id)
        for key in totals:
            totals[key] += int(stats.get(key, 0))

    logger.info(
        "[ReminderEngine] processed due instances orgs=%s stats=%s",
        len(org_ids),
        totals,
    )
    return totals


async def run_reminder_engine_cycle(session: AsyncSession) -> dict[str, int]:
    """Generate instances from configs, then process all due instances."""
    generated = await generate_reminder_instances_all(session)
    stats = await process_due_reminder_instances_all(session)
    return {"generated": generated, **stats}
