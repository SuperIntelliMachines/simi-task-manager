"""Unit tests for Claims → SIMI ReminderConfigCreateBody adapter."""

import pytest
from pydantic import ValidationError

from app.api.adapters.claims_reminder_config import (
    ClaimsReminderConfigAdapterError,
    adapt_claims_reminder_config_payload,
    is_claims_integration_payload,
    map_claims_channel,
    map_claims_entity_type,
)
from app.schemas.reminder import ReminderConfigCreateBody


def _claims_payload(**overrides):
    base = {
        "organization_id": "12",
        "entity_type": "crm_service_case",
        "entity_id": "99",
        "anchor_date": "2026-07-18T10:00:00Z",
        "trigger": {
            "type": "case_created",
            "to_status": "pending_submission",
            "reminder_key": "claims.follow_up",
        },
        "offset": {"amount": 2, "unit": "days"},
        "recipients": [{"user_id": 7, "email": "agent@example.com"}],
        "channels": ["web", "telegram"],
        "template": "claims_follow_up",
        "metadata": {"case_number": "C-100"},
    }
    base.update(overrides)
    return base


def test_detects_crm_service_case_entity_type():
    assert is_claims_integration_payload(_claims_payload()) is True


def test_detects_claims_shape_without_native_fields():
    payload = _claims_payload(entity_type="claims")
    assert is_claims_integration_payload(payload) is True


def test_does_not_detect_native_simi_reminders_payload():
    assert (
        is_claims_integration_payload(
            {
                "organization_id": 1,
                "entity_type": "claims",
                "entity_id": 1,
                "reminders": [
                    {"offset_value": 1, "offset_unit": "days", "channels": ["telegram"]}
                ],
            }
        )
        is False
    )


def test_does_not_detect_legacy_channel_offsets_payload():
    assert (
        is_claims_integration_payload(
            {
                "organization_id": 1,
                "entity_type": "policy",
                "entity_id": 1,
                "channel": "email",
                "offsets": [7, 1],
            }
        )
        is False
    )


def test_entity_type_alias_crm_service_case_to_claims():
    assert map_claims_entity_type("crm_service_case") == "claims"
    assert map_claims_entity_type("CLAIMS") == "claims"


def test_channel_alias_web_to_in_app():
    assert map_claims_channel("web") == "in_app"
    assert map_claims_channel("telegram") == "telegram"
    assert map_claims_channel("in_app") == "in_app"


def test_channel_alias_unknown_rejected():
    with pytest.raises(ClaimsReminderConfigAdapterError, match="unsupported Claims channel"):
        map_claims_channel("pagerduty")


def test_adapt_maps_full_claims_payload():
    adapted = adapt_claims_reminder_config_payload(_claims_payload())

    assert adapted["organization_id"] == 12
    assert adapted["entity_type"] == "claims"
    assert adapted["entity_id"] == 99
    assert adapted["template_key"] == "claims_follow_up"
    assert adapted["replace_existing"] is False
    assert adapted["recipient_data"] == [
        {"user_id": 7, "email": "agent@example.com"}
    ]
    assert adapted["template_variables"]["case_number"] == "C-100"
    assert adapted["template_variables"]["source"] == "claims_reminder_integration"
    assert adapted["template_variables"]["to_status"] == "pending_submission"
    assert adapted["template_variables"]["anchor_date"] == "2026-07-18T10:00:00Z"

    reminder = adapted["reminders"][0]
    assert reminder["channels"] == ["in_app", "telegram"]
    assert reminder["offset_value"] == 2
    assert reminder["offset_unit"] == "days"
    assert reminder["anchor_type"] == "workflow"
    assert reminder["anchor_key"] == "pending_submission"
    assert reminder["offset_direction"] == "after"


def test_adapt_maps_multiple_claims_recipients():
    adapted = adapt_claims_reminder_config_payload(
        _claims_payload(
            recipients=[
                {
                    "recipient_type": "customer",
                    "email": "customer@example.com",
                    "mobile": "+919999999999",
                },
                {
                    "recipient_type": "manager",
                    "email": "manager@example.com",
                    "simi_user_id": 55,
                },
            ]
        )
    )
    assert adapted["recipient_data"] == [
        {
            "recipient_type": "customer",
            "email": "customer@example.com",
            "mobile": "+919999999999",
            "phone": "+919999999999",
        },
        {
            "recipient_type": "manager",
            "email": "manager@example.com",
            "simi_user_id": 55,
            "user_id": 55,
        },
    ]


