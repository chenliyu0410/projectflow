"""Add purchase order lines and receiving state; existing orders and movements stay untouched."""
from alembic import op
import sqlalchemy as sa
revision = '20261012_0017'
down_revision = '20261012_0016'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('purchase_orders',
        sa.Column('organization_id', sa.String(36), primary_key=True),
        sa.Column('order_id', sa.String(36), primary_key=True),
        sa.Column('revision', sa.Integer(), nullable=False),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('closed_by', sa.String(36), nullable=True),
        sa.Column('close_reason', sa.String(500), nullable=True),
        sa.Column('updated_by', sa.String(36), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id', 'order_id'], ['operations_records.organization_id', 'operations_records.id']),
        sa.ForeignKeyConstraint(['organization_id', 'updated_by'], ['users.organization_id', 'users.id']),
        sa.ForeignKeyConstraint(['organization_id', 'closed_by'], ['users.organization_id', 'users.id']),
        sa.CheckConstraint('revision > 0 AND ((closed_at IS NULL AND closed_by IS NULL AND close_reason IS NULL) OR (closed_at IS NOT NULL AND closed_by IS NOT NULL AND close_reason IS NOT NULL))', name='ck_purchase_order_state'))
    op.create_table('purchase_order_lines',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organization_id', sa.String(36), nullable=False),
        sa.Column('order_id', sa.String(36), nullable=False),
        sa.Column('resource_id', sa.String(36), nullable=False),
        sa.Column('line_no', sa.Integer(), nullable=False),
        sa.Column('unit', sa.String(20), nullable=False),
        sa.Column('ordered_milli', sa.BigInteger(), nullable=False),
        sa.Column('received_milli', sa.BigInteger(), nullable=False),
        sa.Column('note', sa.String(500), nullable=False),
        sa.Column('created_by', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('organization_id', 'order_id', 'resource_id', name='uq_purchase_line_resource'),
        sa.UniqueConstraint('organization_id', 'id', name='uq_purchase_line_org_id'),
        sa.ForeignKeyConstraint(['organization_id', 'order_id'], ['purchase_orders.organization_id', 'purchase_orders.order_id']),
        sa.ForeignKeyConstraint(['organization_id', 'resource_id'], ['operations_records.organization_id', 'operations_records.id']),
        sa.ForeignKeyConstraint(['organization_id', 'created_by'], ['users.organization_id', 'users.id']),
        sa.CheckConstraint('line_no > 0 AND ordered_milli > 0 AND ordered_milli <= 999999999999 AND received_milli >= 0 AND received_milli <= ordered_milli', name='ck_purchase_line_quantity'))
    with op.batch_alter_table('inventory_movements') as batch:
        batch.add_column(sa.Column('line_id', sa.String(36), nullable=True))
        batch.create_foreign_key('fk_inventory_line', 'purchase_order_lines', ['organization_id', 'line_id'], ['organization_id', 'id'])
        batch.create_check_constraint('ck_inventory_line', "line_id IS NULL OR kind = 'receipt'")


def downgrade():
    bind = op.get_bind()
    if bind.scalar(sa.text('SELECT count(*) FROM purchase_orders')) or bind.scalar(sa.text('SELECT count(*) FROM purchase_order_lines')) \
            or bind.scalar(sa.text('SELECT count(*) FROM inventory_movements WHERE line_id IS NOT NULL')):
        raise RuntimeError('採購明細或結案資料已存在，拒絕有損降級')
    with op.batch_alter_table('inventory_movements') as batch:
        batch.drop_constraint('ck_inventory_line', type_='check')
        batch.drop_constraint('fk_inventory_line', type_='foreignkey')
        batch.drop_column('line_id')
    op.drop_table('purchase_order_lines')
    op.drop_table('purchase_orders')
