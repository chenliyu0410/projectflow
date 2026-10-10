"""Custom report definitions and historical snapshots; existing values stay intact."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '20261010_0011'
down_revision = '20261010_0010'
branch_labels = None
depends_on = None


def upgrade():
    json_type = sa.JSON().with_variant(postgresql.JSONB(), 'postgresql')
    op.add_column('nodes', sa.Column('report_fields', json_type, nullable=False, server_default='[]'))
    op.add_column('nodes', sa.Column('report_fields_version', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('task_reports', sa.Column('fields', json_type, nullable=False, server_default='[]'))


def downgrade():
    connection = op.get_bind()
    if connection.scalar(sa.text("SELECT count(*) FROM nodes WHERE report_fields_version > 0")) or connection.scalar(sa.text("SELECT count(*) FROM task_reports WHERE CAST(fields AS TEXT) != '[]'")):
        raise RuntimeError('回報欄位已有資料，拒絕有損降級')
    op.drop_column('task_reports', 'fields')
    op.drop_column('nodes', 'report_fields_version')
    op.drop_column('nodes', 'report_fields')
