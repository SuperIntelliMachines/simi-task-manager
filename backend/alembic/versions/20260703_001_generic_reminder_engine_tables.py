"""Create generic reminder_configs and reminder_instances tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260703_001"
down_revision = "20260702_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS reminder_configs (
                id SERIAL PRIMARY KEY,
                organization_id INTEGER NOT NULL REFERENCES organizations(id),
                entity_type VARCHAR(50) NOT NULL,
                entity_id INTEGER NOT NULL,
                channel VARCHAR(50) NOT NULL,
                template_key VARCHAR(100) NOT NULL DEFAULT 'generic_reminder',
                offset_value INTEGER NOT NULL,
                offset_unit VARCHAR(20) NOT NULL DEFAULT 'days',
                dnd_start TIME NULL,
                dnd_end TIME NULL,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS ix_reminder_configs_org_entity
            ON reminder_configs (organization_id, entity_type, entity_id)
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS reminder_instances (
                id SERIAL PRIMARY KEY,
                config_id INTEGER NOT NULL REFERENCES reminder_configs(id) ON DELETE CASCADE,
                organization_id INTEGER NOT NULL REFERENCES organizations(id),
                entity_type VARCHAR(50) NOT NULL,
                entity_id INTEGER NOT NULL,
                scheduled_at TIMESTAMP NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
                sent_at TIMESTAMP NULL,
                attempt_count INTEGER NOT NULL DEFAULT 0,
                last_error TEXT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS ix_reminder_instances_due
            ON reminder_instances (organization_id, status, scheduled_at)
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_reminder_instances_config_scheduled
            ON reminder_instances (config_id, scheduled_at)
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(sa.text("DROP TABLE IF EXISTS reminder_instances"))
    op.execute(sa.text("DROP TABLE IF EXISTS reminder_configs"))
