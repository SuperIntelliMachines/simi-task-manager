"""add reminder_type to policy_reminders

Revision ID: 20260610_002
Revises: 20260610_001
Create Date: 2026-06-10

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260610_002"
down_revision: Union[str, None] = "20260610_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("policy_reminders", sa.Column("reminder_type", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("policy_reminders", "reminder_type")
