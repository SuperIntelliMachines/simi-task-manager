from datetime import timedelta

from app.models.verticals import InsurancePolicy
from app.utils.datetime_utils import utcnow_naive
from app.utils.policy_classifier import (
    policy_list_status_priority,
    sort_policies_default_order,
)


def _policy(policy_id: int, *, days_offset: int, status: str = "active") -> InsurancePolicy:
    now = utcnow_naive()
    return InsurancePolicy(
        id=policy_id,
        organization_id=1,
        policyholder_id=policy_id,
        policy_number=f"POL-{policy_id}",
        premium=1000,
        policy_type="Health",
        carrier="Carrier",
        assigned_agent_user_id=None,
        preferred_channel=None,
        mobile_number=None,
        email=None,
        document_name=None,
        document_path=None,
        expiry_date=now + timedelta(days=days_offset),
        status=status,
        created_at=now,
        updated_at=now,
    )


def test_policy_list_status_priority_order():
    assert policy_list_status_priority(_policy(1, days_offset=-5)) == 1
    assert policy_list_status_priority(_policy(2, days_offset=5)) == 2
    assert policy_list_status_priority(_policy(3, days_offset=30)) == 3


def test_sort_policies_default_order_groups_and_expiry():
    policies = [
        _policy(4, days_offset=60),
        _policy(1, days_offset=-30),
        _policy(3, days_offset=8),
        _policy(2, days_offset=-5),
        _policy(5, days_offset=1),
    ]

    sorted_policies = sort_policies_default_order(policies)

    assert [p.id for p in sorted_policies] == [2, 1, 5, 3, 4]
