"""add policy reminder settings to insurance_policies

Revision ID: 20260611_001
Revises: 20260610_003
Create Date: 2026-06-11

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260611_001"
down_revision: Union[str, None] = "20260610_003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "insurance_policies",
        sa.Column("reminder_type", sa.String(length=32), nullable=False, server_default="default"),
    )
    op.add_column(
        "insurance_policies",
        sa.Column("reminder_unit", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "insurance_policies",
        sa.Column("reminder_value", sa.Integer(), nullable=True),
    )
    op.add_column(
        "insurance_policies",
        sa.Column("dnd_start_time", sa.String(length=8), nullable=True),
    )
    op.add_column(
        "insurance_policies",
        sa.Column("dnd_end_time", sa.String(length=8), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("insurance_policies", "dnd_end_time")
    op.drop_column("insurance_policies", "dnd_start_time")
    op.drop_column("insurance_policies", "reminder_value")
    op.drop_column("insurance_policies", "reminder_unit")
    op.drop_column("insurance_policies", "reminder_type")
