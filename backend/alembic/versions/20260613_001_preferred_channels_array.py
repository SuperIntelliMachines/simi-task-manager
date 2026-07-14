"""Convert insurance_policies.preferred_channel to PostgreSQL TEXT[]."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260613_001"
down_revision = "20260612_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'insurance_policies'
                      AND column_name = 'preferred_channels'
                ) THEN
                    ALTER TABLE insurance_policies
                    RENAME COLUMN preferred_channels TO preferred_channel;
                END IF;

                IF EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'insurance_policies'
                      AND column_name = 'preferred_channel'
                      AND udt_name = 'varchar'
                ) THEN
                    ALTER TABLE insurance_policies
                    ALTER COLUMN preferred_channel TYPE text[]
                    USING CASE
                        WHEN preferred_channel IS NULL OR preferred_channel = '' THEN NULL
                        ELSE ARRAY[preferred_channel]::text[]
                    END;
                END IF;
            END $$;
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(
        sa.text(
            """
            ALTER TABLE insurance_policies
            ALTER COLUMN preferred_channel TYPE varchar(32)
            USING CASE
                WHEN preferred_channel IS NULL OR array_length(preferred_channel, 1) IS NULL THEN NULL
                ELSE preferred_channel[1]
            END
            """
        )
    )
