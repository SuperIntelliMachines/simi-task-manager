"""Add stage metadata columns to policy_reminders."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260629_001"
down_revision = "20260616_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            ALTER TABLE policy_reminders
            ADD COLUMN IF NOT EXISTS stage_direction VARCHAR(20),
            ADD COLUMN IF NOT EXISTS stage_unit VARCHAR(20),
            ADD COLUMN IF NOT EXISTS stage_value INTEGER
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("ALTER TABLE policy_reminders DROP COLUMN IF EXISTS stage_value"))
    op.execute(sa.text("ALTER TABLE policy_reminders DROP COLUMN IF EXISTS stage_unit"))
    op.execute(sa.text("ALTER TABLE policy_reminders DROP COLUMN IF EXISTS stage_direction"))
