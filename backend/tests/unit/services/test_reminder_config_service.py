from datetime import UTC, datetime, time
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.core import Organization
from app.models.reminder_config import ReminderConfig
from app.services.reminder_config_service import ReminderConfigService, ReminderOffsetSetting


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def seed_org(async_session):
    org = Organization(name=f"Org {uuid4().hex[:8]}", created_at=utcnow_naive(), updated_at=utcnow_naive())
    async_session.add(org)
    await async_session.commit()
    return org


@pytest.mark.asyncio
async def test_create_configs_creates_one_row_per_offset(async_session):
    org = await seed_org(async_session)
    service = ReminderConfigService(async_session)

    created = await service.create_configs(
        organization_id=org.id,
        entity_type="policy",
        entity_id=101,
        channel="whatsapp",
        offsets=[30, 15, 5],
        offset_unit="days",
        dnd_start=time(22, 0),
        dnd_end=time(8, 0),
    )

    assert len(created) == 3
    assert {row.offset_value for row in created} == {30, 15, 5}
    assert all(row.template_key is None for row in created)
    assert all(row.is_active is True for row in created)
    assert all(row.channel == "whatsapp" for row in created)
    assert all(row.dnd_start == time(22, 0) for row in created)
    assert all(row.dnd_end == time(8, 0) for row in created)


@pytest.mark.asyncio
async def test_create_configs_skips_active_duplicates(async_session):
    org = await seed_org(async_session)
    service = ReminderConfigService(async_session)

    first = await service.create_configs(
        organization_id=org.id,
        entity_type="policy",
        entity_id=202,
        channel="whatsapp",
        offsets=[30, 15],
    )
    assert len(first) == 2

    second = await service.create_configs(
        organization_id=org.id,
        entity_type="policy",
        entity_id=202,
        channel="whatsapp",
        offsets=[30, 15, 5],
    )

    assert len(second) == 1
    assert second[0].offset_value == 5


@pytest.mark.asyncio
async def test_create_configs_allows_duplicate_when_inactive(async_session):
    org = await seed_org(async_session)
    now = utcnow_naive()
    inactive = ReminderConfig(
        organization_id=org.id,
        entity_type="invoice",
        entity_id=9,
        channel="email",
        template_key=None,
        offset_value=7,
        offset_unit="days",
        is_active=False,
        created_at=now,
        updated_at=now,
    )
    async_session.add(inactive)
    await async_session.commit()

    service = ReminderConfigService(async_session)
    created = await service.create_configs(
        organization_id=org.id,
        entity_type="invoice",
        entity_id=9,
        channel="email",
        offsets=[7],
    )

    assert len(created) == 1
    assert created[0].offset_value == 7
    assert created[0].is_active is True


@pytest.mark.asyncio
async def test_list_active_configs_sorted_by_offset_desc(async_session):
    org = await seed_org(async_session)
    service = ReminderConfigService(async_session)
    await service.create_configs(
        organization_id=org.id,
        entity_type="policy",
        entity_id=333,
        channel="whatsapp",
        offsets=[5, 30, 15],
    )

    rows = await service.list_active_configs(
        organization_id=org.id,
        entity_type="policy",
        entity_id=333,
    )

    assert [row.offset_value for row in rows] == [30, 15, 5]


@pytest.mark.asyncio
async def test_update_config_updates_only_provided_fields(async_session):
    org = await seed_org(async_session)
    service = ReminderConfigService(async_session)
    created = await service.create_configs(
        organization_id=org.id,
        entity_type="policy",
        entity_id=808,
        channel="whatsapp",
        offsets=[30],
    )
    config = created[0]

    updated = await service.update_config(
        config.id,
        updates={"offset_value": 20, "is_active": False},
    )

    assert updated.offset_value == 20
    assert updated.is_active is False
    assert updated.channel == "whatsapp"
    assert updated.updated_at is not None


@pytest.mark.asyncio
async def test_update_config_not_found_raises(async_session):
    service = ReminderConfigService(async_session)
    with pytest.raises(ValueError, match="reminder config not found"):
        await service.update_config(999999, updates={"offset_value": 10})


