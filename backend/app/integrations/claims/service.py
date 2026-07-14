"""Business-facing Claims integration service.

Controllers call this service — never ClaimsClient HTTP details directly.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException

from app.integrations.claims.client import ClaimsClient
from app.integrations.claims.exceptions import ClaimsIntegrationError

logger = logging.getLogger(__name__)


class ClaimsIntegrationService:
    """Proxy read-only Claims operations for SIMI APIs."""

    def __init__(self, client: ClaimsClient | None = None):
        self._client = client or ClaimsClient()

    @property
    def client(self) -> ClaimsClient:
        return self._client

    async def authenticate(self) -> dict[str, str]:
        try:
            token = await self._client.authenticate(force=True)
        except ClaimsIntegrationError as exc:
            raise _to_http_exception(exc) from exc
        # Never return the raw token to API consumers — only confirm success.
        return {"status": "authenticated", "token_type": "bearer", "has_token": bool(token)}

    async def list_service_cases(self, **filters: Any) -> dict[str, Any]:
        try:
            return await self._client.list_service_cases(**filters)
        except ClaimsIntegrationError as exc:
            raise _to_http_exception(exc) from exc

    async def get_service_case(self, case_id: str | int) -> dict[str, Any]:
        try:
            return await self._client.get_service_case(case_id)
        except ClaimsIntegrationError as exc:
            raise _to_http_exception(exc) from exc

    async def get_stats(self) -> dict[str, Any]:
        try:
            return await self._client.get_stats()
        except ClaimsIntegrationError as exc:
            raise _to_http_exception(exc) from exc

    async def get_attention_items(self) -> dict[str, Any]:
        try:
            return await self._client.get_attention_items()
        except ClaimsIntegrationError as exc:
            raise _to_http_exception(exc) from exc

    async def get_metadata(self) -> dict[str, Any]:
        try:
            return await self._client.get_metadata()
        except ClaimsIntegrationError as exc:
            raise _to_http_exception(exc) from exc


def _to_http_exception(exc: ClaimsIntegrationError) -> HTTPException:
    status_code = exc.status_code or 502
    # Do not leak stack traces or secrets — message is already sanitized.
    return HTTPException(status_code=status_code, detail=exc.message)


def get_claims_integration_service() -> ClaimsIntegrationService:
    return ClaimsIntegrationService()
