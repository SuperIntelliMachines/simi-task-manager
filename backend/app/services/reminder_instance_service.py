"""Generic reminder instance operations for the reminder engine."""

from __future__ import annotations

import logging

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reminder_instance import ReminderInstance
from app.utils.datetime_utils import utcnow_naive

logger = logging.getLogger(__name__)


async def cancel_pending_reminder_instances(
    session: AsyncSession,
    *,
    organization_id: int,
    entity_type: str,
    entity_id: int,
) -> int:
    """Cancel pending reminder_instances for any entity type."""
    now = utcnow_naive()
    normalized_type = (entity_type or "").strip().lower()
    result = await session.execute(
        update(ReminderInstance)
        .where(
            ReminderInstance.organization_id == organization_id,
            ReminderInstance.entity_type == normalized_type,
            ReminderInstance.entity_id == entity_id,
            ReminderInstance.status == "PENDING",
        )
        .values(status="CANCELED", updated_at=now)
    )
    cancelled = int(result.rowcount or 0)
    logger.info(
        "[ReminderInstance] cancelled pending org=%s type=%s entity_id=%s count=%s",
        organization_id,
        normalized_type,
        entity_id,
        cancelled,
    )
    return cancelled
