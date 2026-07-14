"""SIMI proxy APIs for the external Gyantr AI Claims module (read-only).

These endpoints do NOT persist Service Cases. All data is fetched live
from Claims via ClaimsClient / ClaimsIntegrationService.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from app.api.deps import PermissionChecker
from app.core.permissions import CLAIMS_VIEW
from app.integrations.claims.service import ClaimsIntegrationService, get_claims_integration_service

router = APIRouter(prefix="/integrations/claims", tags=["claims-integration"])


@router.get(
    "/service-cases",
    dependencies=[Depends(PermissionChecker(CLAIMS_VIEW))],
)
async def list_service_cases(
    status: str | None = Query(default=None),
    search: str | None = Query(default=None),
    page: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=200),
    service: ClaimsIntegrationService = Depends(get_claims_integration_service),
) -> dict[str, Any]:
    return await service.list_service_cases(
        status=status,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/service-cases/{case_id}",
    dependencies=[Depends(PermissionChecker(CLAIMS_VIEW))],
)
async def get_service_case(
    case_id: str,
    service: ClaimsIntegrationService = Depends(get_claims_integration_service),
) -> dict[str, Any]:
    return await service.get_service_case(case_id)


@router.get(
    "/stats",
    dependencies=[Depends(PermissionChecker(CLAIMS_VIEW))],
)
async def get_claims_stats(
    service: ClaimsIntegrationService = Depends(get_claims_integration_service),
) -> dict[str, Any]:
    return await service.get_stats()


@router.get(
    "/attention-items",
    dependencies=[Depends(PermissionChecker(CLAIMS_VIEW))],
)
async def get_attention_items(
    service: ClaimsIntegrationService = Depends(get_claims_integration_service),
) -> dict[str, Any]:
    return await service.get_attention_items()


@router.get(
    "/metadata",
    dependencies=[Depends(PermissionChecker(CLAIMS_VIEW))],
)
async def get_claims_metadata(
    service: ClaimsIntegrationService = Depends(get_claims_integration_service),
) -> dict[str, Any]:
    return await service.get_metadata()
