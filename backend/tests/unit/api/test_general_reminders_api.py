"""Tests for General Reminder Definition CRUD APIs."""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.reminder_definition import ReminderDefinition
from tests.helpers.auth import auth_header, seed_authenticated_context, seed_org, seed_user


def _sample_payload(**overrides):
    body = {
        "module_key": "inventory",
        "reminder_name": "Stock reorder window",
        "description": "Notify when reorder is due",
        "trigger": {"type": "date", "key": "reorder_date"},
        "schedule": {
            "offset_value": 3,
            "offset_unit": "days",
            "direction": "before",
        },
        "channels": ["email", "in_app"],
        "template_key": "generic_reminder",
        "is_active": True,
    }
    body.update(overrides)
    return body


@pytest.mark.asyncio
async def test_create_general_reminder(authed_async_client):
    client, headers, org_id = authed_async_client

    response = await client.post(
        "/api/v1/general-reminders",
        headers=headers,
        json=_sample_payload(),
    )
    assert response.status_code == 201
    data = response.json()
    assert data["organization_id"] == org_id
    assert data["module_key"] == "inventory"
    assert data["reminder_name"] == "Stock reorder window"
    assert data["trigger"] == {"type": "date", "key": "reorder_date"}
    assert data["schedule"]["offset_unit"] == "days"
    assert data["schedule"]["direction"] == "before"
    assert data["channels"] == ["email", "in_app"]
    assert data["is_active"] is True
    assert data["id"]


