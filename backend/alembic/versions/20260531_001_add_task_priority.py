"""
Add priority column to tasks

Revision ID: 20260531_001
Revises: 20260529_001
Create Date: 2026-05-31
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260531_001"
down_revision = "20260529_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("priority", sa.String(length=16), nullable=False, server_default="medium"))


def downgrade() -> None:
    op.drop_column("tasks", "priority")
