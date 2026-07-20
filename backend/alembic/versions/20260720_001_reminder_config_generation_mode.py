"""Add generation_mode to reminder_configs for payload vs resolver scheduling."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260720_001"
down_revision = "20260719_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.add_column(
        "reminder_configs",
        sa.Column(
            "generation_mode",
            sa.String(length=20),
            nullable=False,
            server_default="resolver",
        ),
    )
    op.create_check_constraint(
        "ck_reminder_configs_generation_mode",
        "reminder_configs",
        "generation_mode IN ('payload', 'resolver')",
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.drop_constraint(
        "ck_reminder_configs_generation_mode",
        "reminder_configs",
        type_="check",
    )
    op.drop_column("reminder_configs", "generation_mode")
