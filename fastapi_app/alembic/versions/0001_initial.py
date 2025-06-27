"""create initial tables

Revision ID: 0001_initial
Revises: 
Create Date: 2024-01-01 00:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(), nullable=False, unique=True),
    )
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(), nullable=False, unique=True),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('full_name', sa.String()),
    )
    op.create_table(
        'roles',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(), nullable=False, unique=True),
    )
    op.create_table(
        'user_tenants',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), primary_key=True, nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), primary_key=True, nullable=False),
        sa.Column('role_id', sa.Integer(), sa.ForeignKey('roles.id')),
    )
    op.create_table(
        'tenant_collaborations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_a_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id')),
        sa.Column('tenant_b_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id')),
    )
    op.create_table(
        'documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id')),
        sa.Column('content', sa.String(), nullable=False),
    )

def downgrade() -> None:
    op.drop_table('documents')
    op.drop_table('tenant_collaborations')
    op.drop_table('user_tenants')
    op.drop_table('roles')
    op.drop_table('users')
    op.drop_table('tenants')
