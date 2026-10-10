"""Add collaboration evidence and personal notifications without rewriting existing rows."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
revision = '20261010_0010'
down_revision = '20261010_0009'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('collaboration_requests',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organization_id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('node_id', sa.String(36), nullable=False),
        sa.Column('kind', sa.String(32), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('requested_by', sa.String(36), nullable=False),
        sa.Column('status', sa.String(16), nullable=False),
        sa.Column('evidence', sa.JSON().with_variant(JSONB(), 'postgresql'), nullable=False),
        sa.Column('snapshot', sa.JSON().with_variant(JSONB(), 'postgresql'), nullable=False),
        sa.Column('decided_by', sa.String(36)), sa.Column('comment', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('decided_at', sa.DateTime(timezone=True)), sa.Column('restored_at', sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(['organization_id','project_id','node_id'], ['nodes.organization_id','nodes.project_id','nodes.id']),
        sa.ForeignKeyConstraint(['organization_id','requested_by'], ['users.organization_id','users.id']),
        sa.ForeignKeyConstraint(['organization_id','decided_by'], ['users.organization_id','users.id']),
        sa.CheckConstraint("status IN ('pending','approved','rejected','expired')", name='ck_collaboration_status'))
    op.create_index('ix_collaboration_requests_organization_id', 'collaboration_requests', ['organization_id'])
    op.create_index('uq_collaboration_pending', 'collaboration_requests', ['organization_id','node_id','kind'], unique=True, postgresql_where=sa.text("status = 'pending'"), sqlite_where=sa.text("status = 'pending'"))
    op.create_table('notifications',
        sa.Column('id', sa.String(36), primary_key=True), sa.Column('organization_id', sa.String(36), nullable=False),
        sa.Column('recipient_id', sa.String(36), nullable=False), sa.Column('node_id', sa.String(36), nullable=False),
        sa.Column('event_key', sa.String(160), nullable=False), sa.Column('message', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False), sa.Column('read_at', sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(['organization_id','recipient_id'], ['users.organization_id','users.id']),
        sa.ForeignKeyConstraint(['organization_id','node_id'], ['nodes.organization_id','nodes.id']),
        sa.UniqueConstraint('organization_id','recipient_id','event_key', name='uq_notification_event'))
    op.create_index('ix_notifications_organization_id', 'notifications', ['organization_id'])
    op.create_index('ix_notifications_recipient_id', 'notifications', ['recipient_id'])

def downgrade():
    bind = op.get_bind()
    for name in ('collaboration_requests', 'notifications'):
        if bind.execute(sa.text('SELECT 1 FROM ' + name + ' LIMIT 1')).first():
            raise RuntimeError('collaboration evidence exists; refusing lossy downgrade')
    op.drop_table('notifications')
    op.drop_table('collaboration_requests')
