"""Renewal Intelligence chart classification for the Insurance dashboard."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import Contact, User
from app.models.insurance import PolicyReminder
from app.models.verticals import InsurancePolicy
from app.utils.datetime_utils import normalize_to_utc_naive, utcnow_naive
from app.utils.policy_classifier import days_until_utc
from app.utils.policy_status import POLICY_STATUS_GRACE_PERIOD, POLICY_STATUS_LAPSED, evaluate_policy_status
from app.utils.renewal_frequency import RENEWAL_FREQUENCY_DEFAULT
from app.utils.user_display import format_user_display_name

RENEWAL_STATUS_LAPSED_OVER_90 = "lapsed_over_90"
RENEWAL_STATUS_LAPSED = "lapsed"
RENEWAL_STATUS_GRACE_PERIOD = "grace_period"
RENEWAL_STATUS_DUE_SOON = "due_soon"
RENEWAL_STATUS_FUTURE = "future_renewal"

RENEWAL_STATUS_LABELS = {
    RENEWAL_STATUS_LAPSED_OVER_90: "Lapsed > 90 Days",
    RENEWAL_STATUS_LAPSED: "Lapsed",
    RENEWAL_STATUS_GRACE_PERIOD: "Grace Period",
    RENEWAL_STATUS_DUE_SOON: "Due Soon",
    RENEWAL_STATUS_FUTURE: "Future Renewal",
}

DUE_SOON_MAX_DAYS = 10
LAPSED_OVER_90_DAYS = 90
RENEWAL_INTELLIGENCE_MAX_DAYS_UNTIL_EXPIRY = 30


def is_in_renewal_intelligence_chart_window(days: int | None) -> bool:
    """Include policies expired within 90 days or expiring within the next 30 days."""
    if days is None:
        return False
    return -LAPSED_OVER_90_DAYS <= days <= RENEWAL_INTELLIGENCE_MAX_DAYS_UNTIL_EXPIRY


def classify_renewal_intelligence_status(policy: InsurancePolicy) -> str:
    lifecycle_status = evaluate_policy_status(policy)
    if lifecycle_status == POLICY_STATUS_GRACE_PERIOD:
        return RENEWAL_STATUS_GRACE_PERIOD

    days = days_until_utc(getattr(policy, "expiry_date", None))
    if lifecycle_status == POLICY_STATUS_LAPSED and days is not None and days < -LAPSED_OVER_90_DAYS:
        return RENEWAL_STATUS_LAPSED_OVER_90
    if lifecycle_status == POLICY_STATUS_LAPSED:
        return RENEWAL_STATUS_LAPSED
    if days is not None and days <= DUE_SOON_MAX_DAYS:
        return RENEWAL_STATUS_DUE_SOON
    return RENEWAL_STATUS_FUTURE


def _timing_fields(days: int | None) -> dict[str, int | None]:
    if days is None:
        return {"days_until_due": None, "days_overdue": None}
    if days < 0:
        return {"days_until_due": None, "days_overdue": abs(days)}
    return {"days_until_due": days, "days_overdue": None}


def _serialize_policy_point(
    policy: InsurancePolicy,
    *,
    customer_name: str,
    assigned_agent_name: str | None,
    reminders_sent_count: int = 0,
) -> dict[str, Any]:
    days = days_until_utc(policy.expiry_date)
    renewal_status = classify_renewal_intelligence_status(policy)
    expiry = normalize_to_utc_naive(policy.expiry_date)
    premium = int(getattr(policy, "premium", 0) or 0)
    timing = _timing_fields(days)

    return {
        "policy_id": int(policy.id),
        "customer_name": customer_name,
        "policy_number": policy.policy_number,
        "product_type": getattr(policy, "policy_type", None),
        "renewal_frequency": getattr(policy, "renewal_frequency", None) or RENEWAL_FREQUENCY_DEFAULT,
        "expiry_date": expiry.isoformat() if expiry is not None else None,
        "premium": premium,
        "renewal_status": renewal_status,
        "renewal_status_label": RENEWAL_STATUS_LABELS[renewal_status],
        "days_until_due": timing["days_until_due"],
        "days_overdue": timing["days_overdue"],
        "assigned_agent_user_id": getattr(policy, "assigned_agent_user_id", None),
        "assigned_agent_name": assigned_agent_name,
        "reminders_sent_count": reminders_sent_count,
    }


async def build_renewal_intelligence_chart(
    session: AsyncSession,
    policies: list[InsurancePolicy],
) -> dict[str, Any]:
    if not policies:
        return {"points": [], "filters": {"agents": [], "product_types": []}}

    holder_ids = {policy.policyholder_id for policy in policies if getattr(policy, "policyholder_id", None)}
    agent_ids = {
        policy.assigned_agent_user_id
        for policy in policies
        if getattr(policy, "assigned_agent_user_id", None) is not None
    }

    contacts_by_id: dict[int, Contact] = {}
    if holder_ids:
        contact_result = await session.execute(select(Contact).where(Contact.id.in_(holder_ids)))
        contacts_by_id = {contact.id: contact for contact in contact_result.scalars().all()}

    users_by_id: dict[int, User] = {}
    if agent_ids:
        user_result = await session.execute(select(User).where(User.id.in_(agent_ids)))
        users_by_id = {user.id: user for user in user_result.scalars().all()}

    policy_ids = [int(policy.id) for policy in policies]
    reminder_counts: dict[int, int] = {}
    if policy_ids:
        reminder_result = await session.execute(
            select(PolicyReminder.policy_id, func.count(PolicyReminder.id))
            .where(
                PolicyReminder.policy_id.in_(policy_ids),
                PolicyReminder.status == "SENT",
            )
            .group_by(PolicyReminder.policy_id)
        )
        reminder_counts = {int(row[0]): int(row[1]) for row in reminder_result.all()}

    points: list[dict[str, Any]] = []
    agent_options: dict[str, str] = {}
    product_types: set[str] = set()

    for policy in policies:
        days = days_until_utc(getattr(policy, "expiry_date", None))
        if not is_in_renewal_intelligence_chart_window(days):
            continue

        contact = contacts_by_id.get(policy.policyholder_id)
        customer_name = contact.name if contact is not None else policy.policy_number
        agent_user = users_by_id.get(policy.assigned_agent_user_id) if policy.assigned_agent_user_id else None
        assigned_agent_name = format_user_display_name(agent_user.email) if agent_user is not None else None

        point = _serialize_policy_point(
            policy,
            customer_name=customer_name,
            assigned_agent_name=assigned_agent_name,
            reminders_sent_count=reminder_counts.get(int(policy.id), 0),
        )
        points.append(point)

        if point["product_type"]:
            product_types.add(point["product_type"])

        agent_key = str(point["assigned_agent_user_id"]) if point["assigned_agent_user_id"] is not None else ""
        agent_label = assigned_agent_name or (f"Agent {agent_key}" if agent_key else "Unassigned")
        agent_options[agent_key] = agent_label

    agents = [{"value": value, "label": label} for value, label in sorted(agent_options.items(), key=lambda item: item[1].lower())]

    return {
        "points": points,
        "filters": {
            "agents": agents,
            "product_types": sorted(product_types, key=str.lower),
        },
    }
