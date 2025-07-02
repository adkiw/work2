"""add audit log table

Revision ID: 0002_add_audit_log
Revises: 0001_initial
Create Date: 2025-07-02 20:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0002_add_audit_log'
down_revision = '0001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('table_name', sa.String(), nullable=False),
        sa.Column('record_id', sa.String()),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('details', sa.String()),
    )


def downgrade() -> None:
    op.drop_table('audit_logs')
