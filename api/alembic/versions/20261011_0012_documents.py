"""Persistent node documents and immutable versions; no changes to existing data."""
from alembic import op
import sqlalchemy as sa

revision = '20261011_0012'
down_revision = '20261010_0011'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('documents',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organization_id', sa.String(36), nullable=False),
        sa.Column('node_id', sa.String(36), nullable=True),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('current_version', sa.Integer(), nullable=False),
        sa.UniqueConstraint('organization_id', 'id'),
        sa.ForeignKeyConstraint(['organization_id', 'node_id'], ['nodes.organization_id', 'nodes.id']),
        sa.ForeignKeyConstraint(['organization_id', 'project_id'], ['projects.organization_id', 'projects.id']))
    op.create_index('ix_documents_organization_id', 'documents', ['organization_id'])
    op.create_index('ix_documents_node_id', 'documents', ['node_id'])
    op.create_table('document_versions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organization_id', sa.String(36), nullable=False),
        sa.Column('document_id', sa.String(36), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(200), nullable=False),
        sa.Column('storage_key', sa.String(32), nullable=False, unique=True),
        sa.Column('size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('sha256', sa.String(64), nullable=False),
        sa.Column('created_by', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('comment', sa.String(500), nullable=False),
        sa.ForeignKeyConstraint(['organization_id', 'document_id'], ['documents.organization_id', 'documents.id']),
        sa.ForeignKeyConstraint(['organization_id', 'created_by'], ['users.organization_id', 'users.id']),
        sa.UniqueConstraint('document_id', 'version'),
        sa.CheckConstraint('version > 0 AND size_bytes > 0', name='ck_document_version'))
    op.create_index('ix_document_versions_organization_id', 'document_versions', ['organization_id'])
    op.create_index('ix_document_versions_document_id', 'document_versions', ['document_id'])


def downgrade():
    if op.get_bind().scalar(sa.text('SELECT count(*) FROM documents')):
        raise RuntimeError('文件已有資料，拒絕有損降級')
    op.drop_table('document_versions')
    op.drop_table('documents')
