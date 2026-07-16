"""Tests for recurring reminder configuration and processing."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.enums import ReminderStopCondition
from app.models.core import Organization
from app.models.reminder_config import ReminderConfig
from app.models.reminder_instance import ReminderInstance
from app.services.reminder_generator import ReminderGeneratorService
from app.services.reminder_processor import ReminderProcessorService
from app.services.reminder_resolvers.base import ReminderEntityResolver, ReminderEntitySnapshot
from app.services.reminder_resolvers.registry import register_resolver
from app.utils.reminder_recurrence_validation import validate_recurrence_fields


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def seed_org(async_session):
    org = Organization(name=f"Org {uuid4().hex[:8]}", created_at=utcnow_naive(), updated_at=utcnow_naive())
    async_session.add(org)
    await async_session.commit()
    return org


@register_resolver("recurring_test")
class _RecurringTestResolver(ReminderEntityResolver):
    entity_type = "recurring_test"

    async def list_entities(self, session, organization_id: int):
        return [self._snapshot(organization_id, 42)]

    async def get_entity(self, session, organization_id: int, entity_id: int):
        if entity_id != 42:
            return None
        return self._snapshot(organization_id, entity_id)

    def _snapshot(self, organization_id: int, entity_id: int) -> ReminderEntitySnapshot:
        return ReminderEntitySnapshot(
            organization_id=organization_id,
            entity_type=self.entity_type,
            entity_id=entity_id,
            anchor_date=utcnow_naive() + timedelta(hours=1),
            recipient="+15555550100",
            reference_id="REF-42",
            customer_name="Test User",
        )

    def build_text_message(self, entity, *, entity_label, scheduled_at, now):
        return "recurring reminder"

    def should_stop_reminder(self, entity, config, *, sent_count, now):
        return False


def test_validate_recurrence_defaults():
    enabled, value, unit, max_attempts, stop, config = validate_recurrence_fields()
    assert enabled is False
    assert value is None
    assert unit is None
    assert max_attempts is None
    assert stop == ReminderStopCondition.ENTITY_INELIGIBLE.value
    assert config is None


def test_validate_recurrence_requires_frequency_when_enabled():
    with pytest.raises(Exception, match="repeat_frequency_value"):
        validate_recurrence_fields(repeat_enabled=True)


@pytest.mark.asyncio
async def test_recurring_config_schedules_next_instance_after_send(async_session, monkeypatch):
    org = await seed_org(async_session)
    anchor = utcnow_naive() - timedelta(hours=2)
    config = ReminderConfig(
        organization_id=org.id,
        entity_type="recurring_test",
        entity_id=42,
        channel="email",
        template_key="generic_reminder",
        offset_value=1,
        offset_unit="hours",
        offset_direction="after",
        repeat_enabled=True,
        repeat_frequency_value=24,
        repeat_frequency_unit="hours",
        max_attempts=5,
        stop_condition=ReminderStopCondition.NEVER.value,
        is_active=True,
    )
    async_session.add(config)
    await async_session.flush()

    instance = ReminderInstance(
        config_id=config.id,
        organization_id=org.id,
        entity_type="recurring_test",
        entity_id=42,
        scheduled_at=utcnow_naive() - timedelta(minutes=5),
        status="PENDING",
    )
    async_session.add(instance)
    await async_session.commit()

    async def _ok_send(self, **kwargs):
        return SimpleNamespace(status="sent")

    monkeypatch.setattr(
        "app.services.reminder_processor.ChannelService.send_outbound_message",
        _ok_send,
    )

    processor = ReminderProcessorService(async_session)
    stats = await processor.process_due_reminders(org.id)
    assert stats["sent"] == 1

    rows = list(
        (
            await async_session.execute(
                select(ReminderInstance).where(ReminderInstance.config_id == config.id)
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 2
    assert any(row.status == "SENT" for row in rows)
    assert any(row.status == "PENDING" for row in rows)


@pytest.mark.asyncio
async def test_recurring_generator_skips_when_pending_exists(async_session):
    org = await seed_org(async_session)
    config = ReminderConfig(
        organization_id=org.id,
        entity_type="recurring_test",
        entity_id=42,
        channel="email",
        template_key="generic_reminder",
        offset_value=1,
        offset_unit="hours",
        offset_direction="after",
        repeat_enabled=True,
        repeat_frequency_value=24,
        repeat_frequency_unit="hours",
        is_active=True,
    )
    async_session.add(config)
    await async_session.flush()
    async_session.add(
        ReminderInstance(
            config_id=config.id,
            organization_id=org.id,
            entity_type="recurring_test",
            entity_id=42,
            scheduled_at=utcnow_naive() + timedelta(hours=1),
            status="PENDING",
        )
    )
    await async_session.commit()

    generator = ReminderGeneratorService(async_session)
    created = await generator.generate_from_active_configs(organization_id=org.id)
    assert created == []
