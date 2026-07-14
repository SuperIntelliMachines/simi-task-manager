"""
Merge alembic heads for insurance migration

Revision ID: 20260602_002
Revises: 20260529_010, 20260602_001
Create Date: 2026-06-02
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260602_002"
down_revision = ("20260529_010", "20260602_001")
branch_labels = None
depends_on = None


def upgrade() -> None:
    # merge-only revision; no DB operations here
    pass


def downgrade() -> None:
    # nothing to undo in merge-only revision
    pass
