"""Align ATM-012 agent persistence schema with current contract

Revision ID: 20260529_006
Revises: 20260529_005
Create Date: 2026-05-29
"""

from alembic import op
import sqlalchemy as sa


revision = "20260529_006"
down_revision = "20260529_005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("agent_definitions", "agent_name", new_column_name="key")
    op.add_column("agent_definitions", sa.Column("name", sa.String(length=255), nullable=True))
    op.add_column("agent_definitions", sa.Column("system_prompt", sa.Text(), nullable=True))
    op.add_column("agent_definitions", sa.Column("tool_policy", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")))
    op.add_column("agent_definitions", sa.Column("guardrail_policy", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")))
    op.add_column("agent_definitions", sa.Column("status", sa.String(length=32), nullable=False, server_default="active"))

    op.execute("UPDATE agent_definitions SET name = key WHERE name IS NULL")
    op.alter_column("agent_definitions", "name", nullable=False)

    op.drop_constraint("uq_agent_definitions_org_agent", "agent_definitions", type_="unique")
    op.create_unique_constraint("uq_agent_definitions_org_key", "agent_definitions", ["organization_id", "key"])

    op.alter_column("agent_definitions", "tool_policy", server_default=None)
    op.alter_column("agent_definitions", "guardrail_policy", server_default=None)
    op.alter_column("agent_definitions", "status", server_default=None)


def downgrade() -> None:
    op.drop_constraint("uq_agent_definitions_org_key", "agent_definitions", type_="unique")
    op.create_unique_constraint("uq_agent_definitions_org_agent", "agent_definitions", ["organization_id", "key"])

    op.drop_column("agent_definitions", "status")
    op.drop_column("agent_definitions", "guardrail_policy")
    op.drop_column("agent_definitions", "tool_policy")
    op.drop_column("agent_definitions", "system_prompt")
    op.drop_column("agent_definitions", "name")
    op.alter_column("agent_definitions", "key", new_column_name="agent_name")
