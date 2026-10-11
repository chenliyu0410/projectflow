"""Preserve operations and add project/node associations."""
from alembic import op
import sqlalchemy as sa

revision = '20261011_0014'
down_revision = '20261011_0013'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index('uq_operations_org_id', 'operations_records', ['organization_id', 'id'], unique=True)
    op.create_table('operation_links',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organization_id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('node_id', sa.String(36), nullable=True),
        sa.Column('record_id', sa.String(36), nullable=False),
        sa.Column('created_by', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id', 'record_id'], ['operations_records.organization_id', 'operations_records.id']),
        sa.ForeignKeyConstraint(['organization_id', 'project_id'], ['projects.organization_id', 'projects.id']),
        sa.ForeignKeyConstraint(['organization_id', 'project_id', 'node_id'], ['nodes.organization_id', 'nodes.project_id', 'nodes.id']),
        sa.ForeignKeyConstraint(['organization_id', 'created_by'], ['users.organization_id', 'users.id']))
    op.create_index('uq_operation_links_project', 'operation_links', ['organization_id', 'project_id', 'record_id'], unique=True,
        postgresql_where=sa.text('node_id IS NULL'), sqlite_where=sa.text('node_id IS NULL'))
    op.create_index('uq_operation_links_node', 'operation_links', ['organization_id', 'node_id', 'record_id'], unique=True,
        postgresql_where=sa.text('node_id IS NOT NULL'), sqlite_where=sa.text('node_id IS NOT NULL'))


def downgrade():
    if op.get_bind().scalar(sa.text('SELECT count(*) FROM operation_links')):
        raise RuntimeError('關聯資料已存在，拒絕有損降級')
    op.drop_table('operation_links')
    op.drop_index('uq_operations_org_id', table_name='operations_records')
