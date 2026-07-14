"""Create reminder_definitions table for General Reminder Management."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260714_001"
down_revision = "20260711_002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.create_table(
        "reminder_definitions",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "organization_id",
            sa.BigInteger(),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("module_key", sa.String(length=50), nullable=False),
        sa.Column("reminder_name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "trigger_type",
            sa.String(length=20),
            nullable=False,
            server_default="date",
        ),
        sa.Column("trigger_key", sa.String(length=100), nullable=False),
        sa.Column("offset_value", sa.Integer(), nullable=False),
        sa.Column(
            "offset_unit",
            sa.String(length=20),
            nullable=False,
            server_default="days",
        ),
        sa.Column(
            "offset_direction",
            sa.String(length=20),
            nullable=False,
            server_default="before",
        ),
        sa.Column("recipient_type", sa.String(length=50), nullable=False),
        sa.Column(
            "recipient_value",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
        sa.Column(
            "channels",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
        sa.Column("template_key", sa.String(length=100), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("TRUE"),
        ),
        sa.Column(
            "created_by",
            sa.BigInteger(),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            "trigger_type IN ('date', 'workflow')",
            name="ck_reminder_definitions_trigger_type",
        ),
        sa.CheckConstraint(
            "offset_direction IN ('before', 'after')",
            name="ck_reminder_definitions_offset_direction",
        ),
    )
    op.create_index(
        "ix_reminder_definitions_organization_id",
        "reminder_definitions",
        ["organization_id"],
    )
    op.create_index(
        "ix_reminder_definitions_module_key",
        "reminder_definitions",
        ["module_key"],
    )
    op.create_index(
        "ix_reminder_definitions_trigger_type_key",
        "reminder_definitions",
        ["trigger_type", "trigger_key"],
    )
    op.create_index(
        "ix_reminder_definitions_is_active",
        "reminder_definitions",
        ["is_active"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.drop_index("ix_reminder_definitions_is_active", table_name="reminder_definitions")
    op.drop_index(
        "ix_reminder_definitions_trigger_type_key",
        table_name="reminder_definitions",
    )
    op.drop_index("ix_reminder_definitions_module_key", table_name="reminder_definitions")
    op.drop_index(
        "ix_reminder_definitions_organization_id",
        table_name="reminder_definitions",
    )
    op.drop_table("reminder_definitions")
