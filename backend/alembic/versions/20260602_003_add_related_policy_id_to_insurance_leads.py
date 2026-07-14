"""
Add related_policy_id to insurance_leads

Revision ID: 20260602_003
Revises: 20260602_002
Create Date: 2026-06-02
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260602_003"
down_revision = "20260602_002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # add nullable related_policy_id column and FK to insurance_policies
    op.add_column("insurance_leads", sa.Column("related_policy_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        "fk_insurance_leads_related_policy_id",
        "insurance_leads",
        "insurance_policies",
        ["related_policy_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_insurance_leads_related_policy_id", "insurance_leads", type_="foreignkey")
    op.drop_column("insurance_leads", "related_policy_id")
