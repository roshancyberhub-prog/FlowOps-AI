"""Initial organizations, sessions, leads and audit schema. Frozen PostgreSQL DDL."""

from alembic import op

revision = "0001_foundation"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE organizations (
	id UUID NOT NULL,
	name VARCHAR(120) NOT NULL,
	slug VARCHAR(150) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (slug)
)"""
    )
    op.execute(
        """CREATE TABLE users (
	display_name VARCHAR(100) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	id UUID NOT NULL,
	email VARCHAR(320) NOT NULL,
	hashed_password VARCHAR(1024) NOT NULL,
	is_active BOOLEAN NOT NULL,
	is_superuser BOOLEAN NOT NULL,
	is_verified BOOLEAN NOT NULL,
	PRIMARY KEY (id)
)"""
    )
    op.execute("CREATE UNIQUE INDEX ix_users_email ON users (email)")
    op.execute(
        """CREATE TABLE access_tokens (
	user_id UUID NOT NULL,
	token VARCHAR(43) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (token),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)"""
    )
    op.execute("CREATE INDEX ix_access_tokens_created_at ON access_tokens (created_at)")
    op.execute("CREATE INDEX ix_access_tokens_user_id ON access_tokens (user_id)")
    op.execute(
        """CREATE TABLE audit_logs (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	actor_user_id UUID NOT NULL,
	action VARCHAR(100) NOT NULL,
	resource_id VARCHAR(100) NOT NULL,
	correlation_id VARCHAR(36) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(organization_id) REFERENCES organizations (id),
	FOREIGN KEY(actor_user_id) REFERENCES users (id)
)"""
    )
    op.execute("CREATE INDEX ix_audit_logs_created_at ON audit_logs (created_at)")
    op.execute("CREATE INDEX ix_audit_logs_organization_id ON audit_logs (organization_id)")
    op.execute(
        """CREATE TABLE leads (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	name VARCHAR(150) NOT NULL,
	email VARCHAR(320) NOT NULL,
	company VARCHAR(200),
	job_title VARCHAR(150),
	website VARCHAR(2048),
	industry VARCHAR(100),
	company_size VARCHAR(50),
	country VARCHAR(100),
	source VARCHAR(100),
	status VARCHAR(30) NOT NULL,
	score INTEGER NOT NULL,
	score_reasons JSONB NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_lead_organization_email UNIQUE (organization_id, email),
	CONSTRAINT lead_score_range CHECK (score BETWEEN 0 AND 100),
	FOREIGN KEY(organization_id) REFERENCES organizations (id)
)"""
    )
    op.execute("CREATE INDEX ix_leads_created_at ON leads (created_at)")
    op.execute("CREATE INDEX ix_leads_organization_id ON leads (organization_id)")
    op.execute("CREATE INDEX ix_leads_status ON leads (status)")
    op.execute(
        """CREATE TABLE organization_memberships (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	user_id UUID NOT NULL,
	role VARCHAR(20) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (organization_id, user_id),
	CONSTRAINT membership_role CHECK (role IN ('owner', 'admin', 'member', 'viewer')),
	FOREIGN KEY(organization_id) REFERENCES organizations (id),
	FOREIGN KEY(user_id) REFERENCES users (id)
)"""
    )
    op.execute(
        """CREATE INDEX ix_organization_memberships_organization_id
ON organization_memberships (organization_id)"""
    )
    op.execute(
        "CREATE INDEX ix_organization_memberships_user_id ON organization_memberships (user_id)"
    )


def downgrade() -> None:
    op.drop_table("organization_memberships")
    op.drop_table("leads")
    op.drop_table("audit_logs")
    op.drop_table("access_tokens")
    op.drop_table("users")
    op.drop_table("organizations")
