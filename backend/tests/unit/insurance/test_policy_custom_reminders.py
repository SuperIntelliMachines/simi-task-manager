"""Tests for multiple personalized custom reminders per policy."""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from unittest.mock import AsyncMock

import pytest

from app.jobs.policy_reminder_generator import generate_daily_policy_reminders
from app.models.core import Contact
from app.models.insurance import PolicyReminder
from app.models.reminder_config import ReminderConfig
from app.models.reminder_instance import ReminderInstance
from app.models.verticals import InsurancePolicy
from app.services.insurance_service import InsuranceService
from app.utils.policy_reminder_stages import (
    PERSONALIZED_REMINDER_TYPE,
    build_multi_custom_reminder_schedule,
    build_policy_reminder_schedule,
    get_policy_reminder_offsets,
    personalized_reminder_stage,
)
from tests.helpers.reminder_configs import seed_entity_reminder_settings
from tests.helpers.sqlite_task import SQLITE_BIGINT_PK_TABLES, patch_sqlite_session_bigint_ids
from tests.unit.insurance.test_policy_reminder_generator import patch_sqlite_policy_reminder_ids, seed_org
from uuid import uuid4

from sqlalchemy import select


def test_personalized_reminder_stage_hours_encoding():
    assert personalized_reminder_stage("hours", 12) == 12
    assert personalized_reminder_stage("days", 7) == 7
    assert personalized_reminder_stage("weeks", 2) == 14
    assert personalized_reminder_stage("months", 1) == 30


def test_get_policy_reminder_offsets_from_custom_reminders():
    custom = [
        {"reminder_unit": "days", "reminder_value": 30},
        {"reminder_unit": "days", "reminder_value": 15},
        {"reminder_unit": "days", "reminder_value": 7},
        {"reminder_unit": "days", "reminder_value": 2},
    ]
    offsets = get_policy_reminder_offsets(
        reminder_type="personalized",
        reminder_unit=None,
        reminder_value=None,
        custom_reminders=custom,
    )
    assert offsets == [30, 15, 7, 2]


def test_build_multi_custom_reminder_schedule_includes_all_offsets():
    expiry = datetime(2026, 7, 1, 12, 0, 0)
    custom = [
        {"reminder_unit": "days", "reminder_value": 30},
        {"reminder_unit": "days", "reminder_value": 7},
        {"reminder_unit": "hours", "reminder_value": 12},
    ]
    schedule = build_multi_custom_reminder_schedule(expiry, custom)
    personalized = [item for item in schedule if item.reminder_type == PERSONALIZED_REMINDER_TYPE]
    stages = sorted(entry.stage for entry in personalized)
    assert stages == [7, 12, 30]


def test_build_policy_reminder_schedule_uses_custom_reminders():
    expiry = datetime(2026, 7, 1, 12, 0, 0)
    custom = [{"reminder_unit": "days", "reminder_value": 15}]
    schedule = build_policy_reminder_schedule(
        expiry,
        reminder_type="personalized",
        reminder_unit=None,
        reminder_value=None,
        custom_reminders=custom,
    )
    personalized = [item for item in schedule if item.reminder_type == PERSONALIZED_REMINDER_TYPE]
    assert len(personalized) == 1
    assert personalized[0].stage == 15


@pytest.mark.asyncio
async def test_generate_daily_policy_reminders_for_multi_custom_policy(async_session, monkeypatch):
    org = await seed_org(async_session)
    today = datetime(2026, 6, 1, 10, 0, 0)
    monkeypatch.setattr("app.utils.policy_reminder_stages.utcnow_naive", lambda: today)

    contact = Contact(
        id=7100,
        organization_id=org.id,
        name="Multi Reminder Holder",
        phone="+919999999999",
        created_at=today,
        updated_at=today,
    )
    async_session.add(contact)
    await async_session.flush()

    expiry = today + timedelta(days=7)
    policy = InsurancePolicy(
        id=7101,
        organization_id=org.id,
        policyholder_id=contact.id,
        policy_number="MULTI-CR-001",
        premium=1000,
        expiry_date=expiry,
        status="active",
        reminder_type="personalized",
        preferred_channel=["whatsapp"],
        created_at=today,
        updated_at=today,
    )
    async_session.add(policy)
    await async_session.flush()

    await seed_entity_reminder_settings(
        async_session,
        organization_id=org.id,
        entity_type="policy",
        entity_id=policy.id,
        channels=["whatsapp"],
        offsets=[30, 15, 7, 2],
        template_key="policy_renewal_reminder",
    )
    await async_session.commit()

    created = await generate_daily_policy_reminders(async_session, organization_id=org.id)

    # 4 personalized offsets, single channel (no legacy escalation row)
    assert created == 4

    rows = list(
        (
            await async_session.execute(
                select(ReminderInstance).where(
                    ReminderInstance.entity_type == "policy",
                    ReminderInstance.entity_id == policy.id,
                )
            )
        ).scalars()
    )
    assert len(rows) == 4

    legacy = list(
        (await async_session.execute(select(PolicyReminder).where(PolicyReminder.policy_id == policy.id))).scalars()
    )
    assert len(legacy) == 0


