import pytest

from app.utils.policy_classifier import (
    classify_ui_dashboard_kpis,
    is_active_policy,
    is_critical_renewal,
    is_due_renewal,
    is_grace_period,
    is_lapsed,
    is_other_active,
)


class _Policy:
    def __init__(self, expiry_date, status: str | None = None):
        self.expiry_date = expiry_date
        self.status = status


def test_classify_ui_dashboard_kpis():
    from datetime import timedelta

    from app.utils.datetime_utils import utcnow_naive

    now = utcnow_naive()
    policies = [
        _Policy(now + timedelta(days=20)),
        _Policy(now + timedelta(days=1)),
        _Policy(now + timedelta(days=5)),
        _Policy(now - timedelta(days=1)),
    ]
    kpis = classify_ui_dashboard_kpis(policies)  # type: ignore[arg-type]

    assert kpis["total_policies"] == 4
    assert kpis["active_policies"] == 3
    assert kpis["expiring_policies"] == 1
    assert kpis["due_renewals"] == 1
    assert kpis["upcoming_renewals"] == 1
    assert kpis["grace_period_policies"] == 1
    assert kpis["lapsed_policies"] == 0


def test_is_active_policy_excludes_cancelled_grace_and_lapsed():
    from datetime import timedelta

    from app.utils.datetime_utils import utcnow_naive

    now = utcnow_naive()
    assert is_active_policy(_Policy(now + timedelta(days=45)))
    assert is_active_policy(_Policy(now + timedelta(days=5)))
    assert not is_active_policy(_Policy(now - timedelta(days=1)))
    assert not is_active_policy(_Policy(now + timedelta(days=45), status="cancelled"))
    assert not is_active_policy(_Policy(now + timedelta(days=5), status="cancelled"))


def test_renewal_bucket_helpers():
    from datetime import timedelta

    from app.utils.datetime_utils import utcnow_naive

    now = utcnow_naive()
    assert is_due_renewal(_Policy(now + timedelta(days=10)))
    assert is_due_renewal(_Policy(now + timedelta(days=3)))
    assert not is_due_renewal(_Policy(now + timedelta(days=11)))
    assert not is_due_renewal(_Policy(now + timedelta(days=20)))
    assert is_critical_renewal(_Policy(now + timedelta(days=2)))
    assert is_critical_renewal(_Policy(now + timedelta(days=0)))
    assert is_grace_period(_Policy(now - timedelta(days=1)))
    assert is_lapsed(_Policy(now - timedelta(days=40)))


def test_active_is_union_of_other_due_and_expiring():
    from datetime import timedelta

    from app.utils.datetime_utils import utcnow_naive

    now = utcnow_naive()
    policies = [
        _Policy(now + timedelta(days=45)),
        _Policy(now + timedelta(days=20)),
        _Policy(now + timedelta(days=5)),
        _Policy(now + timedelta(days=1)),
        _Policy(now - timedelta(days=1)),
    ]
    active = [policy for policy in policies if is_active_policy(policy)]
    bucketed = sum(
        1
        for policy in policies
        if is_other_active(policy) or is_due_renewal(policy) or is_critical_renewal(policy)
    )

    assert len(active) == 4
    assert bucketed == len(active)


def test_classify_policy_summary_kpis():
    from datetime import timedelta

    from app.utils.datetime_utils import utcnow_naive
    from app.utils.policy_classifier import classify_policy_summary_kpis, is_expiring_soon_policy

    now = utcnow_naive()
    policies = [
        _Policy(now + timedelta(days=20), status="active"),
        _Policy(now + timedelta(days=5), status="active"),
        _Policy(now + timedelta(days=1), status="active"),
        _Policy(now - timedelta(days=1), status="active"),
        _Policy(now - timedelta(days=31), status="active"),
        _Policy(now + timedelta(days=15), status="cancelled"),
    ]
    summary = classify_policy_summary_kpis(policies)  # type: ignore[arg-type]

    assert summary["total_policies"] == 6
    assert summary["active_policies"] == 3
    assert summary["grace_period_policies"] == 1
    assert summary["lapsed_policies"] == 1
    assert summary["expiring_soon_policies"] == 2
    assert is_expiring_soon_policy(policies[1])  # type: ignore[arg-type]
    assert is_expiring_soon_policy(policies[2])  # type: ignore[arg-type]
    assert not is_expiring_soon_policy(policies[0])  # type: ignore[arg-type]
