"""Durable enqueue metadata; old queued rows remain opt-in."""
from alembic import op
import sqlalchemy as sa
revision = '20261022_0021'
down_revision = '20261021_0020'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('rag_queries') as batch:
        batch.alter_column('project_id', existing_type=sa.String(36), nullable=True)
    with op.batch_alter_table('rag_indexes') as batch:
        batch.add_column(sa.Column('requested_by_user_id', sa.String(36)))
        batch.add_column(sa.Column('requested_at', sa.DateTime(timezone=True)))
        batch.add_column(sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'))
        batch.add_column(sa.Column('next_attempt_at', sa.DateTime(timezone=True)))
        batch.create_foreign_key('fk_rag_index_requester','users',['organization_id','requested_by_user_id'],['organization_id','id'])

def downgrade():
    bind = op.get_bind()
    if bind.scalar(sa.text('SELECT count(*) FROM rag_queries WHERE project_id IS NULL')) or bind.scalar(sa.text('SELECT count(*) FROM rag_indexes WHERE requested_at IS NOT NULL OR requested_by_user_id IS NOT NULL OR attempts <> 0 OR next_attempt_at IS NOT NULL')):
        raise RuntimeError('Refusing lossy downgrade of RAG experience data')
    with op.batch_alter_table('rag_indexes') as batch:
        batch.drop_constraint('fk_rag_index_requester', type_='foreignkey')
        for name in ('requested_by_user_id','requested_at','attempts','next_attempt_at'):
            batch.drop_column(name)
    with op.batch_alter_table('rag_queries') as batch:
        batch.alter_column('project_id', existing_type=sa.String(36), nullable=False)
