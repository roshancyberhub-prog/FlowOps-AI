"""Immutable scoring profiles and reproducible latest lead scores."""

import sqlalchemy as sa
from alembic import op

revision = "0005_scoring"
down_revision = "0004_schedules"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""CREATE TABLE scoring_profiles (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	version_number INTEGER NOT NULL,
	name VARCHAR(100) NOT NULL,
	configuration JSONB NOT NULL,
	created_by UUID,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (organization_id, version_number),
	FOREIGN KEY(organization_id) REFERENCES organizations (id),
	FOREIGN KEY(created_by) REFERENCES users (id)
)""")
    op.execute(
        "CREATE INDEX ix_scoring_profiles_organization_id ON scoring_profiles (organization_id)"
    )
    op.execute("""INSERT INTO scoring_profiles
        (id, organization_id, version_number, name, configuration, created_by, created_at)
        SELECT gen_random_uuid(), id, 1, 'Baseline ICP', '
{
  "schema_version": 1,
  "target_titles": [
    "founder",
    "ceo",
    "cto",
    "head of",
    "director"
  ],
  "target_industries": [
    "software",
    "technology",
    "saas"
  ],
  "target_company_sizes": [
    "11-50",
    "51-200",
    "201-500"
  ],
  "personal_email_domains": [
    "gmail.com",
    "yahoo.com",
    "outlook.com",
    "hotmail.com",
    "icloud.com",
    "proton.me",
    "aol.com"
  ],
  "required_fields": [
    "company",
    "job_title",
    "industry",
    "company_size"
  ],
  "title_weight": 25,
  "industry_weight": 20,
  "size_weight": 15,
  "business_email_weight": 10,
  "website_weight": 10,
  "missing_penalty": -10
}
'::jsonb, NULL, CURRENT_TIMESTAMP FROM organizations""")
    op.add_column("leads", sa.Column("score_profile_id", sa.UUID(), nullable=True))
    op.add_column("leads", sa.Column("score_profile_version", sa.Integer(), nullable=True))
    op.add_column("leads", sa.Column("scored_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        "fk_lead_score_profile", "leads", "scoring_profiles", ["score_profile_id"], ["id"]
    )
    op.execute("""CREATE FUNCTION reject_scoring_profile_mutation() RETURNS trigger AS $$
    BEGIN RAISE EXCEPTION 'Scoring profiles are immutable'; END;
    $$ LANGUAGE plpgsql""")
    op.execute("""CREATE TRIGGER scoring_profile_immutable BEFORE UPDATE OR DELETE
        ON scoring_profiles FOR EACH ROW EXECUTE FUNCTION reject_scoring_profile_mutation()""")


def downgrade() -> None:
    op.drop_constraint("fk_lead_score_profile", "leads", type_="foreignkey")
    op.drop_column("leads", "scored_at")
    op.drop_column("leads", "score_profile_version")
    op.drop_column("leads", "score_profile_id")
    op.execute("DROP TRIGGER scoring_profile_immutable ON scoring_profiles")
    op.execute("DROP FUNCTION reject_scoring_profile_mutation()")
    op.drop_table("scoring_profiles")
