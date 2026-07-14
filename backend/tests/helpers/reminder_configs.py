"""Test helpers for seeding UI-driven reminder_configs."""

from __future__ import annotations

from datetime import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.reminder_config_service import ReminderConfigService, ReminderOffsetSetting
from app.utils.policy_reminder_stages import DEFAULT_REMINDER_OFFSETS

POLICY_TEMPLATE_KEY = "policy_renewal_reminder"


async def seed_entity_reminder_settings(
    session: AsyncSession,
    *,
    organization_id: int,
    entity_type: str,
    entity_id: int,
    channels: list[str] | None = None,
    offsets: list[int] | None = None,
    offset_unit: str = "days",
    template_key: str = "generic_reminder",
    entity_label: str | None = None,
    sender_name: str | None = None,
    dnd_start: time | None = None,
    dnd_end: time | None = None,
):
    """Seed reminder_configs the same way the Reminder Settings UI would."""
    resolved_channels = channels or ["whatsapp"]
    resolved_offsets = offsets if offsets is not None else list(DEFAULT_REMINDER_OFFSETS)
    service = ReminderConfigService(session)
    return await service.save_entity_settings(
        organization_id=organization_id,
        entity_type=entity_type,
        entity_id=entity_id,
        channels=resolved_channels,
        offsets=[
            ReminderOffsetSetting(offset_value=value, offset_unit=offset_unit)
            for value in resolved_offsets
        ],
        template_key=template_key,
        entity_label=entity_label,
        sender_name=sender_name,
        dnd_start=dnd_start,
        dnd_end=dnd_end,
    )


async def seed_policy_reminder_settings(
    session: AsyncSession,
    *,
    organization_id: int,
    policy_id: int,
    policy_type: str = "health",
    channels: list[str] | None = None,
    offsets: list[int] | None = None,
    sender_name: str | None = None,
):
    return await seed_entity_reminder_settings(
        session,
        organization_id=organization_id,
        entity_type="policy",
        entity_id=policy_id,
        channels=channels,
        offsets=offsets,
        template_key=POLICY_TEMPLATE_KEY,
        entity_label=f"{policy_type} Renewal",
        sender_name=sender_name,
    )
