"""TEXT2SQL-LEARNING：使用者確認過的問法候選表，以及每次回答給了哪些建議；既有回答紀錄保留。"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '20261105_0026'
down_revision = '20261104_0025'
branch_labels = None
depends_on = None

QUERY_IDS = ','.join(f"'q{i:02d}'" for i in range(1, 17))


def json_type():
    return sa.JSON().with_variant(postgresql.JSONB(), 'postgresql')


def upgrade():
    with op.batch_alter_table('ai_answers') as batch:
        batch.add_column(sa.Column('suggested_ids', json_type(), nullable=False, server_default='[]'))
    op.create_table(
        'ai_learned_phrases',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id'), nullable=False, index=True),
        sa.Column('phrase', sa.String(60), nullable=False),
        sa.Column('query_id', sa.String(3), nullable=False),
        sa.Column('status', sa.String(12), nullable=False),
        sa.Column('confirmed_by', json_type(), nullable=False),
        sa.Column('first_confirmed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_confirmed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('reviewed_by', sa.String(36), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('checks', json_type(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id', 'reviewed_by'], ['users.organization_id', 'users.id']),
        sa.UniqueConstraint('organization_id', 'phrase', 'query_id', name='uq_ai_learned_phrase'),
        sa.CheckConstraint("status IN ('pending','approved','rejected','disabled')", name='ck_ai_learned_phrase_status'),
        sa.CheckConstraint(f'query_id IN ({QUERY_IDS})', name='ck_ai_learned_phrase_query'),
    )


def downgrade():
    # 候選問法是使用者確認、管理者審核過的資料，有就拒絕；suggested_ids 只記「那次給了哪些建議」，可以丟
    if op.get_bind().scalar(sa.text('SELECT count(*) FROM ai_learned_phrases')):
        raise RuntimeError('已有使用者確認的問法，拒絕有損降級')
    op.drop_table('ai_learned_phrases')
    with op.batch_alter_table('ai_answers') as batch:
        batch.drop_column('suggested_ids')
