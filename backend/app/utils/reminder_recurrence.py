"""Helpers for recurring reminder instance scheduling."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reminder_config import ReminderConfig
from app.models.reminder_instance import ReminderInstance
from app.utils.reminder_schedule import next_recurrence_at


async def count_sent_instances(
    session: AsyncSession,
    *,
    config_id: int,
    entity_id: int,
) -> int:
    result = await session.execute(
        select(func.count())
        .select_from(ReminderInstance)
        .where(
            ReminderInstance.config_id == int(config_id),
            ReminderInstance.entity_id == int(entity_id),
            ReminderInstance.status == "SENT",
        )
    )
    return int(result.scalar_one())


async def has_pending_instance(
    session: AsyncSession,
    *,
    config_id: int,
    entity_id: int,
) -> bool:
    result = await session.execute(
        select(func.count())
        .select_from(ReminderInstance)
        .where(
            ReminderInstance.config_id == int(config_id),
            ReminderInstance.entity_id == int(entity_id),
            ReminderInstance.status == "PENDING",
        )
    )
    return int(result.scalar_one()) > 0


async def instance_exists_at(
    session: AsyncSession,
    *,
    config_id: int,
    scheduled_at: datetime,
) -> bool:
    duplicate = await session.execute(
        select(ReminderInstance.id).where(
            ReminderInstance.config_id == int(config_id),
            ReminderInstance.scheduled_at == scheduled_at,
        )
    )
    return duplicate.scalar_one_or_none() is not None


def compute_next_recurrence_at(
    config: ReminderConfig,
    *,
    from_time: datetime,
) -> datetime | None:
    if not bool(getattr(config, "repeat_enabled", False)):
        return None
    value = getattr(config, "repeat_frequency_value", None)
    unit = getattr(config, "repeat_frequency_unit", None)
    if value is None or not unit:
        return None
    return next_recurrence_at(
        from_time=from_time,
        frequency_value=int(value),
        frequency_unit=str(unit),
    )


async def schedule_next_recurrence(
    session: AsyncSession,
    *,
    config: ReminderConfig,
    organization_id: int,
    entity_type: str,
    entity_id: int,
    from_time: datetime,
) -> ReminderInstance | None:
    """Create the next PENDING instance when recurrence is enabled."""
    if not bool(getattr(config, "repeat_enabled", False)):
        return None

    next_at = compute_next_recurrence_at(config, from_time=from_time)
    if next_at is None:
        return None
    if await instance_exists_at(session, config_id=int(config.id), scheduled_at=next_at):
        return None

    instance = ReminderInstance(
        config_id=config.id,
        organization_id=int(organization_id),
        entity_type=(entity_type or "").strip().lower(),
        entity_id=int(entity_id),
        scheduled_at=next_at,
        status="PENDING",
    )
    session.add(instance)
    return instance
