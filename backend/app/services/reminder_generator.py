from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import (
    DEFAULT_REMINDER_ANCHOR_KEY,
    ReminderAnchorType,
    ReminderOffsetDirection,
)
from app.models.reminder_config import ReminderConfig
from app.models.reminder_instance import ReminderInstance
from app.services.reminder_resolvers import (
    ReminderEntityResolver,
    ReminderEntitySnapshot,
    ReminderResolverFactory,
    UnsupportedReminderEntityTypeError,
    get_reminder_resolver_factory,
)
from app.utils.datetime_utils import normalize_to_utc_naive
from app.utils.reminder_schedule import (
    scheduled_at_for_absolute_config,
    scheduled_at_for_relative_config,
)
from app.utils.reminder_payload_mode import is_payload_config
from app.utils.reminder_recurrence import count_sent_instances, has_pending_instance

logger = logging.getLogger(__name__)

# Sentinel used by Generic Reminder Management / Claims settings for org-wide rules.
# Not a real entity id — generators must fan out to all eligible entities.
ORG_LEVEL_ENTITY_ID = 0


def _resolver_mode_configs(configs: list[ReminderConfig]) -> list[ReminderConfig]:
    """Exclude payload-mode configs — they already have materialized instances."""
    return [config for config in configs if not is_payload_config(config)]


