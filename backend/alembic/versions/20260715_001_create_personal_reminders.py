"""Ensure personal_reminders exists and grant app-role access.

The table may already exist (created outside Alembic by a superuser). This
revision is idempotent and tolerates running as a non-owner app role.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260715_001"
down_revision = "20260714_002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    # Create table / indexes only when the connecting role has privileges.
    # If the table already exists and is owned by another role, these no-op.
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
              CREATE TABLE IF NOT EXISTS personal_reminders (
                  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                  organization_id BIGINT NOT NULL REFERENCES organizations(id),
                  created_by BIGINT NOT NULL REFERENCES users(id),
                  title VARCHAR(255) NOT NULL,
                  description TEXT NULL,
                  scheduled_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
                  channels JSONB NOT NULL DEFAULT '[]'::jsonb,
                  email VARCHAR(255) NULL,
                  mobile_number VARCHAR(20) NULL,
                  whatsapp_number VARCHAR(20) NULL,
                  telegram_chat_id VARCHAR(100) NULL,
                  template_id UUID NULL,
                  custom_message TEXT NULL,
                  status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
                  sent_at TIMESTAMP WITHOUT TIME ZONE NULL,
                  is_active BOOLEAN NOT NULL DEFAULT TRUE,
                  created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
                  updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
                  CONSTRAINT personal_reminders_status_check
                      CHECK (status IN ('PENDING', 'SENT', 'FAILED', 'CANCELLED'))
              );
            EXCEPTION
              WHEN insufficient_privilege THEN
                NULL;
              WHEN duplicate_table THEN
                NULL;
            END $$;
            """
        )
    )

    for index_sql in (
        "CREATE INDEX IF NOT EXISTS idx_personal_reminders_org ON personal_reminders (organization_id)",
        "CREATE INDEX IF NOT EXISTS idx_personal_reminders_created_by ON personal_reminders (created_by)",
        "CREATE INDEX IF NOT EXISTS idx_personal_reminders_scheduled_at ON personal_reminders (scheduled_at)",
        "CREATE INDEX IF NOT EXISTS idx_personal_reminders_status ON personal_reminders (status)",
    ):
        op.execute(
            sa.text(
                f"""
                DO $$
                BEGIN
                  EXECUTE '{index_sql}';
                EXCEPTION
                  WHEN insufficient_privilege THEN
                    NULL;
                  WHEN duplicate_table THEN
                    NULL;
                END $$;
                """
            )
        )

    # Prefer owner/admin to grant app role access when the table was created externally.
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
              IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'simi_user')
                 AND EXISTS (
                   SELECT 1 FROM information_schema.tables
                   WHERE table_schema = 'public' AND table_name = 'personal_reminders'
                 )
              THEN
                GRANT SELECT, INSERT, UPDATE, DELETE
                  ON TABLE public.personal_reminders TO simi_user;
              END IF;
            EXCEPTION
              WHEN insufficient_privilege THEN
                NULL;
              WHEN undefined_object THEN
                NULL;
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
                REVOKE ALL ON TABLE public.personal_reminders FROM simi_user;
              END IF;
            EXCEPTION
              WHEN insufficient_privilege THEN
                NULL;
              WHEN undefined_object THEN
                NULL;
            END $$;
            """
        )
    )
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
              DROP TABLE IF EXISTS personal_reminders;
            EXCEPTION
              WHEN insufficient_privilege THEN
                NULL;
            END $$;
            """
        )
    )
