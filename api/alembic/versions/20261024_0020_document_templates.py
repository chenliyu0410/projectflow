"""Company document templates, numbering counters and template links on generated versions; existing rows unchanged."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '20261024_0020'
down_revision = '20261012_0019'
branch_labels = None
depends_on = None

json_type = sa.JSON().with_variant(postgresql.JSONB(), 'postgresql')


def upgrade():
    op.create_table('document_templates',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organization_id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('current_version', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(16), nullable=False),
        sa.Column('created_by', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('organization_id', 'id'),
        sa.ForeignKeyConstraint(['organization_id', 'created_by'], ['users.organization_id', 'users.id']),
        sa.CheckConstraint("status IN ('active','disabled','deleted')", name='ck_document_template_status'))
    op.create_index('ix_document_templates_organization_id', 'document_templates', ['organization_id'])
    op.create_table('document_template_versions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organization_id', sa.String(36), nullable=False),
        sa.Column('template_id', sa.String(36), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(200), nullable=False),
        sa.Column('storage_key', sa.String(32), nullable=False),
        sa.Column('size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('sha256', sa.String(64), nullable=False),
        sa.Column('fields', json_type, nullable=False),
        sa.Column('numbering', sa.String(60), nullable=False),
        sa.Column('tax_rate', sa.String(10), nullable=False),
        sa.Column('rounding', sa.String(10), nullable=False),
        sa.Column('has_lines', sa.Boolean(), nullable=False),
        sa.Column('created_by', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('organization_id', 'id'),
        sa.UniqueConstraint('template_id', 'version'),
        sa.ForeignKeyConstraint(['organization_id', 'template_id'], ['document_templates.organization_id', 'document_templates.id']),
        sa.ForeignKeyConstraint(['organization_id', 'created_by'], ['users.organization_id', 'users.id']),
        sa.CheckConstraint('version > 0 AND size_bytes > 0', name='ck_document_template_version'))
    op.create_index('ix_document_template_versions_organization_id', 'document_template_versions', ['organization_id'])
    op.create_index('ix_document_template_versions_template_id', 'document_template_versions', ['template_id'])
    op.create_table('document_template_counters',
        sa.Column('organization_id', sa.String(36), primary_key=True),
        sa.Column('template_id', sa.String(36), primary_key=True),
        sa.Column('period', sa.String(8), primary_key=True),
        sa.Column('value', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['organization_id', 'template_id'], ['document_templates.organization_id', 'document_templates.id']),
        sa.CheckConstraint('value >= 0', name='ck_document_template_counter'))
    with op.batch_alter_table('document_versions') as batch:
        batch.add_column(sa.Column('template_version_id', sa.String(36), nullable=True))
        batch.add_column(sa.Column('fill_values', json_type, nullable=True))


def downgrade():
    connection = op.get_bind()
    if connection.scalar(sa.text('SELECT count(*) FROM document_templates')) or connection.scalar(
            sa.text('SELECT count(*) FROM document_versions WHERE template_version_id IS NOT NULL')):
        raise RuntimeError('文件樣板已有資料，拒絕有損降級')
    with op.batch_alter_table('document_versions') as batch:
        batch.drop_column('fill_values')
        batch.drop_column('template_version_id')
    op.drop_table('document_template_counters')
    op.drop_table('document_template_versions')
    op.drop_table('document_templates')
