"""Policy expiry classification — mirrors frontend policy-classifier.ts."""

from __future__ import annotations

from datetime import datetime

from app.models.verticals import InsurancePolicy
from app.utils.datetime_utils import normalize_to_utc_naive, utcnow_naive
from app.utils.policy_status import (
    POLICY_STATUS_ACTIVE,
    POLICY_STATUS_GRACE_PERIOD,
    POLICY_STATUS_LAPSED,
    evaluate_policy_status,
)

INACTIVE_TRACKING_STATUSES = frozenset({"cancelled"})

DUE_RENEWAL_MIN_DAYS = 3
DUE_RENEWAL_MAX_DAYS = 10
EXPIRING_MIN_DAYS = 0
EXPIRING_MAX_DAYS = 2
POLICY_SUMMARY_EXPIRING_SOON_MAX_DAYS = 10


def days_until_utc(expiry_date: datetime | None) -> int | None:
    if expiry_date is None:
        return None
    now = utcnow_naive()
    target = normalize_to_utc_naive(expiry_date)
    return (target.date() - now.date()).days


def is_lapsed(policy: InsurancePolicy) -> bool:
    return evaluate_policy_status(policy) == POLICY_STATUS_LAPSED


def is_grace_period(policy: InsurancePolicy) -> bool:
    return evaluate_policy_status(policy) == POLICY_STATUS_GRACE_PERIOD


def is_active_policy(policy: InsurancePolicy) -> bool:
    """Active lifecycle bucket only."""
    status = (getattr(policy, "status", None) or "").lower()
    if status in INACTIVE_TRACKING_STATUSES:
        return False
    return evaluate_policy_status(policy) == POLICY_STATUS_ACTIVE


def is_due_renewal(policy: InsurancePolicy) -> bool:
    """Due renewals: 3–10 days remaining (active policies only)."""
    if not is_active_policy(policy):
        return False
    days = days_until_utc(policy.expiry_date)
    return days is not None and DUE_RENEWAL_MIN_DAYS <= days <= DUE_RENEWAL_MAX_DAYS


def is_upcoming_renewal(policy: InsurancePolicy) -> bool:
    """Backward-compatible alias for due renewals."""
    return is_due_renewal(policy)


def is_critical_renewal(policy: InsurancePolicy) -> bool:
    """Expiring policies: 0–2 days remaining (active policies only)."""
    if not is_active_policy(policy):
        return False
    days = days_until_utc(policy.expiry_date)
    return days is not None and EXPIRING_MIN_DAYS <= days <= EXPIRING_MAX_DAYS


def is_expiring(policy: InsurancePolicy, max_days: int = EXPIRING_MAX_DAYS) -> bool:
    return is_critical_renewal(policy) if max_days == EXPIRING_MAX_DAYS else is_critical_renewal(policy)


def has_active_status(policy: InsurancePolicy) -> bool:
    return (getattr(policy, "status", None) or "").lower() == "active"


def is_expiring_soon_policy(policy: InsurancePolicy, max_days: int = POLICY_SUMMARY_EXPIRING_SOON_MAX_DAYS) -> bool:
    """Active-status policies expiring within the next N days (inclusive)."""
    if evaluate_policy_status(policy) != POLICY_STATUS_ACTIVE:
        return False
    days = days_until_utc(policy.expiry_date)
    return days is not None and EXPIRING_MIN_DAYS <= days <= max_days


def classify_policy_summary_kpis(policies: list[InsurancePolicy]) -> dict[str, int]:
    """KPI counts for the Insurance dashboard Policy Summary section."""
    return {
        "total_policies": len(policies),
        "active_policies": sum(1 for policy in policies if is_active_policy(policy)),
        "grace_period_policies": sum(1 for policy in policies if is_grace_period(policy)),
        "lapsed_policies": sum(1 for policy in policies if is_lapsed(policy)),
        "expiring_soon_policies": sum(1 for policy in policies if is_expiring_soon_policy(policy)),
    }


def is_due(policy: InsurancePolicy) -> bool:
    return is_due_renewal(policy)


def is_other_active(policy: InsurancePolicy) -> bool:
    return is_active_policy(policy) and not is_due_renewal(policy) and not is_critical_renewal(policy)


def policy_list_status_priority(policy: InsurancePolicy) -> int:
    """Default list order: Lapsed (1) → renewal buckets (2) → other active (3)."""
    if is_lapsed(policy):
        return 1
    if is_critical_renewal(policy) or is_due_renewal(policy):
        return 2
    return 3


def policy_list_sort_key(policy: InsurancePolicy) -> tuple[int, float]:
    priority = policy_list_status_priority(policy)
    expiry = getattr(policy, "expiry_date", None)
    if expiry is None:
        return (priority, 0.0)
    ts = normalize_to_utc_naive(expiry).timestamp()
    expiry_key = -ts if priority == 1 else ts
    return (priority, expiry_key)


def sort_policies_default_order(policies: list[InsurancePolicy]) -> list[InsurancePolicy]:
    return sorted(policies, key=policy_list_sort_key)


def classify_ui_dashboard_kpis(policies: list[InsurancePolicy]) -> dict[str, int]:
    active = sum(1 for policy in policies if evaluate_policy_status(policy) == POLICY_STATUS_ACTIVE)
    due = sum(1 for policy in policies if is_due_renewal(policy))
    expiring = sum(1 for policy in policies if is_critical_renewal(policy))
    grace_period = sum(1 for policy in policies if is_grace_period(policy))
    lapsed = sum(1 for policy in policies if is_lapsed(policy))
    return {
        "total_policies": len(policies),
        "active_policies": active,
        "due_renewals": due,
        "upcoming_renewals": due,
        "expiring_policies": expiring,
        "grace_period_policies": grace_period,
        "lapsed_policies": lapsed,
    }
