"""Preserve existing data and add same-project finish-to-start dependencies."""
from alembic import op
import sqlalchemy as sa
revision = '20261009_0004'
down_revision = '20261008_0003'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('nodes') as batch:
        batch.create_unique_constraint('uq_nodes_project_id', ['organization_id','project_id','id'])
    op.create_table('node_dependencies',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('organization_id',sa.String(36),sa.ForeignKey('organizations.id'),nullable=False),
        sa.Column('project_id',sa.String(36),nullable=False),
        sa.Column('predecessor_id',sa.String(36),nullable=False),
        sa.Column('successor_id',sa.String(36),nullable=False),
        sa.Column('created_by',sa.String(36),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        sa.ForeignKeyConstraint(['organization_id','project_id'],['projects.organization_id','projects.id']),
        sa.ForeignKeyConstraint(['organization_id','project_id','predecessor_id'],['nodes.organization_id','nodes.project_id','nodes.id']),
        sa.ForeignKeyConstraint(['organization_id','project_id','successor_id'],['nodes.organization_id','nodes.project_id','nodes.id']),
        sa.ForeignKeyConstraint(['organization_id','created_by'],['users.organization_id','users.id']),
        sa.UniqueConstraint('organization_id','project_id','predecessor_id','successor_id',name='uq_dependencies_edge'),
        sa.CheckConstraint('predecessor_id != successor_id',name='ck_dependencies_not_self'))
    op.create_index('ix_node_dependencies_organization_id','node_dependencies',['organization_id'])
    op.create_index('ix_node_dependencies_project_id','node_dependencies',['project_id'])


def downgrade():
    op.drop_table('node_dependencies')
    with op.batch_alter_table('nodes') as batch:
        batch.drop_constraint('uq_nodes_project_id',type_='unique')
