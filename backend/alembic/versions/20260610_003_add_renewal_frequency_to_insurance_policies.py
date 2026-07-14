"""add renewal_frequency to insurance_policies

Revision ID: 20260610_003
Revises: 20260610_002
Create Date: 2026-06-10

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260610_003"
down_revision: Union[str, None] = "20260610_002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "insurance_policies",
        sa.Column("renewal_frequency", sa.String(length=32), nullable=False, server_default="yearly"),
    )


def downgrade() -> None:
    op.drop_column("insurance_policies", "renewal_frequency")
