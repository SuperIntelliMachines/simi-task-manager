"""Create policy_custom_reminders table."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260614_001"
down_revision = "20260613_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS policy_custom_reminders (
                id BIGSERIAL PRIMARY KEY,
                policy_id BIGINT NOT NULL REFERENCES insurance_policies(id) ON DELETE CASCADE,
                reminder_unit VARCHAR(20) NOT NULL,
                reminder_value INTEGER NOT NULL,
                dnd_start_time TIME NULL,
                dnd_end_time TIME NULL,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS ix_policy_custom_reminders_policy_id
            ON policy_custom_reminders (policy_id)
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(sa.text("DROP TABLE IF EXISTS policy_custom_reminders"))
