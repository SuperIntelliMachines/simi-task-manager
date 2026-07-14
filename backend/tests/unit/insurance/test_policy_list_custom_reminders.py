"""Tests for policy query eager-loading helpers."""

from __future__ import annotations

import pytest

from app.models.core import Contact
from app.models.insurance import PolicyCustomReminder
from app.models.verticals import InsurancePolicy
from app.utils.policy_queries import select_insurance_policies
from app.utils.policy_response import policy_response_from_model
from tests.unit.insurance.test_policy_reminder_generator import seed_org


@pytest.mark.asyncio
async def test_list_policies_serializes_custom_reminders_without_lazy_load(async_session):
    org = await seed_org(async_session)
    from datetime import UTC, datetime, timedelta

    now = datetime.now(UTC).replace(tzinfo=None)
    contact = Contact(
        id=8100,
        organization_id=org.id,
        name="List Reminder Holder",
        created_at=now,
        updated_at=now,
    )
    async_session.add(contact)
    await async_session.flush()

    policy = InsurancePolicy(
        id=8101,
        organization_id=org.id,
        policyholder_id=8100,
        policy_number="LIST-CR-001",
        premium=1000,
        expiry_date=now + timedelta(days=30),
        status="active",
        reminder_type="personalized",
        preferred_channel=["whatsapp"],
        created_at=now,
        updated_at=now,
    )
    async_session.add(policy)
    await async_session.flush()
    async_session.add(
        PolicyCustomReminder(
            id=8102,
            policy_id=policy.id,
            reminder_unit="days",
            reminder_value=7,
            created_at=now,
            updated_at=now,
        )
    )
    await async_session.commit()

    result = await async_session.execute(
        select_insurance_policies(load_custom_reminders=True).where(
            InsurancePolicy.organization_id == org.id
        )
    )
    rows = list(result.scalars().unique().all())
    assert len(rows) == 1
    response = policy_response_from_model(rows[0])
    assert len(response.custom_reminders) == 1
    assert response.custom_reminders[0].reminder_value == 7


@pytest.mark.asyncio
async def test_list_policies_without_custom_reminders_returns_empty_list(async_session):
    org = await seed_org(async_session)
    from datetime import UTC, datetime, timedelta

    now = datetime.now(UTC).replace(tzinfo=None)
    contact = Contact(
        id=8200,
        organization_id=org.id,
        name="Default Reminder Holder",
        created_at=now,
        updated_at=now,
    )
    async_session.add(contact)
    await async_session.flush()

    policy = InsurancePolicy(
        id=8201,
        organization_id=org.id,
        policyholder_id=8200,
        policy_number="LIST-DEFAULT-001",
        premium=1000,
        expiry_date=now + timedelta(days=30),
        status="active",
        reminder_type="default",
        preferred_channel=["whatsapp"],
        created_at=now,
        updated_at=now,
    )
    async_session.add(policy)
    await async_session.commit()

    result = await async_session.execute(
        select_insurance_policies().where(InsurancePolicy.organization_id == org.id)
    )
    rows = list(result.scalars().unique().all())
    response = policy_response_from_model(rows[0])
    assert response.custom_reminders == []
