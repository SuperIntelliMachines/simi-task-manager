"""Unit tests for the Gyantr AI ClaimsClient (Phase 1 — read-only)."""

from __future__ import annotations

import json

import httpx
import pytest

from app.core.config import Settings
from app.integrations.claims.client import ClaimsClient
from app.integrations.claims.exceptions import (
    ClaimsAuthenticationError,
    ClaimsNotFoundError,
    ClaimsTimeoutError,
)


def _settings(**overrides) -> Settings:
    # Matches working Gyantr layout:
    #   auth: POST {CLAIMS_BASE_URL}/auth/login (JSON email/password/tenant_slug)
    #   resource: {CLAIMS_BASE_URL}{CLAIMS_API_PREFIX}/service-cases/{id}
    base = {
        "claims_base_url": "https://claims.test/api/v1",
        "claims_username": "claims-user@example.com",
        "claims_password": "claims-secret",
        "claims_timeout": 5.0,
        "claims_auth_path": "/auth/login",
        "claims_api_prefix": "/crm",
        "claims_tenant_slug": "sim",
    }
    base.update(overrides)
    return Settings(**base)


def _auth_ok(request: httpx.Request) -> httpx.Response:
    assert request.url.path == "/api/v1/auth/login"
    assert request.headers.get("content-type", "").startswith("application/json")
    body = json.loads(request.content.decode())
    assert body["email"] == "claims-user@example.com"
    assert body["password"] == "claims-secret"
    assert body["tenant_slug"] == "sim"
    assert "username" not in body
    return httpx.Response(
        200,
        json={
            "access_token": "jwt-token-1",
            "refresh_token": "refresh-1",
            "token_type": "bearer",
            "expires_in": 3600,
            "user": {"id": "u1", "email": "claims-user@example.com"},
        },
    )


def test_resource_url_matches_gyantr_crm_service_case_path():
    """Final GET must be .../api/v1/crm/service-cases/{id} (no duplicate /api/v1, includes /crm)."""
    client = ClaimsClient(
        settings=_settings(claims_base_url="http://192.168.0.68:8000/api/v1", claims_api_prefix="/crm")
    )
    case_id = "f2880ade-fe51-4411-bb03-85578b3a2d3f"
    assert client._resource_url(f"/service-cases/{case_id}") == (
        f"http://192.168.0.68:8000/api/v1/crm/service-cases/{case_id}"
    )
    assert client._auth_url() == "http://192.168.0.68:8000/api/v1/auth/login"
    # Regression: previous misconfig (base .../api/v1 + prefix /api/v1) doubled the prefix.
    broken = ClaimsClient(
        settings=_settings(claims_base_url="http://192.168.0.68:8000/api/v1", claims_api_prefix="/api/v1")
    )
    assert "/api/v1/api/v1/" in broken._resource_url(f"/service-cases/{case_id}")


@pytest.mark.asyncio
async def test_authenticate_success():
    def handler(request: httpx.Request) -> httpx.Response:
        return _auth_ok(request)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="https://claims.test") as http:
        client = ClaimsClient(settings=_settings(), http_client=http)
        token = await client.authenticate()
        assert token == "jwt-token-1"
        assert client._access_token == "jwt-token-1"


@pytest.mark.asyncio
async def test_authenticate_failure():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": "Invalid credentials"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="https://claims.test") as http:
        client = ClaimsClient(settings=_settings(), http_client=http)
        with pytest.raises(ClaimsAuthenticationError):
            await client.authenticate()


@pytest.mark.asyncio
async def test_list_service_cases():
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(f"{request.method} {request.url.path}")
        if request.url.path == "/api/v1/auth/login":
            return _auth_ok(request)
        assert request.headers.get("Authorization") == "Bearer jwt-token-1"
        assert request.url.path == "/api/v1/crm/service-cases"
        assert request.url.params.get("status") == "open"
        return httpx.Response(
            200,
            json={"items": [{"id": 1, "status": "open", "title": "Case A"}], "total": 1},
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="https://claims.test") as http:
        client = ClaimsClient(settings=_settings(), http_client=http)
        result = await client.list_service_cases(status="open")
        assert result["total"] == 1
        assert result["items"][0]["title"] == "Case A"
        assert any(c.startswith("POST /api/v1/auth/login") for c in calls)
        assert any(c.startswith("GET /api/v1/crm/service-cases") for c in calls)


