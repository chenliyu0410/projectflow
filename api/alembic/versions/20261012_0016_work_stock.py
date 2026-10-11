"""Extend inventory ledger with work order sources, preserving old movements."""
from alembic import op
import sqlalchemy as sa
revision = '20261012_0016'
down_revision = '20261011_0015'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('inventory_movements') as batch:
        batch.add_column(sa.Column('work_id', sa.String(36), nullable=True))
        batch.add_column(sa.Column('work_label', sa.String(300), nullable=True))
        batch.create_foreign_key('fk_inventory_work', 'operations_records', ['organization_id', 'work_id'], ['organization_id', 'id'])
        batch.drop_constraint('ck_inventory_kind', type_='check')
        batch.create_check_constraint('ck_inventory_kind', "(kind = 'receipt' AND order_id IS NOT NULL AND work_id IS NULL AND delta_milli > 0) OR (kind = 'adjustment' AND order_id IS NULL AND work_id IS NULL AND delta_milli != 0) OR (kind = 'issue' AND work_id IS NOT NULL AND order_id IS NULL AND delta_milli < 0) OR (kind = 'completion' AND work_id IS NOT NULL AND order_id IS NULL AND delta_milli > 0)")


def downgrade():
    if op.get_bind().scalar(sa.text("SELECT count(*) FROM inventory_movements WHERE work_id IS NOT NULL")):
        raise RuntimeError('工單異動已存在，拒絕有損降級')
    with op.batch_alter_table('inventory_movements') as batch:
        batch.drop_constraint('ck_inventory_kind', type_='check')
        batch.drop_constraint('fk_inventory_work', type_='foreignkey')
        batch.drop_column('work_id')
        batch.drop_column('work_label')
        batch.create_check_constraint('ck_inventory_kind', "(kind = 'receipt' AND order_id IS NOT NULL AND delta_milli > 0) OR (kind = 'adjustment' AND order_id IS NULL AND delta_milli != 0)")
