"""
Daily policy reminder generation — delegates to the generic reminder engine.

DEPRECATED module name: use app.jobs.reminder_engine_jobs for new integrations.
"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.verticals import InsurancePolicy
from app.services.policy_generic_reminder_service import (
    ensure_policy_reminder_instances_for_policy,
    generate_daily_policy_reminder_instances,
    generate_daily_policy_reminder_instances_all,
)
from app.utils.policy_queries import select_insurance_policies
from app.utils.policy_reminder_stages import REMINDER_TYPE_PERSONALIZED

logger = logging.getLogger(__name__)


async def generate_daily_policy_reminders(
    session: AsyncSession,
    *,
    organization_id: int | None = None,
) -> int:
    """Generate reminder_instances from active reminder_configs."""
    return await generate_daily_policy_reminder_instances(session, organization_id=organization_id)


async def generate_daily_policy_reminders_all(session: AsyncSession) -> int:
    return await generate_daily_policy_reminder_instances_all(session)


async def ensure_policy_reminder_schedule_for_policy(
    session: AsyncSession,
    policy: InsurancePolicy,
) -> int:
    """Regenerate reminder_instances for the policy organization (UI configs required)."""
    return await ensure_policy_reminder_instances_for_policy(session, policy)


async def repair_personalized_policy_reminder_schedules(
    session: AsyncSession,
    *,
    organization_id: int | None = None,
    policy_id: int | None = None,
) -> dict[str, int]:
    """
    DEPRECATED migration repair: re-sync legacy policy fields into reminder_configs.

    Prefer Reminder Settings UI + reminder_engine_jobs for ongoing operations.
    """
    from app.services.policy_legacy_reminder_sync import PolicyLegacyReminderSyncService
    from app.services.reminder_generator import ReminderGeneratorService
    from app.services.reminder_instance_service import cancel_pending_reminder_instances

    query = select_insurance_policies(load_custom_reminders=True).where(
        InsurancePolicy.reminder_type == REMINDER_TYPE_PERSONALIZED,
    )
    if organization_id is not None:
        query = query.where(InsurancePolicy.organization_id == organization_id)
    if policy_id is not None:
        query = query.where(InsurancePolicy.id == policy_id)

    policies = list((await session.execute(query)).scalars())
    sync_service = PolicyLegacyReminderSyncService(session)
    generator = ReminderGeneratorService(session)
    policies_repaired = 0
    created = 0

    for policy in policies:
        custom_reminders = list(getattr(policy, "custom_reminders", None) or [])
        await cancel_pending_reminder_instances(
            session,
            organization_id=policy.organization_id,
            entity_type="policy",
            entity_id=int(policy.id),
        )
        if custom_reminders:
            await sync_service.sync_policy_reminder_configs(
                policy,
                custom_reminders=custom_reminders,
            )
        instances = await generator.generate_from_active_configs(
            organization_id=policy.organization_id,
            commit=False,
        )
        policy_instances = [row for row in instances if row.entity_id == policy.id]
        if policy_instances:
            policies_repaired += 1
            created += len(policy_instances)

    if created:
        await session.commit()

    logger.info(
        "[PolicyReminderRepair] legacy resync policies_repaired=%s instances_created=%s",
        policies_repaired,
        created,
    )
    return {"policies_repaired": policies_repaired, "deleted": 0, "created": created}


async def repair_personalized_policy_reminder_schedules_all(
    session: AsyncSession,
) -> dict[str, int]:
    return await repair_personalized_policy_reminder_schedules(session)
