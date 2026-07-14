from datetime import UTC, date, datetime, time
from uuid import uuid4

import pytest

from app.models.core import Organization
from app.models.reminder_config import ReminderConfig
from app.models.reminder_instance import ReminderInstance
from app.schemas.reminder import ReminderDefinitionBody, ReminderSettingsSaveBody
from app.services.reminder_config_service import (
    ReminderConfigService,
    ReminderDefinitionSetting,
    ReminderOffsetSetting,
)
from app.services.reminder_generator import ReminderGeneratorService
from app.utils.reminder_config_validation import ReminderSchedulingValidationError, validate_scheduling_fields
from app.utils.reminder_schedule import (
    get_default_reminder_time_of_day,
    scheduled_at_for_absolute_config,
    scheduled_at_for_relative_config,
)


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def seed_org(async_session):
    org = Organization(name=f"Org {uuid4().hex[:8]}", created_at=utcnow_naive(), updated_at=utcnow_naive())
    async_session.add(org)
    await async_session.commit()
    return org

class TestReminderSchedulingValidation:
    def test_relative_requires_offset_fields(self):
        with pytest.raises(ReminderSchedulingValidationError, match="offset_value or scheduled_at"):
            validate_scheduling_fields(
                offset_value=None,
                offset_unit="days",
                time_of_day=None,
                absolute_scheduled_at=None,
            )

    def test_absolute_requires_scheduled_at(self):
        with pytest.raises(ReminderSchedulingValidationError, match="offset_value or scheduled_at"):
            validate_scheduling_fields(
                offset_value=None,
                offset_unit=None,
                time_of_day=None,
                absolute_scheduled_at=None,
            )

    def test_cannot_mix_relative_and_absolute(self):
        with pytest.raises(ReminderSchedulingValidationError, match="not both"):
            validate_scheduling_fields(
                offset_value=7,
                offset_unit="days",
                time_of_day=None,
                absolute_scheduled_at=datetime(2026, 8, 1, 9, 0, 0),
            )


class TestReminderScheduleUtils:
    def test_relative_with_default_time_uses_wall_clock_09_00(self):
        anchor = datetime(2026, 8, 8, 0, 0, 0)
        scheduled = scheduled_at_for_relative_config(
            anchor_date=anchor,
            offset_value=7,
            offset_unit="days",
            time_of_day=None,
        )
        assert scheduled == datetime(2026, 8, 1, 9, 0, 0)

    def test_relative_with_explicit_time_of_day(self):
        anchor = datetime(2026, 8, 8, 0, 0, 0)
        scheduled = scheduled_at_for_relative_config(
            anchor_date=anchor,
            offset_value=7,
            offset_unit="days",
            time_of_day=time(15, 30),
        )
        assert scheduled == datetime(2026, 8, 1, 15, 30, 0)

    def test_relative_after_direction_adds_offset(self):
        anchor = datetime(2026, 7, 10, 8, 0, 0)
        scheduled = scheduled_at_for_relative_config(
            anchor_date=anchor,
            offset_value=24,
            offset_unit="hours",
            offset_direction="after",
        )
        assert scheduled == datetime(2026, 7, 11, 8, 0, 0)

    def test_relative_before_direction_subtracts_offset(self):
        anchor = datetime(2026, 8, 8, 0, 0, 0)
        scheduled = scheduled_at_for_relative_config(
            anchor_date=anchor,
            offset_value=30,
            offset_unit="days",
            offset_direction="before",
        )
        assert scheduled == datetime(2026, 7, 9, 9, 0, 0)

    def test_absolute_uses_configured_datetime(self):
        absolute = datetime(2026, 9, 15, 10, 45, 0)
        assert scheduled_at_for_absolute_config(absolute_scheduled_at=absolute) == absolute

    def test_default_reminder_time_is_09_00(self):
        assert get_default_reminder_time_of_day() == time(9, 0)


