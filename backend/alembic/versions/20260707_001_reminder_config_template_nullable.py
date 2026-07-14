"""Make reminder_config.template_key nullable and non-defaulted."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260707_001"
down_revision = "20260706_001"
branch_labels = None
depends_on = None


def _ensure_reminder_table_ownership() -> None:
    """Transfer reminder tables to simi_user when migration runs as owner/superuser."""
    op.execute(
        sa.text(
            """
            DO $$
            DECLARE
              configs_owner text;
              can_transfer boolean;
            BEGIN
              IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'simi_user') THEN
                RETURN;
              END IF;

              SELECT tableowner
              INTO configs_owner
              FROM pg_tables
              WHERE schemaname = 'public' AND tablename = 'reminder_configs';

              IF configs_owner IS NULL OR configs_owner = 'simi_user' THEN
                RETURN;
              END IF;

              SELECT EXISTS (
                SELECT 1
                FROM pg_roles
                WHERE rolname = current_user
                  AND (rolsuper OR rolname = configs_owner)
              )
              INTO can_transfer;

              IF NOT can_transfer THEN
                RETURN;
              END IF;

              ALTER TABLE public.reminder_configs OWNER TO simi_user;
              ALTER TABLE public.reminder_instances OWNER TO simi_user;
              ALTER SEQUENCE public.reminder_configs_id_seq OWNER TO simi_user;
              ALTER SEQUENCE public.reminder_instances_id_seq OWNER TO simi_user;
            END $$;
            """
        )
    )


def _assert_can_alter_reminder_configs() -> None:
    current_user = op.get_bind().execute(sa.text("SELECT current_user")).scalar()
    table_owner = op.get_bind().execute(
        sa.text(
            """
            SELECT tableowner
            FROM pg_tables
            WHERE schemaname = 'public' AND tablename = 'reminder_configs'
            """
        )
    ).scalar()
    if table_owner and current_user != table_owner:
        raise RuntimeError(
            "Cannot alter public.reminder_configs: migration runs as "
            f"'{current_user}' but the table is owned by '{table_owner}'. "
            "Run backend/sql/transfer_reminder_table_ownership.sql in pgAdmin as "
            "postgres, or set DATABASE_ADMIN_URL to a superuser connection and "
            "rerun `alembic upgrade head`."
        )


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    _ensure_reminder_table_ownership()
    _assert_can_alter_reminder_configs()

    op.alter_column(
        "reminder_configs",
        "template_key",
        existing_type=sa.String(length=100),
        nullable=True,
        server_default=None,
        existing_nullable=False,
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    _assert_can_alter_reminder_configs()

    op.execute(
        sa.text(
            """
            UPDATE public.reminder_configs
            SET template_key = 'generic_reminder'
            WHERE template_key IS NULL
            """
        )
    )
    op.alter_column(
        "reminder_configs",
        "template_key",
        existing_type=sa.String(length=100),
        nullable=False,
        server_default="generic_reminder",
        existing_nullable=True,
    )
