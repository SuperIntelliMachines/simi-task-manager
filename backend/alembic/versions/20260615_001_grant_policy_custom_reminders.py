"""Grant app role access to policy_custom_reminders."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260615_001"
down_revision = "20260614_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    # Table may have been created manually (e.g. pgAdmin) without grants for the app user.
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
              IF EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'policy_custom_reminders'
              ) THEN
                GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.policy_custom_reminders TO simi_user;
                GRANT USAGE, SELECT ON SEQUENCE public.policy_custom_reminders_id_seq TO simi_user;
              END IF;
            EXCEPTION
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
                REVOKE ALL ON TABLE public.policy_custom_reminders FROM simi_user;
                REVOKE ALL ON SEQUENCE public.policy_custom_reminders_id_seq FROM simi_user;
              END IF;
            EXCEPTION
              WHEN undefined_object THEN
                NULL;
            END $$;
            """
        )
    )
