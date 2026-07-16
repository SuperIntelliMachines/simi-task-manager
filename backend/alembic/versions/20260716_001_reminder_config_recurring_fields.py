"""Add recurring reminder and stop-condition fields to reminder_configs and reminder_definitions."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260716_001"
down_revision = "20260715_003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(
        sa.text(
            """
            ALTER TABLE reminder_configs
            ADD COLUMN IF NOT EXISTS repeat_enabled BOOLEAN NOT NULL DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS repeat_frequency_value INTEGER NULL,
            ADD COLUMN IF NOT EXISTS repeat_frequency_unit VARCHAR(20) NULL,
            ADD COLUMN IF NOT EXISTS max_attempts INTEGER NULL,
            ADD COLUMN IF NOT EXISTS stop_condition VARCHAR(50) NOT NULL DEFAULT 'entity_ineligible',
            ADD COLUMN IF NOT EXISTS stop_condition_config JSONB NULL
            """
        )
    )

    op.execute(
        sa.text(
            """
            ALTER TABLE reminder_definitions
            ADD COLUMN IF NOT EXISTS repeat_enabled BOOLEAN NOT NULL DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS repeat_frequency_value INTEGER NULL,
            ADD COLUMN IF NOT EXISTS repeat_frequency_unit VARCHAR(20) NULL,
            ADD COLUMN IF NOT EXISTS max_attempts INTEGER NULL,
            ADD COLUMN IF NOT EXISTS stop_condition VARCHAR(50) NOT NULL DEFAULT 'entity_ineligible',
            ADD COLUMN IF NOT EXISTS stop_condition_config JSONB NULL
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    for table in ("reminder_configs", "reminder_definitions"):
        op.execute(sa.text(f"ALTER TABLE {table} DROP COLUMN IF EXISTS stop_condition_config"))
        op.execute(sa.text(f"ALTER TABLE {table} DROP COLUMN IF EXISTS stop_condition"))
        op.execute(sa.text(f"ALTER TABLE {table} DROP COLUMN IF EXISTS max_attempts"))
        op.execute(sa.text(f"ALTER TABLE {table} DROP COLUMN IF EXISTS repeat_frequency_unit"))
        op.execute(sa.text(f"ALTER TABLE {table} DROP COLUMN IF EXISTS repeat_frequency_value"))
        op.execute(sa.text(f"ALTER TABLE {table} DROP COLUMN IF EXISTS repeat_enabled"))
