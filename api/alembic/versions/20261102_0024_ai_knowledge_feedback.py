"""RAG-PORT: per-document AI use switch and answer feedback; existing documents stay enabled."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '20261102_0024'
down_revision = '20261102_0023'
branch_labels = None
depends_on = None


def json_type():
    return sa.JSON().with_variant(postgresql.JSONB(), 'postgresql')


def upgrade():
    with op.batch_alter_table('documents') as batch:
        batch.add_column(sa.Column('ai_enabled', sa.Boolean(), nullable=False, server_default=sa.true()))
    op.create_table(
        'ai_answers',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id'), nullable=False, index=True),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('dataset', sa.String(20), nullable=False),
        sa.Column('mode', sa.String(20), nullable=False),
        sa.Column('kind', sa.String(40), nullable=False),
        sa.Column('followup', sa.String(16), nullable=False),
        sa.Column('source_ids', json_type(), nullable=False),
        sa.Column('rating', sa.String(12), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.ForeignKeyConstraint(['organization_id', 'user_id'], ['users.organization_id', 'users.id']),
        sa.CheckConstraint("rating IS NULL OR rating IN ('helpful','unhelpful')", name='ck_ai_answer_rating'),
    )


def downgrade():
    connection = op.get_bind()
    if (connection.scalar(sa.text('SELECT count(*) FROM ai_answers'))
            or connection.scalar(sa.text('SELECT count(*) FROM documents WHERE NOT ai_enabled'))):
        raise RuntimeError('已有AI回饋或已停用的文件，拒絕有損降級')
    op.drop_table('ai_answers')
    with op.batch_alter_table('documents') as batch:
        batch.drop_column('ai_enabled')
