"""Align reminder_definitions FK columns to BigInteger (organizations/users PKs)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260714_002"
down_revision = "20260714_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    # Safe if 20260714_001 already created INTEGER FKs against BIGINT PKs.
    op.alter_column(
        "reminder_definitions",
        "organization_id",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=False,
        postgresql_using="organization_id::bigint",
    )
    op.alter_column(
        "reminder_definitions",
        "created_by",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=True,
        postgresql_using="created_by::bigint",
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.alter_column(
        "reminder_definitions",
        "created_by",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=True,
        postgresql_using="created_by::integer",
    )
    op.alter_column(
        "reminder_definitions",
        "organization_id",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=False,
        postgresql_using="organization_id::integer",
    )
