"""alter dnd time columns to TIME type

Revision ID: 20260612_001
Revises: 20260611_001
Create Date: 2026-06-12

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260612_001"
down_revision: Union[str, None] = "20260611_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "insurance_policies",
        "dnd_start_time",
        existing_type=sa.String(length=8),
        type_=sa.Time(),
        postgresql_using="dnd_start_time::time",
        existing_nullable=True,
    )
    op.alter_column(
        "insurance_policies",
        "dnd_end_time",
        existing_type=sa.String(length=8),
        type_=sa.Time(),
        postgresql_using="dnd_end_time::time",
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "insurance_policies",
        "dnd_end_time",
        existing_type=sa.Time(),
        type_=sa.String(length=8),
        postgresql_using="dnd_end_time::text",
        existing_nullable=True,
    )
    op.alter_column(
        "insurance_policies",
        "dnd_start_time",
        existing_type=sa.Time(),
        type_=sa.String(length=8),
        postgresql_using="dnd_start_time::text",
        existing_nullable=True,
    )
