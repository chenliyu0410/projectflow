"""Add milestone and schedule locking without changing existing node values."""
from alembic import op
import sqlalchemy as sa

revision = '20261010_0007'
down_revision = '20261010_0006'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('nodes') as batch:
        batch.add_column(sa.Column('milestone', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column('schedule_locked', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.create_check_constraint('ck_nodes_milestone', "NOT milestone OR (kind = 'task' AND start_date IS NOT NULL AND due_date IS NOT NULL AND start_date = due_date)")
        batch.create_check_constraint('ck_nodes_schedule_locked', 'NOT schedule_locked OR milestone')


def downgrade():
    if op.get_bind().execute(sa.text('SELECT 1 FROM nodes WHERE milestone OR schedule_locked LIMIT 1')).first():
        raise RuntimeError('milestone data exists; refusing to downgrade 20261010_0007')
    with op.batch_alter_table('nodes') as batch:
        batch.drop_constraint('ck_nodes_schedule_locked', type_='check')
        batch.drop_constraint('ck_nodes_milestone', type_='check')
        batch.drop_column('schedule_locked')
        batch.drop_column('milestone')
