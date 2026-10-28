"""Durable bounded CSV imports, row reports and job dispatch."""

import sqlalchemy as sa
from alembic import op

revision = "0006_imports"
down_revision = "0005_scoring"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""CREATE TABLE import_jobs (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	requested_by UUID NOT NULL,
	status VARCHAR(20) NOT NULL,
	filename VARCHAR(200) NOT NULL,
	file_hash VARCHAR(64) NOT NULL,
	source_data BYTEA,
	column_mapping JSONB NOT NULL,
	idempotency_key VARCHAR(200) NOT NULL,
	input_hash VARCHAR(64) NOT NULL,
	total_rows INTEGER NOT NULL,
	processed_rows INTEGER NOT NULL,
	inserted_rows INTEGER NOT NULL,
	invalid_rows INTEGER NOT NULL,
	duplicate_rows INTEGER NOT NULL,
	dispatch_generation INTEGER NOT NULL,
	failure_count INTEGER NOT NULL,
	next_run_at TIMESTAMP WITH TIME ZONE NOT NULL,
	correlation_id VARCHAR(36) NOT NULL,
	error_code VARCHAR(80),
	error_summary VARCHAR(500),
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	started_at TIMESTAMP WITH TIME ZONE,
	completed_at TIMESTAMP WITH TIME ZONE,
	PRIMARY KEY (id),
	CONSTRAINT uq_import_idempotency UNIQUE (organization_id, idempotency_key),
	CONSTRAINT import_status CHECK (status IN ('queued','running','retrying','succeeded','failed')),
	FOREIGN KEY(organization_id) REFERENCES organizations (id),
	FOREIGN KEY(requested_by) REFERENCES users (id)
)""")
    op.execute("CREATE INDEX ix_import_jobs_next_run_at ON import_jobs (next_run_at)")
    op.execute("CREATE INDEX ix_import_jobs_organization_id ON import_jobs (organization_id)")
    op.execute("CREATE INDEX ix_import_jobs_status ON import_jobs (status)")
    op.execute("""CREATE TABLE import_rows (
	id UUID NOT NULL,
	import_job_id UUID NOT NULL,
	row_number INTEGER NOT NULL,
	status VARCHAR(20) NOT NULL,
	email VARCHAR(320),
	input_values JSONB NOT NULL,
	errors JSONB NOT NULL,
	lead_id UUID,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (import_job_id, row_number),
	FOREIGN KEY(import_job_id) REFERENCES import_jobs (id),
	FOREIGN KEY(lead_id) REFERENCES leads (id)
)""")
    op.execute("CREATE INDEX ix_import_rows_import_job_id ON import_rows (import_job_id)")
    op.alter_column("outbox_entries", "execution_id", existing_type=sa.UUID(), nullable=True)
    op.add_column("outbox_entries", sa.Column("import_job_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_outbox_import", "outbox_entries", "import_jobs", ["import_job_id"], ["id"]
    )
    op.create_index("ix_outbox_entries_import_job_id", "outbox_entries", ["import_job_id"])
    op.create_check_constraint(
        "outbox_one_target",
        "outbox_entries",
        "(execution_id IS NOT NULL AND import_job_id IS NULL) OR "
        "(execution_id IS NULL AND import_job_id IS NOT NULL)",
    )


def downgrade() -> None:
    op.execute("DELETE FROM outbox_entries WHERE import_job_id IS NOT NULL")
    op.drop_constraint("outbox_one_target", "outbox_entries", type_="check")
    op.drop_constraint("fk_outbox_import", "outbox_entries", type_="foreignkey")
    op.drop_index("ix_outbox_entries_import_job_id", "outbox_entries")
    op.drop_column("outbox_entries", "import_job_id")
    op.alter_column("outbox_entries", "execution_id", existing_type=sa.UUID(), nullable=False)
    op.drop_table("import_rows")
    op.drop_table("import_jobs")
