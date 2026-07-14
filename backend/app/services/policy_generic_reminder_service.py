"""Deprecated insurance reminder bridge — delegates to the generic reminder engine.

Reminder configuration is UI-driven via ReminderConfigService. Insurance no longer
owns reminder_configs creation on policy create/update.

Legacy policy-field → reminder_configs sync lives in policy_legacy_reminder_sync.py
for migration and repair jobs only.
"""

from __future__ import annotations

import warnings

from sqlalchemy.ext.asyncio import AsyncSession

from app.jobs.reminder_engine_jobs import (
    generate_reminder_instances,
    process_due_reminder_instances,
)
from app.models.reminder_config import ReminderConfig
from app.models.verticals import InsurancePolicy
from app.services.reminder_generator import ReminderGeneratorService
from app.services.reminder_instance_service import cancel_pending_reminder_instances
from app.services.reminder_processor import ReminderProcessorService

POLICY_ENTITY_TYPE = "policy"


class PolicyGenericReminderService:
    """Backward-compatible facade — prefer ReminderConfigService + reminder_engine_jobs."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self._processor = ReminderProcessorService(session)

    async def sync_policy_reminder_configs(
        self,
        policy: InsurancePolicy,
        *,
        custom_reminders: list | None = None,
    ) -> list[ReminderConfig]:
        warnings.warn(
            "sync_policy_reminder_configs is deprecated; configure reminders via "
            "ReminderConfigService.save_entity_settings from the Reminder Settings UI.",
            DeprecationWarning,
            stacklevel=2,
        )
        from app.services.policy_legacy_reminder_sync import sync_policy_reminder_configs_from_policy

        return await sync_policy_reminder_configs_from_policy(
            self.session,
            policy,
            custom_reminders=custom_reminders,
        )

    async def cancel_pending_instances(self, policy: InsurancePolicy) -> int:
        return await cancel_pending_reminder_instances(
            self.session,
            organization_id=policy.organization_id,
            entity_type=POLICY_ENTITY_TYPE,
            entity_id=int(policy.id),
        )

    async def process_due_reminders(self, organization_id: int) -> dict[str, int]:
        return await self._processor.process_due_reminders(organization_id)


async def generate_daily_policy_reminder_instances(
    session: AsyncSession,
    *,
    organization_id: int | None = None,
) -> int:
    """Generate reminder_instances from active reminder_configs (module-independent)."""
    return await generate_reminder_instances(session, organization_id=organization_id)


async def generate_daily_policy_reminder_instances_all(session: AsyncSession) -> int:
    return await generate_reminder_instances(session, organization_id=None)


async def ensure_policy_reminder_instances_for_policy(
    session: AsyncSession,
    policy: InsurancePolicy,
) -> int:
    """Regenerate instances for an org after policy renewal (configs must exist in UI)."""
    generator = ReminderGeneratorService(session)
    created = await generator.generate_from_active_configs(organization_id=policy.organization_id)
    return len(created)
