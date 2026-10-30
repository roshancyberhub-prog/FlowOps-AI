"""Integration settings, signed ingress deduplication and durable outbound attempts."""

from alembic import op

revision = "0008_integrations"
down_revision = "0007_outreach"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE integrations (
	id UUID NOT NULL, 
	organization_id UUID NOT NULL, 
	created_by UUID NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	provider VARCHAR(30) NOT NULL, 
	configuration JSONB NOT NULL, 
	enabled BOOLEAN NOT NULL, 
	revision INTEGER NOT NULL, 
	last_test_status VARCHAR(30) NOT NULL, 
	last_test_at TIMESTAMP WITH TIME ZONE, 
	last_error VARCHAR(80), 
	last_result JSONB NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	FOREIGN KEY(created_by) REFERENCES users (id)
)"""
    )
    op.execute("CREATE INDEX ix_integrations_organization_id ON integrations (organization_id)")
    op.execute(
        """CREATE TABLE webhook_events (
	id UUID NOT NULL, 
	organization_id UUID NOT NULL, 
	integration_id UUID NOT NULL, 
	external_id VARCHAR(100) NOT NULL, 
	body_hash VARCHAR(64) NOT NULL, 
	lead_id UUID NOT NULL, 
	execution_id UUID, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (integration_id, external_id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	FOREIGN KEY(integration_id) REFERENCES integrations (id), 
	FOREIGN KEY(lead_id) REFERENCES leads (id), 
	FOREIGN KEY(execution_id) REFERENCES workflow_executions (id)
)"""
    )
    op.execute("CREATE INDEX ix_webhook_events_integration_id ON webhook_events (integration_id)")
    op.execute("CREATE INDEX ix_webhook_events_organization_id ON webhook_events (organization_id)")
    op.execute(
        """CREATE TABLE webhook_deliveries (
	id UUID NOT NULL, 
	organization_id UUID NOT NULL, 
	integration_id UUID NOT NULL, 
	requested_by UUID NOT NULL, 
	idempotency_key VARCHAR(200) NOT NULL, 
	input_hash VARCHAR(64) NOT NULL, 
	payload JSONB NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	attempt_count INTEGER NOT NULL, 
	next_run_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	lease_token UUID, 
	lease_until TIMESTAMP WITH TIME ZONE, 
	error_code VARCHAR(80), 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (integration_id, idempotency_key), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	FOREIGN KEY(integration_id) REFERENCES integrations (id), 
	FOREIGN KEY(requested_by) REFERENCES users (id)
)"""
    )
    op.execute(
        "CREATE INDEX ix_webhook_deliveries_integration_id ON webhook_deliveries (integration_id)"
    )
    op.execute("CREATE INDEX ix_webhook_deliveries_next_run_at ON webhook_deliveries (next_run_at)")
    op.execute(
        "CREATE INDEX ix_webhook_deliveries_organization_id ON webhook_deliveries (organization_id)"
    )
    op.execute("CREATE INDEX ix_webhook_deliveries_status ON webhook_deliveries (status)")
    op.execute(
        """CREATE TABLE webhook_attempts (
	id UUID NOT NULL, 
	delivery_id UUID NOT NULL, 
	number INTEGER NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	http_status INTEGER, 
	error_code VARCHAR(80), 
	uncertain BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (delivery_id, number), 
	FOREIGN KEY(delivery_id) REFERENCES webhook_deliveries (id)
)"""
    )
    op.execute("CREATE INDEX ix_webhook_attempts_delivery_id ON webhook_attempts (delivery_id)")


def downgrade() -> None:
    op.drop_table("webhook_attempts")
    op.drop_table("webhook_deliveries")
    op.drop_table("webhook_events")
    op.drop_table("integrations")
