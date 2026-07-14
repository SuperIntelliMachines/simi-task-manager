"""Add time_of_day and absolute_scheduled_at to reminder_configs."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260706_001"
down_revision = "20260704_001"
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
            ADD COLUMN IF NOT EXISTS time_of_day TIME NULL,
            ADD COLUMN IF NOT EXISTS absolute_scheduled_at TIMESTAMP NULL
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(sa.text("ALTER TABLE reminder_configs DROP COLUMN IF EXISTS absolute_scheduled_at"))
    op.execute(sa.text("ALTER TABLE reminder_configs DROP COLUMN IF EXISTS time_of_day"))
