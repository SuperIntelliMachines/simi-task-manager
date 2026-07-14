"""
Create core schema

Revision ID: 20260529_001
Revises: 
Create Date: 2026-05-29
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260529_001"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create core tables
    op.create_table(
        "organizations",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("organization_id", sa.BigInteger, sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )

    # Add other tables here following the same pattern.

def downgrade() -> None:
    # Drop core tables
    op.drop_table("users")
    op.drop_table("organizations")