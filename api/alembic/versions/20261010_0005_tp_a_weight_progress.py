"""Preserve existing nodes and add rollup weight and manual progress."""
from alembic import op
import sqlalchemy as sa
revision = '20261010_0005'
down_revision = '20261009_0004'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('nodes') as batch:
        batch.add_column(sa.Column('weight', sa.Integer(), server_default='1', nullable=False))
        batch.add_column(sa.Column('progress', sa.Integer(), nullable=True))
        batch.create_check_constraint('ck_nodes_weight_range', 'weight >= 0 AND weight <= 100')
        batch.create_check_constraint('ck_nodes_progress_range', 'progress IS NULL OR (progress >= 0 AND progress <= 100)')


def downgrade():
    with op.batch_alter_table('nodes') as batch:
        batch.drop_constraint('ck_nodes_progress_range', type_='check')
        batch.drop_constraint('ck_nodes_weight_range', type_='check')
        batch.drop_column('progress')
        batch.drop_column('weight')
