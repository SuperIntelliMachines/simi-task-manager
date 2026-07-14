"""Add ATM-007 insurance leads table

Revision ID: 20260529_008
Revises: 20260529_007
Create Date: 2026-05-29
"""

from alembic import op
import sqlalchemy as sa


revision = "20260529_008"
down_revision = "20260529_007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "insurance_leads",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("organization_id", sa.BigInteger(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("contact_id", sa.BigInteger(), sa.ForeignKey("contacts.id"), nullable=False),
        sa.Column("assigned_agent_user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("demo_logged_at", sa.DateTime(), nullable=True),
        sa.Column("followup_due_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("insurance_leads")
