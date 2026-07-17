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


@pytest.mark.asyncio
async def test_processor_sends_in_app_for_policy_assigned_agent(async_session):
    from app.models.core import Contact
    from app.models.verticals import InsurancePolicy
    from app.services.reminder_resolvers import PolicyReminderResolver

    patch_sqlite_session_bigint_ids(async_session, start_id=93100)
    now = utcnow_naive()
    org = Organization(name=f"Policy InApp {uuid4().hex[:6]}", created_at=now, updated_at=now)
    async_session.add(org)
    await async_session.flush()

    agent = User(
        id=93101,
        organization_id=org.id,
        email=f"agent-{uuid4().hex[:6]}@example.com",
        hashed_password="x",
        role="manager",
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    contact = Contact(
        id=93102,
        organization_id=org.id,
        name="Policy Holder",
        phone="+919111111111",
        created_at=now,
        updated_at=now,
    )
    async_session.add_all([agent, contact])
    await async_session.flush()

    policy = InsurancePolicy(
        id=93103,
        organization_id=org.id,
        policyholder_id=contact.id,
        policy_number=f"INAPP-{uuid4().hex[:6]}",
        premium=1000,
        policy_type="health",
        mobile_number="+919111111111",
        assigned_agent_user_id=agent.id,
        expiry_date=now + timedelta(days=10),
        status="active",
        created_at=now,
        updated_at=now,
    )
    async_session.add(policy)
    await async_session.flush()

    config = ReminderConfig(
        organization_id=org.id,
        entity_type="policy",
        entity_id=0,
        channel="in_app",
        template_key=None,
        entity_label="Policy Renewal",
        offset_value=1,
        offset_unit="days",
        is_active=True,
    )
    async_session.add(config)
    await async_session.flush()

    instance = ReminderInstance(
        config_id=config.id,
        organization_id=org.id,
        entity_type="policy",
        entity_id=policy.id,
        scheduled_at=now - timedelta(minutes=1),
        status="PENDING",
        attempt_count=0,
    )
    async_session.add(instance)
    await async_session.commit()

    factory = ReminderResolverFactory({PolicyReminderResolver().entity_type: PolicyReminderResolver()})
    processor = ReminderProcessorService(async_session, resolver_factory=factory)
    result = await processor.process_due_reminders(org.id)

    assert result["sent"] == 1
    assert result["failed"] == 0

    notifications = await NotificationService(async_session).list_notifications(
        organization_id=org.id,
        user_id=agent.id,
    )
    assert len(notifications) == 1
    assert notifications[0].entity_id == policy.id
    assert notifications[0].title == "Policy Renewal"


@pytest.mark.asyncio
async def test_processor_in_app_prefers_recipient_data_user_id(async_session):
    patch_sqlite_session_bigint_ids(async_session, start_id=93200)
    now = utcnow_naive()
    org = Organization(name=f"Data InApp {uuid4().hex[:6]}", created_at=now, updated_at=now)
    async_session.add(org)
    await async_session.flush()

    user = User(
        id=93201,
        organization_id=org.id,
        email=f"data-{uuid4().hex[:6]}@example.com",
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
        entity_id=22,
        channel="in_app",
        template_key=None,
        entity_label="From Recipient Data",
        offset_value=1,
        offset_unit="days",
        is_active=True,
        recipient_data={"user_id": user.id},
    )
    async_session.add(config)
    await async_session.flush()

    instance = ReminderInstance(
        config_id=config.id,
        organization_id=org.id,
        entity_type="sample_in_app",
        entity_id=22,
        scheduled_at=now - timedelta(minutes=1),
        status="PENDING",
        attempt_count=0,
    )
    async_session.add(instance)
    await async_session.commit()

    # Resolver returns no recipient_user_id — recipient_data must win.
    factory = ReminderResolverFactory({StubInAppResolver.entity_type: StubInAppResolver(user_id=0)})
    processor = ReminderProcessorService(async_session, resolver_factory=factory)

    class NoUserResolver(StubInAppResolver):
        def get_recipient_user_id(self, entity):
            return None

    factory = ReminderResolverFactory({NoUserResolver.entity_type: NoUserResolver(user_id=0)})
    processor = ReminderProcessorService(async_session, resolver_factory=factory)
    result = await processor.process_due_reminders(org.id)

    assert result["sent"] == 1
    notifications = await NotificationService(async_session).list_notifications(
        organization_id=org.id,
        user_id=user.id,
    )
    assert len(notifications) == 1


@pytest.mark.asyncio
async def test_processor_in_app_missing_policy_agent_has_descriptive_error(async_session):
    from app.models.core import Contact
    from app.models.verticals import InsurancePolicy
    from app.services.reminder_resolvers import PolicyReminderResolver

    patch_sqlite_session_bigint_ids(async_session, start_id=93300)
    now = utcnow_naive()
    org = Organization(name=f"Missing Agent {uuid4().hex[:6]}", created_at=now, updated_at=now)
    async_session.add(org)
    await async_session.flush()

    contact = Contact(
        id=93301,
        organization_id=org.id,
        name="No Agent Holder",
        phone="+919222222222",
        created_at=now,
        updated_at=now,
    )
    async_session.add(contact)
    await async_session.flush()

    policy = InsurancePolicy(
        id=93302,
        organization_id=org.id,
        policyholder_id=contact.id,
        policy_number=f"NOAGENT-{uuid4().hex[:6]}",
        premium=1000,
        policy_type="health",
        mobile_number="+919222222222",
        assigned_agent_user_id=None,
        expiry_date=now + timedelta(days=10),
        status="active",
        created_at=now,
        updated_at=now,
    )
    async_session.add(policy)
    await async_session.flush()

    config = ReminderConfig(
        organization_id=org.id,
        entity_type="policy",
        entity_id=policy.id,
        channel="in_app",
        offset_value=1,
        offset_unit="days",
        is_active=True,
    )
    async_session.add(config)
    await async_session.flush()

    instance = ReminderInstance(
        config_id=config.id,
        organization_id=org.id,
        entity_type="policy",
        entity_id=policy.id,
        scheduled_at=now - timedelta(minutes=1),
        status="PENDING",
        attempt_count=0,
    )
    async_session.add(instance)
    await async_session.commit()

    factory = ReminderResolverFactory({PolicyReminderResolver().entity_type: PolicyReminderResolver()})
    processor = ReminderProcessorService(async_session, resolver_factory=factory)
    result = await processor.process_due_reminders(org.id)

    assert result["sent"] == 0
    assert result["failed"] == 1
    await async_session.refresh(instance)
    assert instance.status == "FAILED"
    assert "assigned_agent_user_id" in (instance.last_error or "")
    assert str(policy.id) in (instance.last_error or "")
