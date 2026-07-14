"""Tests for inheriting Telegram linkage when creating a new policy."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.core import Contact
from app.models.verticals import InsurancePolicy
from app.services.insurance_service import InsuranceService
from tests.helpers.sqlite_task import SQLITE_BIGINT_PK_TABLES, patch_sqlite_session_bigint_ids
from tests.unit.insurance.test_policy_reminder_generator import seed_org


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@pytest.mark.asyncio
async def test_create_policy_inherits_telegram_from_latest_linked_policy(async_session, monkeypatch):
    patch_sqlite_session_bigint_ids(async_session, start_id=9800, table_names=SQLITE_BIGINT_PK_TABLES)
    org = await seed_org(async_session)
    today = utcnow_naive()
    monkeypatch.setattr("app.services.insurance_service.utcnow_naive", lambda: today)
    monkeypatch.setattr(
        "app.services.insurance_service.InsuranceService.ensure_default_templates",
        AsyncMock(),
    )
    monkeypatch.setattr(
        "app.services.insurance_service.InsuranceService._ensure_notification_preference",
        AsyncMock(),
    )

    contact = Contact(
        id=9801,
        organization_id=org.id,
        name="Telegram Customer",
        phone="+919876543210",
        created_at=today,
        updated_at=today,
    )
    async_session.add(contact)
    await async_session.flush()

    older_policy = InsurancePolicy(
        id=9802,
        organization_id=org.id,
        policyholder_id=contact.id,
        policy_number=f"POL-OLD-{uuid4().hex[:4]}",
        premium=1000,
        policy_type="health",
        carrier="Carrier",
        preferred_channel=["telegram"],
        mobile_number="919876543210",
        telegram_chat_id=11111111,
        telegram_username="old_user",
        expiry_date=today + timedelta(days=30),
        status="active",
        created_at=today,
        updated_at=today,
    )
    newer_policy = InsurancePolicy(
        id=9803,
        organization_id=org.id,
        policyholder_id=contact.id,
        policy_number=f"POL-NEW-{uuid4().hex[:4]}",
        premium=1200,
        policy_type="health",
        carrier="Carrier",
        preferred_channel=["telegram"],
        mobile_number="+919876543210",
        telegram_chat_id=22222222,
        telegram_username="latest_user",
        expiry_date=today + timedelta(days=60),
        status="active",
        created_at=today,
        updated_at=today,
    )
    async_session.add_all([older_policy, newer_policy])
    await async_session.commit()

    service = InsuranceService(async_session)
    created = await service.create_policy(
        organization_id=org.id,
        policyholder_name="Telegram Customer",
        policy_number=f"POL-INHERIT-{uuid4().hex[:4]}",
        expiry_date=today + timedelta(days=90),
        actor_user_id=None,
        contact_phone="+91 98765 43210",
        preferred_channel=["telegram"],
    )

    stored = (
        await async_session.execute(select(InsurancePolicy).where(InsurancePolicy.id == created.id))
    ).scalar_one()
    assert stored.telegram_chat_id == 22222222
    assert stored.telegram_username == "latest_user"


@pytest.mark.asyncio
async def test_create_policy_leaves_telegram_null_when_no_linked_policy(async_session, monkeypatch):
    patch_sqlite_session_bigint_ids(async_session, start_id=9900, table_names=SQLITE_BIGINT_PK_TABLES)
    org = await seed_org(async_session)
    today = utcnow_naive()
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
    created = await service.create_policy(
        organization_id=org.id,
        policyholder_name=f"New Customer {uuid4().hex[:6]}",
        policy_number=f"POL-NO-TG-{uuid4().hex[:4]}",
        expiry_date=today + timedelta(days=90),
        actor_user_id=None,
        contact_phone="8012345678",
        preferred_channel=["telegram"],
    )

    stored = (
        await async_session.execute(select(InsurancePolicy).where(InsurancePolicy.id == created.id))
    ).scalar_one()
    assert stored.telegram_chat_id is None
    assert stored.telegram_username is None
