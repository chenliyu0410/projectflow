"""Add work order production plans and plan-counted completions; existing work records and movements stay untouched."""
from alembic import op
import sqlalchemy as sa
revision = '20261012_0018'
down_revision = '20261012_0017'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('work_orders',
        sa.Column('organization_id', sa.String(36), primary_key=True),
        sa.Column('work_id', sa.String(36), primary_key=True),
        sa.Column('product_id', sa.String(36), nullable=True),
        sa.Column('unit', sa.String(20), nullable=True),
        sa.Column('planned_milli', sa.BigInteger(), nullable=True),
        sa.Column('completed_milli', sa.BigInteger(), nullable=False),
        sa.Column('note', sa.String(500), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('closed_by', sa.String(36), nullable=True),
        sa.Column('close_reason', sa.String(500), nullable=True),
        sa.Column('updated_by', sa.String(36), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id', 'work_id'], ['operations_records.organization_id', 'operations_records.id']),
        sa.ForeignKeyConstraint(['organization_id', 'product_id'], ['operations_records.organization_id', 'operations_records.id'], name='fk_work_order_product'),
        sa.ForeignKeyConstraint(['organization_id', 'updated_by'], ['users.organization_id', 'users.id']),
        sa.ForeignKeyConstraint(['organization_id', 'closed_by'], ['users.organization_id', 'users.id']),
        sa.CheckConstraint('revision > 0 AND ((closed_at IS NULL AND closed_by IS NULL AND close_reason IS NULL) OR (closed_at IS NOT NULL AND closed_by IS NOT NULL AND close_reason IS NOT NULL))', name='ck_work_order_state'),
        sa.CheckConstraint('(product_id IS NULL AND unit IS NULL AND planned_milli IS NULL AND completed_milli = 0) OR (product_id IS NOT NULL AND unit IS NOT NULL AND planned_milli > 0 AND planned_milli <= 999999999999 AND completed_milli >= 0 AND completed_milli <= planned_milli)', name='ck_work_order_plan'))
    with op.batch_alter_table('inventory_movements') as batch:
        batch.add_column(sa.Column('counted_in_plan', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.create_check_constraint('ck_inventory_plan', "NOT counted_in_plan OR kind = 'completion'")


def downgrade():
    bind = op.get_bind()
    if bind.scalar(sa.text('SELECT count(*) FROM work_orders')) or bind.scalar(sa.text('SELECT count(*) FROM inventory_movements WHERE counted_in_plan')):
        raise RuntimeError('工單計畫或結案資料已存在，拒絕有損降級')
    with op.batch_alter_table('inventory_movements') as batch:
        batch.drop_constraint('ck_inventory_plan', type_='check')
        batch.drop_column('counted_in_plan')
    op.drop_table('work_orders')
