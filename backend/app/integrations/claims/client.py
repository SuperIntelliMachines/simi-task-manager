"""HTTP client for the external Gyantr AI Claims APIs.

This is the ONLY component that talks to Claims over the network.
SIMI must not create or store Service Case data — this client is read-only.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.integrations.claims.exceptions import (
    ClaimsAPIError,
    ClaimsAuthenticationError,
    ClaimsConfigurationError,
    ClaimsNetworkError,
    ClaimsNotFoundError,
    ClaimsTimeoutError,
)
from app.integrations.claims.models import (
    ClaimsAttentionItems,
    ClaimsMetadata,
    ClaimsServiceCase,
    ClaimsServiceCaseList,
    ClaimsStats,
)

logger = logging.getLogger(__name__)


class ClaimsClient:
    """Authenticate with Gyantr AI and call Claims read APIs."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        http_client: httpx.AsyncClient | None = None,
    ):
        self._settings = settings or get_settings()
        self._http_client = http_client
        self._owns_client = http_client is None
        self._access_token: str | None = None
        self._token_expires_at: float | None = None
        self._auth_lock = threading.Lock()

    @property
    def base_url(self) -> str:
        return (self._settings.claims_base_url or "").rstrip("/")

    @property
    def timeout(self) -> float:
        return float(self._settings.claims_timeout or 30.0)

    def _ensure_configured(self) -> None:
        if not self._settings.claims_configured:
            raise ClaimsConfigurationError(
                "Claims integration is not configured. "
                "Set CLAIMS_BASE_URL, CLAIMS_USERNAME (email), CLAIMS_PASSWORD, "
                "and CLAIMS_TENANT_SLUG (or CLAIMS_TENANT_ID)."
            )

    def _mask_email(self, email: str) -> str:
        value = (email or "").strip()
        if "@" not in value:
            return "***"
        local, _, domain = value.partition("@")
        if not local:
            return f"***@{domain}"
        return f"{local[0]}***@{domain}"

    def _auth_login_payload(self) -> dict[str, Any]:
        """Build Gyantr LoginRequest JSON body (from OpenAPI LoginRequest)."""
        payload: dict[str, Any] = {
            # CLAIMS_USERNAME holds the Gyantr account email.
            "email": self._settings.claims_username.strip(),
            "password": self._settings.claims_password,
            "remember_me": False,
        }
        tenant_slug = (self._settings.claims_tenant_slug or "").strip()
        tenant_id = (self._settings.claims_tenant_id or "").strip()
        if tenant_slug:
            payload["tenant_slug"] = tenant_slug
        if tenant_id:
            payload["tenant_id"] = tenant_id
        return payload

    def _resource_url(self, path: str) -> str:
        """Build ``{CLAIMS_BASE_URL}{CLAIMS_API_PREFIX}{path}``.

        Gyantr Service Cases: base ``.../api/v1`` + prefix ``/crm`` + ``/service-cases/{id}``.
        """
        prefix = (self._settings.claims_api_prefix or "").rstrip("/")
        normalized = path if path.startswith("/") else f"/{path}"
        return f"{self.base_url}{prefix}{normalized}"

    def _auth_url(self) -> str:
        auth_path = self._settings.claims_auth_path or "/auth/login"
        if not auth_path.startswith("/"):
            auth_path = f"/{auth_path}"
        # urljoin handles base without trailing slash poorly; build explicitly
        return f"{self.base_url}{auth_path}"

    def _token_is_valid(self) -> bool:
        if not self._access_token:
            return False
        if self._token_expires_at is None:
            return True
        # Refresh 60s before expiry
        return time.time() < (self._token_expires_at - 60)

    async def _get_http_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=self.timeout)
            self._owns_client = True
        return self._http_client

    async def aclose(self) -> None:
        if self._owns_client and self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    async def authenticate(self, *, force: bool = False) -> str:
        """Obtain a JWT access token via Gyantr ``POST /auth/login`` (JSON LoginRequest)."""
        self._ensure_configured()

        if not force and self._token_is_valid() and self._access_token:
            return self._access_token

        client = await self._get_http_client()
        url = self._auth_url()
        payload = self._auth_login_payload()
        content_type = "application/json"

        logger.info(
            "Claims auth request url=%s content_type=%s email=%s tenant_slug=%s tenant_id_set=%s",
            url,
            content_type,
            self._mask_email(str(payload.get("email") or "")),
            payload.get("tenant_slug") or "",
            bool(payload.get("tenant_id")),
        )

        try:
            response = await client.post(
                url,
                json=payload,
                headers={"Content-Type": content_type, "Accept": "application/json"},
            )
        except httpx.TimeoutException as exc:
            logger.error("Claims authentication timed out url=%s", url)
            raise ClaimsTimeoutError("Claims authentication timed out.") from exc
        except httpx.RequestError as exc:
            logger.error("Claims authentication network failure: %s url=%s", type(exc).__name__, url)
            raise ClaimsNetworkError("Unable to reach the Claims service for authentication.") from exc

        body_preview = (response.text or "").strip()[:500]
        if response.status_code >= 400:
            logger.error(
                "Claims authentication client error: %s url=%s body=%s",
                response.status_code,
                url,
                body_preview,
            )
        else:
            logger.info("Claims authentication response status=%s url=%s", response.status_code, url)

        if response.status_code in (401, 403):
            raise ClaimsAuthenticationError("Claims service rejected the configured credentials.")

        if response.status_code >= 500:
            raise ClaimsAPIError(
                "Claims service authentication is temporarily unavailable.",
                status_code=502,
            )

        if response.status_code >= 400:
            raise ClaimsAuthenticationError("Failed to authenticate with the Claims service.")

        try:
            raw_payload = response.json()
        except ValueError as exc:
            raise ClaimsAuthenticationError("Claims service returned an invalid auth response.") from exc

        try:
            parsed = ClaimsTokenResponse.model_validate(raw_payload)
            token = parsed.access_token
            expires_in = parsed.expires_in
        except Exception:
            token = raw_payload.get("access_token") or raw_payload.get("token") or raw_payload.get("jwt")
            expires_in = raw_payload.get("expires_in") if isinstance(raw_payload, dict) else None

        if not token or not isinstance(token, str):
            raise ClaimsAuthenticationError("Claims service did not return an access token.")

        with self._auth_lock:
            self._access_token = token
            if isinstance(expires_in, (int, float)) and expires_in > 0:
                self._token_expires_at = time.time() + float(expires_in)
            else:
                self._token_expires_at = None

        logger.info("Authenticated with Claims service successfully")
        return token

    async def _authorized_request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        retry_on_auth_failure: bool = True,
    ) -> Any:
        self._ensure_configured()
        token = await self.authenticate()
        client = await self._get_http_client()
        url = self._resource_url(path)
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

        try:
            response = await client.request(method, url, params=params, headers=headers)
        except httpx.TimeoutException as exc:
            logger.error("Claims request timed out: %s %s", method, path)
            raise ClaimsTimeoutError() from exc
        except httpx.RequestError as exc:
            logger.error("Claims network failure: %s %s (%s)", method, path, type(exc).__name__)
            raise ClaimsNetworkError() from exc

        if response.status_code == 401 and retry_on_auth_failure:
            logger.info("Claims token expired; re-authenticating...")
            await self.authenticate(force=True)
            return await self._authorized_request(
                method,
                path,
                params=params,
                retry_on_auth_failure=False,
            )

        if response.status_code == 404:
            raise ClaimsNotFoundError("Requested Claims resource was not found.")

        if response.status_code in (401, 403):
            raise ClaimsAuthenticationError("Claims service rejected the access token.")

        if response.status_code >= 500:
            logger.error("Claims service error %s for %s %s", response.status_code, method, path)
            raise ClaimsAPIError(
                "Claims service returned an internal error.",
                status_code=502,
            )

        if response.status_code >= 400:
            detail = _safe_error_detail(response)
            logger.error("Claims client error %s for %s %s: %s", response.status_code, method, path, detail)
            raise ClaimsAPIError(detail or "Claims service rejected the request.", status_code=502)

        if response.status_code == 204 or not response.content:
            return {}

        try:
            return response.json()
        except ValueError as exc:
            raise ClaimsAPIError("Claims service returned a non-JSON response.") from exc

    async def list_service_cases(self, **filters: Any) -> dict[str, Any]:
        """Fetch service cases from Gyantr AI (read-only)."""
        logger.info("Fetching service cases...")
        params = {key: value for key, value in filters.items() if value is not None}
        data = await self._authorized_request("GET", "/service-cases", params=params or None)
        if isinstance(data, list):
            return ClaimsServiceCaseList(items=data, total=len(data)).model_dump()
        if isinstance(data, dict):
            items = data.get("items")
            if items is None:
                items = data.get("results")
            if items is None:
                items = data.get("data")
            if isinstance(items, list) or items is not None:
                normalized = dict(data)
                normalized["items"] = items if isinstance(items, list) else [items]
                return ClaimsServiceCaseList.model_validate(normalized).model_dump()
            return data
        return {"raw": data}

    async def list_all_service_cases(
        self,
        *,
        page_size: int = 100,
        max_pages: int = 100,
        **filters: Any,
    ) -> list[dict[str, Any]]:
        """
        Fetch all Service Cases across pages.

        Contract (SIMI Claims proxy / client models):
        - Pagination uses ``page`` (1-based) and ``page_size``
        - Tenant scope comes from the Claims JWT (service account), not ``organization_id``
        - A page shorter than ``page_size``, empty items, or collected >= ``total`` ends the loop
        """
        if page_size <= 0:
            raise ValueError("page_size must be > 0")
        if max_pages <= 0:
            raise ValueError("max_pages must be > 0")

        # Never forward SIMI organization_id as a Claims query filter.
        filters.pop("organization_id", None)

        collected: list[dict[str, Any]] = []
        page = 1

        while page <= max_pages:
            params: dict[str, Any] = {
                **filters,
                "page": page,
                "page_size": page_size,
            }

            logger.info(
                "Fetching Claims service cases page=%s page_size=%s",
                page,
                page_size,
            )
            payload = await self.list_service_cases(**params)
            raw_items = payload.get("items") if isinstance(payload, dict) else None
            if not isinstance(raw_items, list):
                logger.warning(
                    "Claims list_service_cases returned no items list on page=%s; stopping pagination",
                    page,
                )
                break

            page_items = [item for item in raw_items if isinstance(item, dict)]
            collected.extend(page_items)

            total = payload.get("total") if isinstance(payload, dict) else None
            logger.debug(
                "Claims service cases page=%s fetched=%s total_so_far=%s reported_total=%s",
                page,
                len(page_items),
                len(collected),
                total,
            )

            if not page_items:
                break
            if len(page_items) < page_size:
                break
            if isinstance(total, int) and total >= 0 and len(collected) >= total:
                break

            page += 1
        else:
            logger.warning(
                "Claims list_all_service_cases stopped at max_pages=%s (collected=%s)",
                max_pages,
                len(collected),
            )

        return collected

    async def get_service_case(self, case_id: str | int) -> dict[str, Any]:
        """Fetch a single service case by id."""
        logger.info("Fetching service case %s...", case_id)
        data = await self._authorized_request("GET", f"/service-cases/{case_id}")
        if isinstance(data, dict):
            return ClaimsServiceCase.model_validate(data).model_dump()
        return {"raw": data}

    async def get_stats(self) -> dict[str, Any]:
        """Fetch Claims dashboard statistics."""
        logger.info("Fetching dashboard stats...")
        data = await self._authorized_request("GET", "/stats")
        if isinstance(data, dict):
            return ClaimsStats.model_validate(data).model_dump()
        return {"raw": data}

    async def get_attention_items(self) -> dict[str, Any]:
        """Fetch items requiring attention from Claims."""
        logger.info("Fetching attention items...")
        data = await self._authorized_request("GET", "/attention-items")
        if isinstance(data, list):
            return ClaimsAttentionItems(items=data).model_dump()
        if isinstance(data, dict):
            items = data.get("items")
            if items is None:
                items = data.get("results")
            if items is None:
                items = data.get("data")
            if isinstance(items, list) or items is not None:
                normalized = dict(data)
                normalized["items"] = items if isinstance(items, list) else [items]
                return ClaimsAttentionItems.model_validate(normalized).model_dump()
            return ClaimsAttentionItems.model_validate(data).model_dump()
        return {"raw": data}

    async def get_metadata(self) -> dict[str, Any]:
        """Fetch Claims metadata / lookup values."""
        logger.info("Fetching Claims metadata...")
        data = await self._authorized_request("GET", "/metadata")
        if isinstance(data, dict):
            return ClaimsMetadata.model_validate(data).model_dump()
        return {"raw": data}


def _safe_error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        text = (response.text or "").strip()
        return text[:300] if text else ""

    if isinstance(payload, dict):
        detail = payload.get("detail") or payload.get("message") or payload.get("error")
        if isinstance(detail, str):
            return detail[:300]
        if detail is not None:
            return str(detail)[:300]
    return ""