@pytest.mark.asyncio
async def test_create_policy_does_not_persist_reminder_configs(async_session, monkeypatch):
    patch_sqlite_session_bigint_ids(async_session, start_id=9400, table_names=SQLITE_BIGINT_PK_TABLES)
    patch_sqlite_policy_reminder_ids(async_session, start_id=9500)
    org = await seed_org(async_session)
    today = datetime(2026, 6, 8, 10, 0, 0)
    monkeypatch.setattr("app.services.insurance_service.utcnow_naive", lambda: today)
    monkeypatch.setattr(
        "app.services.insurance_service.InsuranceService.ensure_default_templates",
        AsyncMock(),
    )
    monkeypatch.setattr(
        "app.services.insurance_service.InsuranceService._ensure_notification_preference",
        AsyncMock(),
    )

    service = InsuranceService(async_session)
    policy = await service.create_policy(
        organization_id=org.id,
        policyholder_name=f"Custom Reminder Holder {uuid4().hex[:6]}",
        policy_number=f"CR-{uuid4().hex[:8]}",
        expiry_date=today + timedelta(days=90),
        actor_user_id=None,
        reminder_type="personalized",
        custom_reminders=[
            {"reminder_unit": "days", "reminder_value": 30},
            {"reminder_unit": "days", "reminder_value": 7},
        ],
        dnd_start_time="21:00",
        dnd_end_time="08:00",
        preferred_channel=["whatsapp"],
    )

    rows = (
        await async_session.execute(
            select(ReminderConfig).where(
                ReminderConfig.entity_type == "policy",
                ReminderConfig.entity_id == policy.id,
            )
        )
    ).scalars().all()
    assert len(rows) == 0
    assert policy.reminder_type == "personalized"


@pytest.mark.asyncio
async def test_save_settings_persists_custom_offsets(async_session):
    org = await seed_org(async_session)
    await seed_entity_reminder_settings(
        async_session,
        organization_id=org.id,
        entity_type="policy",
        entity_id=9401,
        channels=["whatsapp"],
        offsets=[30, 7],
        template_key="policy_renewal_reminder",
        dnd_start=time(21, 0),
        dnd_end=time(8, 0),
    )

    rows = (
        await async_session.execute(
            select(ReminderConfig)
            .where(
                ReminderConfig.entity_type == "policy",
                ReminderConfig.entity_id == 9401,
                ReminderConfig.is_active.is_(True),
            )
            .order_by(ReminderConfig.offset_value.desc())
        )
    ).scalars().all()
    assert len(rows) == 2
    assert [row.offset_value for row in rows] == [30, 7]
    assert all(row.dnd_start == time(21, 0) for row in rows)
    assert all(row.dnd_end == time(8, 0) for row in rows)


@pytest.mark.asyncio
async def test_save_settings_update_replaces_offsets(async_session):
    org = await seed_org(async_session)

    await seed_entity_reminder_settings(
        async_session,
        organization_id=org.id,
        entity_type="policy",
        entity_id=9601,
        channels=["whatsapp"],
        offsets=[14],
        template_key="policy_renewal_reminder",
        dnd_start=time(22, 0),
        dnd_end=time(7, 0),
    )

    await seed_entity_reminder_settings(
        async_session,
        organization_id=org.id,
        entity_type="policy",
        entity_id=9601,
        channels=["whatsapp"],
        offsets=[10],
        template_key="policy_renewal_reminder",
        dnd_start=time(23, 30),
        dnd_end=time(6, 30),
    )

    rows = (
        await async_session.execute(
            select(ReminderConfig).where(
                ReminderConfig.entity_type == "policy",
                ReminderConfig.entity_id == 9601,
                ReminderConfig.is_active.is_(True),
            )
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].offset_value == 10
    assert rows[0].dnd_start == time(23, 30)
    assert rows[0].dnd_end == time(6, 30)
