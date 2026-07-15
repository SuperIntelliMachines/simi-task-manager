"""Create reminder_templates table for Reminder Management template CRUD."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260715_002"
down_revision = "20260715_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS reminder_templates (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                organization_id BIGINT NOT NULL REFERENCES organizations(id),
                created_by BIGINT NULL REFERENCES users(id),
                name VARCHAR(255) NOT NULL,
                channel VARCHAR(32) NOT NULL,
                subject VARCHAR(255) NULL,
                title VARCHAR(255) NULL,
                body TEXT NOT NULL,
                variables JSONB NOT NULL DEFAULT '[]'::jsonb,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                whatsapp_template_name VARCHAR(255) NULL,
                approval_status VARCHAR(32) NULL,
                meta_template_id VARCHAR(255) NULL,
                approved_at TIMESTAMP WITHOUT TIME ZONE NULL,
                rejection_reason TEXT NULL,
                created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
                CONSTRAINT ck_reminder_templates_channel
                    CHECK (channel IN ('email', 'in_app', 'sms', 'telegram', 'whatsapp')),
                CONSTRAINT ck_reminder_templates_approval_status
                    CHECK (
                        approval_status IS NULL OR approval_status IN
                        ('draft', 'pending_approval', 'approved', 'rejected')
                    )
            )
            """
        )
    )
    for index_sql in (
        "CREATE INDEX IF NOT EXISTS ix_reminder_templates_organization_id "
        "ON reminder_templates (organization_id)",
        "CREATE INDEX IF NOT EXISTS ix_reminder_templates_channel "
        "ON reminder_templates (channel)",
        "CREATE INDEX IF NOT EXISTS ix_reminder_templates_is_active "
        "ON reminder_templates (is_active)",
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
                  ON TABLE public.reminder_templates TO simi_user;
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
                REVOKE ALL ON TABLE public.reminder_templates FROM simi_user;
              END IF;
            EXCEPTION
              WHEN insufficient_privilege THEN NULL;
              WHEN undefined_object THEN NULL;
            END $$;
            """
        )
    )
    op.execute(sa.text("DROP TABLE IF EXISTS reminder_templates"))
