"""Tests for Reminder Template CRUD APIs."""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.reminder_template import ReminderTemplate
from tests.helpers.auth import auth_header, seed_authenticated_context, seed_org, seed_user


def _email_payload(**overrides):
    body = {
        "name": "Renewal Email",
        "channel": "email",
        "subject": "Your policy renewal",
        "body": "Hello {customer_name}, your policy renews soon.",
        "variables": ["customer_name"],
        "is_active": True,
    }
    body.update(overrides)
    return body


@pytest.mark.asyncio
async def test_create_email_template(authed_async_client):
    client, headers, org_id = authed_async_client

    response = await client.post(
        "/api/v1/reminder-templates",
        headers=headers,
        json=_email_payload(),
    )
    assert response.status_code == 201
    data = response.json()
    assert data["organization_id"] == org_id
    assert data["channel"] == "email"
    assert data["subject"] == "Your policy renewal"
    assert data["approval_status"] is None


@pytest.mark.asyncio
async def test_create_whatsapp_template_defaults_to_draft(authed_async_client):
    client, headers, _org_id = authed_async_client

    response = await client.post(
        "/api/v1/reminder-templates",
        headers=headers,
        json={
            "name": "Renewal WhatsApp",
            "channel": "whatsapp",
            "body": "Hi {{1}}, renewal due {{2}}.",
            "variables": ["customer_name", "due_date"],
            "is_active": True,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["approval_status"] == "draft"
    assert data["whatsapp_template_name"] == "Renewal WhatsApp"


@pytest.mark.asyncio
async def test_list_and_get_template(authed_async_client):
    client, headers, _org_id = authed_async_client
    created = await client.post(
        "/api/v1/reminder-templates",
        headers=headers,
        json=_email_payload(name="List me"),
    )
    template_id = created.json()["id"]

    listed = await client.get("/api/v1/reminder-templates", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1

    fetched = await client.get(f"/api/v1/reminder-templates/{template_id}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "List me"


@pytest.mark.asyncio
async def test_update_and_delete_template(authed_async_client):
    client, headers, _org_id = authed_async_client
    created = await client.post(
        "/api/v1/reminder-templates",
        headers=headers,
        json=_email_payload(),
    )
    template_id = created.json()["id"]

    updated = await client.put(
        f"/api/v1/reminder-templates/{template_id}",
        headers=headers,
        json={"name": "Updated Email", "is_active": False},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Updated Email"
    assert updated.json()["is_active"] is False

    deleted = await client.delete(f"/api/v1/reminder-templates/{template_id}", headers=headers)
    assert deleted.status_code == 204

    missing = await client.get(f"/api/v1/reminder-templates/{template_id}", headers=headers)
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_validation_requires_email_subject(authed_async_client):
    client, headers, _org_id = authed_async_client
    response = await client.post(
        "/api/v1/reminder-templates",
        headers=headers,
        json={
            "name": "Bad Email",
            "channel": "email",
            "body": "No subject",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_organization_isolation(async_session):
    from app.core.database import get_db_session

    org_a, _user_a, headers_a = await seed_authenticated_context(async_session)
    org_b = await seed_org(async_session, name="Org B Templates")
    user_b = await seed_user(async_session, organization_id=org_b.id, role="platform_admin")
    await async_session.commit()
    headers_b = auth_header(user_b.id)

    async def override_session():
        yield async_session

    app.dependency_overrides[get_db_session] = override_session
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            created = await client.post(
                "/api/v1/reminder-templates",
                headers=headers_a,
                json=_email_payload(name="Org A template"),
            )
            assert created.status_code == 201
            template_id = created.json()["id"]

            assert (
                await client.get(f"/api/v1/reminder-templates/{template_id}", headers=headers_b)
            ).status_code == 404
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_template_definitions_groups_by_name(authed_async_client):
    client, headers, _org_id = authed_async_client

    await client.post(
        "/api/v1/reminder-templates",
        headers=headers,
        json=_email_payload(name="Renewal Notice"),
    )
    await client.post(
        "/api/v1/reminder-templates",
        headers=headers,
        json={
            "name": "Renewal Notice",
            "channel": "in_app",
            "title": "Renewal",
            "body": "In-app body for {customer_name}",
            "is_active": True,
        },
    )
    await client.post(
        "/api/v1/reminder-templates",
        headers=headers,
        json={
            "name": "Renewal Notice",
            "channel": "whatsapp",
            "body": "Hi {{1}}",
            "is_active": True,
        },
    )
    await client.post(
        "/api/v1/reminder-templates",
        headers=headers,
        json=_email_payload(name="Other Reminder"),
    )

    response = await client.get("/api/v1/reminder-templates/definitions", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 2
    by_name = {item["name"]: item for item in body["items"]}
    assert "Renewal Notice" in by_name
    renewal = by_name["Renewal Notice"]
    assert set(renewal["channels"]) == {"email", "in_app", "whatsapp"}
    assert len(renewal["template_ids"]) == 3
    assert " (" not in renewal["name"]


@pytest.mark.asyncio
async def test_row_persists(async_session, authed_async_client):
    client, headers, org_id = authed_async_client
    created = await client.post(
        "/api/v1/reminder-templates",
        headers=headers,
        json=_email_payload(name="Persist check"),
    )
    template_id = uuid.UUID(created.json()["id"])
    row = await async_session.get(ReminderTemplate, template_id)
    assert row is not None
    assert int(row.organization_id) == org_id
    assert row.name == "Persist check"
