"""Add nullable task calendar dates without rewriting business data."""
from alembic import op
import sqlalchemy as sa

revision = "20261008_0002"
down_revision = "20261008_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("nodes") as batch:
        batch.add_column(sa.Column("start_date", sa.Date(), nullable=True))
        batch.add_column(sa.Column("due_date", sa.Date(), nullable=True))
        batch.create_check_constraint("ck_nodes_date_order", "start_date IS NULL OR due_date IS NULL OR start_date <= due_date")


def downgrade() -> None:
    with op.batch_alter_table("nodes") as batch:
        batch.drop_constraint("ck_nodes_date_order", type_="check")
        batch.drop_column("due_date")
        batch.drop_column("start_date")
