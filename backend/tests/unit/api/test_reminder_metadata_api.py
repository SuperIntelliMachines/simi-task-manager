"""Tests for Reminder Management metadata APIs."""

from __future__ import annotations

import pytest

from app.services.channel_service import ChannelService
from app.services.reminder_resolvers import ReminderResolverFactory


@pytest.mark.asyncio
async def test_list_reminder_modules_from_resolvers(authed_async_client):
    client, headers, _org_id = authed_async_client

    response = await client.get("/api/v1/reminders/modules", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert len(payload) >= 2

    by_id = {row["id"]: row for row in payload}
    assert "policy" in by_id
    assert "claims" in by_id
    assert by_id["policy"]["name"] == "Insurance"
    assert by_id["policy"]["supports_date"] is True
    assert by_id["policy"]["supports_workflow"] is True
    assert by_id["claims"]["name"] == "Claims"
    assert by_id["claims"]["supports_workflow"] is True

    # Must come from resolvers — never a static central list in the endpoint.
    factory_ids = {item.id for item in ReminderResolverFactory.list_module_summaries()}
    assert set(by_id) == factory_ids


@pytest.mark.asyncio
async def test_get_policy_module_schema(authed_async_client):
    client, headers, _org_id = authed_async_client

    response = await client.get("/api/v1/reminders/modules/policy/schema", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    trigger_keys = {item["key"] for item in payload["trigger_types"]}
    assert "expiry_date" in trigger_keys
    assert any(item["type"] == "date" for item in payload["trigger_types"])
    assert any(item["key"] == "renewal_submitted" for item in payload["workflow_events"])
    assert any(item["id"] == "customer" for item in payload["recipient_types"])
    assert "whatsapp" in payload["supported_channels"]
    assert payload["default_template"] == "policy_renewal_reminder"


@pytest.mark.asyncio
async def test_get_claims_module_schema(authed_async_client):
    client, headers, _org_id = authed_async_client

    response = await client.get("/api/v1/reminders/modules/claims/schema", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    event_keys = {item["key"] for item in payload["workflow_events"]}
    assert "pending_submission" in event_keys
    assert "pending_approval" in event_keys
    assert any(item["id"] == "assignee" for item in payload["recipient_types"])
    assert payload["default_template"] == "claims_workflow_reminder"


@pytest.mark.asyncio
async def test_unknown_module_schema_returns_404(authed_async_client):
    client, headers, _org_id = authed_async_client

    response = await client.get("/api/v1/reminders/modules/inventory/schema", headers=headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_reminder_channels_matches_channel_service(authed_async_client):
    client, headers, _org_id = authed_async_client

    response = await client.get("/api/v1/reminders/channels", headers=headers)
    assert response.status_code == 200
    assert response.json() == ChannelService.supported_channels()
    assert response.json() == ["in_app", "email", "sms", "whatsapp", "telegram"]


@pytest.mark.asyncio
async def test_list_reminder_templates_catalog(authed_async_client):
    client, headers, _org_id = authed_async_client

    response = await client.get("/api/v1/reminders/templates", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert len(payload) >= 1
    ids = {row["id"] for row in payload}
    assert "policy_renewal_reminder" in ids
    assert "generic_due_notice" in ids
    for row in payload:
        assert "name" in row
        assert "channel" in row
        assert "body" in row
