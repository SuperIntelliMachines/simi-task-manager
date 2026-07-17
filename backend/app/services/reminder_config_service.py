from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, time
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import (
    DEFAULT_REMINDER_ANCHOR_KEY,
    DEFAULT_REMINDER_STOP_CONDITION,
    ReminderAnchorType,
    ReminderOffsetDirection,
)
from app.models.reminder_config import ReminderConfig
from app.utils.datetime_utils import normalize_to_utc_naive, utcnow_naive
from app.utils.reminder_config_validation import validate_anchor_fields, validate_scheduling_fields
from app.utils.reminder_recurrence_validation import validate_recurrence_fields


@dataclass(frozen=True)
class ReminderOffsetSetting:
    offset_value: int
    offset_unit: str = "days"
    time_of_day: time | None = None
    anchor_type: str = ReminderAnchorType.DATE.value
    anchor_key: str = DEFAULT_REMINDER_ANCHOR_KEY
    offset_direction: str = ReminderOffsetDirection.BEFORE.value


@dataclass(frozen=True)
class ReminderDefinitionSetting:
    channels: list[str]
    offset_value: int | None = None
    offset_unit: str | None = "days"
    time_of_day: time | None = None
    scheduled_at: datetime | None = None
    anchor_type: str = ReminderAnchorType.DATE.value
    anchor_key: str = DEFAULT_REMINDER_ANCHOR_KEY
    offset_direction: str = ReminderOffsetDirection.BEFORE.value
    repeat_enabled: bool = False
    repeat_frequency_value: int | None = None
    repeat_frequency_unit: str | None = None
    max_attempts: int | None = None
    stop_condition: str = DEFAULT_REMINDER_STOP_CONDITION
    stop_condition_config: dict[str, object] | None = None


