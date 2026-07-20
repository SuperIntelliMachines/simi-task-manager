from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.enums import ReminderGenerationMode
from app.core.config import get_settings
from app.models.core import Organization
from app.models.reminder_config import ReminderConfig
from app.models.reminder_instance import ReminderInstance
from app.models.reminder_template import ReminderTemplate
from app.services.reminder_config_service import (
    ReminderConfigService,
    ReminderDefinitionSetting,
)
from app.services.reminder_generator import ReminderGeneratorService
from app.services.reminder_processor import ReminderProcessorService


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def _seed_org(async_session) -> Organization:
    org = Organization(
        name=f"Payload Org {uuid4().hex[:8]}",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(org)
    await async_session.commit()
    return org


async def _seed_template(
    async_session,
    *,
    organization_id: int,
    name: str,
    channel: str,
    body: str,
    subject: str | None = None,
    whatsapp_template_name: str | None = None,
    approval_status: str | None = None,
) -> ReminderTemplate:
    row = ReminderTemplate(
        organization_id=organization_id,
        name=name,
        channel=channel,
        body=body,
        subject=subject,
        is_active=True,
        variables=[],
        whatsapp_template_name=whatsapp_template_name,
        approval_status=approval_status,
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(row)
    await async_session.commit()
    return row


@pytest.mark.asyncio
async def test_save_payload_mode_materializes_instances(async_session):
    org = await _seed_org(async_session)
    await _seed_template(
        async_session,
        organization_id=org.id,
        name="claims_pending_follow_up",
        channel="email",
        body="Hello {{customer_name}}",
        subject="Case {{case_number}}",
    )
    service = ReminderConfigService(async_session)
    scheduled = utcnow_naive() + timedelta(hours=2)

    configs = await service.save_entity_definitions(
        organization_id=org.id,
        entity_type="claims",
        entity_id=12345,
        definitions=[
            ReminderDefinitionSetting(
                channels=["email"],
                scheduled_at=scheduled,
            )
        ],
        template_key="claims_pending_follow_up",
        template_variables={"customer_name": "John", "case_number": "C-100"},
        recipient_data=[{"email": "customer@example.com"}],
        replace_existing=True,
    )

    assert len(configs) == 1
    assert configs[0].generation_mode == ReminderGenerationMode.PAYLOAD.value

    instances = list(
        (
            await async_session.execute(
                select(ReminderInstance).where(ReminderInstance.config_id == configs[0].id)
            )
        ).scalars()
    )
    assert len(instances) == 1
    assert instances[0].scheduled_at == scheduled
    assert instances[0].status == "PENDING"


@pytest.mark.asyncio
async def test_generate_all_skips_payload_mode_claims_configs(async_session):
    org = await _seed_org(async_session)
    config = ReminderConfig(
        organization_id=org.id,
        entity_type="claims",
        entity_id=12345,
        channel="email",
        template_key="claims_pending_follow_up",
        template_variables={"customer_name": "John"},
        recipient_data=[{"email": "customer@example.com"}],
        offset_value=0,
        offset_unit="days",
        absolute_scheduled_at=utcnow_naive() + timedelta(hours=1),
        generation_mode=ReminderGenerationMode.PAYLOAD.value,
        is_active=True,
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(config)
    await async_session.commit()

    created = await ReminderGeneratorService(async_session).generate_from_active_configs(
        organization_id=org.id
    )
    assert created == []


@pytest.mark.asyncio
async def test_processor_payload_mode_sends_without_resolver(async_session, monkeypatch):
    org = await _seed_org(async_session)
    await _seed_template(
        async_session,
        organization_id=org.id,
        name="claims_pending_follow_up",
        channel="email",
        body="Hello {{customer_name}} your case {{case_number}} is pending.",
        subject="Reminder {{case_number}}",
    )
    scheduled = utcnow_naive() - timedelta(minutes=5)

    config = ReminderConfig(
        organization_id=org.id,
        entity_type="claims",
        entity_id=12345,
        channel="email",
        template_key="claims_pending_follow_up",
        template_variables={"customer_name": "John", "case_number": "C-100"},
        recipient_data=[{"email": "customer@example.com"}],
        offset_value=0,
        offset_unit="days",
        absolute_scheduled_at=scheduled,
        generation_mode=ReminderGenerationMode.PAYLOAD.value,
        is_active=True,
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(config)
    await async_session.flush()

    instance = ReminderInstance(
        config_id=config.id,
        organization_id=org.id,
        entity_type="claims",
        entity_id=12345,
        scheduled_at=scheduled,
        status="PENDING",
    )
    async_session.add(instance)
    await async_session.commit()

    captured: dict[str, object] = {}

    async def _ok_send(self, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(status="sent")

    monkeypatch.setattr(
        "app.services.channel_service.ChannelService.send_outbound_message",
        _ok_send,
    )

    result = await ReminderProcessorService(async_session).process_due_reminders(org.id)
    assert result == {"processed": 1, "sent": 1, "failed": 0}
    assert captured["recipient"] == "customer@example.com"
    assert captured["text"] == "Hello John your case C-100 is pending."


@pytest.mark.asyncio
async def test_processor_payload_mode_email_renders_numbered_placeholders(
    async_session, monkeypatch
):
    """Email bodies with Meta-style {{1}}..{{4}} must render from named variables."""
    org = await _seed_org(async_session)
    await _seed_template(
        async_session,
        organization_id=org.id,
        name="policy_renewal_reminder",
        channel="email",
        body=(
            "Hi {{1}}, this is a reminder for your {{2}} on {{3}}.\n\n"
            "Thank you,\n{{4}}"
        ),
        subject="Reminder: {{2}}",
    )
    scheduled = utcnow_naive() - timedelta(minutes=5)
    template_variables = {
        "customer_name": "Uday",
        "policy_name": "Doctor Appointment",
        "reminder_date": "20 Jul 2026 03:00 PM",
        "company_name": "SIMI",
    }

    config = ReminderConfig(
        organization_id=org.id,
        entity_type="claims",
        entity_id=12345,
        channel="email",
        template_key="policy_renewal_reminder",
        template_variables=template_variables,
        recipient_data=[{"email": "uday@example.com"}],
        offset_value=0,
        offset_unit="days",
        absolute_scheduled_at=scheduled,
        generation_mode=ReminderGenerationMode.PAYLOAD.value,
        is_active=True,
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(config)
    await async_session.flush()

    instance = ReminderInstance(
        config_id=config.id,
        organization_id=org.id,
        entity_type="claims",
        entity_id=12345,
        scheduled_at=scheduled,
        status="PENDING",
    )
    async_session.add(instance)
    await async_session.commit()

    captured: dict[str, object] = {}

    async def _ok_send(self, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(status="sent")

    monkeypatch.setattr(
        "app.services.channel_service.ChannelService.send_outbound_message",
        _ok_send,
    )

    result = await ReminderProcessorService(async_session).process_due_reminders(org.id)
    assert result == {"processed": 1, "sent": 1, "failed": 0}
    assert captured["recipient"] == "uday@example.com"
    assert captured["text"] == (
        "Hi Uday, this is a reminder for your Doctor Appointment on 20 Jul 2026 03:00 PM.\n\n"
        "Thank you,\nSIMI"
    )
    assert "{{" not in captured["text"]
    assert captured["connection_settings"]["subject"] == "Reminder: Doctor Appointment"


@pytest.mark.asyncio
async def test_processor_payload_mode_whatsapp_sends_four_meta_params(async_session, monkeypatch):
    org = await _seed_org(async_session)
    await _seed_template(
        async_session,
        organization_id=org.id,
        name="claims_pending_follow_up",
        channel="whatsapp",
        body="Hi {{1}}, reminder for {{2}} on {{3}}. Thanks, {{4}}",
        whatsapp_template_name="policy_renewal_reminder",
        approval_status="approved",
    )
    scheduled = utcnow_naive() - timedelta(minutes=5)
    template_variables = {
        "customer_name": "John Doe",
        "policy_name": "Health Claim C-100",
        "reminder_date": "20 Jul 2026 03:00 PM",
        "company_name": "SIMI Claims",
    }

    config = ReminderConfig(
        organization_id=org.id,
        entity_type="claims",
        entity_id=12345,
        channel="whatsapp",
        template_key="claims_pending_follow_up",
        template_variables=template_variables,
        recipient_data=[{"whatsapp": "+919876543210"}],
        offset_value=0,
        offset_unit="days",
        absolute_scheduled_at=scheduled,
        generation_mode=ReminderGenerationMode.PAYLOAD.value,
        is_active=True,
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(config)
    await async_session.flush()

    instance = ReminderInstance(
        config_id=config.id,
        organization_id=org.id,
        entity_type="claims",
        entity_id=12345,
        scheduled_at=scheduled,
        status="PENDING",
    )
    async_session.add(instance)
    await async_session.commit()

    captured: dict[str, object] = {}

    async def _ok_send(self, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(status="sent")

    monkeypatch.setattr(
        "app.services.channel_service.ChannelService.send_outbound_message",
        _ok_send,
    )

    result = await ReminderProcessorService(async_session).process_due_reminders(org.id)
    assert result == {"processed": 1, "sent": 1, "failed": 0}
    assert captured["channel"] == "whatsapp"
    assert captured["template_name"] == "policy_renewal_reminder"
    assert captured["template_variables"] == template_variables
    connection_settings = captured["connection_settings"]
    assert connection_settings["use_whatsapp_session_text"] is False
    assert connection_settings["templateLayout"] == {
        "components": [
            {
                "type": "body",
                "param_keys": [
                    "customer_name",
                    "policy_name",
                    "reminder_date",
                    "company_name",
                ],
            }
        ]
    }
    settings = get_settings()
    assert captured["template_language"] == settings.whatsapp_template_language

    from app.channels.whatsapp_template_layout import (
        build_template_components,
        resolve_template_layout,
    )

    layout = resolve_template_layout(
        "policy_renewal_reminder",
        connection_settings,
    )
    components = build_template_components(layout, template_variables)
    body_params = [
        param["text"]
        for component in components
        if component.get("type") == "body"
        for param in component.get("parameters") or []
    ]
    assert body_params == [
        "John Doe",
        "Health Claim C-100",
        "20 Jul 2026 03:00 PM",
        "SIMI Claims",
    ]

