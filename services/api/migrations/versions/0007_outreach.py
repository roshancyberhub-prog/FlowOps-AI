"""Structured draft records and approval-bound delivery receipts."""

from alembic import op

revision = "0007_outreach"
down_revision = "0006_imports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""CREATE TABLE email_drafts (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	lead_id UUID,
	execution_id UUID NOT NULL,
	node_id VARCHAR(64) NOT NULL,
	recipient VARCHAR(320) NOT NULL,
	subject VARCHAR(160) NOT NULL,
	body VARCHAR(4000) NOT NULL,
	qualification JSONB NOT NULL,
	provided_facts JSONB NOT NULL,
	ai_metadata JSONB NOT NULL,
	revision INTEGER NOT NULL,
	status VARCHAR(30) NOT NULL,
	last_edited_by UUID,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (execution_id, node_id),
	FOREIGN KEY(organization_id) REFERENCES organizations (id),
	FOREIGN KEY(lead_id) REFERENCES leads (id),
	FOREIGN KEY(execution_id) REFERENCES workflow_executions (id),
	FOREIGN KEY(last_edited_by) REFERENCES users (id)
)""")
    op.execute("CREATE INDEX ix_email_drafts_execution_id ON email_drafts (execution_id)")
    op.execute("CREATE INDEX ix_email_drafts_lead_id ON email_drafts (lead_id)")
    op.execute("CREATE INDEX ix_email_drafts_organization_id ON email_drafts (organization_id)")
    op.execute("""CREATE TABLE email_deliveries (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	execution_id UUID NOT NULL,
	node_id VARCHAR(64) NOT NULL,
	draft_id UUID NOT NULL,
	approval_id UUID NOT NULL,
	recipient VARCHAR(320) NOT NULL,
	idempotency_key VARCHAR(150) NOT NULL,
	payload_hash VARCHAR(64) NOT NULL,
	provider VARCHAR(30) NOT NULL,
	provider_message_id VARCHAR(120) NOT NULL,
	status VARCHAR(30) NOT NULL,
	delivery_metadata JSONB NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (execution_id, node_id),
	FOREIGN KEY(organization_id) REFERENCES organizations (id),
	FOREIGN KEY(execution_id) REFERENCES workflow_executions (id),
	FOREIGN KEY(draft_id) REFERENCES email_drafts (id),
	FOREIGN KEY(approval_id) REFERENCES approval_requests (id),
	UNIQUE (idempotency_key)
)""")
    op.execute("CREATE INDEX ix_email_deliveries_execution_id ON email_deliveries (execution_id)")
    op.execute(
        "CREATE INDEX ix_email_deliveries_organization_id ON email_deliveries (organization_id)"
    )


def downgrade() -> None:
    op.drop_table("email_deliveries")
    op.drop_table("email_drafts")