@pytest.mark.asyncio
async def test_get_general_reminder(authed_async_client):
    client, headers, _org_id = authed_async_client
    created = await client.post(
        "/api/v1/general-reminders",
        headers=headers,
        json=_sample_payload(reminder_name="Get me"),
    )
    definition_id = created.json()["id"]

    response = await client.get(f"/api/v1/general-reminders/{definition_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == definition_id
    assert response.json()["reminder_name"] == "Get me"


@pytest.mark.asyncio
async def test_list_general_reminders_pagination_and_search(authed_async_client):
    client, headers, _org_id = authed_async_client

    await client.post(
        "/api/v1/general-reminders",
        headers=headers,
        json=_sample_payload(reminder_name="Alpha reorder", module_key="inventory"),
    )
    await client.post(
        "/api/v1/general-reminders",
        headers=headers,
        json=_sample_payload(
            reminder_name="HR onboarding bump",
            module_key="hr",
            trigger={"type": "workflow", "key": "onboarding_started"},
        ),
    )

    listed = await client.get("/api/v1/general-reminders", headers=headers)
    assert listed.status_code == 200
    body = listed.json()
    assert body["total"] >= 2
    assert body["limit"] == 50
    assert len(body["items"]) >= 2

    searched = await client.get("/api/v1/general-reminders?q=onboarding", headers=headers)
    assert searched.status_code == 200
    assert searched.json()["total"] >= 1
    assert all("onboarding" in i["reminder_name"].lower() or i["module_key"] == "hr" for i in searched.json()["items"])

    filtered = await client.get("/api/v1/general-reminders?module_key=hr", headers=headers)
    assert filtered.status_code == 200
    assert all(i["module_key"] == "hr" for i in filtered.json()["items"])


@pytest.mark.asyncio
async def test_update_general_reminder(authed_async_client):
    client, headers, _org_id = authed_async_client
    created = await client.post(
        "/api/v1/general-reminders",
        headers=headers,
        json=_sample_payload(),
    )
    definition_id = created.json()["id"]

    response = await client.put(
        f"/api/v1/general-reminders/{definition_id}",
        headers=headers,
        json={
            "reminder_name": "Updated name",
            "schedule": {
                "offset_value": 15,
                "offset_unit": "minutes",
                "direction": "after",
            },
            "is_active": False,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["reminder_name"] == "Updated name"
    assert data["schedule"]["offset_value"] == 15
    assert data["schedule"]["offset_unit"] == "minutes"
    assert data["schedule"]["direction"] == "after"
    assert data["is_active"] is False
    assert data["module_key"] == "inventory"


@pytest.mark.asyncio
async def test_delete_general_reminder(authed_async_client):
    client, headers, _org_id = authed_async_client
    created = await client.post(
        "/api/v1/general-reminders",
        headers=headers,
        json=_sample_payload(reminder_name="Delete me"),
    )
    definition_id = created.json()["id"]

    deleted = await client.delete(f"/api/v1/general-reminders/{definition_id}", headers=headers)
    assert deleted.status_code == 204

    missing = await client.get(f"/api/v1/general-reminders/{definition_id}", headers=headers)
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_validation_rejects_invalid_structure(authed_async_client):
    client, headers, _org_id = authed_async_client

    bad_trigger = await client.post(
        "/api/v1/general-reminders",
        headers=headers,
        json=_sample_payload(trigger={"type": "cron", "key": "x"}),
    )
    assert bad_trigger.status_code == 422

    bad_unit = await client.post(
        "/api/v1/general-reminders",
        headers=headers,
        json=_sample_payload(
            schedule={"offset_value": 1, "offset_unit": "years", "direction": "before"}
        ),
    )
    assert bad_unit.status_code == 422

    bad_direction = await client.post(
        "/api/v1/general-reminders",
        headers=headers,
        json=_sample_payload(
            schedule={"offset_value": 1, "offset_unit": "days", "direction": "during"}
        ),
    )
    assert bad_direction.status_code == 422

    empty_channels = await client.post(
        "/api/v1/general-reminders",
        headers=headers,
        json=_sample_payload(channels=[]),
    )
    assert empty_channels.status_code == 422


@pytest.mark.asyncio
async def test_accepts_any_module_key_without_allowlist(authed_async_client):
    """Platform must not hardcode Insurance/Claims — any module_key is metadata."""
    client, headers, _org_id = authed_async_client

    for module_key in ("crm", "bms", "hr", "fleet", "custom_xyz"):
        response = await client.post(
            "/api/v1/general-reminders",
            headers=headers,
            json=_sample_payload(
                module_key=module_key,
                reminder_name=f"{module_key} rule",
                trigger={"type": "workflow", "key": "stage_entered"},
            ),
        )
        assert response.status_code == 201, module_key
        assert response.json()["module_key"] == module_key


@pytest.mark.asyncio
async def test_organization_isolation(async_session):
    from app.core.database import get_db_session

    org_a, user_a, headers_a = await seed_authenticated_context(async_session)
    org_b = await seed_org(async_session, name="Org B Isolation")
    user_b = await seed_user(async_session, organization_id=org_b.id, role="platform_admin")
    await async_session.commit()
    headers_b = auth_header(user_b.id)

    async def override_session():
        yield async_session

    app.dependency_overrides[get_db_session] = override_session
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            created = await client.post(
                "/api/v1/general-reminders",
                headers=headers_a,
                json=_sample_payload(reminder_name="Org A only"),
            )
            assert created.status_code == 201
            definition_id = created.json()["id"]
            assert created.json()["organization_id"] == org_a.id

            # Org B cannot get / update / delete Org A's definition
            get_b = await client.get(f"/api/v1/general-reminders/{definition_id}", headers=headers_b)
            assert get_b.status_code == 404

            put_b = await client.put(
                f"/api/v1/general-reminders/{definition_id}",
                headers=headers_b,
                json={"reminder_name": "Hijack"},
            )
            assert put_b.status_code == 404

            del_b = await client.delete(f"/api/v1/general-reminders/{definition_id}", headers=headers_b)
            assert del_b.status_code == 404

            # Org B list does not include Org A's definition
            list_b = await client.get("/api/v1/general-reminders", headers=headers_b)
            assert list_b.status_code == 200
            assert all(i["id"] != definition_id for i in list_b.json()["items"])
            assert all(i["organization_id"] == org_b.id for i in list_b.json()["items"])

            # Org A still sees it
            get_a = await client.get(f"/api/v1/general-reminders/{definition_id}", headers=headers_a)
            assert get_a.status_code == 200
            assert get_a.json()["reminder_name"] == "Org A only"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_unknown_id_returns_404(authed_async_client):
    client, headers, _org_id = authed_async_client
    response = await client.get(
        f"/api/v1/general-reminders/{uuid.uuid4()}",
        headers=headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_definition_persists_via_repository(async_session, authed_async_client):
    client, headers, org_id = authed_async_client
    created = await client.post(
        "/api/v1/general-reminders",
        headers=headers,
        json=_sample_payload(reminder_name="Persist check"),
    )
    assert created.status_code == 201
    definition_id = uuid.UUID(created.json()["id"])

    row = await async_session.get(ReminderDefinition, definition_id)
    assert row is not None
    assert int(row.organization_id) == org_id
    assert row.reminder_name == "Persist check"