@pytest.mark.asyncio
async def test_save_definitions_multiple_reminders_different_channels(async_session):
    org = await seed_org(async_session)
    service = ReminderConfigService(async_session)

    configs = await service.save_entity_definitions(
        organization_id=org.id,
        entity_type="task",
        entity_id=42,
        definitions=[
            ReminderDefinitionSetting(
                channels=["email"],
                offset_value=30,
                offset_unit="days",
            ),
            ReminderDefinitionSetting(
                channels=["whatsapp"],
                offset_value=7,
                offset_unit="days",
            ),
            ReminderDefinitionSetting(
                channels=["sms", "telegram"],
                offset_value=1,
                offset_unit="days",
            ),
        ],
    )

    assert len(configs) == 4
    assert {(row.offset_value, row.channel) for row in configs} == {
        (30, "email"),
        (7, "whatsapp"),
        (1, "sms"),
        (1, "telegram"),
    }


@pytest.mark.asyncio
async def test_save_definitions_absolute_reminder(async_session):
    org = await seed_org(async_session)
    service = ReminderConfigService(async_session)
    absolute_at = datetime(2026, 10, 1, 9, 30, 0)

    configs = await service.save_entity_definitions(
        organization_id=org.id,
        entity_type="crm_contact",
        entity_id=9,
        definitions=[
            ReminderDefinitionSetting(
                channels=["email"],
                scheduled_at=absolute_at,
            )
        ],
    )

    assert len(configs) == 1
    assert configs[0].absolute_scheduled_at == absolute_at
    assert configs[0].offset_value == 0


@pytest.mark.asyncio
async def test_save_entity_settings_backward_compatible_cartesian_product(async_session):
    org = await seed_org(async_session)
    service = ReminderConfigService(async_session)

    configs = await service.save_entity_settings(
        organization_id=org.id,
        entity_type="policy",
        entity_id=100,
        channels=["whatsapp", "email"],
        offsets=[
            ReminderOffsetSetting(offset_value=30, offset_unit="days"),
            ReminderOffsetSetting(offset_value=7, offset_unit="days"),
        ],
    )

    assert len(configs) == 4


@pytest.mark.asyncio
async def test_generator_relative_with_default_time(async_session):
    org = await seed_org(async_session)
    async_session.add(
        ReminderConfig(
            organization_id=org.id,
            entity_type="task",
            entity_id=5,
            channel="email",
            template_key="generic_reminder",
            offset_value=7,
            offset_unit="days",
            is_active=True,
        )
    )
    await async_session.commit()

    service = ReminderGeneratorService(async_session)
    created = await service.generate_instances(
        entity_type="task",
        entity_id=5,
        organization_id=org.id,
        anchor_date=datetime(2026, 8, 1, 0, 0, 0),
    )

    assert len(created) == 1
    assert created[0].scheduled_at == datetime(2026, 7, 25, 9, 0, 0)


@pytest.mark.asyncio
async def test_generator_relative_with_explicit_time_of_day(async_session):
    org = await seed_org(async_session)
    async_session.add(
        ReminderConfig(
            organization_id=org.id,
            entity_type="task",
            entity_id=6,
            channel="email",
            template_key="generic_reminder",
            offset_value=7,
            offset_unit="days",
            time_of_day=time(15, 30),
            is_active=True,
        )
    )
    await async_session.commit()

    service = ReminderGeneratorService(async_session)
    created = await service.generate_instances(
        entity_type="task",
        entity_id=6,
        organization_id=org.id,
        anchor_date=datetime(2026, 8, 8, 0, 0, 0),
    )

    assert len(created) == 1
    assert created[0].scheduled_at == datetime(2026, 8, 1, 15, 30, 0)


@pytest.mark.asyncio
async def test_generator_absolute_reminder_ignores_anchor_clock(async_session):
    org = await seed_org(async_session)
    absolute_at = datetime(2026, 11, 5, 15, 0, 0)
    async_session.add(
        ReminderConfig(
            organization_id=org.id,
            entity_type="pest_control",
            entity_id=3,
            channel="sms",
            template_key="generic_reminder",
            offset_value=0,
            offset_unit="days",
            absolute_scheduled_at=absolute_at,
            is_active=True,
        )
    )
    await async_session.commit()

    service = ReminderGeneratorService(async_session)
    created = await service.generate_instances(
        entity_type="pest_control",
        entity_id=3,
        organization_id=org.id,
        anchor_date=datetime(2026, 1, 1, 0, 0, 0),
    )

    assert len(created) == 1
    assert created[0].scheduled_at == absolute_at


