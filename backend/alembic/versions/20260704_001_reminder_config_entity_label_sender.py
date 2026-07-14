"""Add entity_label and sender_name to reminder_configs."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260704_001"
down_revision = "20260703_001"
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
            ADD COLUMN IF NOT EXISTS entity_label VARCHAR(255) NULL,
            ADD COLUMN IF NOT EXISTS sender_name VARCHAR(255) NULL
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(sa.text("ALTER TABLE reminder_configs DROP COLUMN IF EXISTS sender_name"))
    op.execute(sa.text("ALTER TABLE reminder_configs DROP COLUMN IF EXISTS entity_label"))
