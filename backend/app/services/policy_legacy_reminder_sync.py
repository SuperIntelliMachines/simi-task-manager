"""DEPRECATED: Legacy insurance → reminder_configs sync for migration and repair jobs only.

New reminder schedules must be created via ReminderConfigService.save_entity_settings()
from the common Reminder Settings UI — not from insurance policy fields.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import time
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import Organization
from app.models.reminder_config import ReminderConfig
from app.models.verticals import InsurancePolicy
from app.services.reminder_config_service import ReminderConfigService
from app.utils.datetime_utils import utcnow_naive
from app.utils.policy_reminder_stages import (
    DEFAULT_REMINDER_OFFSETS,
    REMINDER_TYPE_DEFAULT,
    REMINDER_TYPE_PERSONALIZED,
    _reminder_field,
)
from app.utils.preferred_channels import resolve_policy_reminder_channels

logger = logging.getLogger(__name__)

POLICY_ENTITY_TYPE = "policy"
POLICY_TEMPLATE_KEY = "policy_renewal_reminder"


@dataclass(frozen=True)
class ReminderOffsetSpec:
    offset_value: int
    offset_unit: str
    dnd_start: time | None = None
    dnd_end: time | None = None


def _policy_entity_label(policy: InsurancePolicy) -> str:
    policy_type = (policy.policy_type or "Policy").strip()
    return f"{policy_type} Renewal"


def _normalize_custom_reminder_items(custom_reminders: list[Any] | None) -> list[Any]:
    if not custom_reminders:
        return []
    return list(custom_reminders)


def _resolve_custom_reminders_for_sync(
    policy: InsurancePolicy,
    custom_reminders: list[Any] | None,
) -> list[Any] | None:
    """
    Return explicit custom reminders when provided.

    When ``custom_reminders`` is ``None``, fall back to the policy relationship
    (if loaded). ``None`` means "caller did not specify" — not "clear schedule".
    """
    if custom_reminders is not None:
        return _normalize_custom_reminder_items(custom_reminders)
    loaded = list(getattr(policy, "custom_reminders", None) or [])
    if loaded:
        return loaded
    return None


def build_offset_specs_from_policy(
    policy: InsurancePolicy,
    *,
    custom_reminders: list[Any] | None = None,
) -> list[ReminderOffsetSpec]:
    """Derive generic reminder offset specs from legacy policy reminder settings."""
    mode = (getattr(policy, "reminder_type", None) or REMINDER_TYPE_DEFAULT).strip().lower()
    dnd_start = getattr(policy, "dnd_start_time", None)
    dnd_end = getattr(policy, "dnd_end_time", None)
    resolved_custom = _resolve_custom_reminders_for_sync(policy, custom_reminders)

    if mode == REMINDER_TYPE_PERSONALIZED:
        if resolved_custom is not None and resolved_custom:
            specs: list[ReminderOffsetSpec] = []
            seen: set[tuple[str, int]] = set()
            for item in resolved_custom:
                unit = str(_reminder_field(item, "reminder_unit") or "days").strip().lower()
                raw_value = _reminder_field(item, "reminder_value")
                if raw_value is None or int(raw_value) <= 0:
                    continue
                value = int(raw_value)
                key = (unit, value)
                if key in seen:
                    continue
                seen.add(key)
                specs.append(
                    ReminderOffsetSpec(
                        offset_value=value,
                        offset_unit=unit,
                        dnd_start=dnd_start,
                        dnd_end=dnd_end,
                    )
                )
            if specs:
                return specs

        unit = str(getattr(policy, "reminder_unit", None) or "days").strip().lower()
        raw_value = getattr(policy, "reminder_value", None)
        if raw_value is not None and int(raw_value) > 0:
            return [
                ReminderOffsetSpec(
                    offset_value=int(raw_value),
                    offset_unit=unit,
                    dnd_start=dnd_start,
                    dnd_end=dnd_end,
                )
            ]
        return []

    return [
        ReminderOffsetSpec(offset_value=offset, offset_unit="days", dnd_start=dnd_start, dnd_end=dnd_end)
        for offset in DEFAULT_REMINDER_OFFSETS
    ]


class PolicyLegacyReminderSyncService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self._config_service = ReminderConfigService(session)

    async def _resolve_sender_name(self, policy: InsurancePolicy) -> str:
        org = await self.session.get(Organization, policy.organization_id)
        if org is not None and (org.name or "").strip():
            return org.name.strip()
        return "SIMI Insurance"

    async def _list_entity_configs(self, policy: InsurancePolicy) -> list[ReminderConfig]:
        result = await self.session.execute(
            select(ReminderConfig).where(
                ReminderConfig.organization_id == policy.organization_id,
                ReminderConfig.entity_type == POLICY_ENTITY_TYPE,
                ReminderConfig.entity_id == policy.id,
            )
        )
        return list(result.scalars())

    async def _offset_specs_from_entity_configs(
        self,
        policy: InsurancePolicy,
    ) -> list[ReminderOffsetSpec]:
        specs: list[ReminderOffsetSpec] = []
        seen: set[tuple[str, int, str]] = set()
        for config in await self._list_entity_configs(policy):
            key = (config.offset_unit, config.offset_value, config.channel)
            if key in seen:
                continue
            seen.add(key)
            specs.append(
                ReminderOffsetSpec(
                    offset_value=config.offset_value,
                    offset_unit=config.offset_unit,
                    dnd_start=config.dnd_start,
                    dnd_end=config.dnd_end,
                )
            )
        return specs

    async def deactivate_entity_configs(
        self,
        *,
        organization_id: int,
        entity_id: int,
    ) -> int:
        """Deactivate all reminder configs for an entity (e.g. when no offsets remain)."""
        now = utcnow_naive()
        result = await self.session.execute(
            update(ReminderConfig)
            .where(
                ReminderConfig.organization_id == organization_id,
                ReminderConfig.entity_type == POLICY_ENTITY_TYPE,
                ReminderConfig.entity_id == entity_id,
                ReminderConfig.is_active.is_(True),
            )
            .values(is_active=False, updated_at=now)
            .execution_options(synchronize_session="fetch")
        )
        return int(result.rowcount or 0)

    async def _deactivate_stale_configs(
        self,
        *,
        organization_id: int,
        entity_id: int,
        keep_config_ids: list[int],
    ) -> int:
        """Deactivate active configs for the entity that are not in the synced set."""
        if not keep_config_ids:
            return 0

        now = utcnow_naive()
        result = await self.session.execute(
            update(ReminderConfig)
            .where(
                ReminderConfig.organization_id == organization_id,
                ReminderConfig.entity_type == POLICY_ENTITY_TYPE,
                ReminderConfig.entity_id == entity_id,
                ReminderConfig.is_active.is_(True),
                ReminderConfig.id.not_in(keep_config_ids),
            )
            .values(is_active=False, updated_at=now)
            .execution_options(synchronize_session="fetch")
        )
        return int(result.rowcount or 0)

    async def sync_policy_reminder_configs(
        self,
        policy: InsurancePolicy,
        *,
        custom_reminders: list[Any] | None = None,
    ) -> list[ReminderConfig]:
        """
        Replace active generic reminder configs for a policy from its reminder settings.

        New insurance scheduling uses reminder_configs only (not policy_custom_reminders /
        policy_reminders for config storage).
        """
        if policy.id is None:
            await self.session.flush()

        channels = resolve_policy_reminder_channels(getattr(policy, "preferred_channel", None))
        if not channels:
            channels = ["whatsapp"]

        resolved_custom = _resolve_custom_reminders_for_sync(policy, custom_reminders)
        offset_specs = build_offset_specs_from_policy(policy, custom_reminders=resolved_custom)
        if not offset_specs and resolved_custom is None:
            offset_specs = await self._offset_specs_from_entity_configs(policy)

        if not offset_specs:
            if resolved_custom is not None and len(resolved_custom) == 0:
                await self.deactivate_entity_configs(
                    organization_id=policy.organization_id,
                    entity_id=policy.id,
                )
            await self.session.flush()
            return await self._list_entity_configs(policy)

        sender_name = await self._resolve_sender_name(policy)
        entity_label = _policy_entity_label(policy)
        synced: list[ReminderConfig] = []
        now = utcnow_naive()

        for channel in channels:
            for spec in offset_specs:
                result = await self.session.execute(
                    select(ReminderConfig).where(
                        ReminderConfig.organization_id == policy.organization_id,
                        ReminderConfig.entity_type == POLICY_ENTITY_TYPE,
                        ReminderConfig.entity_id == policy.id,
                        ReminderConfig.channel == channel,
                        ReminderConfig.offset_value == spec.offset_value,
                        ReminderConfig.offset_unit == spec.offset_unit,
                    )
                )
                existing = result.scalar_one_or_none()
                if existing is not None:
                    await self.session.refresh(existing)
                    existing.is_active = True
                    existing.entity_label = entity_label
                    existing.sender_name = sender_name
                    existing.template_key = POLICY_TEMPLATE_KEY
                    existing.dnd_start = spec.dnd_start
                    existing.dnd_end = spec.dnd_end
                    existing.updated_at = now
                    synced.append(existing)
                    continue

                config = ReminderConfig(
                    organization_id=policy.organization_id,
                    entity_type=POLICY_ENTITY_TYPE,
                    entity_id=policy.id,
                    channel=channel,
                    template_key=POLICY_TEMPLATE_KEY,
                    entity_label=entity_label,
                    sender_name=sender_name,
                    offset_value=spec.offset_value,
                    offset_unit=spec.offset_unit,
                    dnd_start=spec.dnd_start,
                    dnd_end=spec.dnd_end,
                    is_active=True,
                    created_at=now,
                    updated_at=now,
                )
                self.session.add(config)
                synced.append(config)

        await self.session.flush()

        synced_ids: list[int] = []
        for config in synced:
            if config.id is None:
                await self.session.refresh(config)
            if config.id is not None:
                synced_ids.append(config.id)

        if synced_ids:
            await self.session.execute(
                update(ReminderConfig)
                .where(ReminderConfig.id.in_(synced_ids))
                .values(is_active=True, updated_at=now)
                .execution_options(synchronize_session="fetch")
            )
            for config in synced:
                config.is_active = True

        await self._deactivate_stale_configs(
            organization_id=policy.organization_id,
            entity_id=policy.id,
            keep_config_ids=synced_ids,
        )

        logger.info(
            "[PolicyLegacyReminderSync] synced configs policy_id=%s channel_count=%s offset_count=%s created=%s",
            policy.id,
            len(channels),
            len(offset_specs),
            len(synced),
        )
        return synced


async def sync_policy_reminder_configs_from_policy(
    session: AsyncSession,
    policy: InsurancePolicy,
    *,
    custom_reminders: list[Any] | None = None,
) -> list[ReminderConfig]:
    """Deprecated one-shot sync from policy reminder fields → reminder_configs."""
    return await PolicyLegacyReminderSyncService(session).sync_policy_reminder_configs(
        policy,
        custom_reminders=custom_reminders,
    )
