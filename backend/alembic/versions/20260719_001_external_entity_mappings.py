"""Create external_entity_mappings for generic external → SIMI entity ids."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260719_001"
down_revision = "20260718_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS external_entity_mappings (
                id SERIAL PRIMARY KEY,
                organization_id INTEGER NOT NULL REFERENCES organizations(id),
                source_system VARCHAR(100) NOT NULL,
                entity_type VARCHAR(100) NOT NULL,
                external_entity_id VARCHAR(255) NOT NULL,
                internal_entity_id INTEGER NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                CONSTRAINT uq_external_entity_mappings_org_source_type_external
                    UNIQUE (
                        organization_id,
                        source_system,
                        entity_type,
                        external_entity_id
                    )
            )
            """
        )
    )
    # Unique constraint already indexes the external lookup columns; keep an
    # explicit named index for clarity and planner hints across environments.
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS ix_external_entity_mappings_external_lookup
            ON external_entity_mappings (
                organization_id,
                source_system,
                entity_type,
                external_entity_id
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS ix_external_entity_mappings_internal_lookup
            ON external_entity_mappings (
                organization_id,
                entity_type,
                internal_entity_id
            )
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(
        sa.text(
            "DROP INDEX IF EXISTS ix_external_entity_mappings_internal_lookup"
        )
    )
    op.execute(
        sa.text(
            "DROP INDEX IF EXISTS ix_external_entity_mappings_external_lookup"
        )
    )
    op.execute(sa.text("DROP TABLE IF EXISTS external_entity_mappings"))
