"""Add purchase returns, material returns and reversals to the stock ledger; existing movements stay untouched."""
from alembic import op
import sqlalchemy as sa
revision = '20261012_0019'
down_revision = '20261012_0018'
branch_labels = None
depends_on = None

OLD_KINDS = "(kind = 'receipt' AND order_id IS NOT NULL AND work_id IS NULL AND delta_milli > 0) OR (kind = 'adjustment' AND order_id IS NULL AND work_id IS NULL AND delta_milli != 0) OR (kind = 'issue' AND work_id IS NOT NULL AND order_id IS NULL AND delta_milli < 0) OR (kind = 'completion' AND work_id IS NOT NULL AND order_id IS NULL AND delta_milli > 0)"
NEW_KINDS = ("(kind = 'receipt' AND order_id IS NOT NULL AND work_id IS NULL AND delta_milli > 0)"
    " OR (kind = 'return' AND order_id IS NOT NULL AND work_id IS NULL AND delta_milli < 0)"
    " OR (kind = 'adjustment' AND order_id IS NULL AND work_id IS NULL AND delta_milli != 0)"
    " OR (kind = 'issue' AND work_id IS NOT NULL AND order_id IS NULL AND delta_milli < 0)"
    " OR (kind = 'issue_return' AND work_id IS NOT NULL AND order_id IS NULL AND delta_milli > 0)"
    " OR (kind = 'completion' AND work_id IS NOT NULL AND order_id IS NULL AND delta_milli > 0)"
    " OR (kind = 'reversal' AND (order_id IS NULL OR work_id IS NULL) AND delta_milli != 0)")


def upgrade():
    with op.batch_alter_table('inventory_movements') as batch:
        batch.add_column(sa.Column('reversal_of', sa.String(36), nullable=True))
        batch.create_unique_constraint('uq_inventory_org_id', ['organization_id', 'id'])
        batch.create_unique_constraint('uq_inventory_reversal', ['organization_id', 'reversal_of'])
        batch.drop_constraint('ck_inventory_kind', type_='check')
        batch.drop_constraint('ck_inventory_line', type_='check')
        batch.drop_constraint('ck_inventory_plan', type_='check')
        batch.create_check_constraint('ck_inventory_kind', NEW_KINDS)
        batch.create_check_constraint('ck_inventory_line', "line_id IS NULL OR kind IN ('receipt', 'return', 'reversal')")
        batch.create_check_constraint('ck_inventory_plan', "NOT counted_in_plan OR kind IN ('completion', 'reversal')")
        batch.create_check_constraint('ck_inventory_reversal', "(kind = 'reversal' AND reversal_of IS NOT NULL) OR (kind != 'reversal' AND reversal_of IS NULL)")
    # The self reference needs the (organization_id, id) unique constraint to exist first.
    with op.batch_alter_table('inventory_movements') as batch:
        batch.create_foreign_key('fk_inventory_reversal', 'inventory_movements', ['organization_id', 'reversal_of'], ['organization_id', 'id'])


def downgrade():
    if op.get_bind().scalar(sa.text("SELECT count(*) FROM inventory_movements WHERE kind IN ('return', 'issue_return', 'reversal')")):
        raise RuntimeError('退貨、退料或沖銷紀錄已存在，拒絕有損降級')
    with op.batch_alter_table('inventory_movements') as batch:
        batch.drop_constraint('fk_inventory_reversal', type_='foreignkey')
    with op.batch_alter_table('inventory_movements') as batch:
        batch.drop_constraint('ck_inventory_reversal', type_='check')
        batch.drop_constraint('ck_inventory_plan', type_='check')
        batch.drop_constraint('ck_inventory_line', type_='check')
        batch.drop_constraint('ck_inventory_kind', type_='check')
        batch.create_check_constraint('ck_inventory_kind', OLD_KINDS)
        batch.create_check_constraint('ck_inventory_line', "line_id IS NULL OR kind = 'receipt'")
        batch.create_check_constraint('ck_inventory_plan', "NOT counted_in_plan OR kind = 'completion'")
        batch.drop_constraint('uq_inventory_reversal', type_='unique')
        batch.drop_constraint('uq_inventory_org_id', type_='unique')
        batch.drop_column('reversal_of')
