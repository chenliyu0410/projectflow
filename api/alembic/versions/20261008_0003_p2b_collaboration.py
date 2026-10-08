"""Preserve legacy reports and add collaboration storage and constraints."""
from alembic import op
import sqlalchemy as sa

revision = "20261008_0003"
down_revision = "20261008_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("nodes") as batch:
        batch.add_column(sa.Column("collaborators_revision", sa.Integer(), server_default="0", nullable=False))
    with op.batch_alter_table("task_reports") as batch:
        batch.add_column(sa.Column("workflow_version", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("version", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("finished_on", sa.Date(), nullable=True))
        batch.add_column(sa.Column("reviewed_by", sa.String(36), nullable=True))
        batch.add_column(sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("review_comment", sa.Text(), nullable=True))
        batch.add_column(sa.Column("self_approved", sa.Boolean(), server_default=sa.text("false"), nullable=False))
        batch.create_foreign_key("fk_reports_reviewer", "users", ["organization_id","reviewed_by"], ["organization_id","id"])
        batch.create_unique_constraint("uq_reports_node_id", ["organization_id","node_id","id"])
        batch.create_unique_constraint("uq_reports_node_version", ["organization_id","node_id","version"])
        batch.create_check_constraint('ck_reports_reject_comment', "workflow_version IS NULL OR status != 'rejected' OR (review_comment IS NOT NULL AND length(trim(review_comment)) > 0)")
        batch.create_check_constraint('ck_reports_review_fields', "workflow_version IS NULL OR (status = 'submitted' AND reviewed_by IS NULL AND reviewed_at IS NULL AND self_approved = false) OR (status IN ('approved','rejected') AND reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)")
        batch.create_check_constraint('ck_reports_self_approved', "NOT self_approved OR (workflow_version IS NOT NULL AND workflow_version = 2 AND status = 'approved' AND reviewed_by = submitted_by)")
        batch.create_check_constraint('ck_reports_workflow', "workflow_version IS NULL OR (workflow_version = 2 AND version IS NOT NULL AND version > 0 AND finished_on IS NOT NULL AND result IN ('達成','部分達成','未達成') AND status IN ('submitted','approved','rejected'))")
    op.create_index("uq_reports_pending", "task_reports", ["organization_id","node_id"], unique=True,
                    sqlite_where=sa.text("workflow_version = 2 AND status = 'submitted'"),
                    postgresql_where=sa.text("workflow_version = 2 AND status = 'submitted'"))
    op.create_table('node_collaborators',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('organization_id', sa.String(length=36), nullable=False),
    sa.Column('node_id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=True),
    sa.Column('department_id', sa.String(length=36), nullable=True),
    sa.Column('created_by', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint('(user_id IS NOT NULL AND department_id IS NULL) OR (user_id IS NULL AND department_id IS NOT NULL)', name='ck_collaborator_target'),
    sa.ForeignKeyConstraint(['organization_id', 'created_by'], ['users.organization_id', 'users.id'], ),
    sa.ForeignKeyConstraint(['organization_id', 'department_id'], ['departments.organization_id', 'departments.id'], ),
    sa.ForeignKeyConstraint(['organization_id', 'node_id'], ['nodes.organization_id', 'nodes.id'], ),
    sa.ForeignKeyConstraint(['organization_id', 'user_id'], ['users.organization_id', 'users.id'], ),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('organization_id', 'node_id', 'department_id', name='uq_collaborator_department'),
    sa.UniqueConstraint('organization_id', 'node_id', 'user_id', name='uq_collaborator_user')
    )
    op.create_index(op.f('ix_node_collaborators_node_id'), 'node_collaborators', ['node_id'], unique=False)
    op.create_index(op.f('ix_node_collaborators_organization_id'), 'node_collaborators', ['organization_id'], unique=False)
    op.create_table('task_notes',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('organization_id', sa.String(length=36), nullable=False),
    sa.Column('node_id', sa.String(length=36), nullable=False),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('author_id', sa.String(length=36), nullable=False),
    sa.Column('revision', sa.Integer(), server_default='1', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('edited_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint('revision > 0', name='ck_notes_revision'),
    sa.ForeignKeyConstraint(['organization_id', 'author_id'], ['users.organization_id', 'users.id'], ),
    sa.ForeignKeyConstraint(['organization_id', 'node_id'], ['nodes.organization_id', 'nodes.id'], ),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('organization_id', 'node_id', 'id', name='uq_notes_node_id')
    )
    op.create_index(op.f('ix_task_notes_node_id'), 'task_notes', ['node_id'], unique=False)
    op.create_index(op.f('ix_task_notes_organization_id'), 'task_notes', ['organization_id'], unique=False)
    op.create_table('attachments',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('organization_id', sa.String(length=36), nullable=False),
    sa.Column('node_id', sa.String(length=36), nullable=False),
    sa.Column('uploaded_by', sa.String(length=36), nullable=False),
    sa.Column('original_name', sa.String(length=255), nullable=False),
    sa.Column('storage_key', sa.String(length=128), nullable=False),
    sa.Column('size_bytes', sa.BigInteger(), nullable=False),
    sa.Column('sha256', sa.String(length=64), nullable=True),
    sa.Column('state', sa.String(length=16), server_default='pending', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by', sa.String(length=36), nullable=True),
    sa.Column('report_id', sa.String(length=36), nullable=True),
    sa.Column('note_id', sa.String(length=36), nullable=True),
    sa.CheckConstraint("state != 'ready' OR (sha256 IS NOT NULL AND length(sha256) = 64)", name='ck_attachments_ready_hash'),
    sa.CheckConstraint("state IN ('pending','ready','failed')", name='ck_attachments_state'),
    sa.CheckConstraint('report_id IS NULL OR note_id IS NULL', name='ck_attachments_target'),
    sa.CheckConstraint('size_bytes >= 0', name='ck_attachments_size'),
    sa.ForeignKeyConstraint(['organization_id', 'deleted_by'], ['users.organization_id', 'users.id'], ),
    sa.ForeignKeyConstraint(['organization_id', 'node_id', 'note_id'], ['task_notes.organization_id', 'task_notes.node_id', 'task_notes.id'], ),
    sa.ForeignKeyConstraint(['organization_id', 'node_id', 'report_id'], ['task_reports.organization_id', 'task_reports.node_id', 'task_reports.id'], ),
    sa.ForeignKeyConstraint(['organization_id', 'node_id'], ['nodes.organization_id', 'nodes.id'], ),
    sa.ForeignKeyConstraint(['organization_id', 'uploaded_by'], ['users.organization_id', 'users.id'], ),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('storage_key')
    )
    op.create_index(op.f('ix_attachments_node_id'), 'attachments', ['node_id'], unique=False)
    op.create_index(op.f('ix_attachments_organization_id'), 'attachments', ['organization_id'], unique=False)
    op.create_table('attachment_quotas',
    sa.Column('organization_id', sa.String(length=36), nullable=False),
    sa.Column('charged_bytes', sa.BigInteger(), server_default='0', nullable=False),
    sa.CheckConstraint('charged_bytes >= 0', name='ck_quota_nonnegative'),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
    sa.PrimaryKeyConstraint('organization_id')
    )
    op.execute("INSERT INTO attachment_quotas (organization_id, charged_bytes) SELECT id, 0 FROM organizations")


def downgrade() -> None:
    for table in ("attachments", "attachment_quotas", "task_notes", "node_collaborators"):
        op.drop_table(table)
    op.drop_index("uq_reports_pending", table_name="task_reports")
    with op.batch_alter_table("task_reports") as batch:
        batch.drop_constraint("fk_reports_reviewer", type_="foreignkey")
        batch.drop_constraint("uq_reports_node_id", type_="unique")
        batch.drop_constraint("uq_reports_node_version", type_="unique")
        for name in ("ck_reports_workflow", "ck_reports_review_fields", "ck_reports_reject_comment", "ck_reports_self_approved"):
            batch.drop_constraint(name, type_="check")
        for column in ("self_approved", "review_comment", "reviewed_at", "reviewed_by", "finished_on", "version", "workflow_version"):
            batch.drop_column(column)
    with op.batch_alter_table("nodes") as batch:
        batch.drop_column("collaborators_revision")
