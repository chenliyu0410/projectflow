"""LINE broadcast: the short text an outbox event also pushes to LINE (empty means mail only)."""
from alembic import op
import sqlalchemy as sa

revision = '20261104_0025'
down_revision = '20261102_0024'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('outbox_events') as batch:
        batch.add_column(sa.Column('line_text', sa.Text(), nullable=True))


def downgrade():
    # Only drops which events would also go to LINE; the mail itself is kept.
    with op.batch_alter_table('outbox_events') as batch:
        batch.drop_column('line_text')
