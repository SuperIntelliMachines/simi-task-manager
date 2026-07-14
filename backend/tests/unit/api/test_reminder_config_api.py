from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.models.reminder_config import ReminderConfig


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@pytest.mark.asyncio
async def test_create_multiple_reminders_with_times_and_channels(authed_async_client):
    client, headers, org_id = authed_async_client

    response = await client.post(
        "/api/v1/reminders/config",
        headers=headers,
        json={
            "organization_id": org_id,
            "entity_type": "policy",
            "entity_id": 116,
            "reminders": [
                {"offset_value": 7, "offset_unit": "days", "time_of_day": "10:00", "channels": ["whatsapp"]},
                {"offset_value": 1, "offset_unit": "days", "time_of_day": "18:00", "channels": ["email"]},
                {"offset_value": 0, "offset_unit": "days", "time_of_day": "09:00", "channels": ["whatsapp", "sms"]},
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["configs"]) == 3
    by_offset = {(row["offset_value"], row["time_of_day"]): set(row["channels"]) for row in payload["configs"]}
    assert by_offset[(7, "10:00:00")] == {"whatsapp"}
    assert by_offset[(1, "18:00:00")] == {"email"}
    assert by_offset[(0, "09:00:00")] == {"whatsapp", "sms"}


@pytest.mark.asyncio
async def test_create_reminders_with_null_time_of_day(authed_async_client):
    client, headers, org_id = authed_async_client

    response = await client.post(
        "/api/v1/reminders/config",
        headers=headers,
        json={
            "organization_id": org_id,
            "entity_type": "task",
            "entity_id": 501,
            "reminders": [
                {"offset_value": 3, "offset_unit": "days", "channels": ["telegram"]},
                {"offset_value": 0, "offset_unit": "days", "time_of_day": None, "channels": ["email", "sms"]},
            ],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["configs"]) == 2
    assert any(row["time_of_day"] is None for row in payload["configs"])


@pytest.mark.asyncio
async def test_get_returns_all_grouped_reminder_configs(authed_async_client):
    client, headers, org_id = authed_async_client
    await client.post(
        "/api/v1/reminders/config",
        headers=headers,
        json={
            "organization_id": org_id,
            "entity_type": "invoice",
            "entity_id": 42,
            "reminders": [
                {"offset_value": 5, "offset_unit": "days", "time_of_day": "09:00", "channels": ["email"]},
                {"offset_value": 5, "offset_unit": "days", "time_of_day": "09:00", "channels": ["whatsapp"]},
                {"offset_value": 1, "offset_unit": "days", "channels": ["sms"]},
            ],
        },
    )

    response = await client.get(
        "/api/v1/reminders/config/invoice/42",
        headers=headers,
        params={"organization_id": org_id},
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["configs"]) == 2
    merged = [row for row in payload["configs"] if row["offset_value"] == 5 and row["time_of_day"] == "09:00:00"]
    assert len(merged) == 1
    assert set(merged[0]["channels"]) == {"email", "whatsapp"}


@pytest.mark.asyncio
async def test_patch_updates_schedule_and_channels(authed_async_client, async_session):
    client, headers, org_id = authed_async_client
    create_response = await client.post(
        "/api/v1/reminders/config",
        headers=headers,
        json={
            "organization_id": org_id,
            "entity_type": "crm_contact",
            "entity_id": 77,
            "reminders": [
                {"offset_value": 7, "offset_unit": "days", "time_of_day": "10:00", "channels": ["email"]},
            ],
        },
    )
    config_id = create_response.json()["configs"][0]["config_id"]

    patch_response = await client.patch(
        f"/api/v1/reminders/config/{config_id}",
        headers=headers,
        json={"offset_value": 3, "offset_unit": "hours", "time_of_day": "08:15", "channels": ["email", "sms"]},
    )
    assert patch_response.status_code == 200
    payload = patch_response.json()
    assert payload["offset_value"] == 3
    assert payload["offset_unit"] == "hours"
    assert payload["time_of_day"] == "08:15:00"
    assert set(payload["channels"]) == {"email", "sms"}

    get_response = await client.get(
        "/api/v1/reminders/config/crm_contact/77",
        headers=headers,
        params={"organization_id": org_id},
    )
    assert get_response.status_code == 200
    groups = get_response.json()["configs"]
    assert any(
        row["offset_value"] == 3
        and row["offset_unit"] == "hours"
        and row["time_of_day"] == "08:15:00"
        and set(row["channels"]) == {"email", "sms"}
        for row in groups
    )

    rows = list(
        (
            await async_session.execute(
                select(ReminderConfig).where(
                    ReminderConfig.organization_id == org_id,
                    ReminderConfig.entity_type == "crm_contact",
                    ReminderConfig.entity_id == 77,
                )
            )
        ).scalars()
    )
    assert any(row.channel == "email" and row.is_active is True for row in rows)
    assert any(row.channel == "sms" and row.is_active is True for row in rows)


@pytest.mark.asyncio
async def test_patch_channel_replacement_deactivates_old_rows_only(authed_async_client, async_session):
    client, headers, org_id = authed_async_client
    create_response = await client.post(
        "/api/v1/reminders/config",
        headers=headers,
        json={
            "organization_id": org_id,
            "entity_type": "policy",
            "entity_id": 5001,
            "reminders": [
                {"offset_value": 10, "offset_unit": "days", "channels": ["whatsapp"]},
            ],
        },
    )
    config_id = create_response.json()["configs"][0]["config_id"]

    patch_response = await client.patch(
        f"/api/v1/reminders/config/{config_id}",
        headers=headers,
        json={"offset_value": 10, "offset_unit": "days", "time_of_day": "11:30:00", "channels": ["email", "sms"]},
    )
    assert patch_response.status_code == 200

    get_response = await client.get(
        "/api/v1/reminders/config/policy/5001",
        headers=headers,
        params={"organization_id": org_id},
    )
    assert get_response.status_code == 200
    groups = get_response.json()["configs"]
    assert any(
        row["offset_value"] == 10
        and row["offset_unit"] == "days"
        and row["time_of_day"] == "11:30:00"
        and set(row["channels"]) == {"email", "sms"}
        for row in groups
    )

    rows = list(
        (
            await async_session.execute(
                select(ReminderConfig).where(
                    ReminderConfig.organization_id == org_id,
                    ReminderConfig.entity_type == "policy",
                    ReminderConfig.entity_id == 5001,
                )
            )
        ).scalars()
    )
    assert any(row.channel == "whatsapp" and row.is_active is False for row in rows)
    assert any(row.channel == "email" and row.is_active is True for row in rows)
    assert any(row.channel == "sms" and row.is_active is True for row in rows)


@pytest.mark.asyncio
async def test_patch_with_is_active_null_keeps_replacement_rows_active(authed_async_client, async_session):
    client, headers, org_id = authed_async_client
    create_response = await client.post(
        "/api/v1/reminders/config",
        headers=headers,
        json={
            "organization_id": org_id,
            "entity_type": "policy",
            "entity_id": 5002,
            "reminders": [
                {"offset_value": 10, "offset_unit": "days", "channels": ["whatsapp"]},
            ],
        },
    )
    config_id = create_response.json()["configs"][0]["config_id"]

    patch_response = await client.patch(
        f"/api/v1/reminders/config/{config_id}",
        headers=headers,
        json={
            "offset_value": 10,
            "offset_unit": "days",
            "time_of_day": "11:30:00",
            "channels": ["email", "sms"],
            "is_active": None,
        },
    )
    assert patch_response.status_code == 200

    rows = list(
        (
            await async_session.execute(
                select(ReminderConfig).where(
                    ReminderConfig.organization_id == org_id,
                    ReminderConfig.entity_type == "policy",
                    ReminderConfig.entity_id == 5002,
                )
            )
        ).scalars()
    )
    assert any(row.channel == "whatsapp" and row.is_active is False for row in rows)
    assert any(row.channel == "email" and row.is_active is True for row in rows)
    assert any(row.channel == "sms" and row.is_active is True for row in rows)


@pytest.mark.asyncio
async def test_delete_soft_deactivates_config(authed_async_client):
    client, headers, org_id = authed_async_client
    create_response = await client.post(
        "/api/v1/reminders/config",
        headers=headers,
        json={
            "organization_id": org_id,
            "entity_type": "medical_visit",
            "entity_id": 17,
            "reminders": [
                {"offset_value": 2, "offset_unit": "days", "channels": ["push"]},
            ],
        },
    )
    config_id = create_response.json()["configs"][0]["config_id"]

    delete_response = await client.delete(
        f"/api/v1/reminders/config/{config_id}",
        headers=headers,
    )
    assert delete_response.status_code == 200

    get_response = await client.get(
        "/api/v1/reminders/config/medical_visit/17",
        headers=headers,
        params={"organization_id": org_id},
    )
    assert get_response.status_code == 200
    assert get_response.json()["configs"] == []


@pytest.mark.asyncio
async def test_legacy_create_payload_still_supported(authed_async_client):
    client, headers, org_id = authed_async_client
    response = await client.post(
        "/api/v1/reminders/config",
        headers=headers,
        json={
            "organization_id": org_id,
            "entity_type": "policy",
            "entity_id": 1,
            "channel": "whatsapp",
            "offsets": [30, 7],
            "offset_unit": "days",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["configs"]) == 2


@pytest.mark.asyncio
async def test_validation_failures(authed_async_client):
    client, headers, org_id = authed_async_client
    missing_channels = await client.post(
        "/api/v1/reminders/config",
        headers=headers,
        json={
            "organization_id": org_id,
            "entity_type": "policy",
            "entity_id": 2,
            "reminders": [{"offset_value": 7, "offset_unit": "days", "channels": []}],
        },
    )
    assert missing_channels.status_code == 422

    invalid_offset = await client.post(
        "/api/v1/reminders/config",
        headers=headers,
        json={
            "organization_id": org_id,
            "entity_type": "policy",
            "entity_id": 3,
            "reminders": [{"offset_value": -1, "offset_unit": "days", "channels": ["email"]}],
        },
    )
    assert invalid_offset.status_code == 422

    duplicate_reminders = await client.post(
        "/api/v1/reminders/config",
        headers=headers,
        json={
            "organization_id": org_id,
            "entity_type": "policy",
            "entity_id": 4,
            "reminders": [
                {"offset_value": 7, "offset_unit": "days", "time_of_day": "10:00", "channels": ["email"]},
                {"offset_value": 7, "offset_unit": "days", "time_of_day": "10:00", "channels": ["email"]},
            ],
        },
    )
    assert duplicate_reminders.status_code == 422


@pytest.mark.asyncio
async def test_create_applies_default_anchor_fields(authed_async_client):
    client, headers, org_id = authed_async_client

    response = await client.post(
        "/api/v1/reminders/config",
        headers=headers,
        json={
            "organization_id": org_id,
            "entity_type": "policy",
            "entity_id": 901,
            "reminders": [
                {"offset_value": 7, "offset_unit": "days", "time_of_day": "10:00", "channels": ["email"]},
            ],
        },
    )
    assert response.status_code == 200
    row = response.json()["configs"][0]
    assert row["anchor_type"] == "date"
    assert row["anchor_key"] == "anchor_date"
    assert row["offset_direction"] == "before"


@pytest.mark.asyncio
async def test_create_and_get_custom_anchor_fields(authed_async_client):
    client, headers, org_id = authed_async_client

    create = await client.post(
        "/api/v1/reminders/config",
        headers=headers,
        json={
            "organization_id": org_id,
            "entity_type": "claims",
            "entity_id": 902,
            "reminders": [
                {
                    "offset_value": 2,
                    "offset_unit": "days",
                    "channels": ["email"],
                    "anchor_type": "workflow",
                    "anchor_key": "pending_submission",
                    "offset_direction": "after",
                },
            ],
        },
    )
    assert create.status_code == 200
    created = create.json()["configs"][0]
    assert created["anchor_type"] == "workflow"
    assert created["anchor_key"] == "pending_submission"
    assert created["offset_direction"] == "after"

    listed = await client.get(
        f"/api/v1/reminders/config/claims/902?organization_id={org_id}",
        headers=headers,
    )
    assert listed.status_code == 200
    row = listed.json()["configs"][0]
    assert row["anchor_type"] == "workflow"
    assert row["anchor_key"] == "pending_submission"
    assert row["offset_direction"] == "after"


@pytest.mark.asyncio
async def test_settings_save_returns_anchor_fields(authed_async_client):
    client, headers, org_id = authed_async_client

    response = await client.put(
        "/api/v1/reminders/config/settings",
        headers=headers,
        json={
            "organization_id": org_id,
            "entity_type": "policy",
            "entity_id": 903,
            "reminders": [
                {
                    "channels": ["whatsapp"],
                    "offset_value": 30,
                    "offset_unit": "days",
                    "anchor_type": "date",
                    "anchor_key": "renewal_date",
                    "offset_direction": "before",
                }
            ],
        },
    )
    assert response.status_code == 200
    row = response.json()["configs"][0]
    assert row["anchor_type"] == "date"
    assert row["anchor_key"] == "renewal_date"
    assert row["offset_direction"] == "before"


@pytest.mark.asyncio
async def test_invalid_anchor_fields_rejected(authed_async_client):
    client, headers, org_id = authed_async_client

    bad_type = await client.post(
        "/api/v1/reminders/config",
        headers=headers,
        json={
            "organization_id": org_id,
            "entity_type": "policy",
            "entity_id": 904,
            "reminders": [
                {
                    "offset_value": 1,
                    "offset_unit": "days",
                    "channels": ["email"],
                    "anchor_type": "status",
                }
            ],
        },
    )
    assert bad_type.status_code == 422

    empty_key = await client.post(
        "/api/v1/reminders/config",
        headers=headers,
        json={
            "organization_id": org_id,
            "entity_type": "policy",
            "entity_id": 905,
            "reminders": [
                {
                    "offset_value": 1,
                    "offset_unit": "days",
                    "channels": ["email"],
                    "anchor_key": "   ",
                }
            ],
        },
    )
    assert empty_key.status_code == 422

    bad_direction = await client.post(
        "/api/v1/reminders/config",
        headers=headers,
        json={
            "organization_id": org_id,
            "entity_type": "policy",
            "entity_id": 906,
            "reminders": [
                {
                    "offset_value": 1,
                    "offset_unit": "days",
                    "channels": ["email"],
                    "offset_direction": "during",
                }
            ],
        },
    )
    assert bad_direction.status_code == 422
