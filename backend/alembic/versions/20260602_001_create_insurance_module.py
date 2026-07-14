"""
Create insurance module tables and enums

Revision ID: 20260602_001
Revises: 20260531_001
Create Date: 2026-06-02
"""

from alembic import op
import sqlalchemy as sa

# This migration reuses existing legacy tables: insurance_policies, insurance_leads

# revision identifiers, used by Alembic.
revision = "20260602_001"
down_revision = "20260531_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Create `policy_reminders` referencing existing `insurance_policies`
    conn.execute(
        sa.text(
            """
        CREATE TABLE IF NOT EXISTS policy_reminders (
            id BIGSERIAL PRIMARY KEY,
            policy_id BIGINT NOT NULL REFERENCES insurance_policies(id),
            organization_id BIGINT NOT NULL REFERENCES organizations(id),
            reminder_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
            stage INTEGER NOT NULL,
            channel VARCHAR(50) NOT NULL,
            sent_at TIMESTAMP WITHOUT TIME ZONE,
            status VARCHAR(32) NOT NULL DEFAULT 'scheduled',
            attempt_count INTEGER NOT NULL DEFAULT 0,
            last_error TEXT,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now()
        );
        """
        )
    )

    # Create `reminder_followup_link` referencing existing `insurance_leads`
    conn.execute(
        sa.text(
            """
        CREATE TABLE IF NOT EXISTS reminder_followup_link (
            reminder_id BIGINT NOT NULL REFERENCES policy_reminders(id),
            followup_id BIGINT NOT NULL REFERENCES insurance_leads(id),
            PRIMARY KEY (reminder_id, followup_id)
        );
        """
        )
    )

    # ALTER existing legacy tables to add optional columns if they don't exist
    op.execute(sa.text("ALTER TABLE insurance_policies ADD COLUMN IF NOT EXISTS policy_metadata TEXT"))
    op.execute(sa.text("ALTER TABLE insurance_policies ADD COLUMN IF NOT EXISTS currency VARCHAR(8)"))
    op.execute(sa.text("ALTER TABLE insurance_policies ADD COLUMN IF NOT EXISTS preferred_channel VARCHAR(50)"))

    op.execute(sa.text("ALTER TABLE insurance_leads ADD COLUMN IF NOT EXISTS source VARCHAR(64)"))
    op.execute(sa.text("ALTER TABLE insurance_leads ADD COLUMN IF NOT EXISTS notes TEXT"))
    op.execute(sa.text("ALTER TABLE insurance_leads ADD COLUMN IF NOT EXISTS followup_due_at TIMESTAMP WITHOUT TIME ZONE"))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DROP TABLE IF EXISTS reminder_followup_link CASCADE;"))
    conn.execute(sa.text("DROP TABLE IF EXISTS policy_reminders CASCADE;"))
