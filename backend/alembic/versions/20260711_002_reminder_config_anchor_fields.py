"""Add anchor_type, anchor_key, and offset_direction to reminder_configs."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260711_002"
down_revision = "20260711_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    # Defaults match ReminderConfig / ReminderAnchorType / ReminderOffsetDirection /
    # DEFAULT_REMINDER_ANCHOR_KEY and ReminderGeneratorService fallbacks.
    op.execute(
        sa.text(
            """
            ALTER TABLE reminder_configs
            ADD COLUMN IF NOT EXISTS anchor_type VARCHAR(20) NOT NULL DEFAULT 'date',
            ADD COLUMN IF NOT EXISTS anchor_key VARCHAR(100) NOT NULL DEFAULT 'anchor_date',
            ADD COLUMN IF NOT EXISTS offset_direction VARCHAR(20) NOT NULL DEFAULT 'before'
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(sa.text("ALTER TABLE reminder_configs DROP COLUMN IF EXISTS offset_direction"))
    op.execute(sa.text("ALTER TABLE reminder_configs DROP COLUMN IF EXISTS anchor_key"))
    op.execute(sa.text("ALTER TABLE reminder_configs DROP COLUMN IF EXISTS anchor_type"))
