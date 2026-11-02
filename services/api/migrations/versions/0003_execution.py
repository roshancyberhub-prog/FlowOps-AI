"""Durable execution state, approval checkpoints and dispatch intent."""

from alembic import op

revision = "0003_execution"
down_revision = "0002_workflows"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""CREATE TABLE worker_heartbeats (
	id UUID NOT NULL,
	worker_name VARCHAR(120) NOT NULL,
	last_seen TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (worker_name)
)""")
    op.execute("""CREATE TABLE workflow_executions (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	workflow_id UUID NOT NULL,
	workflow_version_id UUID NOT NULL,
	workflow_name VARCHAR(150) NOT NULL,
	version_number INTEGER NOT NULL,
	requested_by UUID NOT NULL,
	trigger_type VARCHAR(80) NOT NULL,
	status VARCHAR(30) NOT NULL,
	mode VARCHAR(20) NOT NULL,
	idempotency_key VARCHAR(200) NOT NULL,
	input_hash VARCHAR(64) NOT NULL,
	input_summary JSONB NOT NULL,
	context JSONB NOT NULL,
	current_node_id VARCHAR(64),
	node_attempt INTEGER NOT NULL,
	dispatch_generation INTEGER NOT NULL,
	manual_retry_count INTEGER NOT NULL,
	active_duration_ms INTEGER NOT NULL,
	cancel_requested BOOLEAN NOT NULL,
	lease_token UUID,
	lease_until TIMESTAMP WITH TIME ZONE,
	next_run_at TIMESTAMP WITH TIME ZONE NOT NULL,
	correlation_id VARCHAR(36) NOT NULL,
	error_code VARCHAR(80),
	error_summary VARCHAR(500),
	dead_letter BOOLEAN NOT NULL,
	started_at TIMESTAMP WITH TIME ZONE,
	completed_at TIMESTAMP WITH TIME ZONE,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_execution_idempotency UNIQUE (organization_id, idempotency_key),
	CONSTRAINT execution_status CHECK (status IN ('queued','running','waiting_for_approval',
    'retrying','succeeded','failed','cancelled')),
	FOREIGN KEY(organization_id) REFERENCES organizations (id),
	FOREIGN KEY(workflow_id) REFERENCES workflows (id),
	FOREIGN KEY(workflow_version_id) REFERENCES workflow_versions (id),
	FOREIGN KEY(requested_by) REFERENCES users (id)
)""")
    op.execute("""CREATE INDEX ix_workflow_executions_created_at
ON workflow_executions (created_at)""")
    op.execute("""CREATE INDEX ix_workflow_executions_next_run_at
ON workflow_executions (next_run_at)""")
    op.execute("""CREATE INDEX ix_workflow_executions_organization_id
ON workflow_executions (organization_id)""")
    op.execute("""CREATE INDEX ix_workflow_executions_status
ON workflow_executions (status)""")
    op.execute("""CREATE INDEX ix_workflow_executions_workflow_id
ON workflow_executions (workflow_id)""")
    op.execute("""CREATE TABLE execution_steps (
	id UUID NOT NULL,
	execution_id UUID NOT NULL,
	node_id VARCHAR(64) NOT NULL,
	node_type VARCHAR(80) NOT NULL,
	attempt_number INTEGER NOT NULL,
	status VARCHAR(30) NOT NULL,
	input_summary JSONB NOT NULL,
	output_summary JSONB NOT NULL,
	error_code VARCHAR(80),
	error_summary VARCHAR(500),
	error_frames JSONB NOT NULL,
	retryable BOOLEAN NOT NULL,
	uncertain BOOLEAN NOT NULL,
	started_at TIMESTAMP WITH TIME ZONE NOT NULL,
	completed_at TIMESTAMP WITH TIME ZONE,
	duration_ms INTEGER,
	PRIMARY KEY (id),
	UNIQUE (execution_id, node_id, attempt_number),
	FOREIGN KEY(execution_id) REFERENCES workflow_executions (id)
)""")
    op.execute("""CREATE INDEX ix_execution_steps_execution_id
ON execution_steps (execution_id)""")
    op.execute("""CREATE TABLE notifications (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	execution_id UUID NOT NULL,
	node_id VARCHAR(64) NOT NULL,
	message VARCHAR(1000) NOT NULL,
	read_at TIMESTAMP WITH TIME ZONE,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (execution_id, node_id),
	FOREIGN KEY(organization_id) REFERENCES organizations (id),
	FOREIGN KEY(execution_id) REFERENCES workflow_executions (id)
)""")
    op.execute("""CREATE INDEX ix_notifications_organization_id
ON notifications (organization_id)""")
    op.execute("""CREATE TABLE outbox_entries (
	id UUID NOT NULL,
	execution_id UUID NOT NULL,
	dispatch_key VARCHAR(100) NOT NULL,
	available_at TIMESTAMP WITH TIME ZONE NOT NULL,
	published_at TIMESTAMP WITH TIME ZONE,
	attempt_count INTEGER NOT NULL,
	last_error VARCHAR(100),
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(execution_id) REFERENCES workflow_executions (id),
	UNIQUE (dispatch_key)
)""")
    op.execute("""CREATE INDEX ix_outbox_entries_available_at
ON outbox_entries (available_at)""")
    op.execute("""CREATE INDEX ix_outbox_entries_execution_id
ON outbox_entries (execution_id)""")
    op.execute("""CREATE TABLE approval_requests (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	execution_id UUID NOT NULL,
	execution_step_id UUID NOT NULL,
	node_id VARCHAR(64) NOT NULL,
	kind VARCHAR(30) NOT NULL,
	status VARCHAR(20) NOT NULL,
	payload JSONB NOT NULL,
	payload_hash VARCHAR(64) NOT NULL,
	revision INTEGER NOT NULL,
	requested_at TIMESTAMP WITH TIME ZONE NOT NULL,
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
	decided_by UUID,
	decided_at TIMESTAMP WITH TIME ZONE,
	decision_comment VARCHAR(1000) NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (execution_id, node_id),
	FOREIGN KEY(organization_id) REFERENCES organizations (id),
	FOREIGN KEY(execution_id) REFERENCES workflow_executions (id),
	FOREIGN KEY(execution_step_id) REFERENCES execution_steps (id),
	FOREIGN KEY(decided_by) REFERENCES users (id)
)""")
    op.execute("""CREATE INDEX ix_approval_requests_execution_id
ON approval_requests (execution_id)""")
    op.execute("""CREATE INDEX ix_approval_requests_organization_id
ON approval_requests (organization_id)""")
    op.execute("""CREATE INDEX ix_approval_requests_status
ON approval_requests (status)""")


def downgrade() -> None:
    op.drop_table("approval_requests")
    op.drop_table("outbox_entries")
    op.drop_table("notifications")
    op.drop_table("execution_steps")
    op.drop_table("workflow_executions")
    op.drop_table("worker_heartbeats")
