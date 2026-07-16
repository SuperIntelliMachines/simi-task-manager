"""Create reminder_history table for Reminder Management execution logs."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260715_003"
down_revision = "20260715_002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS reminder_history (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                organization_id BIGINT NOT NULL REFERENCES organizations(id),
                reminder_id UUID NULL REFERENCES personal_reminders(id),
                template_id UUID NULL REFERENCES reminder_templates(id),
                created_by BIGINT NOT NULL REFERENCES users(id),
                reminder_title VARCHAR(255) NOT NULL,
                channel VARCHAR(32) NOT NULL,
                recipient VARCHAR(255) NOT NULL,
                status VARCHAR(20) NOT NULL,
                provider_message_id VARCHAR(255) NULL,
                error_message TEXT NULL,
                executed_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
                created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
                CONSTRAINT ck_reminder_history_status
                    CHECK (status IN ('SENT', 'FAILED', 'SKIPPED'))
            )
            """
        )
    )
    for index_sql in (
        "CREATE INDEX IF NOT EXISTS ix_reminder_history_organization_id "
        "ON reminder_history (organization_id)",
        "CREATE INDEX IF NOT EXISTS ix_reminder_history_reminder_id "
        "ON reminder_history (reminder_id)",
        "CREATE INDEX IF NOT EXISTS ix_reminder_history_status "
        "ON reminder_history (status)",
        "CREATE INDEX IF NOT EXISTS ix_reminder_history_channel "
        "ON reminder_history (channel)",
        "CREATE INDEX IF NOT EXISTS ix_reminder_history_executed_at "
        "ON reminder_history (executed_at)",
    ):
        op.execute(
            sa.text(
                f"""
                DO $$
                BEGIN
                  EXECUTE '{index_sql}';
                EXCEPTION
                  WHEN insufficient_privilege THEN NULL;
                  WHEN duplicate_table THEN NULL;
                END $$;
                """
            )
        )

    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
              IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'simi_user') THEN
                GRANT SELECT, INSERT, UPDATE, DELETE
                  ON TABLE public.reminder_history TO simi_user;
              END IF;
            EXCEPTION
              WHEN insufficient_privilege THEN NULL;
              WHEN undefined_object THEN NULL;
            END $$;
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
              IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'simi_user') THEN
                REVOKE ALL ON TABLE public.reminder_history FROM simi_user;
              END IF;
            EXCEPTION
              WHEN insufficient_privilege THEN NULL;
              WHEN undefined_object THEN NULL;
            END $$;
            """
        )
    )
    op.execute(sa.text("DROP TABLE IF EXISTS reminder_history"))
