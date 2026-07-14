"""Tests for ClaimsIntegrationService error mapping."""

from __future__ import annotations

import httpx
import pytest
from fastapi import HTTPException

from app.core.config import Settings
from app.integrations.claims.client import ClaimsClient
from app.integrations.claims.service import ClaimsIntegrationService


def _settings() -> Settings:
    return Settings(
        claims_base_url="https://claims.test/api/v1",
        claims_username="claims-user@example.com",
        claims_password="claims-secret",
        claims_timeout=5.0,
        claims_auth_path="/auth/login",
        claims_api_prefix="/crm",
        claims_tenant_slug="sim",
    )


@pytest.mark.asyncio
async def test_service_maps_auth_failure_to_http_exception():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": "nope"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="https://claims.test") as http:
        service = ClaimsIntegrationService(client=ClaimsClient(settings=_settings(), http_client=http))
        with pytest.raises(HTTPException) as exc_info:
            await service.get_stats()
        assert exc_info.value.status_code == 502
        assert "authenticate" in str(exc_info.value.detail).lower() or "rejected" in str(exc_info.value.detail).lower()


@pytest.mark.asyncio
async def test_service_returns_stats_payload():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/auth/login":
            return httpx.Response(
                200,
                json={
                    "access_token": "t",
                    "refresh_token": "r",
                    "token_type": "bearer",
                    "expires_in": 1800,
                    "user": {"id": "u1"},
                },
            )
        assert request.url.path == "/api/v1/crm/stats"
        return httpx.Response(200, json={"open": 2})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="https://claims.test") as http:
        service = ClaimsIntegrationService(client=ClaimsClient(settings=_settings(), http_client=http))
        result = await service.get_stats()
        assert result["open"] == 2
