"""Add derived RAG indexes without rewriting original documents."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '20261021_0020'
down_revision = '20261012_0019'
branch_labels = None
depends_on = None

J = sa.JSON().with_variant(postgresql.JSONB(), 'postgresql')


def upgrade():
    op.create_table('rag_settings',
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id'), primary_key=True),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('base_url', sa.String(200), nullable=False),
        sa.Column('model', sa.String(120), nullable=False),
        sa.Column('embedding_model', sa.String(120), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False))
    op.create_table('rag_indexes',
        sa.Column('document_id', sa.String(36), primary_key=True),
        sa.Column('organization_id', sa.String(36), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('state', sa.String(16), nullable=False),
        sa.Column('indexed_version', sa.Integer()),
        sa.Column('generation', sa.String(36)),
        sa.Column('fingerprint', sa.String(64)),
        sa.Column('embedding_key', sa.String(64)),
        sa.Column('chunk_count', sa.Integer(), nullable=False),
        sa.Column('error_code', sa.String(40)),
        sa.Column('claim', sa.String(36)),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id','document_id'], ['documents.organization_id','documents.id']),
        sa.CheckConstraint("state IN ('queued','processing','ready','failed','unsupported')", name='ck_rag_index_state'))
    op.create_index('ix_rag_indexes_organization_id', 'rag_indexes', ['organization_id'])
    op.create_table('rag_chunks',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organization_id', sa.String(36), nullable=False),
        sa.Column('document_id', sa.String(36), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('generation', sa.String(36), nullable=False),
        sa.Column('sha256', sa.String(64), nullable=False),
        sa.Column('parent_id', sa.String(120), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('parent_text', sa.Text(), nullable=False),
        sa.Column('locator', J, nullable=False),
        sa.Column('embedding', J),
        sa.ForeignKeyConstraint(['organization_id','document_id'], ['documents.organization_id','documents.id']),
        sa.ForeignKeyConstraint(['document_id','version'], ['document_versions.document_id','document_versions.version']))
    for field in ('organization_id', 'document_id', 'generation'):
        op.create_index('ix_rag_chunks_' + field, 'rag_chunks', [field])
    op.create_table('rag_queries',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organization_id', sa.String(36), nullable=False),
        sa.Column('actor_user_id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('source_ids', J, nullable=False),
        sa.Column('trace', J, nullable=False),
        sa.Column('rating', sa.String(12)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id','actor_user_id'], ['users.organization_id','users.id']),
        sa.ForeignKeyConstraint(['organization_id','project_id'], ['projects.organization_id','projects.id']),
        sa.CheckConstraint("rating IS NULL OR rating IN ('helpful','unhelpful')", name='ck_rag_rating'))
    op.create_index('ix_rag_queries_organization_id', 'rag_queries', ['organization_id'])


def downgrade():
    bind = op.get_bind()
    for table in ('rag_queries', 'rag_chunks', 'rag_indexes', 'rag_settings'):
        if bind.scalar(sa.text(f'SELECT count(*) FROM {table}')):
            raise RuntimeError('拒絕有損降級：RAG 資料仍存在')
    for table in ('rag_queries', 'rag_chunks', 'rag_indexes', 'rag_settings'):
        op.drop_table(table)
