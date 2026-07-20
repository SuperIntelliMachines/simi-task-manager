"""Resolve external tenant identifiers to SIMI organization_id."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.external_organization_mapping import ExternalOrganizationMapping

CLAIMS_SOURCE_SYSTEM = "claims"


class ExternalOrganizationMappingService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def resolve_organization_id(
        self,
        *,
        source_system: str,
        external_id: str,
    ) -> int | None:
        normalized_system = (source_system or "").strip().lower()
        normalized_external = (external_id or "").strip()
        if not normalized_system or not normalized_external:
            return None

        result = await self.session.execute(
            select(ExternalOrganizationMapping.organization_id).where(
                ExternalOrganizationMapping.source_system == normalized_system,
                ExternalOrganizationMapping.external_id == normalized_external,
            )
        )
        value = result.scalar_one_or_none()
        return int(value) if value is not None else None
