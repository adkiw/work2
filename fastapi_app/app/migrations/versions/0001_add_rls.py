"""Enable RLS and tenant policy on documents

Revision ID: 0001
Revises: 
Create Date: 2024-01-01 00:00:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.execute("ALTER TABLE documents ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON documents
        USING (tenant_id::text = current_setting('app.current_tenant')::text)
        """
    )

def downgrade():
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON documents")
    op.execute("ALTER TABLE documents DISABLE ROW LEVEL SECURITY")
