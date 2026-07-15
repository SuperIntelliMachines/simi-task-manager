"""Tests for Personal Reminder CRUD APIs."""

from __future__ import annotations

import uuid
from datetime import datetime

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.personal_reminder import PersonalReminder
from tests.helpers.auth import auth_header, seed_authenticated_context, seed_org, seed_user


def _sample_payload(**overrides):
    body = {
        "title": "Call dentist",
        "description": "Book checkup",
        "scheduled_at": "2026-08-01T09:30:00",
        "channels": ["email", "in_app"],
        "email": "me@example.com",
        "status": "PENDING",
        "is_active": True,
    }
    body.update(overrides)
    return body


@pytest.mark.asyncio
async def test_create_personal_reminder(authed_async_client):
    client, headers, org_id = authed_async_client

    response = await client.post(
        "/api/v1/personal-reminders",
        headers=headers,
        json=_sample_payload(),
    )
    assert response.status_code == 201
    data = response.json()
    assert data["organization_id"] == org_id
    assert data["title"] == "Call dentist"
    assert data["description"] == "Book checkup"
    assert data["status"] == "PENDING"
    assert data["channels"] == ["email", "in_app"]
    assert data["email"] == "me@example.com"
    assert data["scheduled_at"].startswith("2026-08-01T09:30:00")
    assert data["id"]
    assert data["created_by"]
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_get_personal_reminder(authed_async_client):
    client, headers, _org_id = authed_async_client
    created = await client.post(
        "/api/v1/personal-reminders",
        headers=headers,
        json=_sample_payload(title="Get me"),
    )
    reminder_id = created.json()["id"]

    response = await client.get(f"/api/v1/personal-reminders/{reminder_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == reminder_id
    assert response.json()["title"] == "Get me"


@pytest.mark.asyncio
async def test_list_personal_reminders_pagination_and_search(authed_async_client):
    client, headers, _org_id = authed_async_client

    await client.post(
        "/api/v1/personal-reminders",
        headers=headers,
        json=_sample_payload(title="Alpha task", scheduled_at="2026-08-02T10:00:00"),
    )
    await client.post(
        "/api/v1/personal-reminders",
        headers=headers,
        json=_sample_payload(
            title="Beta follow-up",
            description="Needs attention",
            scheduled_at="2026-08-03T10:00:00",
            status="CANCELLED",
        ),
    )

    listed = await client.get("/api/v1/personal-reminders", headers=headers)
    assert listed.status_code == 200
    body = listed.json()
    assert body["total"] >= 2
    assert body["limit"] == 50
    assert len(body["items"]) >= 2

    searched = await client.get("/api/v1/personal-reminders?q=follow-up", headers=headers)
    assert searched.status_code == 200
    assert searched.json()["total"] >= 1

    filtered = await client.get("/api/v1/personal-reminders?status=CANCELLED", headers=headers)
    assert filtered.status_code == 200
    assert all(i["status"] == "CANCELLED" for i in filtered.json()["items"])


@pytest.mark.asyncio
async def test_update_personal_reminder(authed_async_client):
    client, headers, _org_id = authed_async_client
    created = await client.post(
        "/api/v1/personal-reminders",
        headers=headers,
        json=_sample_payload(),
    )
    reminder_id = created.json()["id"]

    response = await client.put(
        f"/api/v1/personal-reminders/{reminder_id}",
        headers=headers,
        json={
            "title": "Updated title",
            "scheduled_at": "2026-09-15T14:00:00",
            "status": "CANCELLED",
            "is_active": False,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated title"
    assert data["status"] == "CANCELLED"
    assert data["is_active"] is False
    assert data["scheduled_at"].startswith("2026-09-15T14:00:00")


@pytest.mark.asyncio
async def test_delete_personal_reminder(authed_async_client):
    client, headers, _org_id = authed_async_client
    created = await client.post(
        "/api/v1/personal-reminders",
        headers=headers,
        json=_sample_payload(title="Delete me"),
    )
    reminder_id = created.json()["id"]

    deleted = await client.delete(f"/api/v1/personal-reminders/{reminder_id}", headers=headers)
    assert deleted.status_code == 204

    missing = await client.get(f"/api/v1/personal-reminders/{reminder_id}", headers=headers)
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_validation_rejects_invalid_payload(authed_async_client):
    client, headers, _org_id = authed_async_client

    bad_status = await client.post(
        "/api/v1/personal-reminders",
        headers=headers,
        json=_sample_payload(status="SNOOZED"),
    )
    assert bad_status.status_code == 422

    empty_title = await client.post(
        "/api/v1/personal-reminders",
        headers=headers,
        json=_sample_payload(title="   "),
    )
    assert empty_title.status_code == 422

    empty_channels = await client.post(
        "/api/v1/personal-reminders",
        headers=headers,
        json=_sample_payload(channels=[]),
    )
    assert empty_channels.status_code == 422


@pytest.mark.asyncio
async def test_organization_and_user_isolation(async_session):
    from app.core.database import get_db_session

    org_a, user_a, headers_a = await seed_authenticated_context(async_session)
    org_b = await seed_org(async_session, name="Org B Personal")
    user_b = await seed_user(async_session, organization_id=org_b.id, role="platform_admin")
    await async_session.commit()
    headers_b = auth_header(user_b.id)

    async def override_session():
        yield async_session

    app.dependency_overrides[get_db_session] = override_session
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            created = await client.post(
                "/api/v1/personal-reminders",
                headers=headers_a,
                json=_sample_payload(title="Org A only"),
            )
            assert created.status_code == 201
            reminder_id = created.json()["id"]
            assert created.json()["organization_id"] == org_a.id
            assert created.json()["created_by"] == user_a.id

            get_b = await client.get(f"/api/v1/personal-reminders/{reminder_id}", headers=headers_b)
            assert get_b.status_code == 404

            put_b = await client.put(
                f"/api/v1/personal-reminders/{reminder_id}",
                headers=headers_b,
                json={"title": "Hijack"},
            )
            assert put_b.status_code == 404

            del_b = await client.delete(f"/api/v1/personal-reminders/{reminder_id}", headers=headers_b)
            assert del_b.status_code == 404

            list_b = await client.get("/api/v1/personal-reminders", headers=headers_b)
            assert list_b.status_code == 200
            assert all(i["id"] != reminder_id for i in list_b.json()["items"])

            get_a = await client.get(f"/api/v1/personal-reminders/{reminder_id}", headers=headers_a)
            assert get_a.status_code == 200
            assert get_a.json()["title"] == "Org A only"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_unknown_id_returns_404(authed_async_client):
    client, headers, _org_id = authed_async_client
    response = await client.get(
        f"/api/v1/personal-reminders/{uuid.uuid4()}",
        headers=headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_row_persists_via_model(async_session, authed_async_client):
    client, headers, org_id = authed_async_client
    created = await client.post(
        "/api/v1/personal-reminders",
        headers=headers,
        json=_sample_payload(title="Persist check"),
    )
    assert created.status_code == 201
    reminder_id = uuid.UUID(created.json()["id"])

    row = await async_session.get(PersonalReminder, reminder_id)
    assert row is not None
    assert int(row.organization_id) == org_id
    assert row.title == "Persist check"
    assert isinstance(row.scheduled_at, datetime)
    assert list(row.channels) == ["email", "in_app"]
