"""N8N complete: outbox lease so an event pulled by n8n is not offered again for a few minutes."""
from alembic import op
import sqlalchemy as sa

revision = '20261102_0023'
down_revision = '20261102_0022'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('outbox_events') as batch:
        batch.add_column(sa.Column('claimed_at', sa.DateTime(timezone=True), nullable=True))


def downgrade():
    # Dropping the lease only allows a possible resend; no business data is lost.
    with op.batch_alter_table('outbox_events') as batch:
        batch.drop_column('claimed_at')
