"""Advanced dependency settings and manually confirmed conditions."""
from alembic import op
import sqlalchemy as sa

revision = '20261010_0008'
down_revision = '20261010_0007'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('node_dependencies') as batch:
        batch.add_column(sa.Column('relation_type', sa.String(2), nullable=False, server_default='FS'))
        batch.add_column(sa.Column('lag_days', sa.Integer(), nullable=False, server_default='0'))
        batch.add_column(sa.Column('enforcement', sa.String(4), nullable=False, server_default='hard'))
        batch.create_check_constraint('ck_dependency_type', "relation_type IN ('FS', 'SS', 'FF')")
        batch.create_check_constraint('ck_dependency_lag', 'lag_days BETWEEN -365 AND 365')
        batch.create_check_constraint('ck_dependency_enforcement', "enforcement IN ('hard', 'soft')")
    op.create_table('node_conditions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organization_id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('node_id', sa.String(36), nullable=False),
        sa.Column('label', sa.String(200), nullable=False),
        sa.Column('enforcement', sa.String(4), nullable=False, server_default='hard'),
        sa.Column('is_met', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('confirmed_by', sa.String(36)),
        sa.Column('confirmed_at', sa.DateTime(timezone=True)),
        sa.Column('reason', sa.String(1000)),
        sa.Column('created_by', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id', 'project_id', 'node_id'], ['nodes.organization_id', 'nodes.project_id', 'nodes.id']),
        sa.ForeignKeyConstraint(['organization_id', 'created_by'], ['users.organization_id', 'users.id']),
        sa.ForeignKeyConstraint(['organization_id', 'confirmed_by'], ['users.organization_id', 'users.id']),
        sa.CheckConstraint("enforcement IN ('hard', 'soft')", name='ck_condition_enforcement'))
    op.create_index('ix_node_conditions_organization_id', 'node_conditions', ['organization_id'])


def downgrade():
    connection = op.get_bind()
    if connection.execute(sa.text('SELECT 1 FROM node_conditions LIMIT 1')).first() or connection.execute(sa.text("SELECT 1 FROM node_dependencies WHERE relation_type != 'FS' OR lag_days != 0 OR enforcement != 'hard' LIMIT 1")).first():
        raise RuntimeError('advanced dependency data exists; refusing to downgrade 20261010_0008')
    op.drop_table('node_conditions')
    with op.batch_alter_table('node_dependencies') as batch:
        for name in ('ck_dependency_type', 'ck_dependency_lag', 'ck_dependency_enforcement'):
            batch.drop_constraint(name, type_='check')
        for name in ('relation_type', 'lag_days', 'enforcement'):
            batch.drop_column(name)
