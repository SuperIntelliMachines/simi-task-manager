"""Daily renewal escalation — escalate lapsed policies."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TypedDict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import Contact
from app.models.verticals import InsurancePolicy
from app.services.insurance_messaging import send_renewal_escalation_agent_notification
from app.services.insurance_service import InsuranceService
from app.utils.datetime_utils import normalize_to_utc_naive, utcnow_naive
from app.utils.policy_status import POLICY_STATUS_LAPSED, evaluate_policy_status

logger = logging.getLogger(__name__)


class RenewalEscalationStats(TypedDict):
    processed: int
    escalated: int
    skipped: int
async def _lapsed_policies_query(
    session: AsyncSession,
    organization_id: int | None,
):
    stmt = select(InsurancePolicy)
    if organization_id is not None:
        stmt = stmt.where(InsurancePolicy.organization_id == organization_id)
    return await session.execute(stmt.order_by(InsurancePolicy.expiry_date.asc()))


async def process_renewal_escalations(
    session: AsyncSession,
    organization_id: int | None = None,
) -> RenewalEscalationStats:
    """Escalate lapsed policies to assigned agents (idempotent)."""
    result = await _lapsed_policies_query(session, organization_id)
    policies = [policy for policy in result.scalars() if evaluate_policy_status(policy) == POLICY_STATUS_LAPSED]

    insurance_service = InsuranceService(session)
    stats: RenewalEscalationStats = {"processed": 0, "escalated": 0, "skipped": 0}

    for policy in policies:
        stats["processed"] += 1
        escalation = await insurance_service.trigger_renewal_escalation(
            policy=policy,
            actor_user_id=policy.assigned_agent_user_id,
        )
        outcome = str(escalation.get("result", ""))

        if outcome == "created":
            stats["escalated"] += 1
            task_id = escalation.get("task_id")
            if task_id is not None and policy.assigned_agent_user_id is not None:
                contact = await session.get(Contact, policy.policyholder_id)
                customer_name = (contact.name if contact is not None else None) or "Customer"
                expiry = normalize_to_utc_naive(policy.expiry_date)
                expiry_label = expiry.strftime("%d-%b-%Y") if expiry is not None else "unknown"
                message = (
                    f"Renewal escalation: policy {policy.policy_number} for {customer_name} "
                    f"expired on {expiry_label} and has not been renewed. "
                    "Immediate follow-up is required."
                )
                sent, error = await send_renewal_escalation_agent_notification(
                    session,
                    organization_id=policy.organization_id,
                    agent_user_id=policy.assigned_agent_user_id,
                    policy_number=policy.policy_number,
                    task_id=int(task_id),
                    message=message,
                )
                if not sent:
                    logger.warning(
                        "[RenewalEscalationJob] policy_id=%s task_id=%s email_failed=%s",
                        policy.id,
                        task_id,
                        error,
                    )
        else:
            stats["skipped"] += 1
            logger.info(
                "[RenewalEscalationJob] policy_id=%s result=skipped reason=%s",
                policy.id,
                escalation.get("reason"),
            )

    if stats["processed"]:
        await session.commit()

    logger.info(
        "[RenewalEscalationJob] processed=%s escalated=%s skipped=%s org_id=%s",
        stats["processed"],
        stats["escalated"],
        stats["skipped"],
        organization_id,
    )
    return stats


async def process_renewal_escalations_all(session: AsyncSession) -> RenewalEscalationStats:
    result = await session.execute(select(InsurancePolicy.organization_id).distinct())
    org_ids = list(result.scalars())
    totals: RenewalEscalationStats = {"processed": 0, "escalated": 0, "skipped": 0}
    for org_id in org_ids:
        org_stats = await process_renewal_escalations(session, organization_id=org_id)
        totals["processed"] += org_stats["processed"]
        totals["escalated"] += org_stats["escalated"]
        totals["skipped"] += org_stats["skipped"]
    return totals
