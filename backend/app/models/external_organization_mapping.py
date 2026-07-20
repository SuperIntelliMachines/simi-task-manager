"""Maps external system tenant IDs (e.g. Claims UUID) to SIMI organization.id."""

from __future__ import annotations

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint

from app.core.database import Base


class ExternalOrganizationMapping(Base):
    __tablename__ = "external_organization_mappings"
    __table_args__ = (
        UniqueConstraint(
            "source_system",
            "external_id",
            name="uq_external_organization_mappings_source_external",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(
        BigInteger, ForeignKey("organizations.id"), nullable=False, index=True
    )
    # e.g. "claims"
    source_system = Column(String(64), nullable=False)
    # External tenant identifier (UUID string for Claims)
    external_id = Column(String(128), nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
