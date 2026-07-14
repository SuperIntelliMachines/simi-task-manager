from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.jobs.policy_reminder_generator import ensure_policy_reminder_schedule_for_policy
from app.models.core import Organization, User
from app.models.insurance import PolicyReminder
from app.models.verticals import InsurancePolicy
from app.services.insurance_service import InsuranceService
from app.services.policy_service import PolicyService
from app.utils.policy_reminder_stages import ESCALATION_REMINDER_TYPE
from tests.helpers.reminder_configs import seed_policy_reminder_settings
from tests.unit.insurance.test_policy_reminder_generator import patch_sqlite_policy_reminder_ids


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def seed_org(async_session) -> Organization:
    org = Organization(
        name=f"Renew Workflow Org {uuid4().hex[:8]}",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(org)
    await async_session.flush()
    return org


def patch_sqlite_policy_reminder_ids(async_session, start_id: int = 8600):
    next_id = {"value": start_id}
    original_add = async_session.add

    def add_with_policy_reminder_id(obj):
        if isinstance(obj, PolicyReminder) and getattr(obj, "id", None) is None:
            obj.id = next_id["value"]
            next_id["value"] += 1
        return original_add(obj)

    async_session.add = add_with_policy_reminder_id  # type: ignore[method-assign]


@pytest.mark.asyncio
async def test_renew_policy_with_new_expiry_cancels_old_reminders_and_creates_schedule(async_session, monkeypatch):
    org = await seed_org(async_session)
    now = utcnow_naive()

    current_expiry = now + timedelta(days=20)
    new_expiry = now + timedelta(days=385)

    policy = InsurancePolicy(
        id=8611,
        organization_id=org.id,
        policyholder_id=1,
        policy_number="POL-RENEW-WF",
        premium=2500,
        policy_type="life",
        carrier="LIC",
        preferred_channel=["whatsapp"],
        expiry_date=current_expiry,
        status="active",
        created_at=now,
        updated_at=now,
    )
    async_session.add(policy)
    await async_session.flush()

    for index, reminder_type in enumerate(
        [
            "DUE_30_DAYS",
            "DUE_15_DAYS",
            "UPCOMING_10_DAYS",
            "UPCOMING_5_DAYS",
            "CRITICAL_2_DAYS",
            "CRITICAL_1_DAY",
            "EXPIRY_DAY",
            ESCALATION_REMINDER_TYPE,
        ]
    ):
        async_session.add(
            PolicyReminder(
                id=8620 + index,
                policy_id=policy.id,
                organization_id=org.id,
                reminder_at=now + timedelta(days=index),
                stage=30 - index,
                reminder_type=reminder_type,
                channel="whatsapp",
                status="PENDING",
                attempt_count=0,
            )
        )
    await async_session.commit()

    async def noop_audit(*_args, **_kwargs):
        return None

    monkeypatch.setattr("app.services.insurance_service.write_audit_event", noop_audit)

    patch_sqlite_policy_reminder_ids(async_session, start_id=8700)

    service = InsuranceService(async_session)
    updated, reminders = await service.renew_policy_with_new_expiry(
        policy_id=policy.id,
        new_expiry_date=new_expiry,
        renewal_notes="Paid via UPI",
        actor_user_id=None,
    )

    assert updated.status == "active"
    assert updated.expiry_date.date() == new_expiry.date()

    all_reminders = list(
        (await async_session.execute(select(PolicyReminder).where(PolicyReminder.policy_id == policy.id))).scalars()
    )
    canceled_old = [row for row in all_reminders if row.id < 8700]
    new_schedule = [row for row in all_reminders if row.id >= 8700]

    assert len(canceled_old) == 8
    assert all(row.status == "CANCELED" for row in canceled_old)
    assert len(new_schedule) == 0
    assert len(reminders) == 8


@pytest.mark.asyncio
async def test_renew_policy_with_new_expiry_rejects_non_increasing_date(async_session, monkeypatch):
    org = await seed_org(async_session)
    now = utcnow_naive()

    policy = InsurancePolicy(
        id=8631,
        organization_id=org.id,
        policyholder_id=1,
        policy_number="POL-REJECT",
        premium=1000,
        policy_type="auto",
        carrier="Carrier",
        expiry_date=now + timedelta(days=30),
        status="active",
        created_at=now,
        updated_at=now,
    )
    async_session.add(policy)
    await async_session.commit()

    async def noop_audit(*_args, **_kwargs):
        return None

    monkeypatch.setattr("app.services.insurance_service.write_audit_event", noop_audit)

    service = InsuranceService(async_session)
    with pytest.raises(ValueError, match="after the current expiry"):
        await service.renew_policy_with_new_expiry(
            policy_id=policy.id,
            new_expiry_date=now + timedelta(days=10),
            renewal_notes=None,
            actor_user_id=None,
        )


@pytest.mark.asyncio
async def test_renew_policy_with_new_expiry_allows_previously_renewed_status(async_session, monkeypatch):
    org = await seed_org(async_session)
    now = utcnow_naive()

    policy = InsurancePolicy(
        id=8641,
        organization_id=org.id,
        policyholder_id=1,
        policy_number="POL-ALREADY",
        premium=1000,
        policy_type="auto",
        carrier="Carrier",
        expiry_date=now + timedelta(days=30),
        status="renewed",
        created_at=now,
        updated_at=now,
    )
    async_session.add(policy)
    await async_session.commit()

    async def noop_audit(*_args, **_kwargs):
        return None

    monkeypatch.setattr("app.services.insurance_service.write_audit_event", noop_audit)

    service = InsuranceService(async_session)
    renewed, _ = await service.renew_policy_with_new_expiry(
        policy_id=policy.id,
        new_expiry_date=now + timedelta(days=400),
        renewal_notes=None,
        actor_user_id=None,
    )
    assert renewed.status == "active"


@pytest.mark.asyncio
async def test_policy_service_renew_with_new_expiry(async_session, monkeypatch):
    org = await seed_org(async_session)
    agent = User(
        organization_id=org.id,
        email=f"agent-{uuid4().hex[:8]}@example.com",
        hashed_password="x",
        is_active=True,
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(agent)
    await async_session.flush()

    now = utcnow_naive()
    policy = InsurancePolicy(
        id=8651,
        organization_id=org.id,
        policyholder_id=1,
        policy_number="POL-SVC",
        premium=1500,
        policy_type="health",
        carrier="Star",
        expiry_date=now + timedelta(days=15),
        status="active",
        created_at=now,
        updated_at=now,
    )
    async_session.add(policy)
    await async_session.commit()

    async def noop_audit(*_args, **_kwargs):
        return None

    monkeypatch.setattr("app.services.insurance_service.write_audit_event", noop_audit)

    patch_sqlite_policy_reminder_ids(async_session, start_id=8800)

    ps = PolicyService(async_session)
    updated, reminders = await ps.renew_policy_with_new_expiry(
        policy.id,
        new_expiry_date=now + timedelta(days=380),
        renewal_notes="Annual renewal",
        actor_user_id=agent.id,
    )

    assert updated.status == "active"
    assert len(reminders) == 0


@pytest.mark.asyncio
async def test_ensure_policy_reminder_schedule_skips_when_outside_30_day_window(async_session):
    org = await seed_org(async_session)
    now = utcnow_naive()
    expiry = now + timedelta(days=365)

    policy = InsurancePolicy(
        id=8661,
        organization_id=org.id,
        policyholder_id=1,
        policy_number="POL-SCHED",
        premium=1200,
        policy_type="auto",
        carrier="Carrier",
        preferred_channel=["email"],
        expiry_date=expiry,
        status="active",
        created_at=now,
        updated_at=now,
    )
    async_session.add(policy)
    await async_session.commit()

    patch_sqlite_policy_reminder_ids(async_session, start_id=8900)

    created = await ensure_policy_reminder_schedule_for_policy(async_session, policy)
    await async_session.commit()

    assert created == 0


@pytest.mark.asyncio
async def test_ensure_policy_reminder_schedule_creates_full_schedule_in_window(async_session):
    org = await seed_org(async_session)
    now = utcnow_naive()
    expiry = now + timedelta(days=25)

    policy = InsurancePolicy(
        id=8662,
        organization_id=org.id,
        policyholder_id=1,
        policy_number="POL-SCHED-IN-WINDOW",
        premium=1200,
        policy_type="auto",
        carrier="Carrier",
        preferred_channel=["email"],
        expiry_date=expiry,
        status="active",
        created_at=now,
        updated_at=now,
    )
    async_session.add(policy)
    await async_session.commit()

    await seed_policy_reminder_settings(
        async_session,
        organization_id=org.id,
        policy_id=policy.id,
        policy_type="auto",
        channels=["email"],
    )

    patch_sqlite_policy_reminder_ids(async_session, start_id=8910)

    created = await ensure_policy_reminder_schedule_for_policy(async_session, policy)
    await async_session.commit()

    assert created == 7
