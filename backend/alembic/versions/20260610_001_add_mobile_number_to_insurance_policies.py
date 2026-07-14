"""Add mobile_number to insurance_policies

Revision ID: 20260610_001
Revises: 20260602_003
Create Date: 2026-06-10
"""

from alembic import op
import sqlalchemy as sa


revision = "20260610_001"
down_revision = "20260602_003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "insurance_policies",
        sa.Column("mobile_number", sa.String(length=15), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("insurance_policies", "mobile_number")
