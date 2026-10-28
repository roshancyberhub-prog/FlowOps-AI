"""Persist the next due interval for published scheduled workflows."""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workflows", sa.Column("scheduled_next_run_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_index("ix_workflows_scheduled_next_run_at", "workflows", ["scheduled_next_run_at"])


def downgrade() -> None:
    op.drop_index("ix_workflows_scheduled_next_run_at", "workflows")
    op.drop_column("workflows", "scheduled_next_run_at")
