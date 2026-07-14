"""
add user roles

Revision ID: 20260529_010
Revises: 20260529_009
Create Date: 2026-05-29 16:30:00
"""

from alembic import op
import sqlalchemy as sa
from app.core.enums import UserRole

# revision identifiers, used by Alembic.
revision = '20260529_010'
down_revision = '20260529_009'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('users', sa.Column('role', sa.Enum(UserRole), nullable=False, server_default=UserRole.TENANT_USER))

def downgrade():
    op.drop_column('users', 'role')