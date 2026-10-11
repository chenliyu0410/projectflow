"""Company operations records; existing tables and data remain intact."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '20261011_0013'
down_revision = '20261011_0012'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('operations_records',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('category', sa.String(32), nullable=False),
        sa.Column('code', sa.String(80), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('status', sa.String(80), nullable=False),
        sa.Column('visibility', sa.String(16), nullable=False),
        sa.Column('fields', sa.JSON().with_variant(postgresql.JSONB(), 'postgresql'), nullable=False),
        sa.Column('source', sa.String(32), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False),
        sa.Column('created_by', sa.String(36), nullable=False),
        sa.Column('updated_by', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('organization_id', 'category', 'code', name='uq_operations_code'),
        sa.ForeignKeyConstraint(['organization_id', 'created_by'], ['users.organization_id', 'users.id']),
        sa.ForeignKeyConstraint(['organization_id', 'updated_by'], ['users.organization_id', 'users.id']),
        sa.CheckConstraint("visibility IN ('internal','restricted') AND revision > 0", name='ck_operations_revision_visibility'))
    op.create_index('ix_operations_records_organization_id', 'operations_records', ['organization_id'])


def downgrade():
    if op.get_bind().scalar(sa.text('SELECT count(*) FROM operations_records')):
        raise RuntimeError('營運資料已存在，拒絕有損降級')
    op.drop_table('operations_records')
