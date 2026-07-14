"""Add ATM-005 channel framework tables

Revision ID: 20260529_004
Revises: 20260529_003
Create Date: 2026-05-29
"""

from alembic import op
import sqlalchemy as sa


revision = "20260529_004"
down_revision = "20260529_003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "channel_connections",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("organization_id", sa.BigInteger(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("provider_reference", sa.String(length=255), nullable=True),
        sa.Column("settings", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("organization_id", "channel", name="uq_channel_connections_org_channel"),
    )

    op.create_table(
        "contact_channel_identities",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("organization_id", sa.BigInteger(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("contact_id", sa.BigInteger(), sa.ForeignKey("contacts.id"), nullable=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("external_user_id", sa.String(length=255), nullable=False),
        sa.Column("external_chat_id", sa.String(length=255), nullable=True),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("is_opted_out", sa.Boolean(), nullable=False),
        sa.Column("last_inbound_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "organization_id",
            "channel",
            "external_user_id",
            name="uq_contact_channel_identity_external_user",
        ),
        sa.UniqueConstraint(
            "organization_id",
            "channel",
            "contact_id",
            name="uq_contact_channel_identity_contact_channel",
        ),
    )

    op.create_table(
        "inbound_messages",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("organization_id", sa.BigInteger(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("channel_connection_id", sa.BigInteger(), sa.ForeignKey("channel_connections.id"), nullable=True),
        sa.Column("identity_id", sa.BigInteger(), sa.ForeignKey("contact_channel_identities.id"), nullable=True),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("external_message_id", sa.String(length=255), nullable=False),
        sa.Column("external_user_id", sa.String(length=255), nullable=False),
        sa.Column("external_chat_id", sa.String(length=255), nullable=True),
        sa.Column("message_type", sa.String(length=64), nullable=False),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "channel",
            "external_message_id",
            name="uq_inbound_messages_channel_external_message",
        ),
    )


def downgrade() -> None:
    op.drop_table("inbound_messages")
    op.drop_table("contact_channel_identities")
    op.drop_table("channel_connections")
