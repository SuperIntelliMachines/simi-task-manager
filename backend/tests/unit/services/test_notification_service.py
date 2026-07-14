"""Unit tests for generic in-app notifications."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.channels.in_app_adapter import InAppAdapter
from app.models.core import Organization, User
from app.models.notification import NOTIFICATION_STATUS_READ, NOTIFICATION_STATUS_UNREAD
from app.services.channel_service import ChannelService
from app.services.notification_service import NotificationService
from app.services.reminder_resolvers.base import ReminderEntitySnapshot
from tests.helpers.sqlite_task import patch_sqlite_session_bigint_ids


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@pytest.mark.asyncio
async def test_notification_service_crud(async_session):
    patch_sqlite_session_bigint_ids(async_session, start_id=91000)
    now = utcnow_naive()
    org = Organization(name=f"Notify Org {uuid4().hex[:6]}", created_at=now, updated_at=now)
    async_session.add(org)
    await async_session.flush()

    user = User(
        id=91001,
        organization_id=org.id,
        email=f"notify-{uuid4().hex[:6]}@example.com",
        hashed_password="x",
        role="manager",
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    async_session.add(user)
    await async_session.commit()

    service = NotificationService(async_session)
    created = await service.create_notification(
        organization_id=org.id,
        user_id=user.id,
        entity_type="policy",
        entity_id=42,
        title="Renewal due",
        message="Please renew policy 42",
        metadata={"reference_id": "POL-42"},
    )
    await async_session.commit()

    assert created.status == NOTIFICATION_STATUS_UNREAD
    assert await service.unread_count(organization_id=org.id, user_id=user.id) == 1

    listed = await service.list_notifications(organization_id=org.id, user_id=user.id)
    assert len(listed) == 1
    assert listed[0].title == "Renewal due"

    read = await service.mark_as_read(organization_id=org.id, user_id=user.id, notification_id=created.id)
    assert read.status == NOTIFICATION_STATUS_READ
    assert await service.unread_count(organization_id=org.id, user_id=user.id) == 0

    await service.create_notification(
        organization_id=org.id,
        user_id=user.id,
        entity_type="claims",
        entity_id=7,
        title="Case attention",
        message="Service case needs review",
    )
    updated = await service.mark_all_as_read(organization_id=org.id, user_id=user.id)
    assert updated == 1
    assert await service.unread_count(organization_id=org.id, user_id=user.id) == 0


@pytest.mark.asyncio
async def test_in_app_adapter_creates_notification(async_session):
    patch_sqlite_session_bigint_ids(async_session, start_id=92000)
    now = utcnow_naive()
    org = Organization(name=f"Adapter Org {uuid4().hex[:6]}", created_at=now, updated_at=now)
    async_session.add(org)
    await async_session.flush()
    user = User(
        id=92001,
        organization_id=org.id,
        email=f"adapter-{uuid4().hex[:6]}@example.com",
        hashed_password="x",
        role="agent",
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    async_session.add(user)
    await async_session.commit()

    adapter = InAppAdapter(async_session)
    provider_id = await adapter.send_outbound_message(
        connection_settings={
            "organization_id": org.id,
            "entity_type": "policy",
            "entity_id": 99,
            "title": "In-app reminder",
            "priority": "high",
            "metadata": {"source": "test"},
        },
        recipient=str(user.id),
        text="Action required",
    )
    assert provider_id.startswith("in-app-")

    service = NotificationService(async_session)
    rows = await service.list_notifications(organization_id=org.id, user_id=user.id)
    assert len(rows) == 1
    assert rows[0].message == "Action required"
    assert rows[0].priority == "high"


@pytest.mark.asyncio
async def test_channel_service_registers_in_app(async_session):
    service = ChannelService(async_session)
    assert "in_app" in service.adapters
    assert service.adapter_for("in_app").channel_name == "in_app"


def test_resolver_exposes_recipient_user_id():
    from app.services.reminder_resolvers.base import ReminderEntityResolver

    class SampleResolver(ReminderEntityResolver):
        entity_type = "sample"

        async def list_entities(self, session, organization_id: int):
            return []

        async def get_entity(self, session, organization_id: int, entity_id: int):
            return None

    entity = ReminderEntitySnapshot(
        organization_id=1,
        entity_type="sample",
        entity_id=1,
        anchor_date=None,
        recipient_user_id=55,
    )
    assert SampleResolver().get_recipient_user_id(entity) == 55