@pytest.mark.asyncio
async def test_generator_one_offset_multiple_channels(async_session):
    org = await seed_org(async_session)
    async_session.add_all(
        [
            ReminderConfig(
                organization_id=org.id,
                entity_type="medical_appointment",
                entity_id=8,
                channel="email",
                template_key="generic_reminder",
                offset_value=3,
                offset_unit="days",
                is_active=True,
            ),
            ReminderConfig(
                organization_id=org.id,
                entity_type="medical_appointment",
                entity_id=8,
                channel="whatsapp",
                template_key="generic_reminder",
                offset_value=3,
                offset_unit="days",
                is_active=True,
            ),
        ]
    )
    await async_session.commit()

    service = ReminderGeneratorService(async_session)
    created = await service.generate_instances(
        entity_type="medical_appointment",
        entity_id=8,
        organization_id=org.id,
        anchor_date=datetime(2026, 8, 10, 0, 0, 0),
    )

    assert len(created) == 2
    assert len({item.config_id for item in created}) == 2
    assert all(item.scheduled_at == datetime(2026, 8, 7, 9, 0, 0) for item in created)


class TestReminderSettingsSchemaValidation:
    def test_legacy_settings_body_still_valid(self):
        body = ReminderSettingsSaveBody(
            organization_id=1,
            entity_type="policy",
            entity_id=10,
            channels=["whatsapp"],
            offsets=[{"offset_value": 30, "offset_unit": "days"}],
        )
        assert body.reminders is None

    def test_new_reminders_body_valid(self):
        body = ReminderSettingsSaveBody(
            organization_id=1,
            entity_type="policy",
            entity_id=10,
            reminders=[
                {
                    "channels": ["email"],
                    "offset_value": 30,
                    "offset_unit": "days",
                }
            ],
        )
        assert len(body.reminders or []) == 1

    def test_definition_rejects_mixed_modes(self):
        with pytest.raises(ValueError):
            ReminderDefinitionBody(
                channels=["email"],
                offset_value=7,
                offset_unit="days",
                scheduled_at=datetime(2026, 8, 1, 9, 0, 0),
            )

    def test_legacy_body_requires_channels_when_offsets_present(self):
        with pytest.raises(ValueError, match="channels"):
            ReminderSettingsSaveBody(
                organization_id=1,
                entity_type="policy",
                entity_id=10,
                channels=[],
                offsets=[{"offset_value": 30, "offset_unit": "days"}],
            )

    def test_definition_defaults_anchor_fields(self):
        body = ReminderDefinitionBody(channels=["email"], offset_value=7, offset_unit="days")
        assert body.anchor_type == "date"
        assert body.anchor_key == "anchor_date"
        assert body.offset_direction == "before"

    def test_definition_accepts_generic_anchor_key(self):
        body = ReminderDefinitionBody(
            channels=["email"],
            offset_value=2,
            offset_unit="days",
            anchor_type="workflow",
            anchor_key="any_custom_stage",
            offset_direction="after",
        )
        assert body.anchor_key == "any_custom_stage"
        assert body.offset_direction == "after"

    def test_definition_rejects_invalid_anchor_type(self):
        with pytest.raises(ValueError, match="anchor_type"):
            ReminderDefinitionBody(
                channels=["email"],
                offset_value=1,
                offset_unit="days",
                anchor_type="status",
            )

    def test_definition_rejects_empty_anchor_key(self):
        with pytest.raises(ValueError, match="anchor_key"):
            ReminderDefinitionBody(
                channels=["email"],
                offset_value=1,
                offset_unit="days",
                anchor_key=" ",
            )