def test_adapt_dedupes_web_and_in_app_channels():
    adapted = adapt_claims_reminder_config_payload(
        _claims_payload(channels=["web", "in_app", "telegram"])
    )
    assert adapted["reminders"][0]["channels"] == ["in_app", "telegram"]


def test_adapt_rejects_missing_offset_amount():
    with pytest.raises(ClaimsReminderConfigAdapterError, match="offset.amount"):
        adapt_claims_reminder_config_payload(
            _claims_payload(offset={"unit": "days"})
        )


def test_adapt_rejects_empty_channels():
    with pytest.raises(ClaimsReminderConfigAdapterError, match="channels"):
        adapt_claims_reminder_config_payload(_claims_payload(channels=[]))


def test_schema_accepts_claims_payload_via_ingress_adapter():
    body = ReminderConfigCreateBody.model_validate(_claims_payload())
    assert body.entity_type == "claims"
    assert body.entity_id == 99
    assert body.template_key == "claims_follow_up"
    assert body.replace_existing is False
    assert body.reminders is not None
    assert len(body.reminders) == 1
    assert body.reminders[0].channels == ["in_app", "telegram"]
    assert body.reminders[0].offset_value == 2
    assert body.reminders[0].anchor_type == "workflow"
    assert body.reminders[0].anchor_key == "pending_submission"
    assert body.reminders[0].offset_direction == "after"


def test_schema_still_accepts_native_simi_payload():
    body = ReminderConfigCreateBody.model_validate(
        {
            "organization_id": 1,
            "entity_type": "policy",
            "entity_id": 116,
            "reminders": [
                {
                    "offset_value": 7,
                    "offset_unit": "days",
                    "channels": ["whatsapp"],
                    "time_of_day": "10:00",
                }
            ],
        }
    )
    assert body.entity_type == "policy"
    assert body.reminders is not None
    assert body.reminders[0].channels == ["whatsapp"]
    assert body.replace_existing is True


def test_schema_rejects_invalid_claims_payload():
    with pytest.raises(ValidationError):
        ReminderConfigCreateBody.model_validate(
            _claims_payload(channels=["not-a-real-channel"])
        )


def test_adapt_rejects_unresolved_tenant_uuid():
    with pytest.raises(
        ClaimsReminderConfigAdapterError, match="requires mapping resolution"
    ):
        adapt_claims_reminder_config_payload(
            _claims_payload(organization_id="11111111-1111-1111-1111-111111111111")
        )


def test_adapt_accepts_resolved_tenant_uuid():
    tenant_uuid = "11111111-1111-1111-1111-111111111111"
    adapted = adapt_claims_reminder_config_payload(
        _claims_payload(organization_id=tenant_uuid),
        resolved_organization_id=615,
    )
    assert adapted["organization_id"] == 615
    assert adapted["template_variables"]["claims_tenant_id"] == tenant_uuid


@pytest.mark.asyncio
async def test_adapt_async_maps_tenant_uuid(async_session):
    from datetime import UTC, datetime

    from app.models.external_organization_mapping import ExternalOrganizationMapping
    from app.api.adapters.claims_reminder_config import (
        adapt_claims_reminder_config_payload_async,
    )
    from app.services.external_organization_mapping_service import CLAIMS_SOURCE_SYSTEM
    from tests.helpers.auth import seed_org

    org = await seed_org(async_session, name="Claims Tenant Map Org")
    tenant_uuid = "11111111-1111-1111-1111-111111111111"
    now = datetime.now(UTC).replace(tzinfo=None)
    async_session.add(
        ExternalOrganizationMapping(
            organization_id=org.id,
            source_system=CLAIMS_SOURCE_SYSTEM,
            external_id=tenant_uuid,
            created_at=now,
            updated_at=now,
        )
    )
    await async_session.commit()

    adapted = await adapt_claims_reminder_config_payload_async(
        _claims_payload(organization_id=tenant_uuid, entity_id=77),
        async_session,
    )
    assert adapted["organization_id"] == org.id
    assert adapted["entity_id"] == 77


@pytest.mark.asyncio
async def test_adapt_async_keeps_integer_organization_id(async_session):
    from app.api.adapters.claims_reminder_config import (
        adapt_claims_reminder_config_payload_async,
    )

    adapted = await adapt_claims_reminder_config_payload_async(
        _claims_payload(organization_id=42),
        async_session,
    )
    assert adapted["organization_id"] == 42
