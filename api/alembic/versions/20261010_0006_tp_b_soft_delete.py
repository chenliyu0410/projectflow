"""Preserve existing nodes and add soft-delete markers for tree editing."""
from alembic import op
import sqlalchemy as sa
revision = '20261010_0006'
down_revision = '20261010_0005'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('nodes') as batch:
        batch.add_column(sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column('deleted_by', sa.String(36), nullable=True))
        batch.create_foreign_key('fk_nodes_deleted_by', 'users', ['organization_id', 'deleted_by'], ['organization_id', 'id'])


def downgrade():
    # Dropping the markers would bring deleted nodes back into every view.
    if op.get_bind().execute(sa.text('SELECT 1 FROM nodes WHERE deleted_at IS NOT NULL LIMIT 1')).first() is not None:
        raise RuntimeError('nodes contain soft-deleted rows; refusing to downgrade 20261010_0006')
    with op.batch_alter_table('nodes') as batch:
        batch.drop_constraint('fk_nodes_deleted_by', type_='foreignkey')
        batch.drop_column('deleted_by')
        batch.drop_column('deleted_at')
