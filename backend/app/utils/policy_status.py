from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.utils.datetime_utils import normalize_to_utc_naive, utcnow_naive

POLICY_STATUS_ACTIVE = "active"
POLICY_STATUS_GRACE_PERIOD = "grace_period"
POLICY_STATUS_LAPSED = "lapsed"

DEFAULT_POLICY_GRACE_PERIOD_DAYS = 30


@dataclass(frozen=True)
class PolicyLifecycleSnapshot:
    status: str
    grace_period_ends_at: datetime
    days_from_renewal: int


def normalize_grace_period_days(value: int | None) -> int:
    if value is None:
        return DEFAULT_POLICY_GRACE_PERIOD_DAYS
    return max(int(value), 0)


def evaluate_policy_status(policy, *, now: datetime | None = None) -> str:
    """Evaluate lifecycle using renewal(expiry) date + grace days."""
    renewal_date_value = normalize_to_utc_naive(getattr(policy, "expiry_date", None))
    if renewal_date_value is None:
        return POLICY_STATUS_ACTIVE

    today = (now or utcnow_naive()).date()
    renewal_date = renewal_date_value.date()
    grace_days = normalize_grace_period_days(getattr(policy, "grace_period_days", None))
    grace_end = renewal_date + timedelta(days=grace_days)

    if today <= renewal_date:
        return POLICY_STATUS_ACTIVE
    if today <= grace_end:
        return POLICY_STATUS_GRACE_PERIOD
    return POLICY_STATUS_LAPSED


def evaluate_policy_lifecycle(policy, *, now: datetime | None = None) -> PolicyLifecycleSnapshot:
    current = normalize_to_utc_naive(now) or utcnow_naive()
    expiry_date = normalize_to_utc_naive(getattr(policy, "expiry_date", None)) or current
    renewal_date = expiry_date.date()
    grace_days = normalize_grace_period_days(getattr(policy, "grace_period_days", None))
    grace_end_date = renewal_date + timedelta(days=grace_days)
    status = evaluate_policy_status(policy, now=current)
    days_from_renewal = (current.date() - renewal_date).days
    grace_end_at = datetime.combine(grace_end_date, datetime.min.time())
    return PolicyLifecycleSnapshot(
        status=status,
        grace_period_ends_at=grace_end_at,
        days_from_renewal=days_from_renewal,
    )
