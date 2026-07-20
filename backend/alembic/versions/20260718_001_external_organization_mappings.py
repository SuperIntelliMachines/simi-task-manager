"""Create external_organization_mappings for Claims tenant UUID → SIMI org."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260718_001"
down_revision = "20260716_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS external_organization_mappings (
                id BIGSERIAL PRIMARY KEY,
                organization_id BIGINT NOT NULL REFERENCES organizations(id),
                source_system VARCHAR(64) NOT NULL,
                external_id VARCHAR(128) NOT NULL,
                created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
                updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
                CONSTRAINT uq_external_organization_mappings_source_external
                    UNIQUE (source_system, external_id)
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS ix_external_organization_mappings_organization_id
            ON external_organization_mappings (organization_id)
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(sa.text("DROP TABLE IF EXISTS external_organization_mappings"))
