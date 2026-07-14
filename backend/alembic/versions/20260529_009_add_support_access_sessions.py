"""
add support_access_sessions table

Revision ID: 20260529_009
Revises: 20260529_008
Create Date: 2026-05-29 16:00:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260529_009'
down_revision = '20260529_008'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'support_access_sessions',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('organization_id', sa.Integer, sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('reason', sa.String, nullable=False),
        sa.Column('expiry', sa.DateTime, nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('created_by', sa.Integer, sa.ForeignKey('users.id'), nullable=False),
    )

def downgrade():
    op.drop_table('support_access_sessions')