class ReminderConfigService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _find_config(
        self,
        *,
        organization_id: int,
        entity_type: str,
        entity_id: int,
        channel: str,
        offset_value: int,
        offset_unit: str,
        time_of_day: time | None,
        absolute_scheduled_at: datetime | None,
        anchor_type: str,
        anchor_key: str,
        offset_direction: str,
    ) -> ReminderConfig | None:
        normalized_type = (entity_type or "").strip().lower()
        query = select(ReminderConfig).where(
            ReminderConfig.organization_id == organization_id,
            ReminderConfig.entity_type == normalized_type,
            ReminderConfig.entity_id == entity_id,
            ReminderConfig.channel == channel,
            ReminderConfig.anchor_type == anchor_type,
            ReminderConfig.anchor_key == anchor_key,
            ReminderConfig.offset_direction == offset_direction,
        )
        if absolute_scheduled_at is not None:
            query = query.where(
                ReminderConfig.absolute_scheduled_at == normalize_to_utc_naive(absolute_scheduled_at)
            )
        else:
            query = query.where(
                ReminderConfig.offset_value == offset_value,
                ReminderConfig.offset_unit == offset_unit,
                ReminderConfig.absolute_scheduled_at.is_(None),
            )
            if time_of_day is None:
                query = query.where(ReminderConfig.time_of_day.is_(None))
            else:
                query = query.where(ReminderConfig.time_of_day == time_of_day)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def _find_active_duplicate(
        self,
        *,
        organization_id: int,
        entity_type: str,
        entity_id: int,
        channel: str,
        offset_value: int,
        anchor_type: str,
        anchor_key: str,
        offset_direction: str,
    ) -> ReminderConfig | None:
        result = await self.session.execute(
            select(ReminderConfig).where(
                ReminderConfig.organization_id == organization_id,
                ReminderConfig.entity_type == entity_type,
                ReminderConfig.entity_id == entity_id,
                ReminderConfig.channel == channel,
                ReminderConfig.offset_value == offset_value,
                ReminderConfig.anchor_type == anchor_type,
                ReminderConfig.anchor_key == anchor_key,
                ReminderConfig.offset_direction == offset_direction,
                ReminderConfig.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def _upsert_config(
        self,
        *,
        organization_id: int,
        entity_type: str,
        entity_id: int,
        channel: str,
        offset_value: int,
        offset_unit: str,
        time_of_day: time | None,
        absolute_scheduled_at: datetime | None,
        anchor_type: str,
        anchor_key: str,
        offset_direction: str,
        template_key: str | None,
        entity_label: str | None,
        sender_name: str | None,
        template_variables: dict[str, Any] | None,
        recipient_data: dict[str, Any] | None,
        dnd_start: time | None,
        dnd_end: time | None,
        repeat_enabled: bool,
        repeat_frequency_value: int | None,
        repeat_frequency_unit: str | None,
        max_attempts: int | None,
        stop_condition: str,
        stop_condition_config: dict[str, object] | None,
        now: datetime,
        synced: list[ReminderConfig],
    ) -> None:
        resolved_template_variables = dict(template_variables or {})
        resolved_recipient_data = dict(recipient_data or {})
        existing = await self._find_config(
            organization_id=organization_id,
            entity_type=entity_type,
            entity_id=entity_id,
            channel=channel,
            offset_value=offset_value,
            offset_unit=offset_unit,
            time_of_day=time_of_day,
            absolute_scheduled_at=absolute_scheduled_at,
            anchor_type=anchor_type,
            anchor_key=anchor_key,
            offset_direction=offset_direction,
        )
        if existing is not None:
            existing.is_active = True
            if entity_label is not None:
                existing.entity_label = entity_label
            if sender_name is not None:
                existing.sender_name = sender_name
            if template_key is not None:
                existing.template_key = template_key
            if template_variables is not None:
                existing.template_variables = resolved_template_variables
            if recipient_data is not None:
                existing.recipient_data = resolved_recipient_data
            existing.dnd_start = dnd_start
            existing.dnd_end = dnd_end
            existing.offset_value = offset_value
            existing.offset_unit = offset_unit
            existing.time_of_day = time_of_day
            existing.absolute_scheduled_at = absolute_scheduled_at
            existing.anchor_type = anchor_type
            existing.anchor_key = anchor_key
            existing.offset_direction = offset_direction
            existing.repeat_enabled = repeat_enabled
            existing.repeat_frequency_value = repeat_frequency_value
            existing.repeat_frequency_unit = repeat_frequency_unit
            existing.max_attempts = max_attempts
            existing.stop_condition = stop_condition
            existing.stop_condition_config = stop_condition_config
            existing.updated_at = now
            synced.append(existing)
            return

        config = ReminderConfig(
            organization_id=organization_id,
            entity_type=entity_type,
            entity_id=entity_id,
            channel=channel,
            template_key=template_key,
            entity_label=entity_label,
            sender_name=sender_name,
            template_variables=resolved_template_variables,
            recipient_data=resolved_recipient_data,
            anchor_type=anchor_type,
            anchor_key=anchor_key,
            offset_direction=offset_direction,
            offset_value=offset_value,
            offset_unit=offset_unit,
            time_of_day=time_of_day,
            absolute_scheduled_at=absolute_scheduled_at,
            dnd_start=dnd_start,
            dnd_end=dnd_end,
            repeat_enabled=repeat_enabled,
            repeat_frequency_value=repeat_frequency_value,
            repeat_frequency_unit=repeat_frequency_unit,
            max_attempts=max_attempts,
            stop_condition=stop_condition,
            stop_condition_config=stop_condition_config,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        self.session.add(config)
        synced.append(config)

    async def save_entity_definitions(
        self,
        *,
        organization_id: int,
        entity_type: str,
        entity_id: int,
        definitions: list[ReminderDefinitionSetting],
        template_key: str | None = None,
        entity_label: str | None = None,
        sender_name: str | None = None,
        template_variables: dict[str, Any] | None = None,
        recipient_data: dict[str, Any] | None = None,
        dnd_start: time | None = None,
        dnd_end: time | None = None,
        commit: bool = True,
        replace_existing: bool = True,
    ) -> list[ReminderConfig]:
        """Upsert reminder_configs for an entity.

        When ``replace_existing`` is True (default), any other active configs for the
        same entity that are not in this payload are deactivated — used by Settings UI.

        When ``replace_existing`` is False, only the provided definitions are upserted
        and existing sibling configs are left untouched — used by Create Reminder.
        """
        normalized_type = (entity_type or "").strip().lower()
        if not definitions:
            if replace_existing:
                await self.deactivate_entity_configs(
                    organization_id=organization_id,
                    entity_type=normalized_type,
                    entity_id=entity_id,
                    commit=False,
                )
            if commit:
                await self.session.commit()
            return []

        now = utcnow_naive()
        synced: list[ReminderConfig] = []

        for definition in definitions:
            mode, offset_value, offset_unit, time_of_day, absolute_scheduled_at = validate_scheduling_fields(
                offset_value=definition.offset_value,
                offset_unit=definition.offset_unit,
                time_of_day=definition.time_of_day,
                absolute_scheduled_at=definition.scheduled_at,
            )
            anchor_type, anchor_key, offset_direction = validate_anchor_fields(
                anchor_type=definition.anchor_type,
                anchor_key=definition.anchor_key,
                offset_direction=definition.offset_direction,
            )
            (
                repeat_enabled,
                repeat_frequency_value,
                repeat_frequency_unit,
                max_attempts,
                stop_condition,
                stop_condition_config,
            ) = validate_recurrence_fields(
                repeat_enabled=definition.repeat_enabled,
                repeat_frequency_value=definition.repeat_frequency_value,
                repeat_frequency_unit=definition.repeat_frequency_unit,
                max_attempts=definition.max_attempts,
                stop_condition=definition.stop_condition,
                stop_condition_config=definition.stop_condition_config,
            )
            normalized_channels = [
                (channel or "").strip().lower() for channel in definition.channels if (channel or "").strip()
            ]
            if not normalized_channels:
                raise ValueError("at least one channel is required per reminder definition")

            if mode == "absolute":
                stored_offset_value = 0
                stored_offset_unit = "days"
                stored_absolute = normalize_to_utc_naive(absolute_scheduled_at)
                stored_time_of_day = None
            else:
                stored_offset_value = int(offset_value or 0)
                stored_offset_unit = str(offset_unit or "days")
                stored_absolute = None
                stored_time_of_day = time_of_day

            for channel in normalized_channels:
                await self._upsert_config(
                    organization_id=organization_id,
                    entity_type=normalized_type,
                    entity_id=entity_id,
                    channel=channel,
                    offset_value=stored_offset_value,
                    offset_unit=stored_offset_unit,
                    time_of_day=stored_time_of_day,
                    absolute_scheduled_at=stored_absolute,
                    anchor_type=anchor_type,
                    anchor_key=anchor_key,
                    offset_direction=offset_direction,
                    template_key=template_key,
                    entity_label=entity_label,
                    sender_name=sender_name,
                    template_variables=template_variables,
                    recipient_data=recipient_data,
                    dnd_start=dnd_start,
                    dnd_end=dnd_end,
                    repeat_enabled=repeat_enabled,
                    repeat_frequency_value=repeat_frequency_value,
                    repeat_frequency_unit=repeat_frequency_unit,
                    max_attempts=max_attempts,
                    stop_condition=stop_condition,
                    stop_condition_config=stop_condition_config,
                    now=now,
                    synced=synced,
                )

        await self.session.flush()

        synced_ids: list[int] = []
        for config in synced:
            if config.id is None:
                await self.session.refresh(config)
            if config.id is not None:
                synced_ids.append(config.id)

        if replace_existing and synced_ids:
            await self.deactivate_stale_entity_configs(
                organization_id=organization_id,
                entity_type=normalized_type,
                entity_id=entity_id,
                keep_config_ids=synced_ids,
                commit=False,
            )

        if commit:
            await self.session.commit()
            for config in synced:
                await self.session.refresh(config)

        return synced

    async def save_entity_settings(
        self,
        *,
        organization_id: int,
        entity_type: str,
        entity_id: int,
        channels: list[str],
        offsets: list[ReminderOffsetSetting],
        template_key: str | None = None,
        entity_label: str | None = None,
        sender_name: str | None = None,
        template_variables: dict[str, Any] | None = None,
        recipient_data: dict[str, Any] | None = None,
        dnd_start: time | None = None,
        dnd_end: time | None = None,
        commit: bool = True,
        # Optional entity-level defaults when offsets omit anchor fields
        anchor_type: str | None = None,
        anchor_key: str | None = None,
        offset_direction: str | None = None,
    ) -> list[ReminderConfig]:
        """
        UI-driven upsert for reminder_configs.

        Creates or reactivates rows for each channel × offset combination and
        deactivates any other active configs for the same entity.
        """
        normalized_type = (entity_type or "").strip().lower()
        normalized_channels = [(channel or "").strip().lower() for channel in channels if (channel or "").strip()]
        if not normalized_channels:
            raise ValueError("at least one channel is required")
        if not offsets:
            await self.deactivate_entity_configs(
                organization_id=organization_id,
                entity_type=normalized_type,
                entity_id=entity_id,
                commit=False,
            )
            if commit:
                await self.session.commit()
            return []

        default_anchor_type, default_anchor_key, default_offset_direction = validate_anchor_fields(
            anchor_type=anchor_type,
            anchor_key=anchor_key,
            offset_direction=offset_direction,
        )

        definitions = [
            ReminderDefinitionSetting(
                channels=normalized_channels,
                offset_value=offset.offset_value,
                offset_unit=offset.offset_unit,
                time_of_day=offset.time_of_day,
                anchor_type=offset.anchor_type or default_anchor_type,
                anchor_key=offset.anchor_key or default_anchor_key,
                offset_direction=offset.offset_direction or default_offset_direction,
            )
            for offset in offsets
        ]
        return await self.save_entity_definitions(
            organization_id=organization_id,
            entity_type=normalized_type,
            entity_id=entity_id,
            definitions=definitions,
            template_key=template_key,
            entity_label=entity_label,
            sender_name=sender_name,
            template_variables=template_variables,
            recipient_data=recipient_data,
            dnd_start=dnd_start,
            dnd_end=dnd_end,
            commit=commit,
        )

    async def deactivate_stale_entity_configs(
        self,
        *,
        organization_id: int,
        entity_type: str,
        entity_id: int,
        keep_config_ids: list[int],
        commit: bool = True,
    ) -> int:
        if not keep_config_ids:
            return 0

        now = utcnow_naive()
        normalized_type = (entity_type or "").strip().lower()
        result = await self.session.execute(
            update(ReminderConfig)
            .where(
                ReminderConfig.organization_id == organization_id,
                ReminderConfig.entity_type == normalized_type,
                ReminderConfig.entity_id == entity_id,
                ReminderConfig.is_active.is_(True),
                ReminderConfig.id.not_in(keep_config_ids),
            )
            .values(is_active=False, updated_at=now)
            .execution_options(synchronize_session="fetch")
        )
        if commit:
            await self.session.commit()
        return int(result.rowcount or 0)

    async def deactivate_entity_configs(
        self,
        *,
        organization_id: int,
        entity_type: str,
        entity_id: int,
        commit: bool = True,
    ) -> int:
        now = utcnow_naive()
        normalized_type = (entity_type or "").strip().lower()
        result = await self.session.execute(
            update(ReminderConfig)
            .where(
                ReminderConfig.organization_id == organization_id,
                ReminderConfig.entity_type == normalized_type,
                ReminderConfig.entity_id == entity_id,
                ReminderConfig.is_active.is_(True),
            )
            .values(is_active=False, updated_at=now)
            .execution_options(synchronize_session="fetch")
        )
        if commit:
            await self.session.commit()
        return int(result.rowcount or 0)

    async def create_configs(
        self,
        *,
        organization_id: int,
        entity_type: str,
        entity_id: int,
        channel: str,
        offsets: list[int],
        offset_unit: str = "days",
        dnd_start: time | None = None,
        dnd_end: time | None = None,
        template_key: str | None = None,
        entity_label: str | None = None,
        sender_name: str | None = None,
        template_variables: dict[str, Any] | None = None,
        recipient_data: dict[str, Any] | None = None,
        anchor_type: str | None = None,
        anchor_key: str | None = None,
        offset_direction: str | None = None,
        commit: bool = True,
    ) -> list[ReminderConfig]:
        """Backward-compatible create API — prefer save_entity_settings for UI sync."""
        created: list[ReminderConfig] = []
        now = utcnow_naive()
        resolved_anchor_type, resolved_anchor_key, resolved_offset_direction = validate_anchor_fields(
            anchor_type=anchor_type,
            anchor_key=anchor_key,
            offset_direction=offset_direction,
        )
        resolved_template_variables = dict(template_variables or {})
        resolved_recipient_data = dict(recipient_data or {})

        for offset_value in offsets:
            existing = await self._find_active_duplicate(
                organization_id=organization_id,
                entity_type=entity_type,
                entity_id=entity_id,
                channel=channel,
                offset_value=offset_value,
                anchor_type=resolved_anchor_type,
                anchor_key=resolved_anchor_key,
                offset_direction=resolved_offset_direction,
            )
            if existing is not None:
                continue

            config = ReminderConfig(
                organization_id=organization_id,
                entity_type=entity_type,
                entity_id=entity_id,
                channel=channel,
                template_key=template_key,
                entity_label=entity_label,
                sender_name=sender_name,
                template_variables=resolved_template_variables,
                recipient_data=resolved_recipient_data,
                anchor_type=resolved_anchor_type,
                anchor_key=resolved_anchor_key,
                offset_direction=resolved_offset_direction,
                offset_value=offset_value,
                offset_unit=offset_unit,
                time_of_day=None,
                absolute_scheduled_at=None,
                dnd_start=dnd_start,
                dnd_end=dnd_end,
                is_active=True,
                created_at=now,
                updated_at=now,
            )
            self.session.add(config)
            created.append(config)

        if created and commit:
            await self.session.commit()
            for config in created:
                await self.session.refresh(config)
        elif created:
            await self.session.flush()

        return created

    async def list_active_configs(
        self,
        *,
        organization_id: int,
        entity_type: str,
        entity_id: int,
    ) -> list[ReminderConfig]:
        result = await self.session.execute(
            select(ReminderConfig)
            .where(
                ReminderConfig.organization_id == organization_id,
                ReminderConfig.entity_type == (entity_type or "").strip().lower(),
                ReminderConfig.entity_id == entity_id,
                ReminderConfig.is_active.is_(True),
            )
            .order_by(
                ReminderConfig.absolute_scheduled_at.desc().nullslast(),
                ReminderConfig.offset_value.desc(),
            )
        )
        return list(result.scalars())

    async def list_active_config_groups(
        self,
        *,
        organization_id: int,
        entity_type: str,
        entity_id: int,
    ) -> list[dict[str, object]]:
        rows = await self.list_active_configs(
            organization_id=organization_id,
            entity_type=entity_type,
            entity_id=entity_id,
        )
        grouped: dict[
            tuple[
                int,
                str,
                int,
                str,
                str,
                str,
                int,
                str,
                time | None,
                bool,
                bool,
                int | None,
                str | None,
                int | None,
                str,
            ],
            dict[str, object],
        ] = defaultdict(dict)
        for row in rows:
            key = (
                row.organization_id,
                row.entity_type,
                row.entity_id,
                row.anchor_type,
                row.anchor_key,
                row.offset_direction,
                row.offset_value,
                row.offset_unit,
                row.time_of_day,
                row.is_active,
                bool(getattr(row, "repeat_enabled", False)),
                getattr(row, "repeat_frequency_value", None),
                getattr(row, "repeat_frequency_unit", None),
                getattr(row, "max_attempts", None),
                getattr(row, "stop_condition", DEFAULT_REMINDER_STOP_CONDITION),
            )
            entry = grouped.get(key)
            if not entry:
                entry = {
                    "config_id": row.id,
                    "organization_id": row.organization_id,
                    "entity_type": row.entity_type,
                    "entity_id": row.entity_id,
                    "anchor_type": row.anchor_type,
                    "anchor_key": row.anchor_key,
                    "offset_direction": row.offset_direction,
                    "offset_value": row.offset_value,
                    "offset_unit": row.offset_unit,
                    "trigger_offset_value": row.offset_value,
                    "trigger_offset_unit": row.offset_unit,
                    "trigger_offset_direction": row.offset_direction,
                    "repeat_enabled": bool(getattr(row, "repeat_enabled", False)),
                    "repeat_frequency_value": getattr(row, "repeat_frequency_value", None),
                    "repeat_frequency_unit": getattr(row, "repeat_frequency_unit", None),
                    "max_attempts": getattr(row, "max_attempts", None),
                    "stop_condition": getattr(
                        row, "stop_condition", DEFAULT_REMINDER_STOP_CONDITION
                    ),
                    "stop_condition_config": getattr(row, "stop_condition_config", None),
                    "template_variables": dict(getattr(row, "template_variables", None) or {}),
                    "recipient_data": dict(getattr(row, "recipient_data", None) or {}),
                    "time_of_day": row.time_of_day,
                    "channels": [],
                    "is_active": row.is_active,
                }
                grouped[key] = entry
            channels = entry["channels"]
            if isinstance(channels, list):
                channels.append(row.channel)
        result = list(grouped.values())
        for item in result:
            item["channels"] = sorted(set(item.get("channels", [])))
        return result

    async def update_config(
        self,
        config_id: int,
        *,
        updates: dict[str, object],
    ) -> ReminderConfig:
        config = await self.session.get(ReminderConfig, config_id)
        if config is None:
            raise ValueError("reminder config not found")

        if "scheduled_at" in updates:
            updates["absolute_scheduled_at"] = normalize_to_utc_naive(
                updates.pop("scheduled_at")  # type: ignore[arg-type]
            )
            updates.setdefault("offset_value", 0)
            updates.setdefault("offset_unit", "days")
            updates["time_of_day"] = None

        if "template_variables" in updates:
            updates["template_variables"] = dict(updates.get("template_variables") or {})

        if "recipient_data" in updates:
            updates["recipient_data"] = dict(updates.get("recipient_data") or {})

        if any(key in updates for key in ("anchor_type", "anchor_key", "offset_direction")):
            anchor_type, anchor_key, offset_direction = validate_anchor_fields(
                anchor_type=updates.get("anchor_type", config.anchor_type),
                anchor_key=updates.get("anchor_key", config.anchor_key),
                offset_direction=updates.get("offset_direction", config.offset_direction),
            )
            if "anchor_type" in updates:
                updates["anchor_type"] = anchor_type
            if "anchor_key" in updates:
                updates["anchor_key"] = anchor_key
            if "offset_direction" in updates:
                updates["offset_direction"] = offset_direction

        for key, value in updates.items():
            setattr(config, key, value)
        config.updated_at = utcnow_naive()

        await self.session.commit()
        await self.session.refresh(config)
        return config

    async def update_config_with_channels(
        self,
        config_id: int,
        *,
        updates: dict[str, object],
        channels: list[str] | None,
    ) -> ReminderConfig:
        target = await self.session.get(ReminderConfig, config_id)
        if target is None:
            raise ValueError("reminder config not found")

        # Treat explicit null as "not provided" for backward compatibility.
        if "is_active" in updates and updates.get("is_active") is None:
            updates.pop("is_active", None)

        result = await self.session.execute(
            select(ReminderConfig).where(
                ReminderConfig.organization_id == target.organization_id,
                ReminderConfig.entity_type == target.entity_type,
                ReminderConfig.entity_id == target.entity_id,
                ReminderConfig.offset_value == target.offset_value,
                ReminderConfig.offset_unit == target.offset_unit,
                ReminderConfig.time_of_day == target.time_of_day,
                ReminderConfig.absolute_scheduled_at == target.absolute_scheduled_at,
                ReminderConfig.anchor_type == target.anchor_type,
                ReminderConfig.anchor_key == target.anchor_key,
                ReminderConfig.offset_direction == target.offset_direction,
                ReminderConfig.is_active.is_(True),
            )
        )
        original_active_rows = list(result.scalars())
        now = utcnow_naive()
        normalized_channels = sorted(set((channels or [])))
        desired_is_active = (
            bool(updates["is_active"])
            if "is_active" in updates
            else True
        )

        if "scheduled_at" in updates:
            updates["absolute_scheduled_at"] = normalize_to_utc_naive(updates.pop("scheduled_at"))  # type: ignore[arg-type]
            updates.setdefault("offset_value", 0)
            updates.setdefault("offset_unit", "days")
            updates["time_of_day"] = None

        if "template_variables" in updates:
            updates["template_variables"] = dict(updates.get("template_variables") or {})

        if "recipient_data" in updates:
            updates["recipient_data"] = dict(updates.get("recipient_data") or {})

        if any(key in updates for key in ("anchor_type", "anchor_key", "offset_direction")):
            anchor_type, anchor_key, offset_direction = validate_anchor_fields(
                anchor_type=updates.get("anchor_type", target.anchor_type),
                anchor_key=updates.get("anchor_key", target.anchor_key),
                offset_direction=updates.get("offset_direction", target.offset_direction),
            )
            if "anchor_type" in updates:
                updates["anchor_type"] = anchor_type
            if "anchor_key" in updates:
                updates["anchor_key"] = anchor_key
            if "offset_direction" in updates:
                updates["offset_direction"] = offset_direction

        for row in original_active_rows:
            # Apply non-channel field updates so these rows preserve latest metadata,
            # then deactivate them as the "replaced" configuration rows.
            for key, value in updates.items():
                if key != "is_active":
                    setattr(row, key, value)
            row.is_active = False
            row.updated_at = now

        if normalized_channels:
            desired_offset_value = int(updates.get("offset_value", target.offset_value))
            desired_offset_unit = str(updates.get("offset_unit", target.offset_unit))
            desired_time_of_day = updates.get("time_of_day", target.time_of_day)
            desired_absolute_at = updates.get("absolute_scheduled_at", target.absolute_scheduled_at)
            desired_dnd_start = updates.get("dnd_start", target.dnd_start)
            desired_dnd_end = updates.get("dnd_end", target.dnd_end)
            desired_anchor_type = str(updates.get("anchor_type", target.anchor_type))
            desired_anchor_key = str(updates.get("anchor_key", target.anchor_key))
            desired_offset_direction = str(
                updates.get("offset_direction", target.offset_direction)
            )

            existing_by_channel_result = await self.session.execute(
                select(ReminderConfig).where(
                    ReminderConfig.organization_id == target.organization_id,
                    ReminderConfig.entity_type == target.entity_type,
                    ReminderConfig.entity_id == target.entity_id,
                    ReminderConfig.offset_value == desired_offset_value,
                    ReminderConfig.offset_unit == desired_offset_unit,
                    ReminderConfig.time_of_day == desired_time_of_day,
                    ReminderConfig.absolute_scheduled_at == desired_absolute_at,
                    ReminderConfig.anchor_type == desired_anchor_type,
                    ReminderConfig.anchor_key == desired_anchor_key,
                    ReminderConfig.offset_direction == desired_offset_direction,
                    ReminderConfig.channel.in_(normalized_channels),
                )
            )
            existing_by_channel = {row.channel: row for row in list(existing_by_channel_result.scalars())}
            desired_template_variables = updates.get(
                "template_variables",
                getattr(target, "template_variables", None) or {},
            )
            if not isinstance(desired_template_variables, dict):
                desired_template_variables = {}
            desired_recipient_data = updates.get(
                "recipient_data",
                getattr(target, "recipient_data", None) or {},
            )
            if not isinstance(desired_recipient_data, dict):
                desired_recipient_data = {}

            for channel in normalized_channels:
                existing = existing_by_channel.get(channel)
                if existing is not None:
                    existing.is_active = desired_is_active
                    existing.entity_label = target.entity_label
                    existing.sender_name = target.sender_name
                    existing.template_variables = dict(desired_template_variables)
                    existing.recipient_data = dict(desired_recipient_data)
                    existing.offset_value = desired_offset_value
                    existing.offset_unit = desired_offset_unit
                    existing.time_of_day = desired_time_of_day
                    existing.absolute_scheduled_at = desired_absolute_at
                    existing.anchor_type = desired_anchor_type
                    existing.anchor_key = desired_anchor_key
                    existing.offset_direction = desired_offset_direction
                    existing.dnd_start = desired_dnd_start
                    existing.dnd_end = desired_dnd_end
                    existing.updated_at = now
                    continue
                config = ReminderConfig(
                    organization_id=target.organization_id,
                    entity_type=target.entity_type,
                    entity_id=target.entity_id,
                    channel=channel,
                    template_key=target.template_key,
                    entity_label=target.entity_label,
                    sender_name=target.sender_name,
                    template_variables=dict(desired_template_variables),
                    recipient_data=dict(desired_recipient_data),
                    anchor_type=desired_anchor_type,
                    anchor_key=desired_anchor_key,
                    offset_direction=desired_offset_direction,
                    offset_value=desired_offset_value,
                    offset_unit=desired_offset_unit,
                    time_of_day=desired_time_of_day,
                    absolute_scheduled_at=desired_absolute_at,
                    dnd_start=desired_dnd_start,
                    dnd_end=desired_dnd_end,
                    is_active=desired_is_active,
                    created_at=now,
                    updated_at=now,
                )
                self.session.add(config)

        await self.session.commit()
        refreshed = await self.session.get(ReminderConfig, config_id)
        if refreshed is None:
            raise ValueError("reminder config not found")
        return refreshed

    async def deactivate_config(self, config_id: int) -> ReminderConfig:
        config = await self.session.get(ReminderConfig, config_id)
        if config is None:
            raise ValueError("reminder config not found")

        config.is_active = False
        config.updated_at = utcnow_naive()
        await self.session.commit()
        await self.session.refresh(config)
        return config
