"""Generic external entity id ↔ SIMI internal entity id mappings."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.external_entity_mapping import ExternalEntityMapping


class ExternalEntityMappingError(ValueError):
    """Raised when an external entity mapping cannot be created or updated."""


def _utcnow() -> datetime:
    return datetime.now(UTC)


class ExternalEntityMappingService:
    """Manage reusable mappings between external systems and SIMI entity ids."""

    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _normalize_source_system(source_system: str) -> str:
        normalized = (source_system or "").strip().lower()
        if not normalized:
            raise ExternalEntityMappingError("source_system must not be empty")
        return normalized

    @staticmethod
    def _normalize_entity_type(entity_type: str) -> str:
        normalized = (entity_type or "").strip().lower()
        if not normalized:
            raise ExternalEntityMappingError("entity_type must not be empty")
        return normalized

    @staticmethod
    def _normalize_external_entity_id(external_entity_id: str) -> str:
        normalized = (external_entity_id or "").strip()
        if not normalized:
            raise ExternalEntityMappingError("external_entity_id must not be empty")
        return normalized

    @staticmethod
    def _coerce_positive_ids(
        *,
        organization_id: int,
        internal_entity_id: int,
    ) -> tuple[int, int]:
        try:
            org_id = int(organization_id)
            internal_id = int(internal_entity_id)
        except (TypeError, ValueError) as exc:
            raise ExternalEntityMappingError(
                "organization_id and internal_entity_id must be integers"
            ) from exc
        if org_id <= 0:
            raise ExternalEntityMappingError("organization_id must be a positive integer")
        if internal_id < 0:
            raise ExternalEntityMappingError("internal_entity_id must be >= 0")
        return org_id, internal_id

    async def create_mapping(
        self,
        *,
        organization_id: int,
        source_system: str,
        entity_type: str,
        external_entity_id: str,
        internal_entity_id: int,
    ) -> ExternalEntityMapping:
        org_id, internal_id = self._coerce_positive_ids(
            organization_id=organization_id,
            internal_entity_id=internal_entity_id,
        )
        source = self._normalize_source_system(source_system)
        etype = self._normalize_entity_type(entity_type)
        external_id = self._normalize_external_entity_id(external_entity_id)

        existing = await self.get_by_external_entity(
            organization_id=org_id,
            source_system=source,
            entity_type=etype,
            external_entity_id=external_id,
        )
        if existing is not None:
            raise ExternalEntityMappingError(
                "mapping already exists for "
                f"organization_id={org_id} source_system={source!r} "
                f"entity_type={etype!r} external_entity_id={external_id!r}"
            )

        now = _utcnow()
        row = ExternalEntityMapping(
            organization_id=org_id,
            source_system=source,
            entity_type=etype,
            external_entity_id=external_id,
            internal_entity_id=internal_id,
            created_at=now,
            updated_at=now,
        )
        self.session.add(row)
        try:
            await self.session.commit()
            await self.session.refresh(row)
        except IntegrityError as exc:
            await self.session.rollback()
            raise ExternalEntityMappingError(
                "mapping already exists for the given external entity key"
            ) from exc
        return row

    async def get_by_external_entity(
        self,
        *,
        organization_id: int,
        source_system: str,
        entity_type: str,
        external_entity_id: str,
    ) -> ExternalEntityMapping | None:
        org_id = int(organization_id)
        source = self._normalize_source_system(source_system)
        etype = self._normalize_entity_type(entity_type)
        external_id = self._normalize_external_entity_id(external_entity_id)

        result = await self.session.execute(
            select(ExternalEntityMapping).where(
                ExternalEntityMapping.organization_id == org_id,
                ExternalEntityMapping.source_system == source,
                ExternalEntityMapping.entity_type == etype,
                ExternalEntityMapping.external_entity_id == external_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_internal_entity(
        self,
        *,
        organization_id: int,
        entity_type: str,
        internal_entity_id: int,
    ) -> ExternalEntityMapping | None:
        org_id = int(organization_id)
        etype = self._normalize_entity_type(entity_type)
        internal_id = int(internal_entity_id)

        result = await self.session.execute(
            select(ExternalEntityMapping)
            .where(
                ExternalEntityMapping.organization_id == org_id,
                ExternalEntityMapping.entity_type == etype,
                ExternalEntityMapping.internal_entity_id == internal_id,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def upsert_mapping(
        self,
        *,
        organization_id: int,
        source_system: str,
        entity_type: str,
        external_entity_id: str,
        internal_entity_id: int,
    ) -> ExternalEntityMapping:
        org_id, internal_id = self._coerce_positive_ids(
            organization_id=organization_id,
            internal_entity_id=internal_entity_id,
        )
        source = self._normalize_source_system(source_system)
        etype = self._normalize_entity_type(entity_type)
        external_id = self._normalize_external_entity_id(external_entity_id)

        existing = await self.get_by_external_entity(
            organization_id=org_id,
            source_system=source,
            entity_type=etype,
            external_entity_id=external_id,
        )
        if existing is None:
            return await self.create_mapping(
                organization_id=org_id,
                source_system=source,
                entity_type=etype,
                external_entity_id=external_id,
                internal_entity_id=internal_id,
            )

        if int(existing.internal_entity_id) != internal_id:
            existing.internal_entity_id = internal_id
            existing.updated_at = _utcnow()
            await self.session.commit()
            await self.session.refresh(existing)
        return existing

    async def delete_mapping(self, mapping_id: int) -> bool:
        row = await self.session.get(ExternalEntityMapping, int(mapping_id))
        if row is None:
            return False
        await self.session.delete(row)
        await self.session.commit()
        return True
