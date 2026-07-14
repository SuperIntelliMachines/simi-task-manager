"""Add ATM-014 insurance policies table

Revision ID: 20260529_007
Revises: 20260529_006
Create Date: 2026-05-29
"""

from alembic import op
import sqlalchemy as sa


revision = "20260529_007"
down_revision = "20260529_006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "insurance_policies",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("organization_id", sa.BigInteger(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("policyholder_id", sa.BigInteger(), sa.ForeignKey("contacts.id"), nullable=False),
        sa.Column("policy_number", sa.String(length=50), nullable=False),
        sa.Column("premium", sa.BigInteger(), nullable=False),
        sa.Column("policy_type", sa.String(length=100), nullable=True),
        sa.Column("carrier", sa.String(length=100), nullable=True),
        sa.Column("assigned_agent_user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("preferred_channel", sa.String(length=32), nullable=True),
        sa.Column("expiry_date", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("policy_number", name="uq_insurance_policies_policy_number"),
    )


def downgrade() -> None:
    op.drop_table("insurance_policies")
