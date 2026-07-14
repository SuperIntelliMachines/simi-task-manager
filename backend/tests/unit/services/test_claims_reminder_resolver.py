"""Unit tests for ClaimsReminderResolver generic anchor resolution."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.integrations.claims.exceptions import (
    ClaimsAuthenticationError,
    ClaimsNetworkError,
    ClaimsNotFoundError,
)
from app.models.reminder_config import ReminderConfig
from app.services.reminder_resolvers.claims_resolver import ClaimsReminderResolver
from app.services.reminder_resolvers.factory import ReminderResolverFactory
from app.services.reminder_resolvers.registry import get_registered_resolvers, load_resolver_plugins


class FakeClaimsClient:
    def __init__(
        self,
        *,
        case: dict[str, Any] | None = None,
        cases: list[dict[str, Any]] | None = None,
        error: Exception | None = None,
        list_error: Exception | None = None,
        pages: list[dict[str, Any]] | None = None,
    ):
        self._case = case
        self._cases = cases
        self._error = error
        self._list_error = list_error
        self._pages = pages
        self.get_service_case = AsyncMock(side_effect=self._get)
        self.list_service_cases = AsyncMock(side_effect=self._list_page)
        self.list_all_service_cases = AsyncMock(side_effect=self._list_all)
        self.list_calls: list[dict[str, Any]] = []

    async def _get(self, case_id: int | str) -> dict[str, Any]:
        if self._error is not None:
            raise self._error
        assert self._case is not None
        return self._case

    async def _list_page(self, **filters: Any) -> dict[str, Any]:
        self.list_calls.append(dict(filters))
        if self._list_error is not None:
            raise self._list_error
        if self._pages is not None:
            page = int(filters.get("page") or 1)
            index = page - 1
            if 0 <= index < len(self._pages):
                return self._pages[index]
            return {"items": [], "total": 0, "page": page, "page_size": filters.get("page_size")}
        items = self._cases if self._cases is not None else ([] if self._case is None else [self._case])
        return {"items": items, "total": len(items), "page": 1, "page_size": len(items) or 100}

    async def _list_all(self, **kwargs: Any) -> list[dict[str, Any]]:
        if self._list_error is not None:
            raise self._list_error
        if self._pages is not None:
            # Mimic ClaimsClient.list_all_service_cases pagination using list_service_cases.
            # Prefer the fixture page_size so short-page detection matches the mocked pages.
            from app.integrations.claims.client import ClaimsClient

            page_size = kwargs.get("page_size")
            first_page_size = self._pages[0].get("page_size") if self._pages else None
            if isinstance(first_page_size, int) and first_page_size > 0:
                page_size = first_page_size
            real = object.__new__(ClaimsClient)
            real.list_service_cases = self.list_service_cases  # type: ignore[method-assign]
            return await ClaimsClient.list_all_service_cases(
                real,
                page_size=int(page_size or 100),
                max_pages=int(kwargs.get("max_pages") or 100),
            )
        if self._cases is not None:
            return list(self._cases)
        if self._case is not None:
            return [self._case]
        return []


@pytest.fixture
def sample_case() -> dict[str, Any]:
    return {
        "id": 123,
        "case_id": 123,
        "status": "open",
        "title": "Intake review",
        "customer_name": "Ada Lovelace",
        "customer_phone": "+919876543210",
        "customer_email": "ada@example.com",
        "assigned_user_id": 55,
        # Lifecycle fields intentionally omitted — pending Claims API confirmation.
    }


@pytest.mark.asyncio
async def test_resolver_loads_service_case(sample_case):
    client = FakeClaimsClient(case=sample_case)
    resolver = ClaimsReminderResolver(client=client)  # type: ignore[arg-type]

    case = await resolver.resolve_case(123)

    client.get_service_case.assert_awaited_once_with(123)
    assert case["id"] == 123
    assert case["title"] == "Intake review"


@pytest.mark.asyncio
async def test_resolver_returns_valid_resolved_entity(sample_case):
    client = FakeClaimsClient(case=sample_case)
    resolver = ClaimsReminderResolver(client=client)  # type: ignore[arg-type]
    session = MagicMock()

    entity = await resolver.get_entity(session, organization_id=607, entity_id=123)

    assert entity is not None
    assert entity.entity_type == "claims"
    assert entity.entity_id == 123
    assert entity.organization_id == 607
    assert entity.recipient == "+919876543210"
    assert entity.recipient_email == "ada@example.com"
    assert entity.recipient_user_id == 55
    assert entity.customer_name == "Ada Lovelace"
    assert entity.reference_id == "123"
    assert entity.metadata["status"] == "open"
    assert entity.source == sample_case
    assert entity.anchor_date is None


@pytest.mark.asyncio
async def test_missing_service_case_returns_none():
    client = FakeClaimsClient(error=ClaimsNotFoundError("not found"))
    resolver = ClaimsReminderResolver(client=client)  # type: ignore[arg-type]

    entity = await resolver.get_entity(MagicMock(), organization_id=1, entity_id=999)

    assert entity is None


@pytest.mark.asyncio
async def test_claims_api_unavailable_propagates():
    client = FakeClaimsClient(error=ClaimsNetworkError("down"))
    resolver = ClaimsReminderResolver(client=client)  # type: ignore[arg-type]

    with pytest.raises(ClaimsNetworkError):
        await resolver.get_entity(MagicMock(), organization_id=1, entity_id=1)


@pytest.mark.asyncio
async def test_claims_authentication_failure_propagates():
    client = FakeClaimsClient(error=ClaimsAuthenticationError("bad credentials"))
    resolver = ClaimsReminderResolver(client=client)  # type: ignore[arg-type]

    with pytest.raises(ClaimsAuthenticationError):
        await resolver.resolve_case(42)


def test_missing_reminder_fields_keep_entity_ineligible(sample_case):
    resolver = ClaimsReminderResolver(client=FakeClaimsClient(case=sample_case))  # type: ignore[arg-type]

    assert resolver.resolve_case_anchor(sample_case) is None
    assert resolver.resolve_recipient(sample_case) == "+919876543210"

    case_without_phone = {**sample_case}
    case_without_phone.pop("customer_phone")
    assert resolver.resolve_recipient(case_without_phone) is None

    metadata = resolver.resolve_metadata(sample_case)
    assert metadata["available_anchor_keys"] == []

    entity = resolver._to_snapshot(organization_id=1, case=sample_case)
    config = ReminderConfig(
        organization_id=1,
        entity_type="claims",
        entity_id=123,
        channel="whatsapp",
        template_key="claims_placeholder",
        offset_value=1,
        offset_unit="days",
        is_active=True,
        anchor_type="workflow",
        anchor_key="pending_submission",
        offset_direction="after",
    )
    assert resolver.is_eligible(entity, configs=[config]) is False


def test_resolve_case_anchor_parses_lifecycle_field_when_present(sample_case):
    resolver = ClaimsReminderResolver()
    case = {
        **sample_case,
        "submitted_at": "2026-07-10T10:00:00+00:00",
    }
    anchor = resolver.resolve_case_anchor(case)
    assert isinstance(anchor, datetime)
    assert anchor.year == 2026
    assert anchor.month == 7
    assert anchor.day == 10


def test_resolve_anchor_maps_workflow_keys(sample_case):
    resolver = ClaimsReminderResolver()
    case = {
        **sample_case,
        "pending_submission_at": "2026-07-10T08:00:00+00:00",
        "return_pending_at": "2026-07-11T12:00:00+00:00",
        "submitted_at": "2026-07-09T09:00:00+00:00",
        "approved_at": "2026-07-12T16:00:00+00:00",
    }
    entity = resolver._to_snapshot(organization_id=1, case=case)

    pending = resolver.resolve_anchor(entity, "workflow", "pending_submission")
    returned = resolver.resolve_anchor(entity, "workflow", "return_pending")
    submitted = resolver.resolve_anchor(entity, "workflow", "submitted")
    approved = resolver.resolve_anchor(entity, "workflow", "approved")

    assert pending == datetime(2026, 7, 10, 8, 0, 0)
    assert returned == datetime(2026, 7, 11, 12, 0, 0)
    assert submitted == datetime(2026, 7, 9, 9, 0, 0)
    assert approved == datetime(2026, 7, 12, 16, 0, 0)

    config = ReminderConfig(
        organization_id=1,
        entity_type="claims",
        entity_id=123,
        channel="email",
        offset_value=24,
        offset_unit="hours",
        is_active=True,
        anchor_type="workflow",
        anchor_key="pending_submission",
        offset_direction="after",
    )
    assert resolver.is_eligible(entity, configs=[config]) is True


def test_resolve_anchor_supports_generic_future_keys(sample_case):
    resolver = ClaimsReminderResolver()
    case = {
        **sample_case,
        "custom_stage_at": "2026-07-15T10:30:00+00:00",
    }
    entity = resolver._to_snapshot(organization_id=1, case=case)
    assert resolver.resolve_anchor(entity, "workflow", "custom_stage") == datetime(
        2026, 7, 15, 10, 30, 0
    )


def test_claims_resolver_is_registered():
    load_resolver_plugins()
    resolvers = get_registered_resolvers()
    assert "claims" in resolvers
    assert "policy" in resolvers  # insurance module (existing)
    assert isinstance(ReminderResolverFactory.get("claims"), ClaimsReminderResolver)


@pytest.mark.asyncio
async def test_list_entities_maps_cases(sample_case):
    cases = [
        sample_case,
        {
            "id": 124,
            "status": "open",
            "customer_name": "Grace Hopper",
            "customer_phone": "+919111111111",
            "submitted_at": "2026-07-10T09:00:00+00:00",
        },
    ]
    client = FakeClaimsClient(cases=cases)
    resolver = ClaimsReminderResolver(client=client)  # type: ignore[arg-type]

    entities = await resolver.list_entities(MagicMock(), organization_id=607)

    assert len(entities) == 2
    assert {e.entity_id for e in entities} == {123, 124}
    assert all(e.entity_type == "claims" for e in entities)
    assert all(e.organization_id == 607 for e in entities)
    assert entities[0].recipient == "+919876543210"
    assert entities[0].recipient_email == "ada@example.com"
    assert entities[0].recipient_user_id == 55
    assert entities[0].metadata["title"] == "Intake review"
    assert entities[1].anchor_date == datetime(2026, 7, 10, 9, 0, 0)
    client.list_all_service_cases.assert_awaited()
    call_kwargs = client.list_all_service_cases.await_args.kwargs
    assert "organization_id" not in call_kwargs
    assert call_kwargs["page_size"] == 100
    assert call_kwargs["max_pages"] == 100


@pytest.mark.asyncio
async def test_list_entities_empty_response():
    client = FakeClaimsClient(cases=[])
    resolver = ClaimsReminderResolver(client=client)  # type: ignore[arg-type]

    entities = await resolver.list_entities(MagicMock(), organization_id=607)

    assert entities == []


@pytest.mark.asyncio
async def test_list_entities_pagination():
    pages = [
        {
            "items": [
                {"id": 1, "status": "open", "customer_phone": "+911"},
                {"id": 2, "status": "open", "customer_phone": "+912"},
            ],
            "total": 3,
            "page": 1,
            "page_size": 2,
        },
        {
            "items": [{"id": 3, "status": "open", "customer_phone": "+913"}],
            "total": 3,
            "page": 2,
            "page_size": 2,
        },
    ]
    client = FakeClaimsClient(pages=pages)
    resolver = ClaimsReminderResolver(client=client)  # type: ignore[arg-type]

    entities = await resolver.list_entities(MagicMock(), organization_id=42)

    assert [e.entity_id for e in entities] == [1, 2, 3]
    assert all(e.organization_id == 42 for e in entities)
    assert len(client.list_calls) >= 2
    assert "organization_id" not in client.list_calls[0]
    assert client.list_calls[0]["page"] == 1
    client.list_all_service_cases.assert_awaited()
    call_kwargs = client.list_all_service_cases.await_args.kwargs
    assert "organization_id" not in call_kwargs
    assert call_kwargs["page_size"] == 100
    assert call_kwargs["max_pages"] == 100


@pytest.mark.asyncio
async def test_list_entities_skips_deleted_and_invalid_cases(sample_case):
    cases = [
        sample_case,
        {"id": 200, "status": "deleted", "customer_phone": "+910"},
        {"id": 201, "status": "open", "is_deleted": True, "customer_phone": "+910"},
        {"status": "open", "customer_phone": "+910"},  # missing id
        {"id": 202, "status": "cancelled", "customer_phone": "+910"},
    ]
    client = FakeClaimsClient(cases=cases)
    resolver = ClaimsReminderResolver(client=client)  # type: ignore[arg-type]

    entities = await resolver.list_entities(MagicMock(), organization_id=1)

    assert [e.entity_id for e in entities] == [123]


@pytest.mark.asyncio
async def test_list_entities_api_failure_propagates():
    client = FakeClaimsClient(list_error=ClaimsNetworkError("down"))
    resolver = ClaimsReminderResolver(client=client)  # type: ignore[arg-type]

    with pytest.raises(ClaimsNetworkError):
        await resolver.list_entities(MagicMock(), organization_id=1)


def test_snapshot_mapping_includes_optional_delivery_fields(sample_case):
    resolver = ClaimsReminderResolver()
    entity = resolver._to_snapshot(organization_id=9, case=sample_case)

    assert entity.entity_type == "claims"
    assert entity.entity_id == 123
    assert entity.organization_id == 9
    assert entity.recipient == "+919876543210"
    assert entity.recipient_email == "ada@example.com"
    assert entity.recipient_user_id == 55
    assert entity.metadata["customer_name"] == "Ada Lovelace"
    assert entity.metadata["recipient_email"] == "ada@example.com"
