"""Unit tests for ExternalEntityMappingService."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.models.core import Organization
from app.services.external_entity_mapping_service import (
    ExternalEntityMappingError,
    ExternalEntityMappingService,
)


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def seed_org(async_session) -> Organization:
    org = Organization(
        name=f"Entity Map Org {uuid4().hex[:8]}",
        created_at=utcnow_naive(),
        updated_at=utcnow_naive(),
    )
    async_session.add(org)
    await async_session.commit()
    return org


@pytest.mark.asyncio
async def test_create_mapping(async_session):
    org = await seed_org(async_session)
    service = ExternalEntityMappingService(async_session)

    created = await service.create_mapping(
        organization_id=org.id,
        source_system="Claims",
        entity_type="CLAIMS",
        external_entity_id=" CASE-12345 ",
        internal_entity_id=9001,
    )

    assert created.id is not None
    assert created.organization_id == org.id
    assert created.source_system == "claims"
    assert created.entity_type == "claims"
    assert created.external_entity_id == "CASE-12345"
    assert created.internal_entity_id == 9001
    assert created.created_at is not None
    assert created.updated_at is not None


@pytest.mark.asyncio
async def test_create_mapping_rejects_duplicate(async_session):
    org = await seed_org(async_session)
    service = ExternalEntityMappingService(async_session)

    await service.create_mapping(
        organization_id=org.id,
        source_system="crm",
        entity_type="account",
        external_entity_id="EXT-1",
        internal_entity_id=1,
    )

    with pytest.raises(ExternalEntityMappingError, match="already exists"):
        await service.create_mapping(
            organization_id=org.id,
            source_system="crm",
            entity_type="account",
            external_entity_id="EXT-1",
            internal_entity_id=2,
        )


@pytest.mark.asyncio
async def test_get_by_external_entity(async_session):
    org = await seed_org(async_session)
    service = ExternalEntityMappingService(async_session)

    await service.create_mapping(
        organization_id=org.id,
        source_system="inventory",
        entity_type="sku",
        external_entity_id="SKU-99",
        internal_entity_id=99,
    )

    found = await service.get_by_external_entity(
        organization_id=org.id,
        source_system="inventory",
        entity_type="sku",
        external_entity_id="SKU-99",
    )
    assert found is not None
    assert found.internal_entity_id == 99

    missing = await service.get_by_external_entity(
        organization_id=org.id,
        source_system="inventory",
        entity_type="sku",
        external_entity_id="SKU-missing",
    )
    assert missing is None


@pytest.mark.asyncio
async def test_get_by_internal_entity(async_session):
    org = await seed_org(async_session)
    service = ExternalEntityMappingService(async_session)

    await service.create_mapping(
        organization_id=org.id,
        source_system="crm",
        entity_type="lead",
        external_entity_id="LEAD-7",
        internal_entity_id=7007,
    )

    found = await service.get_by_internal_entity(
        organization_id=org.id,
        entity_type="lead",
        internal_entity_id=7007,
    )
    assert found is not None
    assert found.external_entity_id == "LEAD-7"

    missing = await service.get_by_internal_entity(
        organization_id=org.id,
        entity_type="lead",
        internal_entity_id=1,
    )
    assert missing is None


@pytest.mark.asyncio
async def test_upsert_mapping_create_path(async_session):
    org = await seed_org(async_session)
    service = ExternalEntityMappingService(async_session)

    created = await service.upsert_mapping(
        organization_id=org.id,
        source_system="claims",
        entity_type="claims",
        external_entity_id="CASE-NEW",
        internal_entity_id=42,
    )

    assert created.internal_entity_id == 42
    loaded = await service.get_by_external_entity(
        organization_id=org.id,
        source_system="claims",
        entity_type="claims",
        external_entity_id="CASE-NEW",
    )
    assert loaded is not None
    assert loaded.id == created.id


@pytest.mark.asyncio
async def test_upsert_mapping_update_path(async_session):
    org = await seed_org(async_session)
    service = ExternalEntityMappingService(async_session)

    original = await service.create_mapping(
        organization_id=org.id,
        source_system="claims",
        entity_type="claims",
        external_entity_id="CASE-UPD",
        internal_entity_id=10,
    )
    original_updated_at = original.updated_at

    updated = await service.upsert_mapping(
        organization_id=org.id,
        source_system="claims",
        entity_type="claims",
        external_entity_id="CASE-UPD",
        internal_entity_id=20,
    )

    assert updated.id == original.id
    assert updated.internal_entity_id == 20
    assert updated.updated_at >= original_updated_at

    unchanged = await service.upsert_mapping(
        organization_id=org.id,
        source_system="claims",
        entity_type="claims",
        external_entity_id="CASE-UPD",
        internal_entity_id=20,
    )
    assert unchanged.internal_entity_id == 20
    assert unchanged.id == original.id


@pytest.mark.asyncio
async def test_delete_mapping(async_session):
    org = await seed_org(async_session)
    service = ExternalEntityMappingService(async_session)

    created = await service.create_mapping(
        organization_id=org.id,
        source_system="crm",
        entity_type="contact",
        external_entity_id="C-1",
        internal_entity_id=5,
    )

    assert await service.delete_mapping(created.id) is True
    assert (
        await service.get_by_external_entity(
            organization_id=org.id,
            source_system="crm",
            entity_type="contact",
            external_entity_id="C-1",
        )
        is None
    )
    assert await service.delete_mapping(created.id) is False


@pytest.mark.asyncio
async def test_create_mapping_rejects_empty_fields(async_session):
    org = await seed_org(async_session)
    service = ExternalEntityMappingService(async_session)

    with pytest.raises(ExternalEntityMappingError, match="source_system"):
        await service.create_mapping(
            organization_id=org.id,
            source_system="  ",
            entity_type="claims",
            external_entity_id="X",
            internal_entity_id=1,
        )
