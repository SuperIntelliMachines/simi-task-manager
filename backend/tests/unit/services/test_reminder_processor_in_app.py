"""ReminderProcessorService in_app channel behavior."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.models.core import Organization, User
from app.models.notification import NOTIFICATION_STATUS_UNREAD
from app.models.reminder_config import ReminderConfig
from app.models.reminder_instance import ReminderInstance
from app.services.notification_service import NotificationService
from app.services.reminder_processor import ReminderProcessorService
from app.services.reminder_resolvers.base import ReminderEntityResolver, ReminderEntitySnapshot
from app.services.reminder_resolvers.factory import ReminderResolverFactory
from tests.helpers.sqlite_task import patch_sqlite_session_bigint_ids


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class StubInAppResolver(ReminderEntityResolver):
    entity_type = "sample_in_app"

    def __init__(self, user_id: int):
        self._user_id = user_id

    async def list_entities(self, session, organization_id: int):
        return []

    async def get_entity(self, session, organization_id: int, entity_id: int):
        return ReminderEntitySnapshot(
            organization_id=organization_id,
            entity_type=self.entity_type,
            entity_id=entity_id,
            anchor_date=utcnow_naive() + timedelta(days=1),
            recipient_user_id=self._user_id,
            reference_id=f"REF-{entity_id}",
            customer_name="Staff User",
        )


@pytest.mark.asyncio
async def test_processor_sends_in_app_without_phone(async_session):
    patch_sqlite_session_bigint_ids(async_session, start_id=93000)
    now = utcnow_naive()
    org = Organization(name=f"InApp Org {uuid4().hex[:6]}", created_at=now, updated_at=now)
    async_session.add(org)
    await async_session.flush()

    user = User(
        id=93001,
        organization_id=org.id,
        email=f"staff-{uuid4().hex[:6]}@example.com",
        hashed_password="x",
        role="manager",
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    async_session.add(user)
    await async_session.flush()

    config = ReminderConfig(
        organization_id=org.id,
        entity_type="sample_in_app",
        entity_id=11,
        channel="in_app",
        template_key=None,
        entity_label="Service Follow-up",
        offset_value=1,
        offset_unit="days",
        is_active=True,
    )
    async_session.add(config)
    await async_session.flush()

    instance = ReminderInstance(
        config_id=config.id,
        organization_id=org.id,
        entity_type="sample_in_app",
        entity_id=11,
        scheduled_at=now - timedelta(minutes=1),
        status="PENDING",
        attempt_count=0,
    )
    async_session.add(instance)
    await async_session.commit()

    factory = ReminderResolverFactory(
        {StubInAppResolver.entity_type: StubInAppResolver(user_id=user.id)}
    )
    processor = ReminderProcessorService(async_session, resolver_factory=factory)
    result = await processor.process_due_reminders(org.id)

    assert result["sent"] == 1
    assert result["failed"] == 0

    notifications = await NotificationService(async_session).list_notifications(
        organization_id=org.id,
        user_id=user.id,
    )
    assert len(notifications) == 1
    assert notifications[0].status == NOTIFICATION_STATUS_UNREAD
    assert notifications[0].title == "Service Follow-up"
    assert notifications[0].entity_type == "sample_in_app"
