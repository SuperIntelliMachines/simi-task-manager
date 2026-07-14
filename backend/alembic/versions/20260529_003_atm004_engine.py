"""Add ATM-004 task, workflow, reminder engine tables and columns

Revision ID: 20260529_003
Revises: 20260529_002
Create Date: 2026-05-29
"""

from alembic import op
import sqlalchemy as sa


revision = "20260529_003"
down_revision = "20260529_002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS domain VARCHAR(64) NOT NULL DEFAULT 'general'")

    op.execute("ALTER TABLE reminders ADD COLUMN IF NOT EXISTS acknowledged_at TIMESTAMP WITHOUT TIME ZONE")
    op.execute("ALTER TABLE reminders ADD COLUMN IF NOT EXISTS canceled_at TIMESTAMP WITHOUT TIME ZONE")
    op.execute("ALTER TABLE reminders ADD COLUMN IF NOT EXISTS sent_at TIMESTAMP WITHOUT TIME ZONE")

    op.execute(
        "ALTER TABLE outbound_messages ADD COLUMN IF NOT EXISTS external_provider_message_id VARCHAR(255)"
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_outbound_messages_channel_provider_message
        ON outbound_messages (channel, external_provider_message_id)
        """
    )

    op.create_table(
        "task_assignments",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("organization_id", sa.BigInteger(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("task_id", sa.BigInteger(), sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("contact_id", sa.BigInteger(), sa.ForeignKey("contacts.id"), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("assigned_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "(user_id IS NOT NULL AND contact_id IS NULL) OR (user_id IS NULL AND contact_id IS NOT NULL)",
            name="ck_task_assignments_exactly_one_recipient",
        ),
    )

    op.create_table(
        "reminder_attempts",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("organization_id", sa.BigInteger(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("reminder_id", sa.BigInteger(), sa.ForeignKey("reminders.id"), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("next_retry_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "workflow_templates",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("organization_id", sa.BigInteger(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("definition", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "workflow_runs",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("organization_id", sa.BigInteger(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("workflow_template_id", sa.BigInteger(), sa.ForeignKey("workflow_templates.id"), nullable=False),
        sa.Column("task_id", sa.BigInteger(), sa.ForeignKey("tasks.id"), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("current_step", sa.String(length=255), nullable=True),
        sa.Column("state_payload", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("workflow_runs")
    op.drop_table("workflow_templates")
    op.drop_table("reminder_attempts")
    op.drop_table("task_assignments")

    op.execute("DROP INDEX IF EXISTS uq_outbound_messages_channel_provider_message")
    op.execute("ALTER TABLE outbound_messages DROP COLUMN IF EXISTS external_provider_message_id")

    op.execute("ALTER TABLE reminders DROP COLUMN IF EXISTS sent_at")
    op.execute("ALTER TABLE reminders DROP COLUMN IF EXISTS canceled_at")
    op.execute("ALTER TABLE reminders DROP COLUMN IF EXISTS acknowledged_at")

    op.execute("ALTER TABLE tasks DROP COLUMN IF EXISTS domain")
