"""Add ATM-012 agent contracts persistence tables

Revision ID: 20260529_005
Revises: 20260529_004
Create Date: 2026-05-29
"""

from alembic import op
import sqlalchemy as sa


revision = "20260529_005"
down_revision = "20260529_004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_definitions",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("organization_id", sa.BigInteger(), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("agent_name", sa.String(length=100), nullable=False),
        sa.Column("domain", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("organization_id", "agent_name", name="uq_agent_definitions_org_agent"),
    )

    op.create_table(
        "agent_invocations",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("organization_id", sa.BigInteger(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("actor_user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("agent", sa.String(length=100), nullable=False),
        sa.Column("domain", sa.String(length=64), nullable=False),
        sa.Column("intent", sa.String(length=100), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("input_summary", sa.Text(), nullable=False),
        sa.Column("output_summary", sa.Text(), nullable=False),
        sa.Column("guardrail_result", sa.String(length=64), nullable=False),
        sa.Column("tool_calls", sa.JSON(), nullable=False),
        sa.Column("token_usage", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("agent_invocations")
    op.drop_table("agent_definitions")