class ReminderGeneratorService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        resolver_factory: ReminderResolverFactory | None = None,
    ):
        self.session = session
        self._resolver_factory = resolver_factory or get_reminder_resolver_factory()

    def _config_anchor_fields(self, config: ReminderConfig) -> tuple[str, str, str]:
        anchor_type = (
            getattr(config, "anchor_type", None) or ReminderAnchorType.DATE.value
        )
        anchor_key = (
            getattr(config, "anchor_key", None) or DEFAULT_REMINDER_ANCHOR_KEY
        )
        offset_direction = (
            getattr(config, "offset_direction", None) or ReminderOffsetDirection.BEFORE.value
        )
        return (
            str(anchor_type).strip().lower(),
            str(anchor_key).strip() or DEFAULT_REMINDER_ANCHOR_KEY,
            str(offset_direction).strip().lower(),
        )

    def _scheduled_at_for_config(
        self,
        *,
        anchor_date: datetime,
        config: ReminderConfig,
    ) -> datetime:
        if config.absolute_scheduled_at is not None:
            return scheduled_at_for_absolute_config(absolute_scheduled_at=config.absolute_scheduled_at)

        _, _, offset_direction = self._config_anchor_fields(config)
        return scheduled_at_for_relative_config(
            anchor_date=anchor_date,
            offset_value=config.offset_value,
            offset_unit=config.offset_unit,
            time_of_day=config.time_of_day,
            offset_direction=offset_direction,
        )

    def _resolve_config_anchor(
        self,
        *,
        resolver: ReminderEntityResolver,
        entity: ReminderEntitySnapshot,
        config: ReminderConfig,
    ) -> datetime | None:
        anchor_type, anchor_key, _ = self._config_anchor_fields(config)
        return normalize_to_utc_naive(
            resolver.resolve_anchor(
                entity,
                anchor_type=anchor_type,
                anchor_key=anchor_key,
            )
        )

    async def _instance_exists(
        self,
        *,
        config_id: int,
        entity_id: int,
        scheduled_at: datetime,
    ) -> bool:
        duplicate = await self.session.execute(
            select(ReminderInstance).where(
                ReminderInstance.config_id == config_id,
                ReminderInstance.entity_id == entity_id,
                ReminderInstance.scheduled_at == scheduled_at,
            )
        )
        return duplicate.scalar_one_or_none() is not None

    async def _create_instance_for_config(
        self,
        *,
        config: ReminderConfig,
        organization_id: int,
        entity_type: str,
        entity_id: int,
        anchor_date: datetime,
    ) -> ReminderInstance | None:
        scheduled_at = self._scheduled_at_for_config(
            anchor_date=anchor_date,
            config=config,
        )

        if bool(getattr(config, "repeat_enabled", False)):
            if await has_pending_instance(
                self.session,
                config_id=int(config.id),
                entity_id=int(entity_id),
            ):
                return None
            sent_count = await count_sent_instances(
                self.session,
                config_id=int(config.id),
                entity_id=int(entity_id),
            )
            if sent_count > 0:
                return None

        if await self._instance_exists(
            config_id=config.id,
            entity_id=int(entity_id),
            scheduled_at=scheduled_at,
        ):
            return None

        instance = ReminderInstance(
            config_id=config.id,
            organization_id=organization_id,
            entity_type=entity_type,
            entity_id=entity_id,
            scheduled_at=scheduled_at,
            status="PENDING",
        )
        self.session.add(instance)
        return instance

    async def _create_instances_for_entity_configs(
        self,
        *,
        resolver: ReminderEntityResolver,
        org_id: int,
        entity_type: str,
        entity: ReminderEntitySnapshot,
        configs: list[ReminderConfig],
    ) -> list[ReminderInstance]:
        if not configs:
            return []
        if not resolver.is_eligible(entity, configs=configs):
            return []

        created: list[ReminderInstance] = []
        entity_id = int(entity.entity_id)
        for config in configs:
            anchor = self._resolve_config_anchor(
                resolver=resolver,
                entity=entity,
                config=config,
            )
            if anchor is None:
                logger.debug(
                    "[ReminderGenerator] unresolved anchor org=%s type=%s id=%s "
                    "config=%s key=%s",
                    org_id,
                    entity_type,
                    entity_id,
                    config.id,
                    getattr(config, "anchor_key", None),
                )
                continue

            instance = await self._create_instance_for_config(
                config=config,
                organization_id=org_id,
                entity_type=entity_type,
                entity_id=entity_id,
                anchor_date=anchor,
            )
            if instance is not None:
                created.append(instance)
        return created

    async def generate_instances(
        self,
        *,
        entity_type: str,
        entity_id: int,
        organization_id: int,
        anchor_date: datetime,
        commit: bool = True,
    ) -> list[ReminderInstance]:
        """
        Generate instances for one entity (backward-compatible API).

        Uses the caller-supplied ``anchor_date`` for every config. Prefer
        ``generate_from_active_configs()`` when anchors should be resolved
        dynamically from ``anchor_type`` / ``anchor_key``.

        Loads both entity-specific configs and org-level configs
        (``entity_id == 0``) so regenerating one entity applies generic rules too.
        """
        if int(entity_id) == ORG_LEVEL_ENTITY_ID:
            raise ValueError(
                "entity_id must be a real entity id; "
                "use generate_from_active_configs for org-level rules"
            )

        anchor = normalize_to_utc_naive(anchor_date)
        if anchor is None:
            raise ValueError("anchor_date is required")

        config_result = await self.session.execute(
            select(ReminderConfig).where(
                ReminderConfig.organization_id == organization_id,
                ReminderConfig.entity_type == entity_type,
                ReminderConfig.is_active.is_(True),
                or_(
                    ReminderConfig.entity_id == entity_id,
                    ReminderConfig.entity_id == ORG_LEVEL_ENTITY_ID,
                ),
            )
        )
        configs = _resolver_mode_configs(list(config_result.scalars()))
        created: list[ReminderInstance] = []

        for config in configs:
            instance = await self._create_instance_for_config(
                config=config,
                organization_id=organization_id,
                entity_type=entity_type,
                entity_id=entity_id,
                anchor_date=anchor,
            )
            if instance is not None:
                created.append(instance)

        if created and commit:
            await self.session.commit()
            for instance in created:
                await self.session.refresh(instance)

        return created

    async def generate_from_active_configs(
        self,
        *,
        organization_id: int | None = None,
        commit: bool = True,
    ) -> list[ReminderInstance]:
        """
        Discover entities from active reminder_configs via registered resolvers.

        Per-entity configs (``entity_id != 0``): resolve that entity and create
        instances as before.

        Org-level configs (``entity_id == 0``): one reusable rule that fans out
        to every eligible entity returned by ``list_entities`` (plus any
        entity-specific lookups). Instances store the real entity id; the
        config itself stays at ``entity_id == 0``.
        """
        query = select(ReminderConfig).where(ReminderConfig.is_active.is_(True))
        if organization_id is not None:
            query = query.where(ReminderConfig.organization_id == organization_id)

        configs = _resolver_mode_configs(list((await self.session.execute(query)).scalars()))
        if not configs:
            return []

        grouped: dict[tuple[int, str], list[ReminderConfig]] = defaultdict(list)
        for config in configs:
            entity_type = (config.entity_type or "").strip().lower()
            grouped[(config.organization_id, entity_type)].append(config)

        created: list[ReminderInstance] = []

        for (org_id, entity_type), type_configs in grouped.items():
            try:
                resolver = self._resolver_factory.resolve(entity_type)
            except UnsupportedReminderEntityTypeError:
                logger.warning(
                    "[ReminderGenerator] no resolver for entity_type=%s; skipping %s config(s)",
                    entity_type,
                    len(type_configs),
                )
                continue

            org_level_configs = [
                c for c in type_configs if int(c.entity_id) == ORG_LEVEL_ENTITY_ID
            ]
            entity_specific_configs = [
                c for c in type_configs if int(c.entity_id) != ORG_LEVEL_ENTITY_ID
            ]

            entities_by_id: dict[int, ReminderEntitySnapshot] = {}
            for entity in await resolver.list_entities(self.session, org_id):
                if int(entity.entity_id) == ORG_LEVEL_ENTITY_ID:
                    continue
                entities_by_id[int(entity.entity_id)] = entity

            # Resolve entity-specific ids missing from list_entities (never look up 0).
            missing_ids = {
                int(c.entity_id) for c in entity_specific_configs
            } - set(entities_by_id.keys())
            for entity_id in missing_ids:
                entity = await resolver.get_entity(self.session, org_id, entity_id)
                if entity is not None and int(entity.entity_id) != ORG_LEVEL_ENTITY_ID:
                    entities_by_id[int(entity.entity_id)] = entity

            # 1) Per-entity configs — unchanged behavior
            for entity_id in {int(c.entity_id) for c in entity_specific_configs}:
                entity = entities_by_id.get(entity_id)
                if entity is None:
                    logger.debug(
                        "[ReminderGenerator] entity not found org=%s type=%s id=%s",
                        org_id,
                        entity_type,
                        entity_id,
                    )
                    continue

                entity_configs = [
                    c for c in entity_specific_configs if int(c.entity_id) == entity_id
                ]
                created.extend(
                    await self._create_instances_for_entity_configs(
                        resolver=resolver,
                        org_id=org_id,
                        entity_type=entity_type,
                        entity=entity,
                        configs=entity_configs,
                    )
                )

            # 2) Org-level configs — fan out to all discovered eligible entities
            if not org_level_configs:
                continue

            for entity in entities_by_id.values():
                created.extend(
                    await self._create_instances_for_entity_configs(
                        resolver=resolver,
                        org_id=org_id,
                        entity_type=entity_type,
                        entity=entity,
                        configs=org_level_configs,
                    )
                )

        if created and commit:
            await self.session.commit()
            for instance in created:
                await self.session.refresh(instance)

        return created
