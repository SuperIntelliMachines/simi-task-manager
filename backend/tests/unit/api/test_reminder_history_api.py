"""Tests for Reminder History read APIs."""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db_session
from app.main import app
from app.models.reminder_history import ReminderHistory
from app.models.reminder_template import ReminderTemplate
from tests.helpers.auth import auth_header, seed_authenticated_context, seed_org, seed_user


def utcnow() -> datetime:
    return datetime.utcnow().replace(tzinfo=None)


async def _seed_history(
    session,
    *,
    org_id: int,
    user_id: int,
    reminder_title: str = "Call client",
    channel: str = "email",
    recipient: str = "client@example.com",
    status: str = "SENT",
    executed_at: datetime | None = None,
    reminder_id=None,
    template_id=None,
    provider_message_id: str | None = "msg-1",
    error_message: str | None = None,
) -> ReminderHistory:
    when = executed_at or utcnow()
    row = ReminderHistory(
        id=uuid4(),
        organization_id=org_id,
        reminder_id=reminder_id,
        template_id=template_id,
        created_by=user_id,
        reminder_title=reminder_title,
        channel=channel,
        recipient=recipient,
        status=status,
        provider_message_id=provider_message_id,
        error_message=error_message,
        executed_at=when,
        created_at=when,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


@pytest.mark.asyncio
async def test_list_reminder_history(authed_async_client, async_session):
    client, headers, org_id = authed_async_client
    user_row = await seed_user(
        async_session, organization_id=org_id, email=f"hist-{uuid4().hex[:8]}@test.com"
    )
    await async_session.commit()

    await _seed_history(async_session, org_id=org_id, user_id=user_row.id, reminder_title="Alpha")
    await _seed_history(
        async_session,
        org_id=org_id,
        user_id=user_row.id,
        reminder_title="Beta",
        executed_at=utcnow() - timedelta(minutes=1),
    )

    response = await client.get("/api/v1/reminder-history", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 2
    assert body["page"] == 1
    assert body["page_size"] == 50
    assert len(body["items"]) >= 2
    assert body["items"][0]["executed_at"] >= body["items"][1]["executed_at"]
    assert {"id", "reminder_title", "channel", "recipient", "status", "executed_at"} <= set(
        body["items"][0].keys()
    )


@pytest.mark.asyncio
async def test_list_pagination(authed_async_client, async_session):
    client, headers, org_id = authed_async_client
    user = await seed_user(async_session, organization_id=org_id, email=f"page-{uuid4().hex[:8]}@test.com")
    await async_session.commit()
    for i in range(5):
        await _seed_history(
            async_session,
            org_id=org_id,
            user_id=user.id,
            reminder_title=f"Item {i}",
            executed_at=utcnow() - timedelta(minutes=i),
        )

    page1 = await client.get("/api/v1/reminder-history?page=1&page_size=2", headers=headers)
    assert page1.status_code == 200
    assert len(page1.json()["items"]) == 2
    assert page1.json()["page"] == 1
    assert page1.json()["page_size"] == 2
    assert page1.json()["total"] >= 5

    page2 = await client.get("/api/v1/reminder-history?page=2&page_size=2", headers=headers)
    assert page2.status_code == 200
    assert len(page2.json()["items"]) == 2
    assert page1.json()["items"][0]["id"] != page2.json()["items"][0]["id"]


@pytest.mark.asyncio
async def test_status_and_channel_filters(authed_async_client, async_session):
    client, headers, org_id = authed_async_client
    user = await seed_user(async_session, organization_id=org_id, email=f"filt-{uuid4().hex[:8]}@test.com")
    await async_session.commit()
    await _seed_history(
        async_session, org_id=org_id, user_id=user.id, status="SENT", channel="email", reminder_title="Ok email"
    )
    await _seed_history(
        async_session,
        org_id=org_id,
        user_id=user.id,
        status="FAILED",
        channel="whatsapp",
        reminder_title="Bad WA",
        error_message="provider down",
        provider_message_id=None,
    )

    by_status = await client.get("/api/v1/reminder-history?status=FAILED", headers=headers)
    assert by_status.status_code == 200
    assert by_status.json()["total"] >= 1
    assert all(item["status"] == "FAILED" for item in by_status.json()["items"])

    by_channel = await client.get("/api/v1/reminder-history?channel=whatsapp", headers=headers)
    assert by_channel.status_code == 200
    assert by_channel.json()["total"] >= 1
    assert all(item["channel"] == "whatsapp" for item in by_channel.json()["items"])


@pytest.mark.asyncio
async def test_search_filter(authed_async_client, async_session):
    client, headers, org_id = authed_async_client
    user = await seed_user(async_session, organization_id=org_id, email=f"search-{uuid4().hex[:8]}@test.com")
    await async_session.commit()
    await _seed_history(
        async_session,
        org_id=org_id,
        user_id=user.id,
        reminder_title="UniqueTitleXYZ",
        recipient="other@example.com",
    )
    await _seed_history(
        async_session,
        org_id=org_id,
        user_id=user.id,
        reminder_title="Other",
        recipient="unique-recipient@example.com",
    )

    by_title = await client.get("/api/v1/reminder-history?search=UniqueTitleXYZ", headers=headers)
    assert by_title.status_code == 200
    assert by_title.json()["total"] >= 1
    assert any(item["reminder_title"] == "UniqueTitleXYZ" for item in by_title.json()["items"])

    by_recipient = await client.get(
        "/api/v1/reminder-history?search=unique-recipient", headers=headers
    )
    assert by_recipient.status_code == 200
    assert by_recipient.json()["total"] >= 1
    assert any("unique-recipient" in item["recipient"] for item in by_recipient.json()["items"])


@pytest.mark.asyncio
async def test_date_range_filter(authed_async_client, async_session):
    client, headers, org_id = authed_async_client
    user = await seed_user(async_session, organization_id=org_id, email=f"date-{uuid4().hex[:8]}@test.com")
    await async_session.commit()
    mid = datetime(2026, 7, 15, 12, 0, 0)
    await _seed_history(
        async_session,
        org_id=org_id,
        user_id=user.id,
        reminder_title="In range",
        executed_at=mid,
    )
    await _seed_history(
        async_session,
        org_id=org_id,
        user_id=user.id,
        reminder_title="Out of range",
        executed_at=datetime(2026, 1, 1, 0, 0, 0),
    )

    response = await client.get(
        "/api/v1/reminder-history"
        "?executed_from=2026-07-15T00:00:00&executed_to=2026-07-15T23:59:59&search=In%20range",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["total"] >= 1
    assert all(item["reminder_title"] == "In range" for item in response.json()["items"])


@pytest.mark.asyncio
async def test_get_by_id_and_404(authed_async_client, async_session):
    client, headers, org_id = authed_async_client
    user = await seed_user(async_session, organization_id=org_id, email=f"get-{uuid4().hex[:8]}@test.com")
    now = utcnow()
    template = ReminderTemplate(
        id=uuid4(),
        organization_id=org_id,
        created_by=user.id,
        name="T1",
        channel="email",
        subject="S",
        title=None,
        body="Body",
        variables=[],
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    async_session.add(template)
    await async_session.commit()

    row = await _seed_history(
        async_session,
        org_id=org_id,
        user_id=user.id,
        reminder_title="Detail me",
        template_id=template.id,
        status="FAILED",
        error_message="boom",
        provider_message_id=None,
    )

    ok = await client.get(f"/api/v1/reminder-history/{row.id}", headers=headers)
    assert ok.status_code == 200
    data = ok.json()
    assert data["id"] == str(row.id)
    assert data["reminder_title"] == "Detail me"
    assert data["status"] == "FAILED"
    assert data["error_message"] == "boom"
    assert data["template"]["id"] == str(template.id)
    assert data["template"]["name"] == "T1"
    assert data["organization_id"] == org_id
    assert data["created_by"] == user.id

    missing = await client.get(f"/api/v1/reminder-history/{uuid4()}", headers=headers)
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_organization_isolation(async_session):
    org_a, user_a, headers_a = await seed_authenticated_context(async_session)
    org_b = await seed_org(async_session, name=f"Org B Hist {uuid4().hex[:6]}")
    user_b = await seed_user(async_session, organization_id=org_b.id, role="platform_admin")
    await async_session.commit()
    headers_b = auth_header(user_b.id)

    row = await _seed_history(
        async_session,
        org_id=org_a.id,
        user_id=user_a.id,
        reminder_title="Org A only",
    )

    async def override_session():
        yield async_session

    app.dependency_overrides[get_db_session] = override_session
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            listed_b = await client.get("/api/v1/reminder-history", headers=headers_b)
            assert listed_b.status_code == 200
            assert all(item["reminder_title"] != "Org A only" for item in listed_b.json()["items"])

            get_b = await client.get(f"/api/v1/reminder-history/{row.id}", headers=headers_b)
            assert get_b.status_code == 404

            listed_a = await client.get("/api/v1/reminder-history", headers=headers_a)
            assert listed_a.status_code == 200
            assert any(item["id"] == str(row.id) for item in listed_a.json()["items"])
    finally:
        app.dependency_overrides.clear()
