"""Extend insurance_policies.mobile_number for optional '+' prefix.

Revision ID: 20260616_001
Revises: 20260615_001
Create Date: 2026-06-16
"""

from alembic import op
import sqlalchemy as sa

revision = "20260616_001"
down_revision = "20260615_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "insurance_policies",
        "mobile_number",
        existing_type=sa.String(length=15),
        type_=sa.String(length=20),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "insurance_policies",
        "mobile_number",
        existing_type=sa.String(length=20),
        type_=sa.String(length=15),
        existing_nullable=True,
    )
