"""Add grace period lifecycle for insurance policies."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260702_001"
down_revision = "20260629_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            ALTER TABLE insurance_policies
            ADD COLUMN IF NOT EXISTS grace_period_days INTEGER NOT NULL DEFAULT 30
            """
        )
    )

    # Normalize lifecycle statuses:
    # - EXPIRED -> GRACE_PERIOD (if still in grace), else LAPSED
    # - ACTIVE remains ACTIVE
    op.execute(
        sa.text(
            """
            UPDATE insurance_policies
            SET status = CASE
                WHEN CURRENT_DATE <= DATE(expiry_date) + COALESCE(grace_period_days, 30) THEN 'grace_period'
                ELSE 'lapsed'
            END
            WHERE LOWER(status) = 'expired'
            """
        )
    )

    # Backfill all non-renewed/escalated rows to deterministic lifecycle state.
    op.execute(
        sa.text(
            """
            UPDATE insurance_policies
            SET status = CASE
                WHEN CURRENT_DATE <= DATE(expiry_date) THEN 'active'
                WHEN CURRENT_DATE <= DATE(expiry_date) + COALESCE(grace_period_days, 30) THEN 'grace_period'
                ELSE 'lapsed'
            END
            WHERE LOWER(status) NOT IN ('renewed', 'escalated')
            """
        )
    )


def downgrade() -> None:
    # Map new states back to legacy EXPIRED for rollback compatibility.
    op.execute(
        sa.text(
            """
            UPDATE insurance_policies
            SET status = 'expired'
            WHERE LOWER(status) IN ('grace_period', 'lapsed')
            """
        )
    )
    op.execute(sa.text("ALTER TABLE insurance_policies DROP COLUMN IF EXISTS grace_period_days"))
