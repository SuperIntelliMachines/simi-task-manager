"""Generic external entity id → SIMI internal entity id mappings."""

from __future__ import annotations

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)

from app.core.database import Base


class ExternalEntityMapping(Base):
    """Maps an external system's entity id to a SIMI Reminder Engine entity_id.

    Generic across modules (Claims, CRM, Inventory, …). Lookups are scoped by
    organization_id + source_system + entity_type.
    """

    __tablename__ = "external_entity_mappings"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "source_system",
            "entity_type",
            "external_entity_id",
            name="uq_external_entity_mappings_org_source_type_external",
        ),
        Index(
            "ix_external_entity_mappings_external_lookup",
            "organization_id",
            "source_system",
            "entity_type",
            "external_entity_id",
        ),
        Index(
            "ix_external_entity_mappings_internal_lookup",
            "organization_id",
            "entity_type",
            "internal_entity_id",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id"),
        nullable=False,
    )
    source_system = Column(String(100), nullable=False)
    entity_type = Column(String(100), nullable=False)
    external_entity_id = Column(String(255), nullable=False)
    internal_entity_id = Column(Integer, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
