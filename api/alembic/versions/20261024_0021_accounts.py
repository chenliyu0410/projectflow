"""Account status, forced password change and login timestamps; existing users stay active."""
from alembic import op
import sqlalchemy as sa

revision = '20261024_0021'
down_revision = '20261024_0020'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users') as batch:
        batch.add_column(sa.Column('status', sa.String(16), nullable=False, server_default='active'))
        batch.add_column(sa.Column('must_change_password', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column('password_changed_at', sa.DateTime(timezone=True), nullable=True))
        batch.create_check_constraint('ck_users_status', "status IN ('active','disabled')")


def downgrade():
    connection = op.get_bind()
    if connection.scalar(sa.text("SELECT count(*) FROM users WHERE status != 'active' OR must_change_password OR password_changed_at IS NOT NULL")):
        raise RuntimeError('帳號已有停用或改密碼紀錄，拒絕有損降級')
    with op.batch_alter_table('users') as batch:
        batch.drop_constraint('ck_users_status', type_='check')
        batch.drop_column('password_changed_at')
        batch.drop_column('last_login_at')
        batch.drop_column('must_change_password')
        batch.drop_column('status')
