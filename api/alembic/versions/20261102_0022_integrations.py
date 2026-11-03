"""N8N batch 1: user email settings, mail outbox and weekly reports; existing users keep email empty."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '20261102_0022'
down_revision = '20261024_0021'
branch_labels = None
depends_on = None


def json_type():
    return sa.JSON().with_variant(postgresql.JSONB(), 'postgresql')


def upgrade():
    with op.batch_alter_table('users') as batch:
        batch.add_column(sa.Column('email', sa.String(254), nullable=True))
        batch.add_column(sa.Column('email_notify', sa.Boolean(), nullable=False, server_default=sa.true()))
    op.create_table(
        'outbox_events',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id'), nullable=False, index=True),
        sa.Column('kind', sa.String(40), nullable=False),
        sa.Column('recipient_id', sa.String(36), nullable=False),
        sa.Column('subject', sa.String(300), nullable=False),
        sa.Column('body_text', sa.Text(), nullable=False),
        sa.Column('body_html', sa.Text(), nullable=False),
        sa.Column('dedupe_key', sa.String(200), nullable=False),
        sa.Column('status', sa.String(16), nullable=False, server_default='pending', index=True),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_error', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['organization_id', 'recipient_id'], ['users.organization_id', 'users.id']),
        sa.UniqueConstraint('organization_id', 'dedupe_key', name='uq_outbox_dedupe'),
        sa.CheckConstraint("status IN ('pending','sent','failed','skipped')", name='ck_outbox_status'),
    )
    op.create_table(
        'weekly_reports',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id'), nullable=False, index=True),
        sa.Column('project_id', sa.String(36), nullable=False, index=True),
        sa.Column('week_start', sa.Date(), nullable=False),
        sa.Column('status', sa.String(16), nullable=False),
        sa.Column('ai_sections', json_type(), nullable=False),
        sa.Column('sections', json_type(), nullable=False),
        sa.Column('facts', json_type(), nullable=False),
        sa.Column('recipient_ids', json_type(), nullable=False),
        sa.Column('excluded_count', sa.Integer(), nullable=False),
        sa.Column('model_label', sa.String(160), nullable=False),
        sa.Column('generated_by', sa.String(36), nullable=False),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('confirmed_by', sa.String(36), nullable=True),
        sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('organization_id', 'project_id', 'week_start', name='uq_weekly_report_week'),
        sa.CheckConstraint("status IN ('draft','sent','unsent')", name='ck_weekly_report_status'),
    )


def downgrade():
    connection = op.get_bind()
    if (connection.scalar(sa.text('SELECT count(*) FROM outbox_events')) or connection.scalar(sa.text('SELECT count(*) FROM weekly_reports'))
            or connection.scalar(sa.text('SELECT count(*) FROM users WHERE email IS NOT NULL OR NOT email_notify'))):
        raise RuntimeError('已有寄送或週報資料，拒絕有損降級')
    op.drop_table('weekly_reports')
    op.drop_table('outbox_events')
    with op.batch_alter_table('users') as batch:
        batch.drop_column('email_notify')
        batch.drop_column('email')