@pytest.mark.asyncio
async def test_list_all_service_cases_paginates():
    pages_seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/auth/login":
            return _auth_ok(request)
        assert request.url.path == "/api/v1/crm/service-cases"
        page = request.url.params.get("page")
        pages_seen.append(str(page))
        assert "organization_id" not in request.url.params
        assert request.url.params.get("page_size") == "2"
        if page == "1":
            return httpx.Response(
                200,
                json={
                    "items": [{"id": 1, "status": "open"}, {"id": 2, "status": "open"}],
                    "total": 3,
                    "page": 1,
                    "page_size": 2,
                },
            )
        return httpx.Response(
            200,
            json={
                "items": [{"id": 3, "status": "open"}],
                "total": 3,
                "page": 2,
                "page_size": 2,
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="https://claims.test") as http:
        client = ClaimsClient(settings=_settings(), http_client=http)
        items = await client.list_all_service_cases(page_size=2)
        assert [item["id"] for item in items] == [1, 2, 3]
        assert pages_seen == ["1", "2"]


@pytest.mark.asyncio
async def test_list_all_service_cases_strips_organization_id_from_filters():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/auth/login":
            return _auth_ok(request)
        assert request.url.path == "/api/v1/crm/service-cases"
        assert "organization_id" not in request.url.params
        assert request.url.params.get("status") == "open"
        assert request.url.params.get("page") == "1"
        assert request.url.params.get("page_size") == "10"
        return httpx.Response(
            200,
            json={"items": [{"id": 1, "status": "open"}], "total": 1, "page": 1, "page_size": 10},
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="https://claims.test") as http:
        client = ClaimsClient(settings=_settings(), http_client=http)
        items = await client.list_all_service_cases(
            page_size=10,
            organization_id=607,  # must not be forwarded to Claims
            status="open",
        )
        assert [item["id"] for item in items] == [1]


@pytest.mark.asyncio
async def test_get_service_case():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/auth/login":
            return _auth_ok(request)
        assert request.url.path == "/api/v1/crm/service-cases/123"
        assert request.headers.get("Authorization") == "Bearer jwt-token-1"
        return httpx.Response(200, json={"id": 123, "status": "open", "title": "Case 123"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="https://claims.test") as http:
        client = ClaimsClient(settings=_settings(), http_client=http)
        result = await client.get_service_case(123)
        assert result["id"] == 123
        assert result["title"] == "Case 123"


@pytest.mark.asyncio
async def test_get_stats():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/auth/login":
            return _auth_ok(request)
        assert request.url.path == "/api/v1/crm/stats"
        return httpx.Response(200, json={"open": 12, "closed": 4, "attention": 3})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="https://claims.test") as http:
        client = ClaimsClient(settings=_settings(), http_client=http)
        result = await client.get_stats()
        assert result["open"] == 12
        assert result["attention"] == 3


@pytest.mark.asyncio
async def test_get_attention_items():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/auth/login":
            return _auth_ok(request)
        assert request.url.path == "/api/v1/crm/attention-items"
        return httpx.Response(200, json={"items": [{"id": 9, "reason": "SLA breach"}]})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="https://claims.test") as http:
        client = ClaimsClient(settings=_settings(), http_client=http)
        result = await client.get_attention_items()
        assert result["items"][0]["reason"] == "SLA breach"


@pytest.mark.asyncio
async def test_get_metadata():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/auth/login":
            return _auth_ok(request)
        assert request.url.path == "/api/v1/crm/metadata"
        return httpx.Response(200, json={"statuses": ["open", "closed"], "priorities": ["high"]})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="https://claims.test") as http:
        client = ClaimsClient(settings=_settings(), http_client=http)
        result = await client.get_metadata()
        assert "open" in result["statuses"]


@pytest.mark.asyncio
async def test_get_service_case_not_found():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/auth/login":
            return _auth_ok(request)
        return httpx.Response(404, json={"detail": "Not found"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="https://claims.test") as http:
        client = ClaimsClient(settings=_settings(), http_client=http)
        with pytest.raises(ClaimsNotFoundError):
            await client.get_service_case("missing")


@pytest.mark.asyncio
async def test_network_timeout_on_list():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/auth/login":
            return _auth_ok(request)
        raise httpx.TimeoutException("timed out", request=request)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="https://claims.test") as http:
        client = ClaimsClient(settings=_settings(), http_client=http)
        with pytest.raises(ClaimsTimeoutError):
            await client.list_service_cases()


@pytest.mark.asyncio
async def test_reauthenticates_on_expired_token():
    tokens_issued = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/auth/login":
            tokens_issued["count"] += 1
            return httpx.Response(
                200,
                json={"access_token": f"jwt-{tokens_issued['count']}", "token_type": "bearer"},
            )
        auth = request.headers.get("Authorization")
        if auth == "Bearer jwt-1":
            return httpx.Response(401, json={"detail": "expired"})
        assert auth == "Bearer jwt-2"
        return httpx.Response(200, json={"open": 1})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="https://claims.test") as http:
        client = ClaimsClient(settings=_settings(), http_client=http)
        result = await client.get_stats()
        assert result["open"] == 1
        assert tokens_issued["count"] == 2
