from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from app.models.core import Organization
from app.models.reminder_config import ReminderConfig
from app.models.reminder_instance import ReminderInstance
from app.services.reminder_generator import ReminderGeneratorService


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)

async def seed_org(async_session):
    org = Organization(name=f"Org {uuid4().hex[:8]}", created_at=utcnow_naive(), updated_at=utcnow_naive())
    async_session.add(org)
    await async_session.commit()
    return org


@pytest.mark.asyncio
async def test_generate_multiple_instances(async_session):
    org = await seed_org(async_session)
    async_session.add_all(
        [
            ReminderConfig(
                organization_id=org.id,
                entity_type="policy",
                entity_id=1,
                channel="whatsapp",
                template_key="generic_reminder",
                offset_value=30,
                offset_unit="days",
                is_active=True,
            ),
            ReminderConfig(
                organization_id=org.id,
                entity_type="policy",
                entity_id=1,
                channel="email",
                template_key="generic_reminder",
                offset_value=15,
                offset_unit="days",
                is_active=True,
            ),
        ]
    )
    await async_session.commit()

    service = ReminderGeneratorService(async_session)
    created = await service.generate_instances(
        entity_type="policy",
        entity_id=1,
        organization_id=org.id,
        anchor_date=datetime(2026, 8, 1, 10, 0, 0),
    )

    assert len(created) == 2
    assert all(item.status == "PENDING" for item in created)


@pytest.mark.asyncio
async def test_generate_instances_prevents_duplicates(async_session):
    org = await seed_org(async_session)
    config = ReminderConfig(
        organization_id=org.id,
        entity_type="task",
        entity_id=9,
        channel="email",
        template_key="generic_reminder",
        offset_value=5,
        offset_unit="days",
        is_active=True,
    )
    async_session.add(config)
    await async_session.flush()
    scheduled_at = datetime(2026, 7, 27, 9, 0, 0)
    async_session.add(
        ReminderInstance(
            config_id=config.id,
            organization_id=org.id,
            entity_type="task",
            entity_id=9,
            scheduled_at=scheduled_at,
            status="PENDING",
        )
    )
    await async_session.commit()

    service = ReminderGeneratorService(async_session)
    created = await service.generate_instances(
        entity_type="task",
        entity_id=9,
        organization_id=org.id,
        anchor_date=datetime(2026, 8, 1, 9, 0, 0),
    )
    assert created == []


@pytest.mark.asyncio
async def test_generate_instances_supports_all_units(async_session):
    org = await seed_org(async_session)
    anchor = datetime(2026, 3, 31, 12, 0, 0)
    configs = [
        ReminderConfig(
            organization_id=org.id,
            entity_type="invoice",
            entity_id=5,
            channel="email",
            template_key="generic_reminder",
            offset_value=48,
            offset_unit="hours",
            is_active=True,
        ),
        ReminderConfig(
            organization_id=org.id,
            entity_type="invoice",
            entity_id=5,
            channel="whatsapp",
            template_key="generic_reminder",
            offset_value=10,
            offset_unit="days",
            is_active=True,
        ),
        ReminderConfig(
            organization_id=org.id,
            entity_type="invoice",
            entity_id=5,
            channel="telegram",
            template_key="generic_reminder",
            offset_value=2,
            offset_unit="weeks",
            is_active=True,
        ),
        ReminderConfig(
            organization_id=org.id,
            entity_type="invoice",
            entity_id=5,
            channel="email",
            template_key="generic_reminder",
            offset_value=1,
            offset_unit="months",
            is_active=True,
        ),
    ]
    async_session.add_all(configs)
    await async_session.commit()

    service = ReminderGeneratorService(async_session)
    created = await service.generate_instances(
        entity_type="invoice",
        entity_id=5,
        organization_id=org.id,
        anchor_date=anchor,
    )

    got = {item.scheduled_at for item in created}
    assert datetime(2026, 3, 29, 9, 0, 0) in got  # 48 hours -> default 09:00 wall clock
    assert datetime(2026, 3, 21, 9, 0, 0) in got  # 10 days
    assert datetime(2026, 3, 17, 9, 0, 0) in got  # 2 weeks
    assert datetime(2026, 2, 28, 9, 0, 0) in got  # 1 month from Mar 31


@pytest.mark.asyncio
async def test_generate_instances_ignores_inactive_configs(async_session):
    org = await seed_org(async_session)
    async_session.add(
        ReminderConfig(
            organization_id=org.id,
            entity_type="lead",
            entity_id=11,
            channel="whatsapp",
            template_key="generic_reminder",
            offset_value=3,
            offset_unit="days",
            is_active=False,
        )
    )
    await async_session.commit()

    service = ReminderGeneratorService(async_session)
    created = await service.generate_instances(
        entity_type="lead",
        entity_id=11,
        organization_id=org.id,
        anchor_date=datetime(2026, 8, 10, 9, 0, 0),
    )
    assert created == []
