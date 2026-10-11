"""Add stock balances and immutable inventory history without changing existing rows."""
from alembic import op
import sqlalchemy as sa

revision = '20261011_0015'
down_revision = '20261011_0014'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('inventory_balances',
        sa.Column('organization_id', sa.String(36), primary_key=True),
        sa.Column('resource_id', sa.String(36), primary_key=True),
        sa.Column('unit', sa.String(20), nullable=False),
        sa.Column('quantity_milli', sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(['organization_id', 'resource_id'], ['operations_records.organization_id', 'operations_records.id']),
        sa.CheckConstraint('quantity_milli >= 0 AND quantity_milli <= 999999999999', name='ck_inventory_balance_quantity'))
    op.create_table('inventory_movements',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organization_id', sa.String(36), nullable=False),
        sa.Column('request_id', sa.String(36), nullable=False),
        sa.Column('resource_id', sa.String(36), nullable=False),
        sa.Column('order_id', sa.String(36), nullable=True),
        sa.Column('kind', sa.String(16), nullable=False),
        sa.Column('unit', sa.String(20), nullable=False),
        sa.Column('delta_milli', sa.BigInteger(), nullable=False),
        sa.Column('before_milli', sa.BigInteger(), nullable=False),
        sa.Column('after_milli', sa.BigInteger(), nullable=False),
        sa.Column('resource_label', sa.String(300), nullable=False),
        sa.Column('order_label', sa.String(300), nullable=True),
        sa.Column('reason', sa.String(500), nullable=False),
        sa.Column('created_by', sa.String(36), nullable=False),
        sa.Column('actor_name', sa.String(120), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('organization_id', 'request_id', name='uq_inventory_request'),
        sa.ForeignKeyConstraint(['organization_id', 'resource_id'], ['operations_records.organization_id', 'operations_records.id']),
        sa.ForeignKeyConstraint(['organization_id', 'order_id'], ['operations_records.organization_id', 'operations_records.id']),
        sa.ForeignKeyConstraint(['organization_id', 'created_by'], ['users.organization_id', 'users.id']),
        sa.CheckConstraint("(kind = 'receipt' AND order_id IS NOT NULL AND delta_milli > 0) OR (kind = 'adjustment' AND order_id IS NULL AND delta_milli != 0)", name='ck_inventory_kind'),
        sa.CheckConstraint('before_milli >= 0 AND after_milli >= 0 AND after_milli = before_milli + delta_milli AND after_milli <= 999999999999', name='ck_inventory_movement_quantity'))
    op.create_index('ix_inventory_resource_date', 'inventory_movements', ['organization_id', 'resource_id', 'created_at'])
    op.create_index('ix_inventory_order_date', 'inventory_movements', ['organization_id', 'order_id', 'created_at'])


def downgrade():
    if op.get_bind().scalar(sa.text('SELECT count(*) FROM inventory_movements')) or op.get_bind().scalar(sa.text('SELECT count(*) FROM inventory_balances')):
        raise RuntimeError('庫存資料已存在，拒絕有損降級')
    op.drop_table('inventory_movements')
    op.drop_table('inventory_balances')
