"""Add ATM-017 approval, sessions, templates, preferences

Revision ID: 20260529_002
Revises: 20260529_001
Create Date: 2026-05-29
"""

from alembic import op
import sqlalchemy as sa


revision = "20260529_002"
down_revision = "20260529_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Recover from local dev/test states where revision exists but base tables were removed.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS organizations (
            id BIGSERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL UNIQUE,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id BIGSERIAL PRIMARY KEY,
            organization_id BIGINT NOT NULL REFERENCES organizations(id),
            email VARCHAR(255) NOT NULL UNIQUE,
            hashed_password VARCHAR(255) NOT NULL,
            is_active BOOLEAN,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL
        )
        """
    )

    op.create_table(
        "organization_memberships",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("organization_id", sa.BigInteger(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "contacts",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("organization_id", sa.BigInteger(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "tasks",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("organization_id", sa.BigInteger(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("due_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "reminders",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("organization_id", sa.BigInteger(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("task_id", sa.BigInteger(), sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("dedupe_key", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("organization_id", "dedupe_key", name="uq_reminders_org_dedupe_key"),
    )

    op.create_table(
        "outbound_messages",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("organization_id", sa.BigInteger(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("task_id", sa.BigInteger(), sa.ForeignKey("tasks.id"), nullable=True),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("recipient", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "audit_events",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("organization_id", sa.BigInteger(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("actor_user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "approval_requests",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("organization_id", sa.BigInteger(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("requested_by_user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("proposed_action", sa.JSON(), nullable=False),
        sa.Column("decision_notes", sa.Text(), nullable=True),
        sa.Column("approved_by_user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("rejected_by_user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("decisioned_at", sa.DateTime(), nullable=True),
        sa.Column("executed_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "agent_sessions",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("organization_id", sa.BigInteger(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("agent_invocation_id", sa.BigInteger(), nullable=True),
        sa.Column("session_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("collected_fields", sa.JSON(), nullable=False),
        sa.Column("missing_fields", sa.JSON(), nullable=False),
        sa.Column("last_user_reply", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "message_templates",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("organization_id", sa.BigInteger(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("purpose", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("required_variables", sa.JSON(), nullable=False),
        sa.Column("provider_template_name", sa.String(length=255), nullable=True),
        sa.Column("approved_by_user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("organization_id", "name", name="uq_message_templates_org_name"),
    )

    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("organization_id", sa.BigInteger(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("contact_id", sa.BigInteger(), sa.ForeignKey("contacts.id"), nullable=True),
        sa.Column("purpose", sa.String(length=64), nullable=False),
        sa.Column("preferred_channel", sa.String(length=32), nullable=False),
        sa.Column("fallback_channel", sa.String(length=32), nullable=True),
        sa.Column("opt_out", sa.Boolean(), nullable=False),
        sa.Column("quiet_hours_start", sa.Integer(), nullable=True),
        sa.Column("quiet_hours_end", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "organization_id",
            "user_id",
            "contact_id",
            "purpose",
            name="uq_notification_preferences_target_purpose",
        ),
        sa.CheckConstraint(
            "(user_id IS NOT NULL AND contact_id IS NULL) OR (user_id IS NULL AND contact_id IS NOT NULL)",
            name="ck_notification_preferences_exactly_one_target",
        ),
        sa.CheckConstraint(
            "(quiet_hours_start IS NULL OR (quiet_hours_start >= 0 AND quiet_hours_start <= 23)) "
            "AND (quiet_hours_end IS NULL OR (quiet_hours_end >= 0 AND quiet_hours_end <= 23))",
            name="ck_notification_preferences_quiet_hours_range",
        ),
    )


def downgrade() -> None:
    op.drop_table("notification_preferences")
    op.drop_table("message_templates")
    op.drop_table("agent_sessions")
    op.drop_table("approval_requests")
    op.drop_table("audit_events")
    op.drop_table("outbound_messages")
    op.drop_table("reminders")
    op.drop_table("tasks")
    op.drop_table("contacts")
    op.drop_table("organization_memberships")
