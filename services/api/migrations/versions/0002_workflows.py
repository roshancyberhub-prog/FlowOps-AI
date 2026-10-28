"""Versioned workflows and immutable published graphs."""

from alembic import op

revision = "0002_workflows"
down_revision = "0001_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""CREATE TABLE workflows (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	name VARCHAR(150) NOT NULL,
	description VARCHAR(1000) NOT NULL,
	status VARCHAR(20) NOT NULL,
	draft_graph JSONB NOT NULL,
	current_version_id UUID,
	version_number INTEGER NOT NULL,
	revision INTEGER NOT NULL,
	created_by UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT workflow_status CHECK (status IN ('draft','active','paused','archived')),
	FOREIGN KEY(organization_id) REFERENCES organizations (id),
	FOREIGN KEY(created_by) REFERENCES users (id)
)""")
    op.execute("""CREATE INDEX ix_workflows_organization_id
ON workflows (organization_id)""")
    op.execute("""CREATE INDEX ix_workflows_status
ON workflows (status)""")
    op.execute("""CREATE INDEX ix_workflows_updated_at
ON workflows (updated_at)""")
    op.execute("""CREATE TABLE workflow_versions (
	id UUID NOT NULL,
	workflow_id UUID NOT NULL,
	version_number INTEGER NOT NULL,
	graph_definition JSONB NOT NULL,
	created_by UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (workflow_id, version_number),
	FOREIGN KEY(workflow_id) REFERENCES workflows (id),
	FOREIGN KEY(created_by) REFERENCES users (id)
)""")
    op.execute("""CREATE INDEX ix_workflow_versions_workflow_id
ON workflow_versions (workflow_id)""")
    op.create_foreign_key(
        "fk_workflow_current_version",
        "workflows",
        "workflow_versions",
        ["current_version_id"],
        ["id"],
    )
    op.execute("""CREATE FUNCTION prevent_workflow_version_mutation() RETURNS trigger
    LANGUAGE plpgsql AS $$ BEGIN
      RAISE EXCEPTION 'Published workflow versions are immutable';
    END; $$""")
    op.execute("""CREATE TRIGGER workflow_version_immutable BEFORE UPDATE OR DELETE
    ON workflow_versions FOR EACH ROW EXECUTE FUNCTION prevent_workflow_version_mutation()""")


def downgrade() -> None:
    op.drop_constraint("fk_workflow_current_version", "workflows", type_="foreignkey")
    op.drop_table("workflow_versions")
    op.drop_table("workflows")
    op.execute("DROP FUNCTION prevent_workflow_version_mutation()")