@pytest.mark.asyncio
async def test_save_entity_settings_upserts_and_deactivates_stale(async_session):
    org = await seed_org(async_session)
    service = ReminderConfigService(async_session)

    first = await service.save_entity_settings(
        organization_id=org.id,
        entity_type="pest_control",
        entity_id=501,
        channels=["whatsapp"],
        offsets=[
            ReminderOffsetSetting(offset_value=30, offset_unit="days"),
            ReminderOffsetSetting(offset_value=7, offset_unit="days"),
        ],
        template_key=None,
    )
    assert len(first) == 2

    second = await service.save_entity_settings(
        organization_id=org.id,
        entity_type="pest_control",
        entity_id=501,
        channels=["whatsapp"],
        offsets=[ReminderOffsetSetting(offset_value=15, offset_unit="days")],
        template_key=None,
    )
    assert len(second) == 1

    rows = await service.list_active_configs(
        organization_id=org.id,
        entity_type="pest_control",
        entity_id=501,
    )
    assert len(rows) == 1
    assert rows[0].offset_value == 15


@pytest.mark.asyncio
async def test_deactivate_config_sets_is_active_false(async_session):
    org = await seed_org(async_session)
    service = ReminderConfigService(async_session)
    created = await service.create_configs(
        organization_id=org.id,
        entity_type="policy",
        entity_id=909,
        channel="whatsapp",
        offsets=[10],
    )
    config = created[0]

    deactivated = await service.deactivate_config(config.id)
    assert deactivated.is_active is False
    assert deactivated.updated_at is not None


@pytest.mark.asyncio
async def test_deactivate_config_not_found_raises(async_session):
    service = ReminderConfigService(async_session)
    with pytest.raises(ValueError, match="reminder config not found"):
        await service.deactivate_config(999999)


@pytest.mark.asyncio
async def test_update_config_with_channels_replaces_one_with_many(async_session):
    org = await seed_org(async_session)
    service = ReminderConfigService(async_session)
    created = await service.create_configs(
        organization_id=org.id,
        entity_type="policy",
        entity_id=1200,
        channel="whatsapp",
        offsets=[10],
        offset_unit="days",
    )
    original = created[0]

    await service.update_config_with_channels(
        original.id,
        updates={"offset_value": 10, "offset_unit": "days", "time_of_day": time(11, 30)},
        channels=["email", "sms"],
    )

    rows = list(
        (
            await async_session.execute(
                select(ReminderConfig).where(
                    ReminderConfig.organization_id == org.id,
                    ReminderConfig.entity_type == "policy",
                    ReminderConfig.entity_id == 1200,
                )
            )
        ).scalars()
    )
    assert any(row.channel == "whatsapp" and row.is_active is False for row in rows)
    assert any(row.channel == "email" and row.is_active is True for row in rows)
    assert any(row.channel == "sms" and row.is_active is True for row in rows)
    assert all(row.time_of_day == time(11, 30) for row in rows if row.channel in {"email", "sms"})


@pytest.mark.asyncio
async def test_update_config_with_channels_removes_extra_channels(async_session):
    org = await seed_org(async_session)
    service = ReminderConfigService(async_session)
    await service.save_entity_settings(
        organization_id=org.id,
        entity_type="task",
        entity_id=1300,
        channels=["email", "sms"],
        offsets=[ReminderOffsetSetting(offset_value=5, offset_unit="days", time_of_day=time(9, 0))],
    )
    active_before = await service.list_active_configs(
        organization_id=org.id,
        entity_type="task",
        entity_id=1300,
    )
    email_config = next(row for row in active_before if row.channel == "email")

    await service.update_config_with_channels(
        email_config.id,
        updates={"offset_value": 5, "offset_unit": "days", "time_of_day": time(9, 0)},
        channels=["sms"],
    )

    active_after = await service.list_active_configs(
        organization_id=org.id,
        entity_type="task",
        entity_id=1300,
    )
    assert {row.channel for row in active_after} == {"sms"}
